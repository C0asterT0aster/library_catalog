"""Webhook handler for barcode scanner input."""
import logging
from typing import Any, Dict, Optional
from aiohttp import web
from homeassistant.core import HomeAssistant

from .api import validate_isbn, ISBNValidationError
from .const import WEBHOOK_ID, WEBHOOK_PATH, WEBHOOK_FIELD_ISBN, WEBHOOK_FIELD_FORMAT
from .models import BarCodeFormat

_LOGGER = logging.getLogger(__name__)


class WebhookHandler:
    """Handler for barcode scanner webhook requests."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize webhook handler."""
        self.hass = hass

    async def handle_barcode(self, request: web.Request) -> web.Response:
        """Handle incoming barcode webhook request.
        
        Accepts JSON POST with flexible field names:
        {
            "isbn": "9780451524935",  # or "isbn_input", "code", "barcode"
            "format": "ISBN13"         # or "barcode_format", "type"
        }
        
        Returns:
            JSON response with status and message
        """
        try:
            # Parse JSON payload
            try:
                data = await request.json()
            except ValueError as e:
                # ValueError raised for invalid JSON
                _LOGGER.warning("Invalid JSON in webhook request: %s", str(e))
                return web.json_response(
                    {"success": False, "error": "Invalid JSON payload"},
                    status=400,
                )

            # Extract ISBN from flexible field names
            isbn_value = self._extract_field(data, WEBHOOK_FIELD_ISBN)
            if not isbn_value:
                _LOGGER.warning("No ISBN found in webhook request")
                return web.json_response(
                    {"success": False, "error": "Missing ISBN/barcode field"},
                    status=400,
                )

            # Extract format (optional)
            format_value = self._extract_field(data, WEBHOOK_FIELD_FORMAT)
            barcode_format = self._parse_barcode_format(format_value)

            # Validate ISBN
            try:
                normalized_isbn = validate_isbn(isbn_value)
            except ISBNValidationError as e:
                _LOGGER.warning("Invalid ISBN in webhook: %s", str(e))
                return web.json_response(
                    {"success": False, "error": f"Invalid ISBN: {str(e)}"},
                    status=400,
                )

            # Fire event for service to handle
            self.hass.bus.async_fire(
                "library_catalog_barcode_received",
                {
                    "isbn": normalized_isbn,
                    "format": barcode_format.value,
                    "raw_isbn": isbn_value,
                },
            )

            _LOGGER.info(
                "Barcode received via webhook: %s (format: %s)",
                normalized_isbn,
                barcode_format.value,
            )

            return web.json_response(
                {
                    "success": True,
                    "message": "Barcode received",
                    "isbn": normalized_isbn,
                    "format": barcode_format.value,
                }
            )

        except Exception as e:
            _LOGGER.error("Error processing webhook request: %s", str(e))
            return web.json_response(
                {"success": False, "error": "Internal server error"},
                status=500,
            )

    def _extract_field(self, data: Dict[str, Any], field_names: tuple) -> Optional[str]:
        """Extract field value using tolerant field name matching.
        
        Args:
            data: Request data dictionary
            field_names: Tuple of possible field names to check
            
        Returns:
            Field value if found, None otherwise
        """
        for field_name in field_names:
            if field_name in data:
                value = data[field_name]
                if isinstance(value, str):
                    return value.strip()
        return None

    def _parse_barcode_format(self, format_str: Optional[str]) -> BarCodeFormat:
        """Parse barcode format string to enum.
        
        Args:
            format_str: Format string (e.g., "ISBN13", "EAN13", "CODE128")
            
        Returns:
            BarCodeFormat enum value
        """
        if not format_str:
            return BarCodeFormat.UNKNOWN

        format_upper = format_str.upper().strip()

        # Map common format strings
        format_mapping = {
            "ISBN10": BarCodeFormat.ISBN10,
            "ISBN13": BarCodeFormat.ISBN13,
            "EAN13": BarCodeFormat.EAN13,
            "EAN": BarCodeFormat.EAN13,  # Common alias
            "CODE128": BarCodeFormat.CODE128,
            "CODE 128": BarCodeFormat.CODE128,  # With space
            "128": BarCodeFormat.CODE128,  # Short form
        }

        return format_mapping.get(format_upper, BarCodeFormat.UNKNOWN)


async def async_setup_webhook(hass: HomeAssistant) -> bool:
    """Set up webhook handler for barcode scanner.
    
    Args:
        hass: Home Assistant instance
        
    Returns:
        True if setup successful
    """
    from homeassistant.components import webhook

    handler = WebhookHandler(hass)

    # Register webhook endpoint
    webhook.async_register(
        hass,
        "Library Catalog",  # Domain
        "Barcode Scanner",  # Name
        WEBHOOK_ID,  # ID
        handler.handle_barcode,  # Handler function
    )

    _LOGGER.info("Webhook registered at %s", WEBHOOK_PATH)
    return True
