"""Automatic helper entity creation for Library Catalog."""
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

_LOGGER = logging.getLogger(__name__)


async def create_input_helpers(hass: HomeAssistant) -> dict[str, Any]:
    """Create all required input helper entities."""

    results = {
        "created": [],
        "already_exists": [],
        "errors": []
    }

    # Define all input helpers
    input_text_configs = {
        "input_text.book_scan_room": {
            "name": "Book Location - Room",
            "initial": "Living Room",
            "icon": "mdi:home"
        },
        "input_text.book_scan_shelf": {
            "name": "Book Location - Shelf",
            "initial": "Shelf 1",
            "icon": "mdi:bookshelf"
        },
        "input_text.book_scan_compartment": {
            "name": "Book Location - Compartment",
            "initial": "Top",
            "icon": "mdi:book-open-variant"
        }
    }

    input_boolean_configs = {
        "input_boolean.book_scanning_active": {
            "name": "Book Adding Active",
            "initial": False,
            "icon": "mdi:book-plus"
        }
    }

    input_number_configs = {
        "input_number.books_scanned_today": {
            "name": "Books Added Today",
            "min": 0,
            "max": 1000,
            "step": 1,
            "icon": "mdi:counter"
        }
    }

    input_datetime_configs = {
        "input_datetime.last_book_scan_time": {
            "name": "Last Book Added Time",
            "has_date": True,
            "has_time": True
        }
    }

    # Create input_text entities
    for entity_id, config in input_text_configs.items():
        try:
            await hass.services.async_call(
                "input_text",
                "create",
                {
                    "name": config["name"],
                    "initial": config.get("initial", ""),
                    "icon": config.get("icon")
                },
                blocking=True
            )
            results["created"].append(entity_id)
            _LOGGER.info("Created input helper: %s", entity_id)
        except Exception as err:
            if "already exists" in str(err).lower():
                results["already_exists"].append(entity_id)
            else:
                results["errors"].append(f"{entity_id}: {err}")
                _LOGGER.error("Failed to create %s: %s", entity_id, err)

    # Create input_boolean entities
    for entity_id, config in input_boolean_configs.items():
        try:
            await hass.services.async_call(
                "input_boolean",
                "create",
                {
                    "name": config["name"],
                    "initial": config.get("initial", False),
                    "icon": config.get("icon")
                },
                blocking=True
            )
            results["created"].append(entity_id)
            _LOGGER.info("Created input helper: %s", entity_id)
        except Exception as err:
            if "already exists" in str(err).lower():
                results["already_exists"].append(entity_id)
            else:
                results["errors"].append(f"{entity_id}: {err}")
                _LOGGER.error("Failed to create %s: %s", entity_id, err)

    # Create input_number entities
    for entity_id, config in input_number_configs.items():
        try:
            await hass.services.async_call(
                "input_number",
                "create",
                {
                    "name": config["name"],
                    "min": config["min"],
                    "max": config["max"],
                    "step": config["step"],
                    "icon": config.get("icon")
                },
                blocking=True
            )
            results["created"].append(entity_id)
            _LOGGER.info("Created input helper: %s", entity_id)
        except Exception as err:
            if "already exists" in str(err).lower():
                results["already_exists"].append(entity_id)
            else:
                results["errors"].append(f"{entity_id}: {err}")
                _LOGGER.error("Failed to create %s: %s", entity_id, err)

    # Create input_datetime entities
    for entity_id, config in input_datetime_configs.items():
        try:
            await hass.services.async_call(
                "input_datetime",
                "create",
                {
                    "name": config["name"],
                    "has_date": config.get("has_date", True),
                    "has_time": config.get("has_time", True)
                },
                blocking=True
            )
            results["created"].append(entity_id)
            _LOGGER.info("Created input helper: %s", entity_id)
        except Exception as err:
            if "already exists" in str(err).lower():
                results["already_exists"].append(entity_id)
            else:
                results["errors"].append(f"{entity_id}: {err}")
                _LOGGER.error("Failed to create %s: %s", entity_id, err)

    return results
