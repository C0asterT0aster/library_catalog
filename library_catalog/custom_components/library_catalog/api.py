"""API client for fetching book metadata from Open Library.

This module provides async methods to fetch book metadata using ISBN.
It uses Home Assistant's aiohttp client session and handles all error cases gracefully.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    OPEN_LIBRARY_API_URL,
    OPEN_LIBRARY_TIMEOUT,
    HTTP_RETRIES,
    HTTP_RETRY_DELAY,
)
from .models import BookData
from .validation import ISBNValidator, ValidationError

_LOGGER = logging.getLogger(__name__)


# Export validation function for webhook
def validate_isbn(isbn: str) -> str:
    """Validate and normalize ISBN.

    Args:
        isbn: ISBN-10 or ISBN-13 string

    Returns:
        Normalized ISBN-13 string

    Raises:
        ISBNValidationError: If ISBN is invalid
    """
    try:
        return ISBNValidator.validate(isbn)
    except ValidationError as err:
        raise ISBNValidationError(f"Invalid ISBN: {err}") from err


class APIError(Exception):
    """Base exception for API errors."""


class ISBNValidationError(APIError):
    """Raised when ISBN validation fails."""


class BookNotFoundError(APIError):
    """Raised when book data cannot be found."""


class NetworkError(APIError):
    """Raised when network request fails."""


class OpenLibraryClient:
    """Async client for Open Library API.

    This client uses Home Assistant's shared aiohttp session and implements
    proper retry logic, timeout handling, and graceful error handling.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the Open Library client.

        Args:
            hass: Home Assistant instance for accessing shared HTTP session
        """
        self._hass = hass
        self._session = async_get_clientsession(hass)

    async def fetch_book_metadata(self, isbn_input: str) -> BookData:
        """Fetch book metadata from Open Library by ISBN.

        This is the main entry point for fetching book data. It handles:
        - ISBN validation and normalization
        - API request with retry logic
        - Response parsing and normalization
        - All error cases gracefully

        Args:
            isbn_input: ISBN-10 or ISBN-13 (with or without hyphens/spaces)

        Returns:
            BookData object with normalized metadata

        Raises:
            ISBNValidationError: If ISBN format is invalid
            BookNotFoundError: If book is not found in Open Library
            NetworkError: If network request fails after retries
        """
        # Step 1: Validate and normalize ISBN
        try:
            isbn = ISBNValidator.validate(isbn_input)
            _LOGGER.debug("Validated ISBN: %s -> %s", isbn_input, isbn)
        except ValidationError as err:
            _LOGGER.warning("Invalid ISBN provided: %s", isbn_input)
            raise ISBNValidationError(f"Invalid ISBN: {err}") from err

        # Step 2: Fetch from API with retry logic
        raw_data = await self._fetch_with_retry(isbn)

        if raw_data is None:
            raise BookNotFoundError(f"Book not found for ISBN {isbn}")

        # Step 3: Normalize response to BookData
        try:
            book_data = self._normalize_response(raw_data, isbn)
            _LOGGER.info(
                "Successfully fetched book: '%s' (ISBN: %s)",
                book_data.title,
                isbn,
            )
            return book_data
        except Exception as err:
            _LOGGER.error("Error normalizing Open Library response: %s", err)
            raise APIError(f"Failed to parse API response: {err}") from err

    async def _fetch_with_retry(
        self, isbn: str, retry_count: int = 0
    ) -> dict[str, Any] | None:
        """Fetch data from Open Library with retry logic.

        Args:
            isbn: Validated ISBN-13
            retry_count: Current retry attempt (internal)

        Returns:
            Raw API response dict or None if not found

        Raises:
            NetworkError: If all retries fail
        """
        url = f"{OPEN_LIBRARY_API_URL}/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
        timeout = ClientTimeout(total=OPEN_LIBRARY_TIMEOUT)

        try:
            async with self._session.get(url, timeout=timeout) as response:
                # Check HTTP status
                if response.status == 404:
                    _LOGGER.debug("Book not found in Open Library (404): %s", isbn)
                    return None

                if response.status == 503:
                    _LOGGER.warning("Open Library service unavailable (503)")
                    # Retry on 503
                    if retry_count < HTTP_RETRIES:
                        await asyncio.sleep(HTTP_RETRY_DELAY * (retry_count + 1))
                        return await self._fetch_with_retry(isbn, retry_count + 1)
                    raise NetworkError("Open Library service unavailable")

                # Raise for other HTTP errors (4xx, 5xx)
                response.raise_for_status()

                # Validate content type
                content_type = response.headers.get("Content-Type", "")
                if "application/json" not in content_type:
                    _LOGGER.warning(
                        "Unexpected content type from Open Library: %s", content_type
                    )
                    return None

                # Parse JSON response
                data = await response.json()

                # Open Library returns: {"ISBN:9780451524935": {...}}
                # Extract the book data
                result = data.get(f"ISBN:{isbn}")

                if result:
                    _LOGGER.debug("Found book data in Open Library for ISBN %s", isbn)
                    return result
                else:
                    _LOGGER.debug(
                        "No book data in Open Library response for ISBN %s", isbn
                    )
                    return None

        except asyncio.TimeoutError as err:
            _LOGGER.warning("Timeout fetching from Open Library for ISBN %s", isbn)

            # Retry on timeout
            if retry_count < HTTP_RETRIES:
                await asyncio.sleep(HTTP_RETRY_DELAY * (retry_count + 1))
                return await self._fetch_with_retry(isbn, retry_count + 1)

            raise NetworkError(f"Timeout after {HTTP_RETRIES} retries") from err

        except ClientResponseError as err:
            _LOGGER.warning(
                "HTTP error %d from Open Library for ISBN %s", err.status, isbn
            )

            # Don't retry on 4xx client errors (except 404 handled above)
            if 400 <= err.status < 500:
                return None

            # Retry on 5xx server errors
            if retry_count < HTTP_RETRIES:
                await asyncio.sleep(HTTP_RETRY_DELAY * (retry_count + 1))
                return await self._fetch_with_retry(isbn, retry_count + 1)

            raise NetworkError(f"HTTP error {err.status}") from err

        except ClientError as err:
            _LOGGER.warning("Network error fetching from Open Library: %s", err)

            # Retry on network errors
            if retry_count < HTTP_RETRIES:
                await asyncio.sleep(HTTP_RETRY_DELAY * (retry_count + 1))
                return await self._fetch_with_retry(isbn, retry_count + 1)

            raise NetworkError(f"Network error after {HTTP_RETRIES} retries") from err

        except Exception as err:
            _LOGGER.error("Unexpected error fetching from Open Library: %s", err)
            raise NetworkError(f"Unexpected error: {err}") from err

    def _normalize_response(self, raw_data: dict[str, Any], isbn: str) -> BookData:
        """Convert Open Library API response to BookData model.

        Handles missing fields gracefully and extracts all available metadata.

        Open Library API response structure:
        {
            "title": "The Great Gatsby",
            "subtitle": "A Novel",
            "authors": [{"name": "F. Scott Fitzgerald"}],
            "publishers": [{"name": "Scribner"}],
            "publish_date": "April 10, 1925",
            "number_of_pages": 180,
            "languages": [{"key": "/languages/eng"}],
            "cover": {"small": "...", "medium": "...", "large": "..."},
            "notes": "...",
            ...
        }

        Args:
            raw_data: Raw API response dict
            isbn: Validated ISBN-13

        Returns:
            BookData object with normalized fields
        """
        # Extract title (required)
        title = raw_data.get("title", "").strip()
        if not title:
            title = "Unknown Title"

        # Extract subtitle (optional)
        subtitle = raw_data.get("subtitle")
        if subtitle:
            subtitle = subtitle.strip() or None

        # Extract authors (required, must have at least one)
        authors = []
        if "authors" in raw_data:
            for author in raw_data["authors"]:
                if isinstance(author, dict) and "name" in author:
                    name = author["name"].strip()
                    if name:
                        authors.append(name)
                elif isinstance(author, str):
                    name = author.strip()
                    if name:
                        authors.append(name)

        # Fallback to "Unknown Author" if no authors found
        if not authors:
            authors = ["Unknown Author"]

        # Extract publisher (optional)
        publisher = None
        if "publishers" in raw_data and raw_data["publishers"]:
            pub = raw_data["publishers"][0]
            if isinstance(pub, dict) and "name" in pub:
                publisher = pub["name"].strip() or None
            elif isinstance(pub, str):
                publisher = pub.strip() or None

        # Extract publication year (optional)
        year = self._extract_year(raw_data.get("publish_date"))

        # Extract description (optional)
        description = None
        if "notes" in raw_data:
            # Open Library sometimes puts description in "notes"
            description = raw_data["notes"]
            if isinstance(description, dict) and "value" in description:
                description = description["value"]
        elif "description" in raw_data:
            description = raw_data["description"]
            if isinstance(description, dict) and "value" in description:
                description = description["value"]

        if description and isinstance(description, str):
            description = description.strip() or None

        # Extract cover URL (optional)
        cover_url = self._extract_cover_url(raw_data.get("cover"))

        # Extract language (optional)
        language = None
        if "languages" in raw_data and raw_data["languages"]:
            lang = raw_data["languages"][0]
            if isinstance(lang, dict) and "key" in lang:
                # Format: "/languages/eng" -> "eng"
                language = lang["key"].split("/")[-1]
            elif isinstance(lang, str):
                language = lang

        # Extract page count (optional)
        pages = raw_data.get("number_of_pages")
        if isinstance(pages, str):
            try:
                pages = int(pages)
            except ValueError:
                pages = None

        # Create BookData (validation happens in __post_init__)
        return BookData(
            isbn=isbn,
            title=title,
            subtitle=subtitle,
            authors=authors,
            publisher=publisher,
            year=year,
            description=description,
            cover_url=cover_url,
            language=language,
            pages=pages,
        )

    def _extract_year(self, publish_date: Any) -> int | None:
        """Extract publication year from various date formats.

        Open Library returns dates in various formats:
        - "1925"
        - "April 10, 1925"
        - "1925-04-10"
        - "10 April 1925"

        Args:
            publish_date: Date string in various formats

        Returns:
            Year as integer or None if parsing fails
        """
        if not publish_date:
            return None

        date_str = str(publish_date).strip()

        # Try to extract 4-digit year using various methods
        import re

        # Look for 4-digit year (1000-2999)
        year_match = re.search(r'\b([12]\d{3})\b', date_str)
        if year_match:
            try:
                year = int(year_match.group(1))
                # Sanity check: year should be reasonable
                if 1000 <= year <= 2100:
                    return year
            except ValueError:
                pass

        return None

    def _extract_cover_url(self, cover_data: Any) -> str | None:
        """Extract cover image URL from Open Library cover data.

        Open Library returns cover as:
        {
            "small": "https://covers.openlibrary.org/b/id/...-S.jpg",
            "medium": "https://covers.openlibrary.org/b/id/...-M.jpg",
            "large": "https://covers.openlibrary.org/b/id/...-L.jpg"
        }

        Args:
            cover_data: Cover dict from API response

        Returns:
            URL to medium cover image or None
        """
        if not cover_data or not isinstance(cover_data, dict):
            return None

        # Prefer medium size, fallback to large, then small
        for size in ["medium", "large", "small"]:
            if size in cover_data:
                url = cover_data[size]
                if isinstance(url, str) and url.strip():
                    return url.strip()

        return None


async def get_book_metadata(hass: HomeAssistant, isbn: str) -> BookData:
    """Fetch book metadata with intelligent fallback strategy.

    This function uses a multi-provider approach:
    1. Try Open Library first (primary)
    2. If insufficient or error, try Google Books (secondary)
    3. Merge results intelligently
    4. Return best available metadata

    This replaces the old single-provider approach for better data quality.

    Args:
        hass: Home Assistant instance
        isbn: ISBN-10 or ISBN-13

    Returns:
        BookData object with best available metadata

    Raises:
        ISBNValidationError: If ISBN is invalid
        BookNotFoundError: If book not found in any provider
        NetworkError: If all providers fail
    """
    from .metadata_providers import MetadataFetcher

    fetcher = MetadataFetcher(hass)
    return await fetcher.fetch_book_metadata(isbn)
