import logging
import voluptuous as vol
from datetime import datetime, timedelta

import json
import asyncio
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.const import CONF_EXCLUDE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, device_registry as dr, entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN, CONF_EXCLUDED_DEVICES, CONF_EXCLUDED_ENTITIES, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_EXCLUDE, default=[]): vol.All(cv.ensure_list, [cv.string]),
})

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform from YAML."""
    exclusions = config.get(CONF_EXCLUDE)
    async_add_entities([UnavailableDevicesSensor(hass, yaml_exclusions=exclusions)], True)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform from a config entry."""
    async_add_entities([UnavailableDevicesSensor(hass, config_entry=entry)], True)

class UnavailableDevicesSensor(SensorEntity):
    """Representation of the Unavailable Devices Sensor."""

    _attr_name = "Unavailable Devices Report"
    _attr_icon = "mdi:check-circle"

    def __init__(
        self, 
        hass: HomeAssistant, 
        yaml_exclusions: list[str] | None = None, 
        config_entry: ConfigEntry | None = None
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._yaml_exclusions = yaml_exclusions or []
        self._config_entry = config_entry
        self._attr_native_value = 0
        self._attr_extra_state_attributes = {}
        self._startup_delay_complete = False
        
        if config_entry:
            self._attr_unique_id = f"{config_entry.entry_id}"
            interval = config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            self._scan_interval = timedelta(seconds=interval)
            _LOGGER.debug(f"Initialized with config_entry. Interval: {interval}s ({self._scan_interval}). Options: {config_entry.options}")
        else:
            self._attr_unique_id = "unavailable_devices_report_sensor"
            self._scan_interval = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
            _LOGGER.debug(f"Initialized with YAML/Default. Interval: {DEFAULT_SCAN_INTERVAL}s")
            
        self._attr_should_poll = False

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        # Schedule the startup delay
        self.hass.loop.create_task(self._startup_delay_timer())
        
        # Setup periodic update
        self.async_on_remove(
            async_track_time_interval(self.hass, self._async_update_interval, self._scan_interval)
        )

    async def _async_update_interval(self, now):
        """Update the entity on interval."""
        await self.async_update()
        self.async_write_ha_state()

    async def _startup_delay_timer(self):
        """Wait for startup delay to complete."""
        await asyncio.sleep(60)
        self._startup_delay_complete = True
        await self.async_update()
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id if self._config_entry else "yaml_config")},
            name="Unavailable Devices Report",
            manufacturer="Custom Component",
            model="Report Sensor",
        )

    @property
    def excluded_device_ids(self) -> list[str]:
        """Return excluded device IDs."""
        if self._config_entry:
            return self._config_entry.options.get(CONF_EXCLUDED_DEVICES, [])
        return []

    @property
    def excluded_entity_ids(self) -> list[str]:
        """Return excluded entity IDs."""
        if self._config_entry:
            return self._config_entry.options.get(CONF_EXCLUDED_ENTITIES, [])
        return self._yaml_exclusions

    def _get_duration_string(self, last_changed: datetime) -> str:
        """Format duration since last_changed."""
        delta = dt_util.utcnow() - last_changed
        seconds = int(delta.total_seconds())
        
        if seconds < 60:
            return f"{seconds}s"
        
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}m"
        
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h {minutes % 60}m"
        
        days = hours // 24
        return f"{days}d {hours % 24}h"

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        _LOGGER.debug("Starting unavailable devices check")
        
        if not self._startup_delay_complete:
            _LOGGER.debug("Skipping check - startup delay active")
            return

        dev_reg = dr.async_get(self.hass)
        ent_reg = er.async_get(self.hass)
        
        unavailable_items = []
        
        # Iterate over all states
        for state in self.hass.states.async_all():
            if state.state in ["unavailable", "unknown"]:
                entity_id = state.entity_id

                # Check entity registry
                entity_entry = ent_reg.async_get(entity_id)
                
                # Filter out Diagnostic and Config entities
                if entity_entry and entity_entry.entity_category in ["diagnostic", "config"]:
                    continue

                # Resolve Device Info
                device_id = None
                device_name = None
                
                # Check entity registry for device_id
                if entity_entry and entity_entry.device_id:
                    device_id = entity_entry.device_id
                    device_entry = dev_reg.async_get(device_id)
                    if device_entry:
                        device_name = device_entry.name_by_user or device_entry.name
                
                unavailable_items.append({
                    "entity": entity_id,
                    "state": state.state,
                    "device_id": device_id,
                    "device_name": device_name,
                    "duration": self._get_duration_string(state.last_changed)
                })
        
        _LOGGER.debug(f"Found {len(unavailable_items)} total unavailable items/entities")
        _LOGGER.debug(f"Unavailable items details: {unavailable_items}")

        # Process Report
        devices = {}         # { device_id: {name, duration} }
        standalone = []      # [{entity_id, duration}, ...]
        candidate_device_ids = set()
        candidate_device_info = {} # { device_id: {name, duration} }
        count = 0
        
        excluded_dev_ids = self.excluded_device_ids
        excluded_ent_ids = self.excluded_entity_ids
        
        for item in unavailable_items:
            entity = item['entity']
            device_name = item['device_name']
            device_id = item['device_id']
            duration = item['duration']
            
            # Check Exclusions
            if entity in excluded_ent_ids:
                _LOGGER.debug(f"Excluding entity: {entity}")
                continue
            
            if device_id and device_id in excluded_dev_ids:
                _LOGGER.debug(f"Excluding device by ID: {device_id} ({device_name})")
                continue

            # Handle case where device name might be in YAML exclusions
            if device_name and device_name in excluded_ent_ids:
                _LOGGER.debug(f"Excluding device by name (from exclusions): {device_name}")
                continue
            
            if device_id:
                candidate_device_ids.add(device_id)
                if device_id not in candidate_device_info:
                    candidate_device_info[device_id] = {"name": device_name, "duration": duration}
            else:
                standalone.append({"entity": entity, "duration": duration})
        
        # Verify candidate devices and Handle Partial Failures
        for device_id in candidate_device_ids:
            # Get all entities for this device
            device_entries = er.async_entries_for_device(ent_reg, device_id)
            total_entities = 0
            unavailable_entities_count = 0
            
            for entry in device_entries:
                if entry.disabled_by:
                    continue
                
                # Check if this entity is ignored (diagnostic/config)
                if entry.entity_category in ["diagnostic", "config"]:
                    continue

                total_entities += 1
                state = self.hass.states.get(entry.entity_id)
                # If state exists and is unavailable/unknown
                if state and state.state in ["unavailable", "unknown"]:
                    unavailable_entities_count += 1
            
            if unavailable_entities_count > 0:
                info = candidate_device_info[device_id]
                # STRICT MODE: Only report if ALL entities of the device are unavailable
                if unavailable_entities_count == total_entities:
                     # Full Device Failure
                     devices[device_id] = info
                     count += 1
                else:
                    # Partial Device Failure - IGNORE
                    _LOGGER.debug(f"Ignoring partial active device {info['name']}: {unavailable_entities_count}/{total_entities} entities unavailable")

        count += len(standalone)

        # Format Markdown Reports
        def format_markdown(devs, items):
            if not devs and not items:
                return "✅ **All systems operational.** No unavailable devices."
            
            res = ""
            if devs:
                res += "**📱 Unavailable Devices**\n"
                sorted_devs = sorted(
                    [(d_id, d_info) for d_id, d_info in devs.items() if d_info["name"] is not None], 
                    key=lambda x: x[1]["name"]
                )
                for d_id, d_info in sorted_devs:
                    res += f"- [{d_info['name']}](/config/devices/device/{d_id}) _({d_info['duration']})_\n"
                res += "\n"

            if items:
                res += "**👻 Standalone Entities**\n"
                for ent_info in sorted(items, key=lambda x: x["entity"]):
                    res += f"- [{ent_info['entity']}](/config/entities/entity/{ent_info['entity']}) _({ent_info['duration']})_\n"
                res += "\n"
            return res.strip()

        def format_devices_only(devs):
            if not devs:
                return "✅ No unavailable devices."
            res = "**📱 Unavailable Devices**\n"
            sorted_devs = sorted(
                [(d_id, d_info) for d_id, d_info in devs.items() if d_info["name"] is not None], 
                key=lambda x: x[1]["name"]
            )
            for d_id, d_info in sorted_devs:
                res += f"- [{d_info['name']}](/config/devices/device/{d_id}) _({d_info['duration']})_\n"
            return res.strip()

        def format_entities_only(items):
            if not items:
                return "✅ No standalone unavailable entities."
            res = "**👻 Standalone Entities**\n"
            for ent_info in sorted(items, key=lambda x: x["entity"]):
                res += f"- [{ent_info['entity']}](/config/entities/entity/{ent_info['entity']}) _({ent_info['duration']})_\n"
            return res.strip()

        # Resolve excluded names for attributes
        excluded_device_names = []
        for d_id in excluded_dev_ids:
            device_entry = dev_reg.async_get(d_id)
            if device_entry:
                excluded_device_names.append(device_entry.name_by_user or device_entry.name)
            else:
                excluded_device_names.append(f"Unknown Device ({d_id})")

        self._attr_native_value = count
        self._attr_extra_state_attributes = {
            "count": count,
            "report_summary": format_markdown(devices, standalone),
            "devices_report": format_devices_only(devices),
            "entities_report": format_entities_only(standalone),
            "unavailable_devices": [{"device_id": k, "name": v["name"], "duration": v["duration"]} for k, v in devices.items()],
            "unavailable_entities": standalone,
            "unavailable_entity_ids": [ent["entity"] for ent in standalone], # Flat list for automation
            "excluded_devices": excluded_device_names,
            "excluded_entities": excluded_ent_ids,
        }

        self._truncate_attributes()

        
        if count == 0:
            self._attr_icon = "mdi:check-circle"
        else:
            self._attr_icon = "mdi:alert-circle"
            
        _LOGGER.info(f"Report updated: {count} devices/entities unavailable")

    def _paginate_attribute(self, attr_name: str, content: str, page_prefix: str, count_attr: str):
        """Split content into pages and store in attributes."""
        MAX_TEXT_BYTES = 10000
        
        # Remove original massive attribute
        self._attr_extra_state_attributes.pop(attr_name, None)
        
        pages = []
        if content:
            encoded_content = content.encode('utf-8')
            total_len = len(encoded_content)
            
            for i in range(0, total_len, MAX_TEXT_BYTES):
                chunk = encoded_content[i:i + MAX_TEXT_BYTES].decode('utf-8', errors='ignore')
                pages.append(chunk)

        # Store pages and count
        self._attr_extra_state_attributes[count_attr] = len(pages)
        for idx, page_content in enumerate(pages):
            self._attr_extra_state_attributes[f"{page_prefix}_{idx+1}"] = page_content
            
        return len(pages)

    def _truncate_attributes(self):
        """Split attributes to avoid database overflow."""
        # 1. Truncate Raw Lists
        limit = 30
        devs = self._attr_extra_state_attributes.get("unavailable_devices", [])
        ents = self._attr_extra_state_attributes.get("unavailable_entities", [])
        ent_ids = self._attr_extra_state_attributes.get("unavailable_entity_ids", [])
        
        if len(devs) > limit:
            self._attr_extra_state_attributes["unavailable_devices"] = devs[:limit]
            self._attr_extra_state_attributes["unavailable_devices_truncated"] = len(devs) - limit
            
        if len(ents) > limit:
            self._attr_extra_state_attributes["unavailable_entities"] = ents[:limit] 
            self._attr_extra_state_attributes["unavailable_entities_truncated"] = len(ents) - limit

        # Truncate excluded lists (they can be huge)
        ex_devs = self._attr_extra_state_attributes.get("excluded_devices", [])
        if len(ex_devs) > limit:
            self._attr_extra_state_attributes["excluded_devices"] = ex_devs[:limit]
            self._attr_extra_state_attributes["excluded_devices_truncated"] = len(ex_devs) - limit

        ex_ents = self._attr_extra_state_attributes.get("excluded_entities", [])
        if len(ex_ents) > limit:
            self._attr_extra_state_attributes["excluded_entities"] = ex_ents[:limit]
            self._attr_extra_state_attributes["excluded_entities_truncated"] = len(ex_ents) - limit

        # Truncate flat list too (generous limit)
        if len(ent_ids) > 100:
             self._attr_extra_state_attributes["unavailable_entity_ids"] = ent_ids[:100]

        # 2. Paginate Markdown Reports
        report_summary = self._attr_extra_state_attributes.get("report_summary", "")
        devices_report = self._attr_extra_state_attributes.get("devices_report", "")
        entities_report = self._attr_extra_state_attributes.get("entities_report", "")

        pgs_total = self._paginate_attribute("report_summary", report_summary, "report_page", "report_pages")
        pgs_dev = self._paginate_attribute("devices_report", devices_report, "devices_page", "devices_pages")
        pgs_ent = self._paginate_attribute("entities_report", entities_report, "entities_page", "entities_pages")

        _LOGGER.debug(f"Reports split: Total={pgs_total}, Devs={pgs_dev}, Ents={pgs_ent} pages")
