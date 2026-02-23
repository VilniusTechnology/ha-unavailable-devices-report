from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import logging

_LOGGER = logging.getLogger(__name__)

from .const import DOMAIN, CONF_EXCLUDED_DEVICES, CONF_EXCLUDED_ENTITIES, CONF_LOGGING_LEVEL, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, CONF_IGNORE_UNKNOWN

class UnavailableDevicesReportConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Unavailable Devices Report."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title="Unavailable Devices Report", data=user_input)

        return self.async_show_form(step_id="user")

    async def async_step_import(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle import from YAML."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        
        return self.async_create_entry(title="Unavailable Devices Report", data=user_input or {})

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> UnavailableDevicesReportOptionsFlowHandler:
        """Get the options flow for this handler."""
        return UnavailableDevicesReportOptionsFlowHandler(config_entry)


class UnavailableDevicesReportOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Unavailable Devices Report."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        errors = {}
        
        try:
            schema = vol.Schema(
                {
                    vol.Optional(
                        CONF_EXCLUDED_DEVICES,
                        default=self._config_entry.options.get(CONF_EXCLUDED_DEVICES, []),
                    ): selector.DeviceSelector(
                        selector.DeviceSelectorConfig(multiple=True)
                    ),
                    vol.Optional(
                        CONF_EXCLUDED_ENTITIES,
                        default=self._config_entry.options.get(CONF_EXCLUDED_ENTITIES, []),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(multiple=True)
                    ),
                    vol.Optional(
                        CONF_LOGGING_LEVEL,
                        default=self._config_entry.options.get(CONF_LOGGING_LEVEL, "INFO"),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self._config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=30,
                            max=3600,
                            step=10,
                            unit_of_measurement="seconds",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(
                        CONF_IGNORE_UNKNOWN,
                        default=self._config_entry.options.get(CONF_IGNORE_UNKNOWN, False),
                    ): selector.BooleanSelector(),
                }
            )
        except Exception as e:
            _LOGGER.error("Failed to build options schema: %s", e)
            return self.async_show_form(
                step_id="init",
                errors={"base": str(e)},
            )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )
