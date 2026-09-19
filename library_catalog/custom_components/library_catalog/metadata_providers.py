"""Metadata provider abstraction and fallback strategy for book data sources.

This module provides a unified interface for fetching book metadata from multiple
sources with intelligent fallback and merging logic.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

from homeassistant.core import HomeAssistant

from .models import BookData

_LOGGER = logging.getLogger(__name__)


class MetadataProvider(ABC):
    """Abstract base class for metadata providers."""

    @abstractmethod
    async def fetch_book_metadata(self, isbn: str) -> BookData:
        """Fetch book metadata by ISBN.

        Args:
            isbn: ISBN-10 or ISBN-13

        Returns:
            BookData object

        Raises:
            ISBNValidationError: If ISBN is invalid
            BookNotFoundError: If book not found
            NetworkError: If network request fails
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of this provider."""
        pass


class MetadataFetcher:
    """Fetches book metadata with fallback strategy and intelligent merging.

    Strategy:
    1. Try primary provider (Open Library)
    2. If result is insufficient or error, try secondary provider (Google Books)
    3. Merge results to create best possible metadata
    4. Return normalized result or clear error
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the metadata fetcher.

        Args:
            hass: Home Assistant instance
        """
        self._hass = hass

        # Lazy import to avoid circular dependencies
        from .api import OpenLibraryClient
        from .google_books import GoogleBooksClient

        self._primary = OpenLibraryClient(hass)
        self._secondary = GoogleBooksClient(hass)

    async def fetch_book_metadata(self, isbn: str) -> BookData:
        """Fetch book metadata with fallback strategy.

        Tries Open Library first, falls back to Google Books if needed,
        and merges results intelligently.

        Args:
            isbn: ISBN-10 or ISBN-13

        Returns:
            BookData object with best available metadata

        Raises:
            ISBNValidationError: If ISBN format is invalid
            BookNotFoundError: If book not found in any provider
            NetworkError: If all providers fail with network errors
        """
        from .api import BookNotFoundError, ISBNValidationError, NetworkError

        primary_data: Optional[BookData] = None
        secondary_data: Optional[BookData] = None
        primary_error: Optional[Exception] = None
        secondary_error: Optional[Exception] = None

        # Step 1: Try primary provider (Open Library)
        try:
            _LOGGER.debug("Fetching metadata from Open Library")
            primary_data = await self._primary.fetch_book_metadata(isbn)
            _LOGGER.info("Successfully fetched metadata from Open Library")

            # Check if data is sufficient
            if self._is_sufficient(primary_data):
                _LOGGER.debug("Open Library data is sufficient, returning")
                return primary_data

            _LOGGER.debug("Open Library data is insufficient, will try fallback")

        except ISBNValidationError:
            # ISBN validation errors should not trigger fallback
            _LOGGER.error("ISBN validation failed")
            raise

        except BookNotFoundError as err:
            _LOGGER.info("Book not found in Open Library, trying fallback")
            primary_error = err

        except NetworkError as err:
            _LOGGER.warning("Network error with Open Library: %s", err)
            primary_error = err

        except Exception as err:
            _LOGGER.error("Unexpected error with Open Library: %s", err)
            primary_error = err

        # Step 2: Try secondary provider (Google Books)
        try:
            _LOGGER.debug("Fetching metadata from Google Books")
            secondary_data = await self._secondary.fetch_book_metadata(isbn)
            _LOGGER.info("Successfully fetched metadata from Google Books")

        except ISBNValidationError:
            # ISBN validation errors should not happen here (already validated)
            _LOGGER.error("ISBN validation failed in Google Books (unexpected)")
            raise

        except BookNotFoundError as err:
            _LOGGER.info("Book not found in Google Books")
            secondary_error = err

        except NetworkError as err:
            _LOGGER.warning("Network error with Google Books: %s", err)
            secondary_error = err

        except Exception as err:
            _LOGGER.error("Unexpected error with Google Books: %s", err)
            secondary_error = err

        # Step 3: Merge results or raise appropriate error
        if primary_data and secondary_data:
            # Both providers returned data - merge them
            _LOGGER.info("Merging metadata from Open Library and Google Books")
            return self._merge_metadata(primary_data, secondary_data)

        elif primary_data:
            # Only primary provider returned data
            _LOGGER.info("Using Open Library data only")
            return primary_data

        elif secondary_data:
            # Only secondary provider returned data
            _LOGGER.info("Using Google Books data only")
            return secondary_data

        else:
            # Neither provider returned data - raise appropriate error
            _LOGGER.error("No metadata found from any provider")

            # If both failed with BookNotFoundError, raise that
            if isinstance(primary_error, BookNotFoundError) and isinstance(
                secondary_error, BookNotFoundError
            ):
                raise BookNotFoundError(
                    f"Book not found in Open Library or Google Books for ISBN {isbn}"
                )

            # If both failed with NetworkError, raise that
            if isinstance(primary_error, NetworkError) and isinstance(
                secondary_error, NetworkError
            ):
                raise NetworkError(
                    "All book data providers failed due to network errors"
                )

            # Mixed errors or unexpected - raise generic BookNotFoundError
            raise BookNotFoundError(
                f"Failed to fetch book metadata for ISBN {isbn}"
            )

    def _is_sufficient(self, data: BookData) -> bool:
        """Check if metadata is sufficient to use without fallback.

        A result is considered sufficient if it has:
        - Title (always present in BookData)
        - At least one real author (not "Unknown Author")
        - At least one additional useful field (publisher, year, description, or cover)

        Args:
            data: BookData object

        Returns:
            True if data is sufficient, False otherwise
        """
        # Title is always present (required in BookData)

        # Check for real authors (not fallback)
        has_real_authors = (
            data.authors
            and len(data.authors) > 0
            and data.authors[0] != "Unknown Author"
        )

        if not has_real_authors:
            return False

        # Check for at least one additional useful field
        has_additional_data = any(
            [
                data.publisher,
                data.year,
                data.description,
                data.cover_url,
                data.pages and data.pages > 0,
            ]
        )

        return has_additional_data

    def _merge_metadata(
        self, primary: BookData, secondary: BookData
    ) -> BookData:
        """Merge metadata from two providers intelligently.

        Strategy:
        - Always use primary ISBN (they should match)
        - Prefer primary title unless it's generic
        - Prefer real authors over "Unknown Author"
        - Fill missing fields from secondary source
        - Prefer longer descriptions
        - Prefer cover URLs that exist

        Args:
            primary: BookData from primary provider (Open Library)
            secondary: BookData from secondary provider (Google Books)

        Returns:
            Merged BookData object
        """
        _LOGGER.debug("Merging metadata from two providers")

        # ISBN (use primary, they should match)
        isbn = primary.isbn

        # Title - prefer primary unless it's generic
        title = primary.title
        if title == "Unknown Title" and secondary.title != "Unknown Title":
            title = secondary.title

        # Subtitle - prefer non-empty
        subtitle = primary.subtitle or secondary.subtitle

        # Authors - prefer real authors over "Unknown Author"
        authors = primary.authors
        if authors == ["Unknown Author"] and secondary.authors != ["Unknown Author"]:
            authors = secondary.authors
        elif not authors:
            authors = secondary.authors

        # Publisher - prefer non-empty
        publisher = primary.publisher or secondary.publisher

        # Year - prefer non-None
        year = primary.year or secondary.year

        # Description - prefer longer description
        description = primary.description
        if secondary.description:
            if not description or len(secondary.description) > len(description):
                description = secondary.description

        # Cover URL - prefer non-empty
        cover_url = primary.cover_url or secondary.cover_url

        # Language - prefer non-empty
        language = primary.language or secondary.language

        # Pages - prefer non-None and non-zero
        pages = primary.pages
        if not pages or pages == 0:
            pages = secondary.pages

        _LOGGER.debug(
            "Merged metadata: title=%s, authors=%s, has_description=%s, has_cover=%s",
            title,
            authors,
            bool(description),
            bool(cover_url),
        )

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


async def get_book_metadata(hass: HomeAssistant, isbn: str) -> BookData:
    """Fetch book metadata with intelligent fallback and merging.

    This is the main entry point for fetching book metadata.
    It tries Open Library first, falls back to Google Books if needed,
    and merges results intelligently.

    Args:
        hass: Home Assistant instance
        isbn: ISBN-10 or ISBN-13

    Returns:
        BookData object with best available metadata

    Raises:
        ISBNValidationError: If ISBN format is invalid
        BookNotFoundError: If book not found in any provider
        NetworkError: If all providers fail with network errors
    """
    fetcher = MetadataFetcher(hass)
    return await fetcher.fetch_book_metadata(isbn)
