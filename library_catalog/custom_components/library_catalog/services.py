"""Service handlers for Library Catalog integration.

These handlers are thin wrappers around the book service layer.
They handle Home Assistant-specific concerns (service schemas, event firing)
and delegate all business logic to LibraryBookService.
"""
import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    SERVICE_ADD_BOOK,
    SERVICE_ADD_BOOK_MANUAL,
    SERVICE_SEARCH,
    SERVICE_DELETE_BOOK,
    CONF_ISBN,
    CONF_LOCATION,
    CONF_ROOM,
    CONF_SHELF,
    CONF_COMPARTMENT,
    CONF_QUERY,
    CONF_SEARCH_BY,
    CONF_LIMIT,
    CONF_TITLE,
    CONF_SUBTITLE,
    CONF_AUTHORS,
    CONF_PUBLISHER,
    CONF_YEAR,
    CONF_DESCRIPTION,
    CONF_COVER_URL,
    CONF_LANGUAGE,
    CONF_PAGES,
    SEARCH_DEFAULT_LIMIT,
)
from .models import BookLocation
from .book_service import DuplicateISBNError, BookNotFoundError

_LOGGER = logging.getLogger(__name__)

# Service schemas
LOCATION_SCHEMA = vol.Schema({
    vol.Required(CONF_ROOM): cv.string,
    vol.Required(CONF_SHELF): cv.string,
    vol.Required(CONF_COMPARTMENT): cv.string,
})

ADD_BOOK_SCHEMA = vol.Schema({
    vol.Required(CONF_ISBN): cv.string,
    vol.Required(CONF_LOCATION): LOCATION_SCHEMA,
})

SEARCH_SCHEMA = vol.Schema({
    vol.Required(CONF_QUERY): cv.string,
    vol.Optional(CONF_SEARCH_BY, default="title"): vol.In(["title", "author", "isbn", "room"]),
    vol.Optional(CONF_LIMIT, default=SEARCH_DEFAULT_LIMIT): cv.positive_int,
})

DELETE_BOOK_SCHEMA = vol.Schema({
    vol.Required(CONF_ISBN): cv.string,
})

ADD_BOOK_MANUAL_SCHEMA = vol.Schema({
    vol.Required(CONF_ISBN): cv.string,
    vol.Required(CONF_TITLE): cv.string,
    vol.Required(CONF_AUTHORS): cv.ensure_list,
    vol.Required(CONF_LOCATION): LOCATION_SCHEMA,
    vol.Optional(CONF_SUBTITLE): cv.string,
    vol.Optional(CONF_PUBLISHER): cv.string,
    vol.Optional(CONF_YEAR): cv.positive_int,
    vol.Optional(CONF_DESCRIPTION): cv.string,
    vol.Optional(CONF_COVER_URL): cv.url,
    vol.Optional(CONF_LANGUAGE): cv.string,
    vol.Optional(CONF_PAGES): cv.positive_int,
})


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for the Library Catalog integration."""

    async def add_book_service(call: ServiceCall) -> None:
        """Handle adding a book via ISBN lookup.

        This is a thin wrapper that:
        1. Extracts parameters from service call
        2. Delegates to book_service.add_book_by_isbn()
        3. Fires Home Assistant event on success
        """
        isbn = call.data[CONF_ISBN]
        location_data = call.data[CONF_LOCATION]

        try:
            # Get book service
            book_service = _get_book_service(hass)
            if not book_service:
                raise ValueError("Library Catalog not available")

            # Create location
            location = BookLocation(
                room=location_data[CONF_ROOM],
                shelf=location_data[CONF_SHELF],
                compartment=location_data[CONF_COMPARTMENT],
            )

            # Delegate to service layer
            book_entity = await book_service.add_book_by_isbn(isbn, location)

            # Fire Home Assistant event for automations
            hass.bus.async_fire(
                f"{DOMAIN}_book_added",
                {
                    "isbn": book_entity.isbn,
                    "title": book_entity.title,
                    "authors": book_entity.authors,
                    "location": {
                        "room": location.room,
                        "shelf": location.shelf,
                        "compartment": location.compartment,
                    },
                }
            )

        except DuplicateISBNError as err:
            _LOGGER.warning("Duplicate ISBN: %s", err.message)
            raise ValueError(err.message) from err
        except BookNotFoundError as err:
            _LOGGER.error("Book not found: %s", err.message)
            raise ValueError(err.message) from err
        except Exception as err:
            _LOGGER.error("Failed to add book: %s", err)
            raise

    async def add_book_manual_service(call: ServiceCall) -> None:
        """Handle adding a book with manual metadata.

        This is a thin wrapper that:
        1. Extracts parameters from service call
        2. Delegates to book_service.add_book_manual()
        3. Fires Home Assistant event on success
        """
        isbn = call.data[CONF_ISBN]
        title = call.data[CONF_TITLE]
        authors = call.data[CONF_AUTHORS]
        location_data = call.data[CONF_LOCATION]

        try:
            # Get book service
            book_service = _get_book_service(hass)
            if not book_service:
                raise ValueError("Library Catalog not available")

            # Create location
            location = BookLocation(
                room=location_data[CONF_ROOM],
                shelf=location_data[CONF_SHELF],
                compartment=location_data[CONF_COMPARTMENT],
            )

            # Delegate to service layer
            book_entity = await book_service.add_book_manual(
                isbn=isbn,
                title=title,
                authors=authors,
                location=location,
                subtitle=call.data.get(CONF_SUBTITLE),
                publisher=call.data.get(CONF_PUBLISHER),
                year=call.data.get(CONF_YEAR),
                description=call.data.get(CONF_DESCRIPTION),
                cover_url=call.data.get(CONF_COVER_URL),
                language=call.data.get(CONF_LANGUAGE),
                pages=call.data.get(CONF_PAGES),
            )

            # Fire Home Assistant event for automations
            hass.bus.async_fire(
                f"{DOMAIN}_book_added",
                {
                    "isbn": book_entity.isbn,
                    "title": book_entity.title,
                    "authors": book_entity.authors,
                    "location": {
                        "room": location.room,
                        "shelf": location.shelf,
                        "compartment": location.compartment,
                    },
                }
            )

        except DuplicateISBNError as err:
            _LOGGER.warning("Duplicate ISBN: %s", err.message)
            raise ValueError(err.message) from err
        except Exception as err:
            _LOGGER.error("Failed to add book manually: %s", err)
            raise

    async def search_service(call: ServiceCall) -> dict:
        """Handle searching for books.

        This is a thin wrapper that:
        1. Extracts parameters from service call
        2. Delegates to book_service.search_books()
        3. Formats response for Home Assistant
        """
        query = call.data[CONF_QUERY]
        search_by = call.data[CONF_SEARCH_BY]
        limit = call.data[CONF_LIMIT]

        try:
            # Get book service
            book_service = _get_book_service(hass)
            if not book_service:
                raise ValueError("Library Catalog not available")

            # Delegate to service layer
            result = await book_service.search_books(query, search_by, limit)

            _LOGGER.info(
                "Search completed: %d results for '%s' (search_by=%s)",
                len(result.books),
                query,
                search_by,
            )

            # Convert to service response format
            books_list = [
                {
                    "isbn": book.isbn,
                    "title": book.title,
                    "subtitle": book.subtitle,
                    "authors": book.authors,
                    "publisher": book.publisher,
                    "year": book.year,
                    "description": book.description,
                    "cover_url": book.cover_url,
                    "language": book.language,
                    "pages": book.pages,
                    "location": {
                        "room": book.location.room,
                        "shelf": book.location.shelf,
                        "compartment": book.location.compartment,
                    } if book.location else None,
                }
                for book in result.books
            ]

            return {
                "books": books_list,
                "total_count": result.total_count,
                "query": query,
                "search_type": search_by,
            }

        except Exception as err:
            _LOGGER.error("Failed to search books: %s", err)
            raise

    async def delete_book_service(call: ServiceCall) -> None:
        """Handle deleting a book.

        This is a thin wrapper that:
        1. Extracts parameters from service call
        2. Delegates to book_service.delete_book()
        3. Fires Home Assistant event on success
        """
        isbn = call.data[CONF_ISBN]

        try:
            # Get book service
            book_service = _get_book_service(hass)
            if not book_service:
                raise ValueError("Library Catalog not available")

            # Delegate to service layer
            deleted_book = await book_service.delete_book(isbn)

            _LOGGER.info("Book deleted: %s", isbn)

            # Fire Home Assistant event for automations
            hass.bus.async_fire(
                f"{DOMAIN}_book_deleted",
                {
                    "isbn": deleted_book.isbn,
                    "title": deleted_book.title,
                }
            )

        except BookNotFoundError as err:
            _LOGGER.warning("Book not found: %s", err.message)
            raise ValueError(err.message) from err
        except Exception as err:
            _LOGGER.error("Failed to delete book: %s", err)
            raise

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_BOOK,
        add_book_service,
        schema=ADD_BOOK_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_BOOK_MANUAL,
        add_book_manual_service,
        schema=ADD_BOOK_MANUAL_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEARCH,
        search_service,
        schema=SEARCH_SCHEMA,
        supports_response="optional",
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_BOOK,
        delete_book_service,
        schema=DELETE_BOOK_SCHEMA,
    )

    _LOGGER.info("Library Catalog services registered")


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload services for the Library Catalog integration."""
    hass.services.async_remove(DOMAIN, SERVICE_ADD_BOOK)
    hass.services.async_remove(DOMAIN, SERVICE_ADD_BOOK_MANUAL)
    hass.services.async_remove(DOMAIN, SERVICE_SEARCH)
    hass.services.async_remove(DOMAIN, SERVICE_DELETE_BOOK)
    _LOGGER.info("Library Catalog services unregistered")


def _get_book_service(hass: HomeAssistant):
    """Get the book service instance from any active entry."""
    for entry_data in hass.data[DOMAIN].values():
        if isinstance(entry_data, dict) and "book_service" in entry_data:
            return entry_data["book_service"]
    return None
