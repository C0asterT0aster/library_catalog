from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from typing import Any
import asyncio
import logging

from .const import UPDATE_INTERVAL
from .database import LibraryCatalogDatabase

_LOGGER = logging.getLogger(__name__)

class LibraryCatalogCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the library catalog.

    This coordinator manages periodic updates of library statistics
    and book counts from the local database.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, database: LibraryCatalogDatabase) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            entry: Config entry
            database: Library database instance
        """
        self.entry = entry
        self.database = database
        super().__init__(
            hass,
            _LOGGER,
            name="Library Catalog",
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> Any:
        """Fetch statistics from the local database.

        This method is called periodically to update library statistics.
        Individual book lookups are done on-demand via services.

        Returns:
            Dictionary with library statistics

        Raises:
            UpdateFailed: If database query fails
        """
        try:
            # Get book count and other stats from database
            book_count = await self.database.get_book_count()

            return {
                "book_count": book_count,
                "last_updated": self.last_update_success,
            }
        except Exception as e:
            raise UpdateFailed(f"Error fetching library statistics: {e}") from e

    async def refresh_data(self) -> None:
        """Refresh the data from the database."""
        await self.async_request_refresh()