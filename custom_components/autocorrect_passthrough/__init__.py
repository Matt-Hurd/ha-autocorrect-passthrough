"""Autocorrect"""
from __future__ import annotations

import logging
import aiohttp

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import ulid

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

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Autocorrect from a config entry."""
    agent = ModifiedConversationAgent(hass, entry)
    conversation.async_set_agent(hass, entry, agent)
    return True

class ModifiedConversationAgent(conversation.AbstractConversationAgent):
    """Autocorrect."""

    @property
    def supported_languages(self) -> list[str]:
        """Return a list of supported languages."""
        # You can modify this to return the languages your agent supports
        return ["en"]

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the agent."""
        self.hass = hass
        self.entry = entry
        self.agent_url = entry.options.get(CONF_AGENT_URL)

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Process a sentence."""
        debug_level = self.entry.options.get(CONF_DEBUG_LEVEL, DEBUG_LEVEL_NO_DEBUG)

        if user_input.conversation_id is None:
            user_input.conversation_id = ulid.ulid()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.agent_url, json=user_input) as response:
                    if response.status == 200:
                        result_text = await response.text()
                    else:
                        raise Exception(f"Error from agent: {response.status}")
        except Exception as e:
            _LOGGER.error("Error communicating with agent: %s", str(e))
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                f"Error communicating with agent: {str(e)}",
            )
            return conversation.ConversationResult(
                conversation_id=user_input.conversation_id,
                response=intent_response
            )

        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(result_text)

        if debug_level != DEBUG_LEVEL_NO_DEBUG:
            debug_info = f"Agent URL: {self.agent_url}\nInput: {user_input.text}\nOutput: {result_text}"
            if debug_level == DEBUG_LEVEL_VERBOSE_DEBUG:
                intent_response.async_set_speech(f"{result_text}\n\nDebug Info:\n{debug_info}")

        return conversation.ConversationResult(
            conversation_id=user_input.conversation_id,
            response=intent_response
        )