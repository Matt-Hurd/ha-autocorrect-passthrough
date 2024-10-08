"""Config flow for Autocorrect integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectOptionDict,
    SelectSelectorMode,
)

from .const import (
    CONF_DEBUG_LEVEL,
    CONF_AGENT_URL,
    DEBUG_LEVEL_NO_DEBUG,
    DEBUG_LEVEL_LOW_DEBUG,
    DEBUG_LEVEL_VERBOSE_DEBUG,
    DOMAIN,
    DEFAULT_NAME,
    DEFAULT_DEBUG_LEVEL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_AGENT_URL): str,
        vol.Optional(CONF_DEBUG_LEVEL, default=DEFAULT_DEBUG_LEVEL): SelectSelector(
            SelectSelectorConfig(
                options=[
                    SelectOptionDict(value=DEBUG_LEVEL_NO_DEBUG, label="No Debug"),
                    SelectOptionDict(value=DEBUG_LEVEL_LOW_DEBUG, label="Some Debug"),
                    SelectOptionDict(value=DEBUG_LEVEL_VERBOSE_DEBUG, label="Verbose Debug"),
                ],
                mode=SelectSelectorMode.DROPDOWN
            ),
        ),
    }
)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Modified Agent config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        _LOGGER.debug("ConfigFlow::user_input %s", user_input)
        if user_input is None:
            return self.async_show_form(
                step_id="user", 
                data_schema=STEP_USER_DATA_SCHEMA, 
            )

        return self.async_create_entry(
            title=user_input.get(CONF_NAME, DEFAULT_NAME), 
            data={},
            options={
                CONF_AGENT_URL: user_input[CONF_AGENT_URL],
                CONF_DEBUG_LEVEL: user_input.get(CONF_DEBUG_LEVEL, DEFAULT_DEBUG_LEVEL),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlow(config_entry)

class OptionsFlow(config_entries.OptionsFlow):
    """Modified config flow options handler."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = self.agent_config_option_schema(self.config_entry.options)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema),
        )

    def agent_config_option_schema(self, options: dict) -> dict:
        """Return a schema for Modified Agent options."""
        return {
            vol.Required(
                CONF_AGENT_URL,
                default=options.get(CONF_AGENT_URL, ""),
            ): str,
            vol.Required(
                CONF_DEBUG_LEVEL, 
                default=options.get(CONF_DEBUG_LEVEL, DEFAULT_DEBUG_LEVEL),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        SelectOptionDict(value=DEBUG_LEVEL_NO_DEBUG, label="No Debug"),
                        SelectOptionDict(value=DEBUG_LEVEL_LOW_DEBUG, label="Some Debug"),
                        SelectOptionDict(value=DEBUG_LEVEL_VERBOSE_DEBUG, label="Verbose Debug"),
                    ],
                    mode=SelectSelectorMode.DROPDOWN
                ),
            ),
        }