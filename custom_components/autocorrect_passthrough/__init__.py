"""Autocorrect"""
from __future__ import annotations

import logging
import traceback
import aiohttp

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import ulid
from homeassistant.core import callback

from homeassistant.helpers import (
    config_validation as cv,
    intent,
)

from .const import (
    CONF_DEBUG_LEVEL,
    CONF_AGENT_URL,
    DEBUG_LEVEL_NO_DEBUG,
    DEBUG_LEVEL_LOW_DEBUG,
    DEBUG_LEVEL_VERBOSE_DEBUG,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
import yarl

class ModifiedConversationAgent(conversation.AbstractConversationAgent):
    """Autocorrect."""

    @property
    def supported_languages(self) -> list[str]:
        """Return a list of supported languages."""
        return ["en"]

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the agent."""
        self.hass = hass
        self.entry = entry
        self._agent_url = None
        self._debug_level = DEBUG_LEVEL_NO_DEBUG
        self._update_config(entry.options)
        
        # Register update listener
        self._unsubscribe_updates = entry.add_update_listener(self.async_update_options)

    @callback
    def _update_config(self, config: dict) -> None:
        """Update the configuration."""
        self._set_agent_url(config.get(CONF_AGENT_URL))
        self._debug_level = config.get(CONF_DEBUG_LEVEL, DEBUG_LEVEL_NO_DEBUG)

    def _set_agent_url(self, url: str) -> None:
        """Set and validate the agent URL."""
        if not url:
            _LOGGER.error("Agent URL is not set in the configuration")
            self._agent_url = None
            return
        
        try:
            parsed_url = yarl.URL(url)
            if not parsed_url.scheme or not parsed_url.host:
                raise ValueError("Invalid URL format")
            self._agent_url = parsed_url
        except Exception as e:
            _LOGGER.error("Invalid agent URL: %s. Error: %s", url, str(e))
            self._agent_url = None

    async def async_update_options(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Update options."""
        self._update_config(entry.options)

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Process a sentence."""
        if not self._agent_url:
            return self._create_error_response(user_input, "Agent URL is not properly configured")

        input_data = {
            "text": user_input.text,
            "context": user_input.context.as_dict(),
            "conversation_id": user_input.conversation_id or str(ulid.ulid()),
            "device_id": user_input.device_id,
            "language": user_input.language,
            "agent_id": user_input.agent_id,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(str(self._agent_url), json=input_data) as response:
                    if response.status == 200:
                        result_text = await response.text()
                    else:
                        raise Exception(f"Error from agent: {response.status}")
        except Exception as e:
            _LOGGER.error("Error communicating with agent: %s", str(e))
            _LOGGER.error("Traceback:\n%s", traceback.format_exc())
            return self._create_error_response(user_input, f"Error communicating with agent: {str(e)}")

        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(result_text)

        if self._debug_level != DEBUG_LEVEL_NO_DEBUG:
            debug_info = f"Agent URL: {self._agent_url}\nInput: {user_input.text}\nOutput: {result_text}"
            if self._debug_level == DEBUG_LEVEL_VERBOSE_DEBUG:
                intent_response.async_set_speech(f"{result_text}\n\nDebug Info:\n{debug_info}")

        return conversation.ConversationResult(
            conversation_id=input_data["conversation_id"],
            response=intent_response
        )

    def _create_error_response(self, user_input: conversation.ConversationInput, error_message: str) -> conversation.ConversationResult:
        """Create an error response."""
        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_error(
            intent.IntentResponseErrorCode.UNKNOWN,
            error_message,
        )
        return conversation.ConversationResult(
            conversation_id=user_input.conversation_id or str(ulid.ulid()),
            response=intent_response
        )

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Autocorrect from a config entry."""
    agent = ModifiedConversationAgent(hass, entry)
    conversation.async_set_agent(hass, entry, agent)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    agent = conversation.async_get_agent(hass, entry.entry_id)
    if isinstance(agent, ModifiedConversationAgent):
        agent._unsubscribe_updates()
    conversation.async_unset_agent(hass, entry)
    return True