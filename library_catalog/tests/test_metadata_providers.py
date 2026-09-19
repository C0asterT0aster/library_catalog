"""Tests for metadata provider fallback and merging strategy."""
from __future__ import annotations

import sys
from unittest.mock import AsyncMock, Mock, MagicMock, patch

import pytest

# Mock Home Assistant modules before importing our code
sys.modules["homeassistant"] = MagicMock()
sys.modules["homeassistant.core"] = MagicMock()
sys.modules["homeassistant.helpers"] = MagicMock()
sys.modules["homeassistant.helpers.aiohttp_client"] = MagicMock()

from custom_components.library_catalog.metadata_providers import (
    MetadataFetcher,
    get_book_metadata,
)
from custom_components.library_catalog.api import (
    BookNotFoundError,
    ISBNValidationError,
    NetworkError,
)
from custom_components.library_catalog.models import BookData


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.data = {}
    return hass


@pytest.fixture
def sample_open_library_data():
    """Sample data from Open Library."""
    return BookData(
        isbn="9780451524935",
        title="1984",
        subtitle="A Novel",
        authors=["George Orwell"],
        publisher="Signet Classic",
        year=1950,
        description="A dystopian novel.",
        cover_url="https://covers.openlibrary.org/b/id/7222246-M.jpg",
        language="eng",
        pages=328,
    )


@pytest.fixture
def sample_google_books_data():
    """Sample data from Google Books."""
    return BookData(
        isbn="9780451524935",
        title="Nineteen Eighty-Four",
        subtitle="A Novel",
        authors=["George Orwell"],
        publisher="Signet Classics",
        year=1950,
        description="A dystopian social science fiction novel and cautionary tale about the dangers of totalitarianism.",
        cover_url="https://books.google.com/books/content?id=1234-M.jpg",
        language="en",
        pages=328,
    )


@pytest.fixture
def insufficient_open_library_data():
    """Insufficient data from Open Library (missing key fields)."""
    return BookData(
        isbn="9780451524935",
        title="1984",
        authors=["Unknown Author"],  # No real author
        # No publisher, year, description, or cover
    )


@pytest.fixture
def minimal_google_books_data():
    """Minimal but valid data from Google Books."""
    return BookData(
        isbn="9780451524935",
        title="1984",
        authors=["George Orwell"],
        publisher="Penguin",
        year=1949,
    )


class TestMetadataFetcher:
    """Test MetadataFetcher with fallback strategy."""

    @pytest.mark.asyncio
    async def test_primary_provider_success_sufficient_data(
        self, mock_hass, sample_open_library_data
    ):
        """Test that sufficient data from primary provider is returned without fallback."""
        with patch(
            "custom_components.library_catalog.api.OpenLibraryClient"
        ) as mock_ol, patch(
            "custom_components.library_catalog.google_books.GoogleBooksClient"
        ) as mock_gb:
            # Mock primary provider to return sufficient data
            mock_ol_instance = Mock()
            mock_ol_instance.fetch_book_metadata = AsyncMock(
                return_value=sample_open_library_data
            )
            mock_ol.return_value = mock_ol_instance

            # Mock secondary provider (should not be called)
            mock_gb_instance = Mock()
            mock_gb_instance.fetch_book_metadata = AsyncMock()
            mock_gb.return_value = mock_gb_instance

            fetcher = MetadataFetcher(mock_hass)
            result = await fetcher.fetch_book_metadata("9780451524935")

            # Should return Open Library data
            assert result.title == "1984"
            assert result.authors == ["George Orwell"]
            assert result.publisher == "Signet Classic"

            # Secondary provider should NOT have been called
            mock_gb_instance.fetch_book_metadata.assert_not_called()

    @pytest.mark.asyncio
    async def test_primary_provider_insufficient_fallback_to_secondary(
        self, mock_hass, insufficient_open_library_data, sample_google_books_data
    ):
        """Test fallback to secondary provider when primary returns insufficient data."""
        with patch(
            "custom_components.library_catalog.api.OpenLibraryClient"
        ) as mock_ol, patch(
            "custom_components.library_catalog.google_books.GoogleBooksClient"
        ) as mock_gb:
            # Mock primary provider to return insufficient data
            mock_ol_instance = Mock()
            mock_ol_instance.fetch_book_metadata = AsyncMock(
                return_value=insufficient_open_library_data
            )
            mock_ol.return_value = mock_ol_instance

            # Mock secondary provider
            mock_gb_instance = Mock()
            mock_gb_instance.fetch_book_metadata = AsyncMock(
                return_value=sample_google_books_data
            )
            mock_gb.return_value = mock_gb_instance

            fetcher = MetadataFetcher(mock_hass)
            result = await fetcher.fetch_book_metadata("9780451524935")

            # Should have called both providers
            mock_ol_instance.fetch_book_metadata.assert_called_once()
            mock_gb_instance.fetch_book_metadata.assert_called_once()

            # Result should be merged
            assert result.title == "1984"  # From Open Library
            assert result.authors == ["George Orwell"]  # From Google Books (better than "Unknown Author")
            assert result.description is not None  # From Google Books

    @pytest.mark.asyncio
    async def test_primary_provider_not_found_fallback_to_secondary(
        self, mock_hass, sample_google_books_data
    ):
        """Test fallback when primary provider returns BookNotFoundError."""
        with patch(
            "custom_components.library_catalog.api.OpenLibraryClient"
        ) as mock_ol, patch(
            "custom_components.library_catalog.google_books.GoogleBooksClient"
        ) as mock_gb:
            # Mock primary provider to raise BookNotFoundError
            mock_ol_instance = Mock()
            mock_ol_instance.fetch_book_metadata = AsyncMock(
                side_effect=BookNotFoundError("Not found in Open Library")
            )
            mock_ol.return_value = mock_ol_instance

            # Mock secondary provider
            mock_gb_instance = Mock()
            mock_gb_instance.fetch_book_metadata = AsyncMock(
                return_value=sample_google_books_data
            )
            mock_gb.return_value = mock_gb_instance

            fetcher = MetadataFetcher(mock_hass)
            result = await fetcher.fetch_book_metadata("9780451524935")

            # Should return Google Books data
            assert result.title == "Nineteen Eighty-Four"
            assert result.authors == ["George Orwell"]

            # Both providers should have been called
            mock_ol_instance.fetch_book_metadata.assert_called_once()
            mock_gb_instance.fetch_book_metadata.assert_called_once()

    @pytest.mark.asyncio
    async def test_primary_provider_network_error_fallback_to_secondary(
        self, mock_hass, sample_google_books_data
    ):
        """Test fallback when primary provider returns NetworkError."""
        with patch(
            "custom_components.library_catalog.api.OpenLibraryClient"
        ) as mock_ol, patch(
            "custom_components.library_catalog.google_books.GoogleBooksClient"
        ) as mock_gb:
            # Mock primary provider to raise NetworkError
            mock_ol_instance = Mock()
            mock_ol_instance.fetch_book_metadata = AsyncMock(
                side_effect=NetworkError("Network timeout")
            )
            mock_ol.return_value = mock_ol_instance

            # Mock secondary provider
            mock_gb_instance = Mock()
            mock_gb_instance.fetch_book_metadata = AsyncMock(
                return_value=sample_google_books_data
            )
            mock_gb.return_value = mock_gb_instance

            fetcher = MetadataFetcher(mock_hass)
            result = await fetcher.fetch_book_metadata("9780451524935")

            # Should return Google Books data
            assert result.title == "Nineteen Eighty-Four"

    @pytest.mark.asyncio
    async def test_both_providers_not_found(self, mock_hass):
        """Test when both providers return BookNotFoundError."""
        with patch(
            "custom_components.library_catalog.api.OpenLibraryClient"
        ) as mock_ol, patch(
            "custom_components.library_catalog.google_books.GoogleBooksClient"
        ) as mock_gb:
            # Both providers raise BookNotFoundError
            mock_ol_instance = Mock()
            mock_ol_instance.fetch_book_metadata = AsyncMock(
                side_effect=BookNotFoundError("Not found")
            )
            mock_ol.return_value = mock_ol_instance

            mock_gb_instance = Mock()
            mock_gb_instance.fetch_book_metadata = AsyncMock(
                side_effect=BookNotFoundError("Not found")
            )
            mock_gb.return_value = mock_gb_instance

            fetcher = MetadataFetcher(mock_hass)

            with pytest.raises(BookNotFoundError, match="not found"):
                await fetcher.fetch_book_metadata("9780451524935")

    @pytest.mark.asyncio
    async def test_both_providers_network_error(self, mock_hass):
        """Test when both providers return NetworkError."""
        with patch(
            "custom_components.library_catalog.api.OpenLibraryClient"
        ) as mock_ol, patch(
            "custom_components.library_catalog.google_books.GoogleBooksClient"
        ) as mock_gb:
            # Both providers raise NetworkError
            mock_ol_instance = Mock()
            mock_ol_instance.fetch_book_metadata = AsyncMock(
                side_effect=NetworkError("Timeout")
            )
            mock_ol.return_value = mock_ol_instance

            mock_gb_instance = Mock()
            mock_gb_instance.fetch_book_metadata = AsyncMock(
                side_effect=NetworkError("Timeout")
            )
            mock_gb.return_value = mock_gb_instance

            fetcher = MetadataFetcher(mock_hass)

            with pytest.raises(NetworkError, match="network errors"):
                await fetcher.fetch_book_metadata("9780451524935")

    @pytest.mark.asyncio
    async def test_isbn_validation_error_no_fallback(self, mock_hass):
        """Test that ISBN validation errors do not trigger fallback."""
        with patch(
            "custom_components.library_catalog.api.OpenLibraryClient"
        ) as mock_ol, patch(
            "custom_components.library_catalog.google_books.GoogleBooksClient"
        ) as mock_gb:
            # Primary provider raises ISBNValidationError
            mock_ol_instance = Mock()
            mock_ol_instance.fetch_book_metadata = AsyncMock(
                side_effect=ISBNValidationError("Invalid ISBN")
            )
            mock_ol.return_value = mock_ol_instance

            mock_gb_instance = Mock()
            mock_gb_instance.fetch_book_metadata = AsyncMock()
            mock_gb.return_value = mock_gb_instance

            fetcher = MetadataFetcher(mock_hass)

            with pytest.raises(ISBNValidationError):
                await fetcher.fetch_book_metadata("invalid")

            # Secondary provider should NOT have been called
            mock_gb_instance.fetch_book_metadata.assert_not_called()


class TestMetadataMerging:
    """Test metadata merging logic."""

    @pytest.mark.asyncio
    async def test_merge_prefers_real_authors_over_unknown(self, mock_hass):
        """Test that merge prefers real authors over 'Unknown Author'."""
        with patch(
            "custom_components.library_catalog.api.OpenLibraryClient"
        ) as mock_ol, patch(
            "custom_components.library_catalog.google_books.GoogleBooksClient"
        ) as mock_gb:
            # Primary has "Unknown Author"
            primary_data = BookData(
                isbn="9780451524935",
                title="1984",
                authors=["Unknown Author"],
            )

            # Secondary has real author
            secondary_data = BookData(
                isbn="9780451524935",
                title="1984",
                authors=["George Orwell"],
                publisher="Penguin",
            )

            mock_ol_instance = Mock()
            mock_ol_instance.fetch_book_metadata = AsyncMock(return_value=primary_data)
            mock_ol.return_value = mock_ol_instance

            mock_gb_instance = Mock()
            mock_gb_instance.fetch_book_metadata = AsyncMock(return_value=secondary_data)
            mock_gb.return_value = mock_gb_instance

            fetcher = MetadataFetcher(mock_hass)
            result = await fetcher.fetch_book_metadata("9780451524935")

            # Should use real author from Google Books
            assert result.authors == ["George Orwell"]

    @pytest.mark.asyncio
    async def test_merge_prefers_longer_description(self, mock_hass):
        """Test that merge prefers longer descriptions when both providers are used."""
        with patch(
            "custom_components.library_catalog.api.OpenLibraryClient"
        ) as mock_ol, patch(
            "custom_components.library_catalog.google_books.GoogleBooksClient"
        ) as mock_gb:
            # Primary has real author but NO description (insufficient)
            primary_data = BookData(
                isbn="9780451524935",
                title="1984",
                authors=["George Orwell"],
                # No description, publisher, year, or cover - triggers fallback
            )

            # Secondary has longer description
            secondary_data = BookData(
                isbn="9780451524935",
                title="1984",
                authors=["George Orwell"],
                description="A dystopian social science fiction novel and cautionary tale about totalitarianism.",
                publisher="Penguin",
            )

            mock_ol_instance = Mock()
            mock_ol_instance.fetch_book_metadata = AsyncMock(return_value=primary_data)
            mock_ol.return_value = mock_ol_instance

            mock_gb_instance = Mock()
            mock_gb_instance.fetch_book_metadata = AsyncMock(return_value=secondary_data)
            mock_gb.return_value = mock_gb_instance

            fetcher = MetadataFetcher(mock_hass)
            result = await fetcher.fetch_book_metadata("9780451524935")

            # Should use description from Google Books (merged)
            assert "dystopian social science fiction" in result.description
            # Should have merged publisher too
            assert result.publisher == "Penguin"

    @pytest.mark.asyncio
    async def test_merge_fills_missing_fields(self, mock_hass):
        """Test that merge fills missing fields from secondary provider."""
        with patch(
            "custom_components.library_catalog.api.OpenLibraryClient"
        ) as mock_ol, patch(
            "custom_components.library_catalog.google_books.GoogleBooksClient"
        ) as mock_gb:
            # Primary missing several fields
            primary_data = BookData(
                isbn="9780451524935",
                title="1984",
                authors=["George Orwell"],
                # No publisher, year, cover
            )

            # Secondary has those fields
            secondary_data = BookData(
                isbn="9780451524935",
                title="1984",
                authors=["George Orwell"],
                publisher="Penguin",
                year=1949,
                cover_url="https://example.com/cover.jpg",
                pages=328,
            )

            mock_ol_instance = Mock()
            mock_ol_instance.fetch_book_metadata = AsyncMock(return_value=primary_data)
            mock_ol.return_value = mock_ol_instance

            mock_gb_instance = Mock()
            mock_gb_instance.fetch_book_metadata = AsyncMock(return_value=secondary_data)
            mock_gb.return_value = mock_gb_instance

            fetcher = MetadataFetcher(mock_hass)
            result = await fetcher.fetch_book_metadata("9780451524935")

            # Should have fields from Google Books
            assert result.publisher == "Penguin"
            assert result.year == 1949
            assert result.cover_url == "https://example.com/cover.jpg"
            assert result.pages == 328

    @pytest.mark.asyncio
    async def test_merge_prefers_primary_title_unless_generic(self, mock_hass):
        """Test that merge prefers primary title unless it's 'Unknown Title'."""
        with patch(
            "custom_components.library_catalog.api.OpenLibraryClient"
        ) as mock_ol, patch(
            "custom_components.library_catalog.google_books.GoogleBooksClient"
        ) as mock_gb:
            # Primary has generic title
            primary_data = BookData(
                isbn="9780451524935",
                title="Unknown Title",
                authors=["George Orwell"],
            )

            # Secondary has real title
            secondary_data = BookData(
                isbn="9780451524935",
                title="1984",
                authors=["George Orwell"],
            )

            mock_ol_instance = Mock()
            mock_ol_instance.fetch_book_metadata = AsyncMock(return_value=primary_data)
            mock_ol.return_value = mock_ol_instance

            mock_gb_instance = Mock()
            mock_gb_instance.fetch_book_metadata = AsyncMock(return_value=secondary_data)
            mock_gb.return_value = mock_gb_instance

            fetcher = MetadataFetcher(mock_hass)
            result = await fetcher.fetch_book_metadata("9780451524935")

            # Should use real title from Google Books
            assert result.title == "1984"


class TestIsSufficient:
    """Test the _is_sufficient method."""

    def test_sufficient_with_all_fields(self, mock_hass):
        """Test data is sufficient when all fields are present."""
        fetcher = MetadataFetcher(mock_hass)

        data = BookData(
            isbn="9780451524935",
            title="1984",
            authors=["George Orwell"],
            publisher="Penguin",
            year=1949,
            description="A novel.",
            cover_url="https://example.com/cover.jpg",
        )

        assert fetcher._is_sufficient(data) is True

    def test_insufficient_with_unknown_author(self, mock_hass):
        """Test data is insufficient with 'Unknown Author'."""
        fetcher = MetadataFetcher(mock_hass)

        data = BookData(
            isbn="9780451524935",
            title="1984",
            authors=["Unknown Author"],
            publisher="Penguin",
        )

        assert fetcher._is_sufficient(data) is False

    def test_insufficient_without_additional_fields(self, mock_hass):
        """Test data is insufficient without additional fields."""
        fetcher = MetadataFetcher(mock_hass)

        data = BookData(
            isbn="9780451524935",
            title="1984",
            authors=["George Orwell"],
            # No publisher, year, description, cover
        )

        assert fetcher._is_sufficient(data) is False

    def test_sufficient_with_minimal_but_useful_data(self, mock_hass):
        """Test data is sufficient with author and one additional field."""
        fetcher = MetadataFetcher(mock_hass)

        data = BookData(
            isbn="9780451524935",
            title="1984",
            authors=["George Orwell"],
            year=1949,
            # Just year is enough
        )

        assert fetcher._is_sufficient(data) is True


class TestConvenienceFunction:
    """Test the get_book_metadata convenience function."""

    @pytest.mark.asyncio
    async def test_get_book_metadata_success(self, mock_hass, sample_open_library_data):
        """Test convenience function uses MetadataFetcher."""
        with patch(
            "custom_components.library_catalog.metadata_providers.MetadataFetcher"
        ) as mock_fetcher_class:
            mock_fetcher = Mock()
            mock_fetcher.fetch_book_metadata = AsyncMock(
                return_value=sample_open_library_data
            )
            mock_fetcher_class.return_value = mock_fetcher

            result = await get_book_metadata(mock_hass, "9780451524935")

            assert result.title == "1984"
            mock_fetcher.fetch_book_metadata.assert_called_once_with("9780451524935")
