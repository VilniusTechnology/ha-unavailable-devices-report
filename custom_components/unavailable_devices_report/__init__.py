from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

import logging
from .const import DOMAIN, CONF_LOGGING_LEVEL

PLATFORMS: list[Platform] = [Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Unavailable Devices Report from a config entry."""
    _set_logging_level(entry.options.get(CONF_LOGGING_LEVEL, "INFO"))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register update listener to update options
    entry.async_on_unload(entry.add_update_listener(update_listener))
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener."""
    _set_logging_level(entry.options.get(CONF_LOGGING_LEVEL, "INFO"))
    await hass.config_entries.async_reload(entry.entry_id)

def _set_logging_level(level: str) -> None:
    """Set the logging level."""
    logging.getLogger(__package__).setLevel(level)

def setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the component."""
    return True
