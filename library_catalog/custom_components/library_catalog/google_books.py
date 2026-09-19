"""Google Books API client for fetching book metadata.

This module provides async methods to fetch book metadata using ISBN from Google Books API.
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
    GOOGLE_BOOKS_API_URL,
    GOOGLE_BOOKS_TIMEOUT,
    HTTP_RETRIES,
    HTTP_RETRY_DELAY,
)
from .models import BookData
from .validation import ISBNValidator, ValidationError

_LOGGER = logging.getLogger(__name__)


class GoogleBooksClient:
    """Async client for Google Books API.

    This client uses Home Assistant's shared aiohttp session and implements
    proper retry logic, timeout handling, and graceful error handling.

    Google Books API does not require an API key for basic ISBN lookups.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the Google Books client.

        Args:
            hass: Home Assistant instance for accessing shared HTTP session
        """
        self._hass = hass
        self._session = async_get_clientsession(hass)

    async def fetch_book_metadata(self, isbn_input: str) -> BookData:
        """Fetch book metadata from Google Books by ISBN.

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
            BookNotFoundError: If book is not found in Google Books
            NetworkError: If network request fails after retries
        """
        # Step 1: Validate and normalize ISBN
        try:
            isbn = ISBNValidator.validate(isbn_input)
            _LOGGER.debug("Validated ISBN for Google Books: %s -> %s", isbn_input, isbn)
        except ValidationError as err:
            _LOGGER.warning("Invalid ISBN provided to Google Books: %s", isbn_input)
            from .api import ISBNValidationError
            raise ISBNValidationError(f"Invalid ISBN: {err}") from err

        # Step 2: Fetch from API with retry logic
        raw_data = await self._fetch_with_retry(isbn)

        if raw_data is None:
            from .api import BookNotFoundError
            raise BookNotFoundError(f"Book not found in Google Books for ISBN {isbn}")

        # Step 3: Normalize response to BookData
        try:
            book_data = self._normalize_response(raw_data, isbn)
            _LOGGER.info(
                "Successfully fetched book from Google Books: '%s' (ISBN: %s)",
                book_data.title,
                isbn,
            )
            return book_data
        except Exception as err:
            _LOGGER.error("Error normalizing Google Books response: %s", err)
            from .api import APIError
            raise APIError(f"Failed to parse Google Books API response: {err}") from err

    async def _fetch_with_retry(
        self, isbn: str, retry_count: int = 0
    ) -> dict[str, Any] | None:
        """Fetch data from Google Books with retry logic.

        Args:
            isbn: Validated ISBN-13
            retry_count: Current retry attempt (internal)

        Returns:
            Raw API response dict or None if not found

        Raises:
            NetworkError: If all retries fail
        """
        # Google Books API: Search by ISBN
        # URL: https://www.googleapis.com/books/v1/volumes?q=isbn:9780451524935
        url = f"{GOOGLE_BOOKS_API_URL}?q=isbn:{isbn}"
        timeout = ClientTimeout(total=GOOGLE_BOOKS_TIMEOUT)

        try:
            async with self._session.get(url, timeout=timeout) as response:
                # Check HTTP status
                if response.status == 404:
                    _LOGGER.debug("Book not found in Google Books (404): %s", isbn)
                    return None

                if response.status == 429:
                    # Rate limited
                    _LOGGER.warning("Google Books API rate limited (429)")
                    if retry_count < HTTP_RETRIES:
                        # Exponential backoff for rate limiting
                        await asyncio.sleep(HTTP_RETRY_DELAY * (2 ** retry_count))
                        return await self._fetch_with_retry(isbn, retry_count + 1)
                    from .api import NetworkError
                    raise NetworkError("Google Books API rate limit exceeded")

                if response.status == 503:
                    _LOGGER.warning("Google Books service unavailable (503)")
                    if retry_count < HTTP_RETRIES:
                        await asyncio.sleep(HTTP_RETRY_DELAY * (retry_count + 1))
                        return await self._fetch_with_retry(isbn, retry_count + 1)
                    from .api import NetworkError
                    raise NetworkError("Google Books service unavailable")

                # Raise for other HTTP errors (4xx, 5xx)
                response.raise_for_status()

                # Validate content type
                content_type = response.headers.get("Content-Type", "")
                if "application/json" not in content_type:
                    _LOGGER.warning(
                        "Unexpected content type from Google Books: %s", content_type
                    )
                    return None

                # Parse JSON response
                data = await response.json()

                # Google Books returns: {"totalItems": 1, "items": [{...}]}
                total_items = data.get("totalItems", 0)

                if total_items == 0:
                    _LOGGER.debug(
                        "No book data in Google Books response for ISBN %s", isbn
                    )
                    return None

                items = data.get("items", [])
                if not items or len(items) == 0:
                    _LOGGER.debug("Empty items list in Google Books response")
                    return None

                # Return the first item (most relevant)
                result = items[0]
                _LOGGER.debug("Found book data in Google Books for ISBN %s", isbn)
                return result

        except asyncio.TimeoutError as err:
            _LOGGER.warning("Timeout fetching from Google Books for ISBN %s", isbn)

            # Retry on timeout
            if retry_count < HTTP_RETRIES:
                await asyncio.sleep(HTTP_RETRY_DELAY * (retry_count + 1))
                return await self._fetch_with_retry(isbn, retry_count + 1)

            from .api import NetworkError
            raise NetworkError(f"Timeout after {HTTP_RETRIES} retries") from err

        except ClientResponseError as err:
            _LOGGER.warning(
                "HTTP error %d from Google Books for ISBN %s", err.status, isbn
            )

            # Don't retry on 4xx client errors (except 429 handled above)
            if 400 <= err.status < 500:
                return None

            # Retry on 5xx server errors
            if retry_count < HTTP_RETRIES:
                await asyncio.sleep(HTTP_RETRY_DELAY * (retry_count + 1))
                return await self._fetch_with_retry(isbn, retry_count + 1)

            from .api import NetworkError
            raise NetworkError(f"HTTP error {err.status}") from err

        except ClientError as err:
            _LOGGER.warning("Network error fetching from Google Books: %s", err)

            # Retry on network errors
            if retry_count < HTTP_RETRIES:
                await asyncio.sleep(HTTP_RETRY_DELAY * (retry_count + 1))
                return await self._fetch_with_retry(isbn, retry_count + 1)

            from .api import NetworkError
            raise NetworkError(f"Network error after {HTTP_RETRIES} retries") from err

        except Exception as err:
            _LOGGER.error("Unexpected error fetching from Google Books: %s", err)
            from .api import NetworkError
            raise NetworkError(f"Unexpected error: {err}") from err

    def _normalize_response(self, raw_data: dict[str, Any], isbn: str) -> BookData:
        """Convert Google Books API response to BookData model.

        Handles missing fields gracefully and extracts all available metadata.

        Google Books API response structure:
        {
            "volumeInfo": {
                "title": "The Great Gatsby",
                "subtitle": "A Novel",
                "authors": ["F. Scott Fitzgerald"],
                "publisher": "Scribner",
                "publishedDate": "1925-04-10",
                "pageCount": 180,
                "language": "en",
                "imageLinks": {
                    "smallThumbnail": "http://...",
                    "thumbnail": "http://..."
                },
                "description": "...",
                ...
            }
        }

        Args:
            raw_data: Raw API response dict (single item from "items" array)
            isbn: Validated ISBN-13

        Returns:
            BookData object with normalized fields
        """
        # Extract volumeInfo
        volume_info = raw_data.get("volumeInfo", {})

        # Extract title (required)
        title = volume_info.get("title", "").strip()
        if not title:
            title = "Unknown Title"

        # Extract subtitle (optional)
        subtitle = volume_info.get("subtitle")
        if subtitle:
            subtitle = subtitle.strip() or None

        # Extract authors (required, must have at least one)
        authors = []
        if "authors" in volume_info:
            for author in volume_info["authors"]:
                if isinstance(author, str):
                    name = author.strip()
                    if name:
                        authors.append(name)

        # Fallback to "Unknown Author" if no authors found
        if not authors:
            authors = ["Unknown Author"]

        # Extract publisher (optional)
        publisher = volume_info.get("publisher")
        if publisher and isinstance(publisher, str):
            publisher = publisher.strip() or None

        # Extract publication year (optional)
        year = self._extract_year(volume_info.get("publishedDate"))

        # Extract description (optional)
        description = volume_info.get("description")
        if description and isinstance(description, str):
            description = description.strip() or None

        # Extract cover URL (optional)
        cover_url = self._extract_cover_url(volume_info.get("imageLinks"))

        # Extract language (optional)
        language = volume_info.get("language")
        if language and isinstance(language, str):
            language = language.strip() or None

        # Extract page count (optional)
        pages = volume_info.get("pageCount")
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

    def _extract_year(self, published_date: Any) -> int | None:
        """Extract publication year from various date formats.

        Google Books returns dates in various formats:
        - "1925"
        - "1925-04-10"
        - "1925-04"

        Args:
            published_date: Date string in various formats

        Returns:
            Year as integer or None if parsing fails
        """
        if not published_date:
            return None

        date_str = str(published_date).strip()

        # Try to extract 4-digit year
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

    def _extract_cover_url(self, image_links: Any) -> str | None:
        """Extract cover image URL from Google Books image links.

        Google Books returns imageLinks as:
        {
            "smallThumbnail": "http://...",
            "thumbnail": "http://...",
            "small": "http://...",
            "medium": "http://...",
            "large": "http://...",
            "extraLarge": "http://..."
        }

        Args:
            image_links: ImageLinks dict from API response

        Returns:
            URL to cover image or None
        """
        if not image_links or not isinstance(image_links, dict):
            return None

        # Prefer higher quality images, fallback to lower
        for size in ["large", "medium", "thumbnail", "smallThumbnail", "small", "extraLarge"]:
            if size in image_links:
                url = image_links[size]
                if isinstance(url, str) and url.strip():
                    # Google Books returns HTTP URLs, upgrade to HTTPS
                    url = url.strip()
                    if url.startswith("http://"):
                        url = url.replace("http://", "https://", 1)
                    return url

        return None


async def get_book_metadata_google(hass: HomeAssistant, isbn: str) -> BookData:
    """Convenience function to fetch book metadata from Google Books.

    Args:
        hass: Home Assistant instance
        isbn: ISBN-10 or ISBN-13

    Returns:
        BookData object

    Raises:
        ISBNValidationError: If ISBN is invalid
        BookNotFoundError: If book not found
        NetworkError: If network request fails
    """
    client = GoogleBooksClient(hass)
    return await client.fetch_book_metadata(isbn)
