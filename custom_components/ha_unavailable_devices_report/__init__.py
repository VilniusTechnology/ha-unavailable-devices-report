from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

import logging
from .const import DOMAIN, CONF_LOGGING_LEVEL

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Unavailable Devices Report from a config entry."""
    _set_logging_level(entry.options.get(CONF_LOGGING_LEVEL, "INFO"))

    
    # Register Services
    async def async_remove_items(call):
        """Handle the service call to remove items."""
        entity_ids = call.data.get("entity_id", [])
        device_ids = call.data.get("device_id", [])
        
        # Ensure lists
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]
        if isinstance(device_ids, str):
            device_ids = [device_ids]
            
        ent_reg = er.async_get(hass)
        dev_reg = dr.async_get(hass)
        
        for entity_id in entity_ids:
            if ent_reg.async_get(entity_id):
                ent_reg.async_remove(entity_id)
                _LOGGER.info(f"Removed entity: {entity_id}")
                
        for device_id in device_ids:
            if dev_reg.async_get(device_id):
                dev_reg.async_remove_device(device_id)
                _LOGGER.info(f"Removed device: {device_id}")

    hass.services.async_register(DOMAIN, "remove_items", async_remove_items)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register update listener to update options
    entry.async_on_unload(entry.add_update_listener(update_listener))
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener."""
    _LOGGER.debug(f"Update listener called. Options: {entry.options}")
    _set_logging_level(entry.options.get(CONF_LOGGING_LEVEL, "INFO"))
    await hass.config_entries.async_reload(entry.entry_id)

def _set_logging_level(level: str) -> None:
    """Set the logging level."""
    logging.getLogger(__package__).setLevel(level)

def setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the component."""
    return True
