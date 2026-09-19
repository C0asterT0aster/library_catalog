"""Webhook handler for barcode scanner input."""
import logging
from typing import Any, Dict, Optional
from aiohttp import web
from homeassistant.core import HomeAssistant

from .api import validate_isbn, get_book_metadata, ISBNValidationError, BookNotFoundError as APIBookNotFoundError
from .const import DOMAIN, WEBHOOK_ID, WEBHOOK_PATH, WEBHOOK_FIELD_ISBN, WEBHOOK_FIELD_FORMAT
from .models import BarCodeFormat, BookData
from .book_service import DuplicateISBNError, BookNotFoundError

_LOGGER = logging.getLogger(__name__)


class WebhookHandler:
    """Handler for barcode scanner webhook requests.

    This webhook handles the barcode scanning workflow:
    1. Validates the payload
    2. Validates/normalizes the ISBN
    3. Checks whether the book already exists
    4. Looks up metadata if necessary
    5. Returns the normalized result

    Note: The book is NOT stored automatically. Storage requires a physical
    location (room/shelf/compartment) which must be provided separately via
    the add_book service or through a UI workflow.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize webhook handler."""
        self.hass = hass

    async def handle_barcode(self, request: web.Request) -> web.Response:
        """Handle incoming barcode webhook request.

        Accepts JSON POST with flexible field names:
        {
            "isbn": "9780451524935",  # or "isbn_input", "code", "barcode"
            "format": "ISBN13"         # or "barcode_format", "type" (optional)
        }

        Workflow:
        1. Validate payload (JSON, ISBN present)
        2. Validate/normalize ISBN
        3. Check if book already exists in database
        4. If not exists, fetch metadata from APIs
        5. Return complete book data + existence status

        Returns:
            JSON response with:
            - success: bool
            - isbn: normalized ISBN-13
            - exists: whether book is already in catalog
            - book_data: metadata (title, authors, etc.) if available
            - error: error message if failed
        """
        try:
            # Step 1: Parse and validate JSON payload
            try:
                data = await request.json()
            except ValueError as e:
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

            # Step 2: Validate and normalize ISBN
            try:
                normalized_isbn = validate_isbn(isbn_value)
            except ISBNValidationError as e:
                _LOGGER.warning("Invalid ISBN in webhook: %s", str(e))
                return web.json_response(
                    {"success": False, "error": f"Invalid ISBN: {str(e)}"},
                    status=400,
                )

            _LOGGER.info(
                "Barcode validated via webhook: %s (format: %s)",
                normalized_isbn,
                barcode_format.value,
            )

            # Step 3: Check if book already exists
            book_service = self._get_book_service()
            if not book_service:
                _LOGGER.error("Book service not available")
                return web.json_response(
                    {"success": False, "error": "Service not available"},
                    status=503,
                )

            exists = False
            existing_book = None
            book_metadata = None

            try:
                existing_book = await book_service.get_book(normalized_isbn)
                exists = True
                _LOGGER.info("Book already exists in catalog: %s", normalized_isbn)
            except BookNotFoundError:
                # Book doesn't exist - fetch metadata
                _LOGGER.info("Book not in catalog, fetching metadata: %s", normalized_isbn)

                # Step 4: Fetch metadata from APIs
                try:
                    book_metadata = await get_book_metadata(self.hass, normalized_isbn)
                    _LOGGER.info("Metadata fetched successfully: %s - %s", book_metadata.title, normalized_isbn)
                except APIBookNotFoundError as e:
                    _LOGGER.warning("Metadata not found for ISBN %s: %s", normalized_isbn, str(e))
                    return web.json_response(
                        {
                            "success": False,
                            "error": f"Book metadata not found for ISBN {normalized_isbn}",
                            "isbn": normalized_isbn,
                            "exists": False,
                        },
                        status=404,
                    )
                except Exception as e:
                    _LOGGER.error("Failed to fetch metadata: %s", str(e))
                    return web.json_response(
                        {
                            "success": False,
                            "error": f"Failed to fetch book metadata: {str(e)}",
                            "isbn": normalized_isbn,
                            "exists": False,
                        },
                        status=500,
                    )

            # Step 5: Fire event for Home Assistant automations
            self.hass.bus.async_fire(
                "library_catalog_barcode_scanned",
                {
                    "isbn": normalized_isbn,
                    "format": barcode_format.value,
                    "raw_isbn": isbn_value,
                    "exists": exists,
                    "title": existing_book.title if existing_book else (book_metadata.title if book_metadata else None),
                },
            )

            # Build response
            response_data = {
                "success": True,
                "isbn": normalized_isbn,
                "format": barcode_format.value,
                "exists": exists,
            }

            if exists and existing_book:
                # Return existing book data
                response_data["book"] = {
                    "title": existing_book.title,
                    "subtitle": existing_book.subtitle,
                    "authors": existing_book.authors,
                    "publisher": existing_book.publisher,
                    "year": existing_book.year,
                    "description": existing_book.description,
                    "cover_url": existing_book.cover_url,
                    "language": existing_book.language,
                    "pages": existing_book.pages,
                    "location": existing_book.location.to_dict() if existing_book.location else None,
                }
                response_data["message"] = "Book already in catalog"
            elif book_metadata:
                # Return fetched metadata
                response_data["book"] = {
                    "title": book_metadata.title,
                    "subtitle": book_metadata.subtitle,
                    "authors": book_metadata.authors,
                    "publisher": book_metadata.publisher,
                    "year": book_metadata.year,
                    "description": book_metadata.description,
                    "cover_url": book_metadata.cover_url,
                    "language": book_metadata.language,
                    "pages": book_metadata.pages,
                }
                response_data["message"] = "Book metadata retrieved. Use add_book service with location to store."

            return web.json_response(response_data, status=200)

        except Exception as e:
            _LOGGER.error("Error processing webhook request: %s", str(e), exc_info=True)
            return web.json_response(
                {"success": False, "error": "Internal server error"},
                status=500,
            )

    def _get_book_service(self):
        """Get the book service instance from any active entry."""
        for entry_data in self.hass.data.get(DOMAIN, {}).values():
            if isinstance(entry_data, dict) and "book_service" in entry_data:
                return entry_data["book_service"]
        return None

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
                if isinstance(value, str) and value.strip():
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
            "EAN_13": BarCodeFormat.EAN13,  # Underscore variant
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
        DOMAIN,
        "Library Catalog Scanner",
        WEBHOOK_ID,
        handler.handle_barcode,
    )

    _LOGGER.info("Webhook registered at %s", WEBHOOK_PATH)
    return True
