"""Tests for Google Books API client."""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, Mock, MagicMock, patch

import pytest
from aiohttp import ClientError, ClientResponseError

# Mock Home Assistant modules before importing our code
sys.modules["homeassistant"] = MagicMock()
sys.modules["homeassistant.core"] = MagicMock()
sys.modules["homeassistant.helpers"] = MagicMock()
sys.modules["homeassistant.helpers.aiohttp_client"] = MagicMock()

from custom_components.library_catalog.google_books import GoogleBooksClient, get_book_metadata_google
from custom_components.library_catalog.api import (
    BookNotFoundError,
    ISBNValidationError,
    NetworkError,
)
from custom_components.library_catalog.models import BookData


# Sample Google Books API responses for testing
SAMPLE_GOOGLE_BOOKS_RESPONSE = {
    "totalItems": 1,
    "items": [
        {
            "volumeInfo": {
                "title": "1984",
                "subtitle": "A Novel",
                "authors": ["George Orwell"],
                "publisher": "Signet Classic",
                "publishedDate": "1950-06",
                "pageCount": 328,
                "language": "eng",
                "imageLinks": {
                    "smallThumbnail": "http://books.google.com/books/content?id=1234-S.jpg",
                    "thumbnail": "http://books.google.com/books/content?id=1234-M.jpg",
                    "small": "http://books.google.com/books/content?id=1234-S.jpg",
                    "medium": "http://books.google.com/books/content?id=1234-M.jpg",
                    "large": "http://books.google.com/books/content?id=1234-L.jpg",
                },
                "description": "A dystopian social science fiction novel and cautionary tale.",
            }
        }
    ],
}

SAMPLE_MINIMAL_RESPONSE = {
    "totalItems": 1,
    "items": [
        {
            "volumeInfo": {
                "title": "The Catcher in the Rye",
                "authors": ["J.D. Salinger"],
            }
        }
    ],
}

SAMPLE_MISSING_AUTHORS_RESPONSE = {
    "totalItems": 1,
    "items": [
        {
            "volumeInfo": {
                "title": "The Great Gatsby",
                # No authors field - should default to "Unknown Author"
            }
        }
    ],
}

SAMPLE_EMPTY_RESPONSE = {
    "totalItems": 0,
    "items": [],
}

SAMPLE_NO_ITEMS_RESPONSE = {
    "totalItems": 0,
}


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.data = {}
    return hass


@pytest.fixture
def mock_session():
    """Create a mock aiohttp ClientSession."""
    session = Mock()
    return session


def create_mock_response(status, json_data=None, content_type="application/json"):
    """Helper to create a properly mocked aiohttp response."""
    response = Mock()
    response.status = status
    response.headers = {"Content-Type": content_type}

    if json_data is not None:
        response.json = AsyncMock(return_value=json_data)

    response.raise_for_status = Mock()

    # Make it work as async context manager
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)

    return response


class TestGoogleBooksClient:
    """Test GoogleBooksClient class."""

    def test_client_initialization(self, mock_hass):
        """Test client initializes with Home Assistant instance."""
        with patch(
            "custom_components.library_catalog.google_books.async_get_clientsession",
            return_value=Mock(),
        ):
            client = GoogleBooksClient(mock_hass)
            assert client._hass == mock_hass
            assert client._session is not None

    @pytest.mark.asyncio
    async def test_fetch_book_metadata_success(self, mock_hass, mock_session):
        """Test successful book metadata fetch."""
        with patch(
            "custom_components.library_catalog.google_books.async_get_clientsession",
            return_value=mock_session,
        ):
            mock_response = create_mock_response(200, SAMPLE_GOOGLE_BOOKS_RESPONSE)
            mock_session.get = Mock(return_value=mock_response)

            client = GoogleBooksClient(mock_hass)
            book_data = await client.fetch_book_metadata("978-0-451-52493-5")

            assert isinstance(book_data, BookData)
            assert book_data.isbn == "9780451524935"
            assert book_data.title == "1984"
            assert book_data.subtitle == "A Novel"
            assert book_data.authors == ["George Orwell"]
            assert book_data.publisher == "Signet Classic"
            assert book_data.year == 1950
            assert book_data.pages == 328
            assert book_data.language == "eng"
            assert "books.google.com" in book_data.cover_url
            assert "https://" in book_data.cover_url  # Should be upgraded to HTTPS
            assert "dystopian" in book_data.description.lower()

    @pytest.mark.asyncio
    async def test_fetch_book_metadata_minimal_data(self, mock_hass, mock_session):
        """Test fetch with minimal data (only title and author)."""
        with patch(
            "custom_components.library_catalog.google_books.async_get_clientsession",
            return_value=mock_session,
        ):
            mock_response = create_mock_response(200, SAMPLE_MINIMAL_RESPONSE)
            mock_session.get = Mock(return_value=mock_response)

            client = GoogleBooksClient(mock_hass)
            book_data = await client.fetch_book_metadata("9780316769174")

            assert book_data.title == "The Catcher in the Rye"
            assert book_data.authors == ["J.D. Salinger"]
            assert book_data.subtitle is None
            assert book_data.publisher is None
            assert book_data.year is None
            assert book_data.pages is None

    @pytest.mark.asyncio
    async def test_fetch_book_metadata_missing_authors(self, mock_hass, mock_session):
        """Test fetch when authors field is missing."""
        with patch(
            "custom_components.library_catalog.google_books.async_get_clientsession",
            return_value=mock_session,
        ):
            mock_response = create_mock_response(200, SAMPLE_MISSING_AUTHORS_RESPONSE)
            mock_session.get = Mock(return_value=mock_response)

            client = GoogleBooksClient(mock_hass)
            book_data = await client.fetch_book_metadata("9780743273565")

            assert book_data.title == "The Great Gatsby"
            assert book_data.authors == ["Unknown Author"]

    @pytest.mark.asyncio
    async def test_fetch_book_metadata_invalid_isbn(self, mock_hass, mock_session):
        """Test fetch with invalid ISBN."""
        with patch(
            "custom_components.library_catalog.google_books.async_get_clientsession",
            return_value=mock_session,
        ):
            client = GoogleBooksClient(mock_hass)

            with pytest.raises(ISBNValidationError, match="Invalid ISBN"):
                await client.fetch_book_metadata("invalid-isbn")

            with pytest.raises(ISBNValidationError, match="Invalid ISBN"):
                await client.fetch_book_metadata("12345")

            with pytest.raises(ISBNValidationError, match="Invalid ISBN"):
                await client.fetch_book_metadata("")

    @pytest.mark.asyncio
    async def test_fetch_book_metadata_not_found(self, mock_hass, mock_session):
        """Test fetch when book is not found (empty response)."""
        with patch(
            "custom_components.library_catalog.google_books.async_get_clientsession",
            return_value=mock_session,
        ):
            mock_response = create_mock_response(200, SAMPLE_EMPTY_RESPONSE)
            mock_session.get = Mock(return_value=mock_response)

            client = GoogleBooksClient(mock_hass)

            with pytest.raises(BookNotFoundError, match="Book not found"):
                await client.fetch_book_metadata("9780451524935")

    @pytest.mark.asyncio
    async def test_fetch_book_metadata_no_items(self, mock_hass, mock_session):
        """Test fetch when response has no items field."""
        with patch(
            "custom_components.library_catalog.google_books.async_get_clientsession",
            return_value=mock_session,
        ):
            mock_response = create_mock_response(200, SAMPLE_NO_ITEMS_RESPONSE)
            mock_session.get = Mock(return_value=mock_response)

            client = GoogleBooksClient(mock_hass)

            with pytest.raises(BookNotFoundError):
                await client.fetch_book_metadata("9780451524935")

    @pytest.mark.asyncio
    async def test_fetch_book_metadata_404(self, mock_hass, mock_session):
        """Test fetch when API returns 404."""
        with patch(
            "custom_components.library_catalog.google_books.async_get_clientsession",
            return_value=mock_session,
        ):
            mock_response = create_mock_response(404)
            mock_session.get = Mock(return_value=mock_response)

            client = GoogleBooksClient(mock_hass)

            with pytest.raises(BookNotFoundError):
                await client.fetch_book_metadata("9780451524935")

    @pytest.mark.asyncio
    async def test_fetch_book_metadata_rate_limited(self, mock_hass, mock_session):
        """Test fetch when API returns 429 (rate limited)."""
        with patch(
            "custom_components.library_catalog.google_books.async_get_clientsession",
            return_value=mock_session,
        ):
            # First 3 calls return 429, then timeout waiting
            mock_response_429 = create_mock_response(429)
            mock_session.get = Mock(return_value=mock_response_429)

            client = GoogleBooksClient(mock_hass)

            with pytest.raises(NetworkError, match="rate limit"):
                await client.fetch_book_metadata("9780451524935")

            # Should have retried 3 times
            assert mock_session.get.call_count == 4  # Initial + 3 retries

    @pytest.mark.asyncio
    async def test_fetch_book_metadata_timeout(self, mock_hass, mock_session):
        """Test fetch when request times out."""
        with patch(
            "custom_components.library_catalog.google_books.async_get_clientsession",
            return_value=mock_session,
        ):
            # Create mock that raises TimeoutError
            mock_response = Mock()
            mock_response.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_response.__aexit__ = AsyncMock(return_value=None)
            mock_session.get = Mock(return_value=mock_response)

            client = GoogleBooksClient(mock_hass)

            with pytest.raises(NetworkError, match="Timeout"):
                await client.fetch_book_metadata("9780451524935")

    @pytest.mark.asyncio
    async def test_fetch_book_metadata_network_error(self, mock_hass, mock_session):
        """Test fetch when network error occurs."""
        with patch(
            "custom_components.library_catalog.google_books.async_get_clientsession",
            return_value=mock_session,
        ):
            # Create mock that raises ClientError
            mock_response = Mock()
            mock_response.__aenter__ = AsyncMock(
                side_effect=ClientError("Connection failed")
            )
            mock_response.__aexit__ = AsyncMock(return_value=None)
            mock_session.get = Mock(return_value=mock_response)

            client = GoogleBooksClient(mock_hass)

            with pytest.raises(NetworkError, match="Network error"):
                await client.fetch_book_metadata("9780451524935")

    @pytest.mark.asyncio
    async def test_fetch_book_metadata_http_503(self, mock_hass, mock_session):
        """Test fetch when API returns 503 service unavailable."""
        with patch(
            "custom_components.library_catalog.google_books.async_get_clientsession",
            return_value=mock_session,
        ):
            mock_response = create_mock_response(503)
            mock_session.get = Mock(return_value=mock_response)

            client = GoogleBooksClient(mock_hass)

            with pytest.raises(NetworkError, match="service unavailable"):
                await client.fetch_book_metadata("9780451524935")

    @pytest.mark.asyncio
    async def test_fetch_book_metadata_http_500(self, mock_hass, mock_session):
        """Test fetch when API returns 500 server error."""
        with patch(
            "custom_components.library_catalog.google_books.async_get_clientsession",
            return_value=mock_session,
        ):
            # Create mock that raises ClientResponseError
            error = ClientResponseError(
                request_info=Mock(),
                history=(),
                status=500,
                message="Internal Server Error",
            )
            mock_response = Mock()
            mock_response.__aenter__ = AsyncMock(side_effect=error)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            mock_session.get = Mock(return_value=mock_response)

            client = GoogleBooksClient(mock_hass)

            with pytest.raises(NetworkError, match="HTTP error"):
                await client.fetch_book_metadata("9780451524935")

    @pytest.mark.asyncio
    async def test_fetch_book_metadata_wrong_content_type(self, mock_hass, mock_session):
        """Test fetch when API returns non-JSON content."""
        with patch(
            "custom_components.library_catalog.google_books.async_get_clientsession",
            return_value=mock_session,
        ):
            mock_response = create_mock_response(200, content_type="text/html")
            mock_session.get = Mock(return_value=mock_response)

            client = GoogleBooksClient(mock_hass)

            with pytest.raises(BookNotFoundError):
                await client.fetch_book_metadata("9780451524935")

    @pytest.mark.asyncio
    async def test_fetch_with_retry_success_after_failure(self, mock_hass, mock_session):
        """Test retry logic succeeds after initial failure."""
        with patch(
            "custom_components.library_catalog.google_books.async_get_clientsession",
            return_value=mock_session,
        ):
            # First call fails with timeout, second succeeds
            timeout_response = Mock()
            timeout_response.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
            timeout_response.__aexit__ = AsyncMock(return_value=None)

            success_response = create_mock_response(200, SAMPLE_GOOGLE_BOOKS_RESPONSE)

            mock_session.get = Mock(side_effect=[timeout_response, success_response])

            client = GoogleBooksClient(mock_hass)
            book_data = await client.fetch_book_metadata("9780451524935")

            assert book_data.title == "1984"
            # Should have been called twice (initial + 1 retry)
            assert mock_session.get.call_count == 2

    @pytest.mark.asyncio
    async def test_http_url_upgraded_to_https(self, mock_hass, mock_session):
        """Test that HTTP cover URLs are upgraded to HTTPS."""
        with patch(
            "custom_components.library_catalog.google_books.async_get_clientsession",
            return_value=mock_session,
        ):
            mock_response = create_mock_response(200, SAMPLE_GOOGLE_BOOKS_RESPONSE)
            mock_session.get = Mock(return_value=mock_response)

            client = GoogleBooksClient(mock_hass)
            book_data = await client.fetch_book_metadata("9780451524935")

            # Verify URL was upgraded from http:// to https://
            assert book_data.cover_url is not None
            assert book_data.cover_url.startswith("https://")
            assert "http://" not in book_data.cover_url


class TestYearExtraction:
    """Test year extraction from various date formats."""

    @pytest.mark.asyncio
    async def test_extract_year_from_year_only(self, mock_hass, mock_session):
        """Test extracting year from 'YYYY' format."""
        with patch(
            "custom_components.library_catalog.google_books.async_get_clientsession",
            return_value=mock_session,
        ):
            response_data = {
                "totalItems": 1,
                "items": [
                    {
                        "volumeInfo": {
                            "title": "Test Book",
                            "authors": ["Test Author"],
                            "publishedDate": "1984",
                        }
                    }
                ],
            }

            mock_response = create_mock_response(200, response_data)
            mock_session.get = Mock(return_value=mock_response)

            client = GoogleBooksClient(mock_hass)
            book_data = await client.fetch_book_metadata("9780451524935")

            assert book_data.year == 1984

    @pytest.mark.asyncio
    async def test_extract_year_from_iso_date(self, mock_hass, mock_session):
        """Test extracting year from 'YYYY-MM-DD' format."""
        with patch(
            "custom_components.library_catalog.google_books.async_get_clientsession",
            return_value=mock_session,
        ):
            response_data = {
                "totalItems": 1,
                "items": [
                    {
                        "volumeInfo": {
                            "title": "Test Book",
                            "authors": ["Test Author"],
                            "publishedDate": "2020-05-15",
                        }
                    }
                ],
            }

            mock_response = create_mock_response(200, response_data)
            mock_session.get = Mock(return_value=mock_response)

            client = GoogleBooksClient(mock_hass)
            book_data = await client.fetch_book_metadata("9780451524935")

            assert book_data.year == 2020

    @pytest.mark.asyncio
    async def test_extract_year_from_partial_date(self, mock_hass, mock_session):
        """Test extracting year from 'YYYY-MM' format."""
        with patch(
            "custom_components.library_catalog.google_books.async_get_clientsession",
            return_value=mock_session,
        ):
            response_data = {
                "totalItems": 1,
                "items": [
                    {
                        "volumeInfo": {
                            "title": "Test Book",
                            "authors": ["Test Author"],
                            "publishedDate": "1950-06",
                        }
                    }
                ],
            }

            mock_response = create_mock_response(200, response_data)
            mock_session.get = Mock(return_value=mock_response)

            client = GoogleBooksClient(mock_hass)
            book_data = await client.fetch_book_metadata("9780451524935")

            assert book_data.year == 1950


class TestConvenienceFunction:
    """Test the get_book_metadata_google convenience function."""

    @pytest.mark.asyncio
    async def test_get_book_metadata_google_success(self, mock_hass, mock_session):
        """Test convenience function works."""
        with patch(
            "custom_components.library_catalog.google_books.async_get_clientsession",
            return_value=mock_session,
        ):
            mock_response = create_mock_response(200, SAMPLE_GOOGLE_BOOKS_RESPONSE)
            mock_session.get = Mock(return_value=mock_response)

            book_data = await get_book_metadata_google(mock_hass, "9780451524935")

            assert book_data.title == "1984"
            assert book_data.authors == ["George Orwell"]
