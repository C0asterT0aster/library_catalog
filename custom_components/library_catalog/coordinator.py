from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from typing import Any
import asyncio
import logging

from .api import get_book_data
from .const import UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

class LibraryCatalogCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the library catalog."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        super().__init__(
            hass,
            _LOGGER,
            name="Library Catalog",
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> Any:
        """Fetch data from the API."""
        try:
            # Fetch book data from the external API
            book_data = await fetch_book_data()
            return book_data
        except Exception as e:
            raise UpdateFailed(f"Error fetching data: {e}") from e

    async def refresh_data(self) -> None:
        """Refresh the data from the API."""
        await self.async_request_refresh()