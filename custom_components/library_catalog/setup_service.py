"""Automatic setup service for Library Catalog - writes YAML files directly."""
import logging
from typing import Any
import yaml
from pathlib import Path

from homeassistant.core import HomeAssistant, ServiceCall
import voluptuous as vol

_LOGGER = logging.getLogger(__name__)


# Configuration YAML that will be written
INPUT_HELPERS_YAML = """
# Library Catalog Input Helpers - Auto-generated
input_text:
  book_scan_room:
    name: "Book Location - Room"
    initial: "Living Room"
    icon: mdi:home

  book_scan_shelf:
    name: "Book Location - Shelf"
    initial: "Shelf 1"
    icon: mdi:bookshelf

  book_scan_compartment:
    name: "Book Location - Compartment"
    initial: "Top"
    icon: mdi:book-open-variant

input_boolean:
  book_scanning_active:
    name: "Book Adding Active"
    initial: false
    icon: mdi:book-plus

input_number:
  books_scanned_today:
    name: "Books Added Today"
    min: 0
    max: 1000
    step: 1
    icon: mdi:counter

input_datetime:
  last_book_scan_time:
    name: "Last Book Added Time"
    has_date: true
    has_time: true
"""

# Scripts that will be created
SCRIPTS = {
    "start_book_adding": {
        "alias": "Start Adding Books",
        "icon": "mdi:book-plus",
        "sequence": [
            {
                "service": "input_number.set_value",
                "target": {"entity_id": "input_number.books_scanned_today"},
                "data": {"value": 0}
            },
            {
                "service": "input_boolean.turn_on",
                "target": {"entity_id": "input_boolean.book_scanning_active"}
            },
            {
                "service": "notify.notify",
                "data": {
                    "title": "📚 Add Books",
                    "message": "Location: {{ states('input_text.book_scan_room') }} > {{ states('input_text.book_scan_shelf') }}",
                    "data": {
                        "actions": [
                            {
                                "action": "ADD_BOOK_ISBN",
                                "title": "➕ Add Book",
                                "behavior": "textInput",
                                "textInputButtonTitle": "Add",
                                "textInputPlaceholder": "Enter ISBN (13 digits)"
                            }
                        ],
                        "tag": "book_adder",
                        "group": "book_adder"
                    }
                }
            }
        ]
    },
    "stop_book_adding": {
        "alias": "Stop Adding Books",
        "icon": "mdi:stop",
        "sequence": [
            {
                "service": "input_boolean.turn_off",
                "target": {"entity_id": "input_boolean.book_scanning_active"}
            },
            {
                "service": "notify.notify",
                "data": {
                    "title": "✅ Complete",
                    "message": "Added {{ states('input_number.books_scanned_today') | int }} books",
                    "data": {"tag": "book_adder"}
                }
            }
        ]
    }
}

# Automations that will be created
AUTOMATIONS = [
    {
        "id": "library_catalog_handle_add_book",
        "alias": "Library Catalog - Handle Add Book",
        "description": "Process ISBN from notification",
        "trigger": [
            {
                "platform": "event",
                "event_type": "mobile_app_notification_action",
                "event_data": {"action": "ADD_BOOK_ISBN"}
            }
        ],
        "condition": [
            {
                "condition": "state",
                "entity_id": "input_boolean.book_scanning_active",
                "state": "on"
            }
        ],
        "action": [
            {
                "variables": {
                    "isbn_input": "{{ trigger.event.data.reply_text }}"
                }
            },
            {
                "service": "library_catalog.add_book",
                "data": {
                    "isbn": "{{ isbn_input }}",
                    "location": {
                        "room": "{{ states('input_text.book_scan_room') }}",
                        "shelf": "{{ states('input_text.book_scan_shelf') }}",
                        "compartment": "{{ states('input_text.book_scan_compartment') }}"
                    }
                },
                "continue_on_error": True
            },
            {
                "service": "input_number.increment",
                "target": {"entity_id": "input_number.books_scanned_today"}
            },
            {
                "service": "input_datetime.set_datetime",
                "target": {"entity_id": "input_datetime.last_book_scan_time"},
                "data": {"timestamp": "{{ now().timestamp() }}"}
            },
            {
                "service": "notify.notify",
                "data": {
                    "title": "✅ Book Added!",
                    "message": "ISBN: {{ isbn_input }} | Total: {{ states('input_number.books_scanned_today') | int }}",
                    "data": {
                        "actions": [
                            {
                                "action": "ADD_BOOK_ISBN",
                                "title": "➕ Add Another",
                                "behavior": "textInput",
                                "textInputButtonTitle": "Add",
                                "textInputPlaceholder": "Enter ISBN"
                            },
                            {
                                "action": "STOP_ADDING_BOOKS",
                                "title": "🛑 Stop"
                            }
                        ],
                        "tag": "book_adder_result",
                        "group": "book_adder"
                    }
                }
            }
        ],
        "mode": "single"
    },
    {
        "id": "library_catalog_handle_stop",
        "alias": "Library Catalog - Handle Stop",
        "trigger": [
            {
                "platform": "event",
                "event_type": "mobile_app_notification_action",
                "event_data": {"action": "STOP_ADDING_BOOKS"}
            }
        ],
        "action": [
            {
                "service": "script.stop_book_adding"
            }
        ],
        "mode": "single"
    }
]


async def async_setup_automation_service(hass: HomeAssistant) -> None:
    """Set up the automatic setup service."""

    async def handle_auto_setup(call: ServiceCall) -> None:
        """Handle the auto_setup service call."""
        _LOGGER.info("Starting automatic Library Catalog setup")

        results = {
            "config_written": False,
            "scripts_created": 0,
            "automations_created": 0,
            "errors": []
        }

        try:
            # Step 1: Write input helpers to configuration.yaml
            _LOGGER.info("Writing input helpers to configuration.yaml...")
            config_path = Path(hass.config.path("configuration.yaml"))

            if not config_path.exists():
                results["errors"].append("configuration.yaml not found")
            else:
                # Read existing configuration
                with open(config_path, "r", encoding="utf-8") as f:
                    config_content = f.read()

                # Check if Library Catalog section already exists
                if "# Library Catalog Input Helpers" in config_content:
                    _LOGGER.info("Input helpers already exist, skipping...")
                else:
                    # Append to end of file
                    with open(config_path, "a", encoding="utf-8") as f:
                        f.write("\n\n" + INPUT_HELPERS_YAML)
                    results["config_written"] = True
                    _LOGGER.info("Input helpers written to configuration.yaml")

            # Step 2: Create scripts
            _LOGGER.info("Creating scripts...")
            scripts_path = Path(hass.config.path("scripts.yaml"))

            # Read existing scripts if file exists
            existing_scripts = {}
            if scripts_path.exists():
                try:
                    with open(scripts_path, "r", encoding="utf-8") as f:
                        existing_scripts = yaml.safe_load(f) or {}
                except Exception as err:
                    _LOGGER.warning("Could not read existing scripts.yaml: %s", err)

            # Remove old library catalog scripts
            existing_scripts = {
                k: v for k, v in existing_scripts.items()
                if k not in ["start_book_scanning", "stop_book_scanning", "start_book_adding", "stop_book_adding"]
            }

            # Add our scripts
            existing_scripts.update(SCRIPTS)

            # Write back to file
            with open(scripts_path, "w", encoding="utf-8") as f:
                yaml.dump(existing_scripts, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

            # Reload scripts
            await hass.services.async_call("script", "reload", blocking=True)

            results["scripts_created"] = len(SCRIPTS)
            _LOGGER.info("Created %d scripts", len(SCRIPTS))

        except Exception as err:
            error_msg = f"Failed to create scripts: {err}"
            results["errors"].append(error_msg)
            _LOGGER.error(error_msg)

        try:
            # Step 3: Create automations
            _LOGGER.info("Creating automations...")
            automations_path = Path(hass.config.path("automations.yaml"))

            # Read existing automations if file exists
            existing_automations = []
            if automations_path.exists():
                try:
                    with open(automations_path, "r", encoding="utf-8") as f:
                        existing_automations = yaml.safe_load(f) or []
                        if not isinstance(existing_automations, list):
                            existing_automations = []
                except Exception as err:
                    _LOGGER.warning("Could not read existing automations.yaml: %s", err)

            # Remove old library_catalog automations
            existing_automations = [
                a for a in existing_automations
                if not (isinstance(a, dict) and a.get("id", "").startswith("library_catalog_"))
            ]

            # Add our automations
            existing_automations.extend(AUTOMATIONS)

            # Write back to file
            with open(automations_path, "w", encoding="utf-8") as f:
                yaml.dump(existing_automations, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

            # Reload automations
            await hass.services.async_call("automation", "reload", blocking=True)

            results["automations_created"] = len(AUTOMATIONS)
            _LOGGER.info("Created %d automations", len(AUTOMATIONS))

        except Exception as err:
            error_msg = f"Failed to create automations: {err}"
            results["errors"].append(error_msg)
            _LOGGER.error(error_msg)

        # Step 4: Send notification with results
        message = "✅ **Setup Complete!**\n\n"

        if results["config_written"]:
            message += "📝 **Input helpers written to configuration.yaml**\n"
            message += "⚠️ **YOU MUST RESTART HOME ASSISTANT NOW!**\n\n"
        else:
            message += "ℹ️ Input helpers already exist\n\n"

        message += f"**Scripts:** {results['scripts_created']} created\n"
        message += f"**Automations:** {results['automations_created']} created\n"

        if results["errors"]:
            message += f"\n⚠️ **Errors:** {len(results['errors'])}\n"
            for error in results["errors"][:3]:
                message += f"- {error}\n"

        if results["config_written"]:
            message += "\n**IMPORTANT:**\n"
            message += "1. ⚠️ **RESTART HOME ASSISTANT** (Settings → System → Restart)\n"
            message += "2. Wait for restart (2 minutes)\n"
            message += "3. Add dashboard card (see AUTO_SETUP.md)\n"
            message += "4. Click 'Start Adding Books'!\n"
        else:
            message += "\n**Next Steps:**\n"
            message += "1. Go to Overview (dashboard)\n"
            message += "2. Add card (see AUTO_SETUP.md for YAML)\n"
            message += "3. Click 'Start Adding Books'\n"
            message += "4. Enter ISBN in notification!\n"

        await hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": "📚 Library Catalog - Auto Setup",
                "message": message,
                "notification_id": "library_catalog_setup"
            },
            blocking=False
        )

        _LOGGER.info("Auto-setup complete: %s", results)

    hass.services.async_register(
        "library_catalog",
        "auto_setup",
        handle_auto_setup,
        schema=vol.Schema({})
    )

    _LOGGER.info("Auto-setup service registered")
