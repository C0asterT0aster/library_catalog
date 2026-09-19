"""Library Catalog integration for Home Assistant."""
import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, WEBHOOK_ID
from .coordinator import LibraryCatalogCoordinator
from .database import LibraryCatalogDatabase
from .webhook import WebhookHandler

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Library Catalog integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Library Catalog from a config entry."""
    _LOGGER.info("Setting up Library Catalog integration")

    # Initialize database
    try:
        db_path = Path(hass.config.path())
        database = LibraryCatalogDatabase(db_path)
        await database.async_initialize()
    except Exception as err:
        _LOGGER.error("Failed to initialize database: %s", err)
        raise ConfigEntryNotReady(f"Database initialization failed: {err}") from err

    # Create coordinator
    coordinator = LibraryCatalogCoordinator(hass, entry, database)
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator and database
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "database": database,
    }

    # Register services (only once, not per entry)
    if len(hass.data[DOMAIN]) == 1:
        from .services import async_setup_services
        await async_setup_services(hass)
        _LOGGER.info("Services registered")

    # Set up webhook for barcode scanning
    webhook_handler = WebhookHandler(hass)
    hass.components.webhook.async_register(
        DOMAIN,
        "Library Catalog Scanner",
        WEBHOOK_ID,
        webhook_handler.handle_barcode,
    )
    _LOGGER.info("Webhook registered at /api/webhook/%s", WEBHOOK_ID)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Library Catalog integration")

    # Unregister webhook
    hass.components.webhook.async_unregister(WEBHOOK_ID)

    # Close database
    data = hass.data[DOMAIN].pop(entry.entry_id)
    database = data["database"]
    await database.async_close()

    # Unregister services if this was the last entry
    if not hass.data[DOMAIN]:
        from .services import async_unload_services
        await async_unload_services(hass)
        _LOGGER.info("Services unregistered")

    return True
