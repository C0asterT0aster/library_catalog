"""Config flow for Library Catalog integration."""
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
import voluptuous as vol

from .const import DOMAIN, CONF_NAME

class LibraryCatalogConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Library Catalog.

    This integration requires no API keys and works entirely locally
    with Open Library and Google Books public APIs.
    """

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step.

        User can optionally provide a name for their library catalog.
        Multiple config entries allow managing multiple independent libraries.
        """
        if user_input is None:
            # Show form to configure library name
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Optional(CONF_NAME, default="My Library"): str,
                }),
            )

        # Create config entry with provided name
        library_name = user_input.get(CONF_NAME, "My Library")

        # Check if entry with this name already exists
        await self.async_set_unique_id(f"library_catalog_{library_name.lower().replace(' ', '_')}")
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=library_name,
            data=user_input
        )

    async def async_step_import(self, user_input):
        """Import a config entry from YAML (legacy support)."""
        return await self.async_step_user(user_input)