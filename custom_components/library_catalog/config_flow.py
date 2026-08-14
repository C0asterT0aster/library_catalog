from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from .const import DOMAIN, CONF_ISBN_API_KEY
from .api import fetch_book_data

class LibraryCatalogConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Library Catalog."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(step_id="user")

        isbn_api_key = user_input.get(CONF_ISBN_API_KEY)

        if not isbn_api_key:
            errors = {"base": "invalid_api_key"}
            return self.async_show_form(step_id="user", errors=errors)

        # Fetch book data to validate the API key
        book_data = await fetch_book_data(isbn_api_key)
        if book_data is None:
            errors = {"base": "cannot_connect"}
            return self.async_show_form(step_id="user", errors=errors)

        return self.async_create_entry(title="Library Catalog", data=user_input)

    async def async_step_import(self, user_input):
        """Import a config entry from YAML."""
        return await self.async_step_user(user_input)