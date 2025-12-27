import logging
import voluptuous as vol
from datetime import datetime, timedelta

import json
import asyncio
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.const import CONF_EXCLUDE
from homeassistant.core import HomeAssistant, callback, CoreState
from homeassistant.helpers import config_validation as cv, device_registry as dr, entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN, CONF_EXCLUDED_DEVICES, CONF_EXCLUDED_ENTITIES, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, CONF_IGNORE_UNKNOWN

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
        self._attr_extra_state_attributes = {
            "report_page_1": "✅ **System Initializing...**\nPlease wait ~60s for the first report.",
            "report_pages": 1,
            "devices_page_1": "✅ **System Initializing...**", 
            "devices_pages": 1,
            "entities_page_1": "✅ **System Initializing...**",
            "entities_pages": 1,
        }
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
        if self.hass.state == CoreState.running:
            _LOGGER.debug("Home Assistant is already running. Skipping startup delay.")
        else:
            _LOGGER.debug("Waiting 60s for Home Assistant startup...")
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
        
        # Check ignore_unknown option
        ignore_unknown = False
        if self._config_entry:
            ignore_unknown = self._config_entry.options.get(CONF_IGNORE_UNKNOWN, False)

        # Iterate over all states
        for state in self.hass.states.async_all():
            if state.state in ["unavailable", "unknown"]:
                if state.state == "unknown" and ignore_unknown:
                     continue

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
                
                is_reg = False
                if entity_entry:
                    # Only consider registered if not hidden and not disabled
                    if not entity_entry.hidden_by and not entity_entry.disabled_by:
                        is_reg = True

                unavailable_items.append({
                    "entity": entity_id,
                    "state": state.state,
                    "device_id": device_id,
                    "device_name": device_name,
                    "duration": self._get_duration_string(state.last_changed),
                    "is_registered": is_reg
                })
        
        _LOGGER.debug(f"Found {len(unavailable_items)} total unavailable items/entities")
        _LOGGER.debug(f"Unavailable items details: {unavailable_items}")

        # Process Report
        # 1. Collect Valid Candidates
        candidate_items = [] 
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
            
            candidate_items.append(item)
        
        # 2. Identify Full Device Failures
        full_failure_device_ids = set()
        unavailable_devices = {} # { device_id: {name, duration} }
        unknown_devices = {}     # { device_id: {name, duration} }
        
        for device_id in candidate_device_ids:
            # Get all entities for this device
            device_entries = er.async_entries_for_device(ent_reg, device_id)
            total_entities = 0
            unavailable_count = 0
            unknown_count = 0
            
            for entry in device_entries:
                if entry.disabled_by:
                    continue
                
                # Check if this entity is ignored (diagnostic/config)
                if entry.entity_category in ["diagnostic", "config"]:
                    continue

                total_entities += 1
                state = self.hass.states.get(entry.entity_id)
                # If state exists and is unavailable/unknown
                if state:
                    if state.state == "unavailable":
                        unavailable_count += 1
                    elif state.state == "unknown":
                        unknown_count += 1
            
            # Full failure if all entities are either unavailable or unknown
            if total_entities > 0 and (unavailable_count + unknown_count) == total_entities:
                 full_failure_device_ids.add(device_id)
                 
                 # If ANY entity is truly unavailable, mark device as Unavailable (higher severity)
                 # Otherwise (all unknown), mark as Unknown
                 if unavailable_count > 0:
                    unavailable_devices[device_id] = candidate_device_info[device_id]
                 else:
                    unknown_devices[device_id] = candidate_device_info[device_id]
                 
                 count += 1
            else:
                # Partial Device Failure
                _LOGGER.debug(f"Device {candidate_device_info[device_id]['name']} is partially active.")

        # 3. Process Items based on Device Status
        standalone_unavailable = []
        standalone_unknown = []

        for item in candidate_items:
            device_id = item['device_id']
            if device_id in full_failure_device_ids:
                continue # Already reported as a Device
            
            # If device is NOT fully unavailable, report the entity separately
            data = {
                "entity": item['entity'], 
                "duration": item['duration'], 
                "is_registered": item.get("is_registered", False)
            }
            
            if item['state'] == "unavailable":
                standalone_unavailable.append(data)
            else:
                standalone_unknown.append(data)

        count += len(standalone_unavailable) + len(standalone_unknown)

        # Format Markdown Reports
        def format_markdown(unavail_devs, unknown_devs, unavail_ents, unknown_ents):
            if not unavail_devs and not unknown_devs and not unavail_ents and not unknown_ents:
                return "✅ **All systems operational.** No unavailable devices."
            
            res = ""
            
            # 1. Unavailable Devices
            if unavail_devs:
                res += "**📱 Unavailable Devices**\n"
                sorted_devs = sorted(
                    [(d_id, d_info) for d_id, d_info in unavail_devs.items() if d_info["name"] is not None], 
                    key=lambda x: x[1]["name"]
                )
                for d_id, d_info in sorted_devs:
                    res += f"- [{d_info['name']}](/config/devices/device/{d_id}) _({d_info['duration']})_\n"
                res += "\n"

            # 2. Unknown Devices
            if unknown_devs:
                res += "**📱 Unknown Devices**\n"
                sorted_devs = sorted(
                    [(d_id, d_info) for d_id, d_info in unknown_devs.items() if d_info["name"] is not None], 
                    key=lambda x: x[1]["name"]
                )
                for d_id, d_info in sorted_devs:
                    res += f"- [{d_info['name']}](/config/devices/device/{d_id}) _({d_info['duration']})_\n"
                res += "\n"

            # 3. Unavailable Entities
            if unavail_ents:
                res += "**👻 Standalone Entities**\n"
                for ent_info in sorted(unavail_ents, key=lambda x: x["entity"]):
                    if ent_info.get("is_registered", False):
                        res += f"- [{ent_info['entity']}](/config/entities/entity/{ent_info['entity']}) _({ent_info['duration']})_\n"
                    else:
                        res += f"- {ent_info['entity']} _({ent_info['duration']})_\n"
                res += "\n"

            # 4. Unknown Entities
            if unknown_ents:
                res += "**👻 Unknown Entities**\n"
                for ent_info in sorted(unknown_ents, key=lambda x: x["entity"]):
                    if ent_info.get("is_registered", False):
                        res += f"- [{ent_info['entity']}](/config/entities/entity/{ent_info['entity']}) _({ent_info['duration']})_\n"
                    else:
                        res += f"- {ent_info['entity']} _({ent_info['duration']})_\n"
                res += "\n"
                
            return res.strip()

        def format_devices_only(unavail_devs, unknown_devs):
            if not unavail_devs and not unknown_devs:
                return "✅ No unavailable devices."
            res = ""
            
            if unavail_devs:
                res += "**📱 Unavailable Devices**\n"
                sorted_devs = sorted(
                    [(d_id, d_info) for d_id, d_info in unavail_devs.items() if d_info["name"] is not None], 
                    key=lambda x: x[1]["name"]
                )
                for d_id, d_info in sorted_devs:
                    res += f"- [{d_info['name']}](/config/devices/device/{d_id}) _({d_info['duration']})_\n"
                res += "\n"
                
            if unknown_devs:
                res += "**📱 Unknown Devices**\n"
                sorted_devs = sorted(
                    [(d_id, d_info) for d_id, d_info in unknown_devs.items() if d_info["name"] is not None], 
                    key=lambda x: x[1]["name"]
                )
                for d_id, d_info in sorted_devs:
                    res += f"- [{d_info['name']}](/config/devices/device/{d_id}) _({d_info['duration']})_\n"
                res += "\n"
                
            return res.strip()

        def format_entities_only(unavail_ents, unknown_ents):
            if not unavail_ents and not unknown_ents:
                return "✅ No standalone unavailable entities."
            res = ""
            
            if unavail_ents:
                res += "**👻 Standalone Entities**\n"
                for ent_info in sorted(unavail_ents, key=lambda x: x["entity"]):
                    if ent_info.get("is_registered", False):
                        res += f"- [{ent_info['entity']}](/config/entities/entity/{ent_info['entity']}) _({ent_info['duration']})_\n"
                    else:
                        res += f"- {ent_info['entity']} _({ent_info['duration']})_\n"
                res += "\n"
                
            if unknown_ents:
                res += "**👻 Unknown Entities**\n"
                for ent_info in sorted(unknown_ents, key=lambda x: x["entity"]):
                    if ent_info.get("is_registered", False):
                        res += f"- [{ent_info['entity']}](/config/entities/entity/{ent_info['entity']}) _({ent_info['duration']})_\n"
                    else:
                        res += f"- {ent_info['entity']} _({ent_info['duration']})_\n"
                res += "\n"
                
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
            # "report_summary": format_markdown(...), # REMOVED
            "devices_report": format_devices_only(unavailable_devices, unknown_devices),
            "entities_report": format_entities_only(standalone_unavailable, standalone_unknown),
            "unavailable_devices": [{"device_id": k, "name": v["name"], "duration": v["duration"]} for k, v in unavailable_devices.items()],
            "unknown_devices": [{"device_id": k, "name": v["name"], "duration": v["duration"]} for k, v in unknown_devices.items()],
            "unavailable_device_ids": list(unavailable_devices.keys()),
            "unknown_device_ids": list(unknown_devices.keys()),
            "unavailable_entities": standalone_unavailable,
            "unknown_entities": standalone_unknown,
            "unavailable_entity_ids": [ent["entity"] for ent in standalone_unavailable], 
            "unknown_entity_ids": [ent["entity"] for ent in standalone_unknown],
            "excluded_devices": excluded_device_names,
            "excluded_entities": excluded_ent_ids,
        }

        try:
            self._truncate_attributes()
        except Exception as e:
            _LOGGER.error(f"Failed to truncate/paginate attributes: {e}", exc_info=True)
            self._attr_extra_state_attributes["error"] = f"Truncation failed: {str(e)}"

        if count == 0:
            self._attr_icon = "mdi:check-circle"
        else:
            self._attr_icon = "mdi:alert-circle"
            
        _LOGGER.info(f"Report updated: {count} devices/entities unavailable")

    def _paginate_attribute(self, attr_name: str, content: str, page_prefix: str, count_attr: str):
        """Split content into pages and store in attributes."""
        MAX_TEXT_BYTES = 2048
        
        # Remove original massive attribute
        self._attr_extra_state_attributes.pop(attr_name, None)
        
        pages = []
        if content:
            lines = content.split('\n')
            current_page = ""
            
            for line in lines:
                line_full = line + "\n"
                
                # Check if adding this line exceeds the limit
                if len((current_page + line_full).encode('utf-8')) > MAX_TEXT_BYTES:
                    if current_page:
                        pages.append("\n" + current_page)
                        current_page = line_full
                    else:
                        # Single line exceeds limit, add it anyway
                        pages.append("\n" + line_full)
                        current_page = ""
                else:
                    current_page += line_full
            
            if current_page:
                pages.append("\n" + current_page)

        # Store pages and count
        self._attr_extra_state_attributes[count_attr] = len(pages)
        for idx, page_content in enumerate(pages):
            self._attr_extra_state_attributes[f"{page_prefix}_{idx+1}"] = page_content
            
        return len(pages)

    def _truncate_attributes(self):
        """Split attributes to avoid database overflow."""
        # 1. Truncate Raw Lists
        limit = 20
        devs = self._attr_extra_state_attributes.get("unavailable_devices", [])
        ents = self._attr_extra_state_attributes.get("unavailable_entities", [])
        ent_ids = self._attr_extra_state_attributes.get("unavailable_entity_ids", [])
        
        if len(devs) > limit:
            self._attr_extra_state_attributes["unavailable_devices"] = devs[:limit]
            self._attr_extra_state_attributes["unavailable_devices_truncated"] = len(devs) - limit
        
        # Truncate Unknown Devices
        uk_devs = self._attr_extra_state_attributes.get("unknown_devices", [])
        if len(uk_devs) > limit:
            self._attr_extra_state_attributes["unknown_devices"] = uk_devs[:limit]
            self._attr_extra_state_attributes["unknown_devices_truncated"] = len(uk_devs) - limit
            
        if len(ents) > limit:
            self._attr_extra_state_attributes["unavailable_entities"] = ents[:limit] 
            self._attr_extra_state_attributes["unavailable_entities_truncated"] = len(ents) - limit
            
        # Truncate Unknown Entities
        uk_ents = self._attr_extra_state_attributes.get("unknown_entities", [])
        if len(uk_ents) > limit:
            self._attr_extra_state_attributes["unknown_entities"] = uk_ents[:limit] 
            self._attr_extra_state_attributes["unknown_entities_truncated"] = len(uk_ents) - limit

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
            
        uk_ent_ids = self._attr_extra_state_attributes.get("unknown_entity_ids", [])
        if len(uk_ent_ids) > 100:
            self._attr_extra_state_attributes["unknown_entity_ids"] = uk_ent_ids[:100]

        # 2. Paginate Markdown Reports
        # report_summary = self._attr_extra_state_attributes.get("report_summary", "")
        devices_report = self._attr_extra_state_attributes.get("devices_report", "")
        entities_report = self._attr_extra_state_attributes.get("entities_report", "")

        # pgs_total = self._paginate_attribute("report_summary", report_summary, "report_page", "report_pages")
        pgs_dev = self._paginate_attribute("devices_report", devices_report, "devices_page", "devices_pages")
        pgs_ent = self._paginate_attribute("entities_report", entities_report, "entities_page", "entities_pages")

        _LOGGER.debug(f"Reports split: Devs={pgs_dev}, Ents={pgs_ent} pages")
