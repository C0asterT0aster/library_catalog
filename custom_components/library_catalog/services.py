"""Service handlers for Library Catalog integration."""
import logging
from datetime import datetime, timezone

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
    ERROR_BOOK_ALREADY_EXISTS,
    ERROR_BOOK_NOT_FOUND,
    MSG_BOOK_ADDED_SUCCESS,
    MSG_BOOK_DELETED_SUCCESS,
)
from .api import get_book_metadata, validate_isbn
from .models import BookEntity, BookLocation

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
        """Handle adding a book to the catalog."""
        isbn = call.data[CONF_ISBN]
        location_data = call.data[CONF_LOCATION]

        try:
            # Validate ISBN
            validated_isbn = validate_isbn(isbn)

            # Get first available database from any entry
            database = _get_database(hass)
            if not database:
                raise ValueError("Library Catalog database not available")

            # Check if book already exists
            existing_book = await database.async_get_book(validated_isbn)
            if existing_book:
                _LOGGER.warning("Book already exists: %s", validated_isbn)
                raise ValueError(ERROR_BOOK_ALREADY_EXISTS)

            # Fetch metadata from APIs
            _LOGGER.info("Fetching metadata for ISBN: %s", validated_isbn)
            book_data = await get_book_metadata(hass, validated_isbn)

            # Create location
            location = BookLocation(
                room=location_data[CONF_ROOM],
                shelf=location_data[CONF_SHELF],
                compartment=location_data[CONF_COMPARTMENT],
            )

            # Create book entity with timestamps
            now = datetime.now(timezone.utc)
            book_entity = BookEntity(
                isbn=book_data.isbn,
                title=book_data.title,
                subtitle=book_data.subtitle,
                authors=book_data.authors,
                publisher=book_data.publisher,
                year=book_data.year,
                description=book_data.description,
                cover_url=book_data.cover_url,
                language=book_data.language,
                pages=book_data.pages,
                location=location,
                created_at=now,
                updated_at=now,
            )

            # Add to database
            await database.async_add_book(book_entity)

            _LOGGER.info("Book added: %s - %s", book_entity.title, validated_isbn)

            # Fire event for automations
            hass.bus.async_fire(
                f"{DOMAIN}_book_added",
                {
                    "isbn": validated_isbn,
                    "title": book_entity.title,
                    "authors": book_entity.authors,
                    "location": {
                        "room": location.room,
                        "shelf": location.shelf,
                        "compartment": location.compartment,
                    },
                }
            )

        except Exception as err:
            _LOGGER.error("Failed to add book: %s", err)
            raise

    async def add_book_manual_service(call: ServiceCall) -> None:
        """Handle adding a book with manual metadata entry (no API calls)."""
        isbn = call.data[CONF_ISBN]
        title = call.data[CONF_TITLE]
        authors = call.data[CONF_AUTHORS]
        location_data = call.data[CONF_LOCATION]

        try:
            # Validate ISBN
            validated_isbn = validate_isbn(isbn)

            database = _get_database(hass)
            if not database:
                raise ValueError("Library Catalog database not available")

            # Check if book already exists
            existing_book = await database.async_get_book(validated_isbn)
            if existing_book:
                _LOGGER.warning("Book already exists: %s", validated_isbn)
                raise ValueError(ERROR_BOOK_ALREADY_EXISTS)

            # Create location
            location = BookLocation(
                room=location_data[CONF_ROOM],
                shelf=location_data[CONF_SHELF],
                compartment=location_data[CONF_COMPARTMENT],
            )

            # Create book entity with manual data
            now = datetime.now(timezone.utc)
            book_entity = BookEntity(
                isbn=validated_isbn,
                title=title,
                subtitle=call.data.get(CONF_SUBTITLE),
                authors=authors,
                publisher=call.data.get(CONF_PUBLISHER),
                year=call.data.get(CONF_YEAR),
                description=call.data.get(CONF_DESCRIPTION),
                cover_url=call.data.get(CONF_COVER_URL),
                language=call.data.get(CONF_LANGUAGE),
                pages=call.data.get(CONF_PAGES),
                location=location,
                created_at=now,
                updated_at=now,
            )

            # Add to database
            await database.async_add_book(book_entity)

            _LOGGER.info("Book added manually: %s - %s", book_entity.title, validated_isbn)

            # Fire event for automations
            hass.bus.async_fire(
                f"{DOMAIN}_book_added",
                {
                    "isbn": validated_isbn,
                    "title": book_entity.title,
                    "authors": book_entity.authors,
                    "location": {
                        "room": location.room,
                        "shelf": location.shelf,
                        "compartment": location.compartment,
                    },
                }
            )

        except Exception as err:
            _LOGGER.error("Failed to add book manually: %s", err)
            raise

    async def search_service(call: ServiceCall) -> dict:
        """Handle searching for books in the catalog."""
        query = call.data[CONF_QUERY]
        search_by = call.data[CONF_SEARCH_BY]
        limit = call.data[CONF_LIMIT]

        try:
            database = _get_database(hass)
            if not database:
                raise ValueError("Library Catalog database not available")

            # Perform search based on type
            if search_by == "title":
                result = await database.async_search_by_title(query, limit=limit)
            elif search_by == "author":
                result = await database.async_search_by_author(query, limit=limit)
            elif search_by == "isbn":
                result = await database.async_search_by_isbn(query, limit=limit)
            elif search_by == "room":
                result = await database.async_search_by_room(query, limit=limit)
            else:
                raise ValueError(f"Invalid search_by value: {search_by}")

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
        """Handle deleting a book from the catalog."""
        isbn = call.data[CONF_ISBN]

        try:
            # Validate ISBN
            validated_isbn = validate_isbn(isbn)

            database = _get_database(hass)
            if not database:
                raise ValueError("Library Catalog database not available")

            # Check if book exists
            existing_book = await database.async_get_book(validated_isbn)
            if not existing_book:
                _LOGGER.warning("Book not found: %s", validated_isbn)
                raise ValueError(ERROR_BOOK_NOT_FOUND)

            # Delete the book
            await database.async_delete_book(validated_isbn)

            _LOGGER.info("Book deleted: %s", validated_isbn)

            # Fire event for automations
            hass.bus.async_fire(
                f"{DOMAIN}_book_deleted",
                {
                    "isbn": validated_isbn,
                    "title": existing_book.title,
                }
            )

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


def _get_database(hass: HomeAssistant):
    """Get the database instance from any active entry."""
    for entry_data in hass.data[DOMAIN].values():
        if isinstance(entry_data, dict) and "database" in entry_data:
            return entry_data["database"]
    return None
