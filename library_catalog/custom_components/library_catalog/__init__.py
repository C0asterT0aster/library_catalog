"""Library Catalog integration for Home Assistant."""
import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .database import LibraryCatalogDatabase

_LOGGER = logging.getLogger(__name__)

PLATFORMS = []  # No platforms yet (no sensors, switches, etc.)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Library Catalog integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Library Catalog from a config entry."""
    _LOGGER.info("Setting up Library Catalog integration")

    # Initialize database
    config_path = Path(hass.config.path())
    database = LibraryCatalogDatabase(config_path)

    try:
        await database.async_initialize()
        _LOGGER.info("Database initialized successfully")
    except Exception as err:
        _LOGGER.error("Failed to initialize database: %s", err)
        raise ConfigEntryNotReady(f"Database initialization failed: {err}") from err

    # Store database instance
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "database": database,
    }

    # Setup platforms (none yet)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info("Library Catalog integration setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Library Catalog integration")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Close database connection
    if entry.entry_id in hass.data[DOMAIN]:
        database = hass.data[DOMAIN][entry.entry_id].get("database")
        if database:
            await database.async_close()
            _LOGGER.info("Database connection closed")

        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry."""
    _LOGGER.info("Removing Library Catalog integration")
    # Database file is kept for data preservation
    # User can manually delete it if needed