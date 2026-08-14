"""Config flow for Library Catalog integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_NAME

_LOGGER = logging.getLogger(__name__)


class LibraryCatalogConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Library Catalog."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check if already configured
            await self.async_set_unique_id(user_input.get(CONF_NAME, "library_catalog"))
            self._abort_if_unique_id_configured()

            # Create the config entry
            return self.async_create_entry(
                title=user_input.get(CONF_NAME, "Library Catalog"),
                data=user_input,
            )

        # Show configuration form
        data_schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default="Library Catalog"): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )
