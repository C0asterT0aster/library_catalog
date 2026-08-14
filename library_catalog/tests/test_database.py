"""Tests for database layer."""
import pytest
import pytest_asyncio
import sqlite3
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

from custom_components.library_catalog.database import LibraryCatalogDatabase
from custom_components.library_catalog.models import BookEntity, BookLocation


@pytest_asyncio.fixture
async def temp_db_path():
    """Create a temporary directory for test database."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest_asyncio.fixture
async def database(temp_db_path):
    """Create and initialize a test database."""
    db = LibraryCatalogDatabase(temp_db_path)
    await db.async_initialize()
    yield db
    await db.async_close()


@pytest.fixture
def sample_book():
    """Create a sample book entity for testing."""
    return BookEntity(
        isbn="9780316769174",  # Valid ISBN-13
        title="The Catcher in the Rye",
        subtitle="A Classic Novel",
        authors=["J.D. Salinger"],
        publisher="Little, Brown and Company",
        year=1951,
        description="A story about teenage rebellion.",
        cover_url="https://example.com/cover.jpg",
        language="en",
        pages=234,
        location=BookLocation(room="Living Room", shelf="Shelf 1", compartment="Top"),
    )


@pytest.fixture
def sample_book_no_location():
    """Create a sample book without location."""
    return BookEntity(
        isbn="9780451524935",
        title="1984",
        subtitle=None,
        authors=["George Orwell"],
        publisher="Signet Classic",
        year=1950,
        description="A dystopian novel.",
        cover_url=None,
        language="en",
        pages=328,
        location=None,
    )


class TestDatabaseInitialization:
    """Test database initialization."""

    @pytest.mark.asyncio
    async def test_initialize_creates_database(self, temp_db_path):
        """Test that initialization creates database file."""
        db = LibraryCatalogDatabase(temp_db_path)
        await db.async_initialize()

        assert db.db_path.exists()
        assert db._initialized
        assert db._connection is not None

        await db.async_close()

    @pytest.mark.asyncio
    async def test_initialize_creates_schema(self, database):
        """Test that schema is created correctly."""
        # Check schema_version table
        cursor = await database._connection.execute(
            "SELECT version FROM schema_version"
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row[0] == 1

        # Check books table exists
        cursor = await database._connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='books'"
        )
        row = await cursor.fetchone()
        assert row is not None

    @pytest.mark.asyncio
    async def test_close_database(self, temp_db_path):
        """Test database closing."""
        db = LibraryCatalogDatabase(temp_db_path)
        await db.async_initialize()
        await db.async_close()

        assert db._connection is None
        assert not db._initialized


class TestCRUDOperations:
    """Test CRUD operations."""

    @pytest.mark.asyncio
    async def test_add_book(self, database, sample_book):
        """Test adding a book."""
        await database.async_add_book(sample_book)

        # Verify book was added
        retrieved = await database.async_get_book(sample_book.isbn)
        assert retrieved is not None
        assert retrieved.isbn == sample_book.isbn
        assert retrieved.title == sample_book.title
        assert retrieved.authors == sample_book.authors

    @pytest.mark.asyncio
    async def test_add_book_no_location(self, database, sample_book_no_location):
        """Test adding a book without location."""
        await database.async_add_book(sample_book_no_location)

        retrieved = await database.async_get_book(sample_book_no_location.isbn)
        assert retrieved is not None
        assert retrieved.location is None

    @pytest.mark.asyncio
    async def test_add_duplicate_isbn_raises_error(self, database, sample_book):
        """Test that adding duplicate ISBN raises IntegrityError."""
        await database.async_add_book(sample_book)

        # Try to add same ISBN again
        with pytest.raises(sqlite3.IntegrityError):
            await database.async_add_book(sample_book)

    @pytest.mark.asyncio
    async def test_get_book_not_found(self, database):
        """Test getting non-existent book returns None."""
        result = await database.async_get_book("9999999999999")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_book(self, database, sample_book):
        """Test updating a book."""
        await database.async_add_book(sample_book)

        # Update book
        sample_book.title = "Updated Title"
        sample_book.pages = 300
        await database.async_update_book(sample_book)

        # Verify update
        retrieved = await database.async_get_book(sample_book.isbn)
        assert retrieved.title == "Updated Title"
        assert retrieved.pages == 300

    @pytest.mark.asyncio
    async def test_delete_book(self, database, sample_book):
        """Test deleting a book."""
        await database.async_add_book(sample_book)

        # Delete book
        result = await database.async_delete_book(sample_book.isbn)
        assert result is True

        # Verify deletion
        retrieved = await database.async_get_book(sample_book.isbn)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_book(self, database):
        """Test deleting non-existent book returns False."""
        result = await database.async_delete_book("9999999999999")
        assert result is False


class TestLocationOperations:
    """Test location-specific operations."""

    @pytest.mark.asyncio
    async def test_update_location(self, database, sample_book):
        """Test updating book location."""
        await database.async_add_book(sample_book)

        # Update location
        new_location = BookLocation(room="Bedroom", shelf="Shelf 2", compartment="Bottom")
        result = await database.async_update_location(sample_book.isbn, new_location)
        assert result is True

        # Verify location update
        retrieved = await database.async_get_book(sample_book.isbn)
        assert retrieved.location is not None
        assert retrieved.location.room == "Bedroom"
        assert retrieved.location.shelf == "Shelf 2"
        assert retrieved.location.compartment == "Bottom"

    @pytest.mark.asyncio
    async def test_clear_location(self, database, sample_book):
        """Test clearing book location."""
        await database.async_add_book(sample_book)

        # Clear location
        result = await database.async_update_location(sample_book.isbn, None)
        assert result is True

        # Verify location cleared
        retrieved = await database.async_get_book(sample_book.isbn)
        assert retrieved.location is None

    @pytest.mark.asyncio
    async def test_update_location_nonexistent_book(self, database):
        """Test updating location of non-existent book returns False."""
        location = BookLocation(room="Test", shelf="Test", compartment="Test")
        result = await database.async_update_location("9999999999999", location)
        assert result is False


class TestSearchOperations:
    """Test search operations."""

    @pytest.mark.asyncio
    async def test_get_all_books(self, database, sample_book, sample_book_no_location):
        """Test getting all books."""
        await database.async_add_book(sample_book)
        await database.async_add_book(sample_book_no_location)

        books, total = await database.async_get_all_books()
        assert total == 2
        assert len(books) == 2

    @pytest.mark.asyncio
    async def test_get_all_books_pagination(self, database):
        """Test pagination of get_all_books."""
        # Add multiple books
        for i in range(5):
            book = BookEntity(
                isbn=f"978000000000{i}",
                title=f"Book {i}",
                authors=["Test Author"],
            )
            await database.async_add_book(book)

        # Test pagination
        books, total = await database.async_get_all_books(limit=2, offset=0)
        assert total == 5
        assert len(books) == 2

        books, total = await database.async_get_all_books(limit=2, offset=2)
        assert total == 5
        assert len(books) == 2

    @pytest.mark.asyncio
    async def test_get_book_count(self, database, sample_book, sample_book_no_location):
        """Test getting book count."""
        assert await database.async_get_book_count() == 0

        await database.async_add_book(sample_book)
        assert await database.async_get_book_count() == 1

        await database.async_add_book(sample_book_no_location)
        assert await database.async_get_book_count() == 2

    @pytest.mark.asyncio
    async def test_search_by_isbn(self, database, sample_book):
        """Test searching by ISBN."""
        await database.async_add_book(sample_book)

        result = await database.async_search_by_isbn("9783442478951")
        assert result.total_count == 1
        assert len(result.books) == 1
        assert result.books[0].isbn == sample_book.isbn

    @pytest.mark.asyncio
    async def test_search_by_isbn_partial(self, database, sample_book):
        """Test partial ISBN search."""
        await database.async_add_book(sample_book)

        result = await database.async_search_by_isbn("978344")
        assert result.total_count == 1
        assert len(result.books) == 1

    @pytest.mark.asyncio
    async def test_search_by_title(self, database, sample_book):
        """Test searching by title."""
        await database.async_add_book(sample_book)

        result = await database.async_search_by_title("Hitchhiker")
        assert result.total_count == 1
        assert len(result.books) == 1
        assert result.books[0].title == sample_book.title

    @pytest.mark.asyncio
    async def test_search_by_title_case_insensitive(self, database, sample_book):
        """Test case-insensitive title search."""
        await database.async_add_book(sample_book)

        result = await database.async_search_by_title("hitchhiker")
        assert result.total_count == 1

    @pytest.mark.asyncio
    async def test_search_by_author(self, database, sample_book):
        """Test searching by author."""
        await database.async_add_book(sample_book)

        result = await database.async_search_by_author("Douglas Adams")
        assert result.total_count == 1
        assert len(result.books) == 1

    @pytest.mark.asyncio
    async def test_search_by_author_partial(self, database, sample_book):
        """Test partial author search."""
        await database.async_add_book(sample_book)

        result = await database.async_search_by_author("Adams")
        assert result.total_count == 1

    @pytest.mark.asyncio
    async def test_search_by_room(self, database, sample_book):
        """Test searching by room."""
        await database.async_add_book(sample_book)

        result = await database.async_search_by_room("Living Room")
        assert result.total_count == 1
        assert len(result.books) == 1

    @pytest.mark.asyncio
    async def test_search_no_results(self, database):
        """Test search with no results."""
        result = await database.async_search_by_title("Nonexistent")
        assert result.total_count == 0
        assert len(result.books) == 0


class TestDatabaseStats:
    """Test database statistics."""

    @pytest.mark.asyncio
    async def test_get_database_stats(self, database, sample_book):
        """Test getting database statistics."""
        await database.async_add_book(sample_book)

        stats = await database.async_get_database_stats()
        assert stats["total_books"] == 1
        assert stats["database_size_bytes"] > 0
        assert "database_path" in stats
        assert stats["schema_version"] == 1

    @pytest.mark.asyncio
    async def test_export_all_books(self, database, sample_book):
        """Test exporting all books."""
        await database.async_add_book(sample_book)

        exported = await database.async_export_all_books()
        assert len(exported) == 1
        assert exported[0]["isbn"] == sample_book.isbn
        assert exported[0]["title"] == sample_book.title


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_operations_without_initialization(self, temp_db_path):
        """Test that operations fail gracefully without initialization."""
        db = LibraryCatalogDatabase(temp_db_path)

        book = BookEntity(isbn="123", title="Test", authors=["Test"])

        with pytest.raises(RuntimeError, match="Database not initialized"):
            await db.async_add_book(book)

        with pytest.raises(RuntimeError, match="Database not initialized"):
            await db.async_get_book("123")

        with pytest.raises(RuntimeError, match="Database not initialized"):
            await db.async_delete_book("123")

    @pytest.mark.asyncio
    async def test_invalid_json_in_authors(self, database):
        """Test handling of corrupted authors JSON."""
        # Manually insert book with invalid JSON
        await database._connection.execute(
            """
            INSERT INTO books (isbn, title, authors)
            VALUES (?, ?, ?)
            """,
            ("123", "Test", "invalid json"),
        )
        await database._connection.commit()

        # Should handle gracefully
        book = await database.async_get_book("123")
        assert book is not None
        assert book.authors == []
