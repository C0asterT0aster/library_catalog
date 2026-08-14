"""Tests for API client."""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from custom_components.library_catalog.api import (
    validate_isbn,
    ISBNValidationError,
    BookNotFoundError,
    normalize_open_library_response,
    normalize_google_books_response,
    get_book_data,
    fetch_open_library_data,
    fetch_google_books_data,
)
from custom_components.library_catalog.models import BookData


class TestISBNValidation:
    """Test ISBN validation and normalization."""

    def test_valid_isbn10(self):
        """Test validation of valid ISBN-10."""
        # Valid ISBN-10: 0451524934 (1984 by George Orwell)
        result = validate_isbn("0451524934")
        assert result == "9780451524935"  # Should convert to ISBN-13

    def test_valid_isbn10_with_hyphens(self):
        """Test validation of ISBN-10 with hyphens."""
        result = validate_isbn("0-451-52493-4")
        assert result == "9780451524935"

    def test_valid_isbn13(self):
        """Test validation of valid ISBN-13."""
        # Valid ISBN-13: 9780451524935
        result = validate_isbn("9780451524935")
        assert result == "9780451524935"

    def test_valid_isbn13_with_hyphens(self):
        """Test validation of ISBN-13 with hyphens."""
        result = validate_isbn("978-0-451-52493-5")
        assert result == "9780451524935"

    def test_invalid_isbn_length(self):
        """Test that invalid ISBN length raises error."""
        with pytest.raises(ISBNValidationError, match="Invalid ISBN length"):
            validate_isbn("123456789")

    def test_invalid_isbn_checksum(self):
        """Test that invalid ISBN checksum raises error."""
        with pytest.raises(ISBNValidationError):
            validate_isbn("9780451524930")  # Wrong checksum

    def test_invalid_isbn_characters(self):
        """Test that ISBN with invalid characters raises error."""
        with pytest.raises(ISBNValidationError):
            validate_isbn("978045152493X")  # Invalid character


class TestOpenLibraryNormalization:
    """Test normalization of Open Library API responses."""

    def test_normalize_complete_response(self):
        """Test normalization of complete Open Library response."""
        raw_data = {
            "title": "The Great Gatsby",
            "subtitle": "A Novel of Wealth and Love",
            "authors": [{"name": "F. Scott Fitzgerald"}],
            "publishers": ["Scribner"],
            "publish_date": 1925,
            "description": "A classic novel of the Jazz Age.",
            "cover": {"medium": "123456", "small": "123456"},
            "number_of_pages": 180,
            "languages": ["eng"],
        }
        
        result = normalize_open_library_response(raw_data, "9780743273565")
        
        assert isinstance(result, BookData)
        assert result.isbn == "9780743273565"
        assert result.title == "The Great Gatsby"
        assert result.subtitle == "A Novel of Wealth and Love"
        assert "F. Scott Fitzgerald" in result.authors
        assert result.publisher == "Scribner"
        assert result.year == 1925
        assert result.cover_url == "https://covers.openlibrary.org/b/id/123456-M.jpg"
        assert result.pages == 180

    def test_normalize_minimal_response(self):
        """Test normalization of minimal Open Library response."""
        raw_data = {
            "title": "Unknown Book",
        }
        
        result = normalize_open_library_response(raw_data, "9780123456789")
        
        assert result.isbn == "9780123456789"
        assert result.title == "Unknown Book"
        assert result.authors == []
        assert result.publisher is None


class TestGoogleBooksNormalization:
    """Test normalization of Google Books API responses."""

    def test_normalize_complete_response(self):
        """Test normalization of complete Google Books response."""
        raw_data = {
            "volumeInfo": {
                "title": "1984",
                "subtitle": "A Political Novel",
                "authors": ["George Orwell"],
                "publisher": "Signet Classics",
                "publishedDate": "1949-01-01",
                "description": "A dystopian novel.",
                "imageLinks": {
                    "thumbnail": "http://example.com/thumbnail.jpg",
                    "medium": "http://example.com/medium.jpg",
                },
                "pageCount": 328,
                "language": "en",
            }
        }
        
        result = normalize_google_books_response(raw_data, "9780451524935")
        
        assert isinstance(result, BookData)
        assert result.isbn == "9780451524935"
        assert result.title == "1984"
        assert result.subtitle == "A Political Novel"
        assert "George Orwell" in result.authors
        assert result.publisher == "Signet Classics"
        assert result.year == 1949
        assert result.cover_url == "http://example.com/medium.jpg"
        assert result.pages == 328

    def test_normalize_minimal_response(self):
        """Test normalization of minimal Google Books response."""
        raw_data = {
            "volumeInfo": {
                "title": "Some Book",
            }
        }
        
        result = normalize_google_books_response(raw_data, "9780123456789")
        
        assert result.isbn == "9780123456789"
        assert result.title == "Some Book"
        assert result.authors == []


@pytest.mark.asyncio
class TestAPIFetching:
    """Test API fetching functions."""

    @pytest.mark.asyncio
    async def test_fetch_open_library_not_found(self):
        """Test Open Library 404 response."""
        mock_response = AsyncMock()
        mock_response.status = 404
        
        mock_session = AsyncMock()
        mock_session.get = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await fetch_open_library_data("9780451524935", session=mock_session)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_google_books_not_found(self):
        """Test Google Books not found response."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"items": []})
        
        mock_session = AsyncMock()
        mock_session.get = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await fetch_google_books_data("9780451524935", session=mock_session)
        
        assert result is None


@pytest.mark.asyncio
class TestGetBookData:
    """Test the main get_book_data function."""

    @pytest.mark.asyncio
    async def test_get_book_data_invalid_isbn(self):
        """Test get_book_data with invalid ISBN."""
        with pytest.raises(ISBNValidationError):
            await get_book_data("invalid-isbn")

    @pytest.mark.asyncio
    async def test_get_book_data_open_library_success(self):
        """Test successful book fetch from Open Library."""
        mock_open_lib_data = {
            "title": "The Great Gatsby",
            "authors": [{"name": "F. Scott Fitzgerald"}],
        }
        
        mock_google_data = None
        
        with patch(
            "custom_components.library_catalog.api.fetch_open_library_data",
            new_callable=AsyncMock,
            return_value=mock_open_lib_data,
        ):
            with patch(
                "custom_components.library_catalog.api.fetch_google_books_data",
                new_callable=AsyncMock,
                return_value=mock_google_data,
            ):
                result = await get_book_data("9780743273565")
        
        assert isinstance(result, BookData)
        assert result.isbn == "9780743273565"
        assert result.title == "The Great Gatsby"

    @pytest.mark.asyncio
    async def test_get_book_data_google_books_fallback(self):
        """Test fallback to Google Books when Open Library fails."""
        mock_google_data = {
            "volumeInfo": {
                "title": "1984",
                "authors": ["George Orwell"],
            }
        }
        
        with patch(
            "custom_components.library_catalog.api.fetch_open_library_data",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with patch(
                "custom_components.library_catalog.api.fetch_google_books_data",
                new_callable=AsyncMock,
                return_value=mock_google_data,
            ):
                result = await get_book_data("9780451524935")
        
        assert isinstance(result, BookData)
        assert result.isbn == "9780451524935"
        assert result.title == "1984"

    @pytest.mark.asyncio
    async def test_get_book_data_not_found(self):
        """Test BookNotFoundError when book is not in any API."""
        with patch(
            "custom_components.library_catalog.api.fetch_open_library_data",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with patch(
                "custom_components.library_catalog.api.fetch_google_books_data",
                new_callable=AsyncMock,
                return_value=None,
            ):
                with pytest.raises(BookNotFoundError):
                    # Use a valid obscure ISBN
                    await get_book_data("9780451524935")


class TestBookDataModel:
    """Test BookData model and conversions."""

    def test_book_data_creation(self):
        """Test creating BookData instance."""
        book = BookData(
            isbn="9780743273565",
            title="The Great Gatsby",
            subtitle="A Novel",
            authors=["F. Scott Fitzgerald"],
            publisher="Scribner",
            year=1925,
            pages=180,
        )
        
        assert book.isbn == "9780743273565"
        assert book.title == "The Great Gatsby"
        assert len(book.authors) == 1

    def test_book_data_to_dict(self):
        """Test converting BookData to dictionary."""
        book = BookData(
            isbn="9780743273565",
            title="The Great Gatsby",
            authors=["F. Scott Fitzgerald"],
        )
        
        data_dict = book.to_dict()
        
        assert isinstance(data_dict, dict)
        assert data_dict["isbn"] == "9780743273565"
        assert data_dict["title"] == "The Great Gatsby"
