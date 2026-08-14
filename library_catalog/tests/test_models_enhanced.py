"""Tests for enhanced models with validation."""
import pytest
from datetime import datetime, timezone

from custom_components.library_catalog.models import (
    BookLocation,
    BookData,
    BookEntity,
    SearchResult,
)
from custom_components.library_catalog.validation import ValidationError


class TestBookLocationWithValidation:
    """Test BookLocation with validation."""

    def test_create_valid_location(self):
        """Test creating valid location."""
        location = BookLocation(room="Living Room", shelf="Shelf 1", compartment="Top")
        assert location.room == "Living Room"
        assert location.shelf == "Shelf 1"
        assert location.compartment == "Top"

    def test_create_location_empty_room(self):
        """Test that empty room raises error."""
        with pytest.raises(ValidationError, match="Room cannot be empty"):
            BookLocation(room="", shelf="Shelf", compartment="Top")

    def test_create_location_empty_shelf(self):
        """Test that empty shelf raises error."""
        with pytest.raises(ValidationError, match="Shelf cannot be empty"):
            BookLocation(room="Room", shelf="", compartment="Top")

    def test_create_location_empty_compartment(self):
        """Test that empty compartment raises error."""
        with pytest.raises(ValidationError, match="Compartment cannot be empty"):
            BookLocation(room="Room", shelf="Shelf", compartment="")

    def test_location_to_dict(self):
        """Test location to_dict conversion."""
        location = BookLocation(room="Living Room", shelf="Shelf 1", compartment="Top")
        data = location.to_dict()

        assert data["room"] == "Living Room"
        assert data["shelf"] == "Shelf 1"
        assert data["compartment"] == "Top"

    def test_location_from_dict(self):
        """Test location from_dict creation."""
        data = {"room": "Bedroom", "shelf": "Shelf 2", "compartment": "Bottom"}
        location = BookLocation.from_dict(data)

        assert location.room == "Bedroom"
        assert location.shelf == "Shelf 2"
        assert location.compartment == "Bottom"

    def test_location_str_representation(self):
        """Test location string representation."""
        location = BookLocation(room="Office", shelf="Shelf 3", compartment="Middle")
        assert str(location) == "Office > Shelf 3 > Middle"


class TestBookDataWithValidation:
    """Test BookData with validation."""

    def test_create_valid_book_data(self):
        """Test creating valid book data."""
        book_data = BookData(
            isbn="978-3-16-148410-0",
            title="Test Book",
            authors=["Test Author"],
        )

        assert book_data.isbn == "9783161484100"  # Normalized
        assert book_data.title == "Test Book"
        assert book_data.authors == ["Test Author"]

    def test_book_data_isbn_normalization(self):
        """Test that ISBN is normalized."""
        book_data = BookData(
            isbn="0-306-40615-2",  # ISBN-10
            title="Test",
            authors=["Author"],
        )

        assert len(book_data.isbn) == 13
        assert book_data.isbn.startswith("978")

    def test_book_data_missing_title(self):
        """Test that missing title raises error."""
        with pytest.raises(ValidationError, match="Title is required"):
            BookData(
                isbn="9783161484100",
                title="",
                authors=["Author"],
            )

    def test_book_data_missing_authors(self):
        """Test that missing authors raises error."""
        with pytest.raises(ValidationError, match="At least one author is required"):
            BookData(
                isbn="9783161484100",
                title="Test",
                authors=[],
            )

    def test_book_data_to_dict(self):
        """Test book data to_dict conversion."""
        book_data = BookData(
            isbn="9783161484100",
            title="Test Book",
            subtitle="A Subtitle",
            authors=["Author One", "Author Two"],
            publisher="Test Publisher",
            year=2020,
            description="Test description",
            cover_url="https://example.com/cover.jpg",
            language="en",
            pages=300,
        )

        data = book_data.to_dict()

        assert data["isbn"] == "9783161484100"
        assert data["title"] == "Test Book"
        assert data["authors"] == ["Author One", "Author Two"]
        assert data["year"] == 2020


class TestBookEntityWithValidation:
    """Test BookEntity with comprehensive validation."""

    def test_create_valid_book_entity(self):
        """Test creating valid book entity."""
        book = BookEntity(
            isbn="978-3-16-148410-0",
            title="The Hitchhiker's Guide to the Galaxy",
            authors=["Douglas Adams"],
        )

        assert book.isbn == "9783161484100"
        assert book.title == "The Hitchhiker's Guide to the Galaxy"
        assert book.authors == ["Douglas Adams"]

    def test_book_entity_with_all_fields(self):
        """Test creating book entity with all fields."""
        location = BookLocation(room="Living Room", shelf="Shelf 1", compartment="Top")

        book = BookEntity(
            isbn="9783161484100",
            title="Test Book",
            subtitle="A Great Subtitle",
            authors=["Author One", "Author Two"],
            publisher="Test Publisher",
            year=2020,
            description="A fascinating book about testing.",
            cover_url="https://example.com/cover.jpg",
            language="en",
            pages=250,
            location=location,
        )

        assert book.subtitle == "A Great Subtitle"
        assert len(book.authors) == 2
        assert book.publisher == "Test Publisher"
        assert book.year == 2020
        assert book.pages == 250
        assert book.location.room == "Living Room"

    def test_book_entity_invalid_isbn(self):
        """Test that invalid ISBN raises error."""
        with pytest.raises(ValidationError, match="ISBN"):
            BookEntity(
                isbn="invalid",
                title="Test",
                authors=["Author"],
            )

    def test_book_entity_missing_title(self):
        """Test that missing title raises error."""
        with pytest.raises(ValidationError, match="Title"):
            BookEntity(
                isbn="9783161484100",
                title="",
                authors=["Author"],
            )

    def test_book_entity_missing_authors(self):
        """Test that missing authors raises error."""
        with pytest.raises(ValidationError, match="author"):
            BookEntity(
                isbn="9783161484100",
                title="Test Book",
                authors=[],
            )

    def test_book_entity_title_too_long(self):
        """Test that too long title raises error."""
        with pytest.raises(ValidationError, match="Title too long"):
            BookEntity(
                isbn="9783161484100",
                title="x" * 501,
                authors=["Author"],
            )

    def test_book_entity_invalid_year(self):
        """Test that invalid year raises error."""
        with pytest.raises(ValidationError, match="Year out of range"):
            BookEntity(
                isbn="9783161484100",
                title="Test",
                authors=["Author"],
                year=500,
            )

    def test_book_entity_invalid_pages(self):
        """Test that invalid page count raises error."""
        with pytest.raises(ValidationError, match="Page count must be positive"):
            BookEntity(
                isbn="9783161484100",
                title="Test",
                authors=["Author"],
                pages=-10,
            )

    def test_book_entity_timestamps(self):
        """Test that timestamps are set automatically."""
        book = BookEntity(
            isbn="9783161484100",
            title="Test",
            authors=["Author"],
        )

        assert isinstance(book.created_at, datetime)
        assert isinstance(book.updated_at, datetime)
        assert book.created_at.tzinfo is not None  # Timezone-aware

    def test_book_entity_to_dict(self):
        """Test book entity to_dict conversion."""
        location = BookLocation(room="Office", shelf="Shelf 2", compartment="Middle")

        book = BookEntity(
            isbn="9783161484100",
            title="Test Book",
            authors=["Test Author"],
            location=location,
        )

        data = book.to_dict()

        assert data["isbn"] == "9783161484100"
        assert data["title"] == "Test Book"
        assert data["location"]["room"] == "Office"
        assert "created_at" in data
        assert "updated_at" in data

    def test_book_entity_from_dict(self):
        """Test book entity from_dict creation."""
        data = {
            "isbn": "9783161484100",
            "title": "Test Book",
            "authors": ["Test Author"],
            "year": 2020,
            "pages": 300,
        }

        book = BookEntity.from_dict(data)

        assert book.isbn == "9783161484100"
        assert book.title == "Test Book"
        assert book.year == 2020
        assert book.pages == 300

    def test_book_entity_from_book_data(self):
        """Test creating book entity from book data."""
        book_data = BookData(
            isbn="9783161484100",
            title="Test Book",
            subtitle="Test Subtitle",
            authors=["Test Author"],
            publisher="Test Publisher",
            year=2020,
            pages=300,
        )

        location = BookLocation(room="Library", shelf="Shelf 5", compartment="Top")
        book = BookEntity.from_book_data(book_data, location)

        assert book.isbn == book_data.isbn
        assert book.title == book_data.title
        assert book.subtitle == book_data.subtitle
        assert book.authors == book_data.authors
        assert book.location.room == "Library"
        assert isinstance(book.created_at, datetime)


class TestSearchResult:
    """Test SearchResult model."""

    def test_search_result_creation(self):
        """Test creating search result."""
        books = [
            BookEntity(isbn="9783161484100", title="Book 1", authors=["Author 1"]),
            BookEntity(isbn="9780451524935", title="Book 2", authors=["Author 2"]),
        ]

        result = SearchResult(
            books=books,
            total_count=10,
            query="test",
            search_type="title",
            limit=2,
            offset=0,
        )

        assert len(result.books) == 2
        assert result.total_count == 10
        assert result.query == "test"

    def test_search_result_has_more(self):
        """Test has_more method."""
        books = [
            BookEntity(isbn="9783161484100", title="Book 1", authors=["Author"]),
        ]

        result = SearchResult(
            books=books,
            total_count=5,
            query="test",
            search_type="title",
            limit=2,
            offset=0,
        )

        assert result.has_more() is True

    def test_search_result_no_more(self):
        """Test has_more when all results retrieved."""
        books = [
            BookEntity(isbn="9783161484100", title="Book 1", authors=["Author"]),
        ]

        result = SearchResult(
            books=books,
            total_count=1,
            query="test",
            search_type="title",
            limit=10,
            offset=0,
        )

        assert result.has_more() is False

    def test_search_result_next_offset(self):
        """Test next_offset calculation."""
        result = SearchResult(
            books=[],
            total_count=100,
            query="test",
            search_type="title",
            limit=10,
            offset=20,
        )

        assert result.next_offset() == 30


class TestModelExtensibility:
    """Test that models are ready for future extensions."""

    def test_book_entity_future_fields_docstring(self):
        """Test that BookEntity documents future extensibility."""
        assert "categories" in BookEntity.__doc__
        assert "tags" in BookEntity.__doc__
        assert "rating" in BookEntity.__doc__
        assert "reading_status" in BookEntity.__doc__
        assert "series" in BookEntity.__doc__

    def test_models_use_optional_types(self):
        """Test that models properly use Optional for nullable fields."""
        book = BookEntity(
            isbn="9783161484100",
            title="Test",
            authors=["Author"],
        )

        # These should all be None without breaking
        assert book.subtitle is None
        assert book.publisher is None
        assert book.year is None
        assert book.description is None
        assert book.cover_url is None
        assert book.language is None
        assert book.pages is None
        assert book.location is None
