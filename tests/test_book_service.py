"""Tests for the book service layer."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.library_catalog.book_service import (
    LibraryBookService,
    DuplicateISBNError,
    BookNotFoundError,
)
from custom_components.library_catalog.models import BookData, BookEntity, BookLocation
from custom_components.library_catalog.api import ISBNValidationError


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    return MagicMock()


@pytest.fixture
def mock_database():
    """Create a mock database instance."""
    db = AsyncMock()
    db.async_get_book = AsyncMock(return_value=None)
    db.async_add_book = AsyncMock()
    db.async_update_book = AsyncMock()
    db.async_delete_book = AsyncMock(return_value=True)
    db.async_update_location = AsyncMock(return_value=True)
    db.async_search_by_title = AsyncMock()
    db.async_search_by_author = AsyncMock()
    db.async_search_by_isbn = AsyncMock()
    db.async_search_by_room = AsyncMock()
    db.async_get_all_books = AsyncMock(return_value=([], 0))
    db.async_get_database_stats = AsyncMock(return_value={})
    return db


@pytest.fixture
def book_service(mock_hass, mock_database):
    """Create a book service instance."""
    return LibraryBookService(mock_hass, mock_database)


@pytest.fixture
def sample_location():
    """Create a sample book location."""
    return BookLocation(room="Living Room", shelf="Shelf 1", compartment="Top")


@pytest.fixture
def sample_book_data():
    """Create sample book metadata."""
    return BookData(
        isbn="9780451524935",
        title="1984",
        subtitle="A Novel",
        authors=["George Orwell"],
        publisher="Signet Classic",
        year=1949,
        description="A dystopian novel",
        cover_url="https://example.com/cover.jpg",
        language="en",
        pages=328,
    )


@pytest.fixture
def sample_book_entity(sample_location):
    """Create a sample book entity."""
    now = datetime.now(timezone.utc)
    return BookEntity(
        isbn="9780451524935",
        title="1984",
        subtitle="A Novel",
        authors=["George Orwell"],
        publisher="Signet Classic",
        year=1949,
        description="A dystopian novel",
        cover_url="https://example.com/cover.jpg",
        language="en",
        pages=328,
        location=sample_location,
        created_at=now,
        updated_at=now,
    )


class TestAddBookByISBN:
    """Tests for add_book_by_isbn method."""

    @pytest.mark.asyncio
    async def test_add_book_success(
        self, book_service, mock_database, sample_location, sample_book_data
    ):
        """Test successful book addition via ISBN."""
        # Mock metadata fetch
        with patch(
            "custom_components.library_catalog.book_service.get_book_metadata",
            return_value=sample_book_data,
        ), patch(
            "custom_components.library_catalog.book_service.validate_isbn",
            return_value="9780451524935",
        ):
            # Add book
            result = await book_service.add_book_by_isbn(
                "9780451524935", sample_location
            )

            # Verify
            assert result.isbn == "9780451524935"
            assert result.title == "1984"
            assert result.location == sample_location
            mock_database.async_get_book.assert_called_once_with("9780451524935")
            mock_database.async_add_book.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_book_duplicate_isbn(
        self, book_service, mock_database, sample_location, sample_book_entity
    ):
        """Test adding book with duplicate ISBN."""
        # Mock existing book
        mock_database.async_get_book.return_value = sample_book_entity

        with patch(
            "custom_components.library_catalog.book_service.validate_isbn",
            return_value="9780451524935",
        ):
            # Attempt to add duplicate
            with pytest.raises(DuplicateISBNError) as exc_info:
                await book_service.add_book_by_isbn("9780451524935", sample_location)

            # Verify error
            assert exc_info.value.isbn == "9780451524935"
            assert exc_info.value.existing_book == sample_book_entity
            mock_database.async_add_book.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_book_invalid_isbn(self, book_service, sample_location):
        """Test adding book with invalid ISBN."""
        with patch(
            "custom_components.library_catalog.book_service.validate_isbn",
            side_effect=ISBNValidationError("Invalid ISBN"),
        ):
            # Attempt to add with invalid ISBN
            with pytest.raises(ISBNValidationError):
                await book_service.add_book_by_isbn("invalid", sample_location)

    @pytest.mark.asyncio
    async def test_add_book_metadata_not_found(
        self, book_service, mock_database, sample_location
    ):
        """Test adding book when metadata is not found."""
        with patch(
            "custom_components.library_catalog.book_service.validate_isbn",
            return_value="9780451524935",
        ), patch(
            "custom_components.library_catalog.book_service.get_book_metadata",
            side_effect=BookNotFoundError("Metadata not found"),
        ):
            # Attempt to add book
            with pytest.raises(BookNotFoundError):
                await book_service.add_book_by_isbn("9780451524935", sample_location)

            mock_database.async_add_book.assert_not_called()


class TestAddBookManual:
    """Tests for add_book_manual method."""

    @pytest.mark.asyncio
    async def test_add_manual_book_success(
        self, book_service, mock_database, sample_location
    ):
        """Test successful manual book addition."""
        with patch(
            "custom_components.library_catalog.book_service.validate_isbn",
            return_value="9780451524935",
        ):
            # Add book manually
            result = await book_service.add_book_manual(
                isbn="9780451524935",
                title="1984",
                authors=["George Orwell"],
                location=sample_location,
                publisher="Signet Classic",
                year=1949,
            )

            # Verify
            assert result.isbn == "9780451524935"
            assert result.title == "1984"
            assert result.authors == ["George Orwell"]
            assert result.publisher == "Signet Classic"
            mock_database.async_add_book.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_manual_book_duplicate(
        self, book_service, mock_database, sample_location, sample_book_entity
    ):
        """Test manual addition with duplicate ISBN."""
        mock_database.async_get_book.return_value = sample_book_entity

        with patch(
            "custom_components.library_catalog.book_service.validate_isbn",
            return_value="9780451524935",
        ):
            # Attempt duplicate
            with pytest.raises(DuplicateISBNError):
                await book_service.add_book_manual(
                    isbn="9780451524935",
                    title="1984",
                    authors=["George Orwell"],
                    location=sample_location,
                )


class TestGetBook:
    """Tests for get_book method."""

    @pytest.mark.asyncio
    async def test_get_book_success(
        self, book_service, mock_database, sample_book_entity
    ):
        """Test successful book retrieval."""
        mock_database.async_get_book.return_value = sample_book_entity

        with patch(
            "custom_components.library_catalog.book_service.validate_isbn",
            return_value="9780451524935",
        ):
            result = await book_service.get_book("9780451524935")

            assert result == sample_book_entity
            mock_database.async_get_book.assert_called_once_with("9780451524935")

    @pytest.mark.asyncio
    async def test_get_book_not_found(self, book_service, mock_database):
        """Test getting non-existent book."""
        mock_database.async_get_book.return_value = None

        with patch(
            "custom_components.library_catalog.book_service.validate_isbn",
            return_value="9780451524935",
        ):
            with pytest.raises(BookNotFoundError) as exc_info:
                await book_service.get_book("9780451524935")

            assert exc_info.value.isbn == "9780451524935"


class TestSearchBooks:
    """Tests for search_books method."""

    @pytest.mark.asyncio
    async def test_search_by_title(self, book_service, mock_database):
        """Test searching books by title."""
        from custom_components.library_catalog.models import SearchResult

        mock_result = SearchResult(
            books=[],
            total_count=0,
            query="1984",
            search_type="title",
            limit=50,
            offset=0,
        )
        mock_database.async_search_by_title.return_value = mock_result

        result = await book_service.search_books("1984", "title")

        assert result == mock_result
        mock_database.async_search_by_title.assert_called_once_with("1984", 50, 0)

    @pytest.mark.asyncio
    async def test_search_invalid_type(self, book_service):
        """Test searching with invalid search_by value."""
        with pytest.raises(ValueError) as exc_info:
            await book_service.search_books("test", "invalid_type")

        assert "Invalid search_by value" in str(exc_info.value)


class TestDeleteBook:
    """Tests for delete_book method."""

    @pytest.mark.asyncio
    async def test_delete_book_success(
        self, book_service, mock_database, sample_book_entity
    ):
        """Test successful book deletion."""
        mock_database.async_get_book.return_value = sample_book_entity
        mock_database.async_delete_book.return_value = True

        with patch(
            "custom_components.library_catalog.book_service.validate_isbn",
            return_value="9780451524935",
        ):
            result = await book_service.delete_book("9780451524935")

            assert result == sample_book_entity
            mock_database.async_delete_book.assert_called_once_with("9780451524935")

    @pytest.mark.asyncio
    async def test_delete_book_not_found(self, book_service, mock_database):
        """Test deleting non-existent book."""
        mock_database.async_get_book.return_value = None

        with patch(
            "custom_components.library_catalog.book_service.validate_isbn",
            return_value="9780451524935",
        ):
            with pytest.raises(BookNotFoundError):
                await book_service.delete_book("9780451524935")


class TestUpdateBook:
    """Tests for update_book method."""

    @pytest.mark.asyncio
    async def test_update_book_success(
        self, book_service, mock_database, sample_book_entity
    ):
        """Test successful book update."""
        mock_database.async_get_book.return_value = sample_book_entity

        with patch(
            "custom_components.library_catalog.book_service.validate_isbn",
            return_value="9780451524935",
        ):
            result = await book_service.update_book(
                "9780451524935",
                title="New Title",
                year=2000,
            )

            assert result.title == "New Title"
            assert result.year == 2000
            mock_database.async_update_book.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_location(
        self, book_service, mock_database, sample_book_entity, sample_location
    ):
        """Test updating book location."""
        mock_database.async_update_location.return_value = True
        mock_database.async_get_book.return_value = sample_book_entity

        with patch(
            "custom_components.library_catalog.book_service.validate_isbn",
            return_value="9780451524935",
        ):
            result = await book_service.update_location("9780451524935", sample_location)

            assert result.isbn == "9780451524935"
            mock_database.async_update_location.assert_called_once_with(
                "9780451524935", sample_location
            )
