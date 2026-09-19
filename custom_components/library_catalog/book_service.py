"""Business logic layer for Library Catalog.

This module contains all book management business logic, separated from
Home Assistant integration code. All operations are independently testable.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List, Tuple

from homeassistant.core import HomeAssistant

from .api import get_book_metadata, validate_isbn, BookNotFoundError as APIBookNotFoundError, ISBNValidationError
from .database import LibraryCatalogDatabase
from .models import BookData, BookEntity, BookLocation, SearchResult

_LOGGER = logging.getLogger(__name__)


class BookServiceError(Exception):
    """Base exception for book service errors."""
    pass


class DuplicateISBNError(BookServiceError):
    """Raised when attempting to add a book with duplicate ISBN."""

    def __init__(self, isbn: str, existing_book: BookEntity):
        self.isbn = isbn
        self.existing_book = existing_book
        self.message = f"Book with ISBN {isbn} already exists: {existing_book.title}"
        super().__init__(self.message)


class BookNotFoundError(BookServiceError):
    """Raised when a book is not found."""

    def __init__(self, isbn: str):
        self.isbn = isbn
        self.message = f"Book with ISBN {isbn} not found"
        super().__init__(self.message)


class LibraryBookService:
    """Business logic service for book management.

    This service encapsulates all book-related business logic:
    - ISBN validation
    - Metadata fetching and normalization
    - Duplicate detection
    - CRUD operations
    - Location management

    It is independent of Home Assistant and can be tested in isolation.
    """

    def __init__(self, hass: HomeAssistant, database: LibraryCatalogDatabase):
        """Initialize the book service.

        Args:
            hass: Home Assistant instance (for API client)
            database: Database instance
        """
        self.hass = hass
        self.database = database

    async def add_book_by_isbn(
        self,
        isbn: str,
        location: BookLocation,
    ) -> BookEntity:
        """Add a book by ISBN with automatic metadata fetching.

        Workflow:
        1. Validate ISBN format
        2. Check for duplicates
        3. Query metadata providers (Open Library → Google Books)
        4. Normalize metadata to BookData
        5. Create BookEntity with location and timestamps
        6. Store in database

        Args:
            isbn: ISBN-10 or ISBN-13
            location: Physical location of the book

        Returns:
            The created BookEntity

        Raises:
            ISBNValidationError: Invalid ISBN format
            DuplicateISBNError: ISBN already exists in database
            BookNotFoundError: No metadata found from any provider
            DatabaseError: Database operation failed
        """
        # Step 1: Validate ISBN
        _LOGGER.debug("Validating ISBN: %s", isbn)
        try:
            validated_isbn = validate_isbn(isbn)
        except ISBNValidationError as err:
            _LOGGER.error("ISBN validation failed: %s", err)
            raise

        # Step 2: Check for duplicates
        _LOGGER.debug("Checking for duplicate ISBN: %s", validated_isbn)
        existing = await self.database.async_get_book(validated_isbn)
        if existing:
            _LOGGER.warning("Duplicate ISBN detected: %s", validated_isbn)
            raise DuplicateISBNError(isbn=validated_isbn, existing_book=existing)

        # Step 3 & 4: Query metadata providers and normalize
        _LOGGER.info("Fetching metadata for ISBN: %s", validated_isbn)
        try:
            book_data = await get_book_metadata(self.hass, validated_isbn)
        except APIBookNotFoundError as err:
            _LOGGER.error("Metadata fetch failed: %s", err)
            raise

        # Step 5: Create BookEntity with location and timestamps
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

        # Step 6: Store in database
        _LOGGER.info("Storing book: %s - %s", book_entity.title, validated_isbn)
        await self.database.async_add_book(book_entity)

        _LOGGER.info("Book added successfully: %s", validated_isbn)
        return book_entity

    async def add_book_manual(
        self,
        isbn: str,
        title: str,
        authors: List[str],
        location: BookLocation,
        subtitle: Optional[str] = None,
        publisher: Optional[str] = None,
        year: Optional[int] = None,
        description: Optional[str] = None,
        cover_url: Optional[str] = None,
        language: Optional[str] = None,
        pages: Optional[int] = None,
    ) -> BookEntity:
        """Add a book with manually provided metadata (no API calls).

        Workflow:
        1. Validate ISBN format
        2. Check for duplicates
        3. Create BookEntity from provided data
        4. Store in database

        Args:
            isbn: ISBN-10 or ISBN-13
            title: Book title
            authors: List of author names
            location: Physical location
            subtitle: Optional subtitle
            publisher: Optional publisher
            year: Optional publication year
            description: Optional description
            cover_url: Optional cover image URL
            language: Optional language code
            pages: Optional page count

        Returns:
            The created BookEntity

        Raises:
            ISBNValidationError: Invalid ISBN format
            DuplicateISBNError: ISBN already exists
        """
        # Step 1: Validate ISBN
        _LOGGER.debug("Validating ISBN for manual entry: %s", isbn)
        try:
            validated_isbn = validate_isbn(isbn)
        except ISBNValidationError as err:
            _LOGGER.error("ISBN validation failed: %s", err)
            raise

        # Step 2: Check for duplicates
        _LOGGER.debug("Checking for duplicate ISBN: %s", validated_isbn)
        existing = await self.database.async_get_book(validated_isbn)
        if existing:
            _LOGGER.warning("Duplicate ISBN detected: %s", validated_isbn)
            raise DuplicateISBNError(isbn=validated_isbn, existing_book=existing)

        # Step 3: Create BookEntity from manual data
        now = datetime.now(timezone.utc)
        book_entity = BookEntity(
            isbn=validated_isbn,
            title=title,
            subtitle=subtitle,
            authors=authors,
            publisher=publisher,
            year=year,
            description=description,
            cover_url=cover_url,
            language=language,
            pages=pages,
            location=location,
            created_at=now,
            updated_at=now,
        )

        # Step 4: Store in database
        _LOGGER.info("Storing manual book: %s - %s", book_entity.title, validated_isbn)
        await self.database.async_add_book(book_entity)

        _LOGGER.info("Manual book added successfully: %s", validated_isbn)
        return book_entity

    async def get_book(self, isbn: str) -> BookEntity:
        """Get a book by ISBN.

        Args:
            isbn: ISBN to retrieve

        Returns:
            The BookEntity

        Raises:
            ISBNValidationError: Invalid ISBN format
            BookNotFoundError: Book not found
        """
        # Validate ISBN
        validated_isbn = validate_isbn(isbn)

        # Retrieve from database
        book = await self.database.async_get_book(validated_isbn)
        if not book:
            raise BookNotFoundError(isbn=validated_isbn)

        return book

    async def search_books(
        self,
        query: str,
        search_by: str = "title",
        limit: int = 50,
        offset: int = 0,
    ) -> SearchResult:
        """Search for books.

        Args:
            query: Search term
            search_by: Field to search ("title", "author", "isbn", "room")
            limit: Maximum results
            offset: Result offset for pagination

        Returns:
            SearchResult with matching books

        Raises:
            ValueError: Invalid search_by value
        """
        _LOGGER.debug("Searching books: query=%s, search_by=%s", query, search_by)

        if search_by == "title":
            result = await self.database.async_search_by_title(query, limit, offset)
        elif search_by == "author":
            result = await self.database.async_search_by_author(query, limit, offset)
        elif search_by == "isbn":
            result = await self.database.async_search_by_isbn(query, limit, offset)
        elif search_by == "room":
            result = await self.database.async_search_by_room(query, limit, offset)
        else:
            raise ValueError(f"Invalid search_by value: {search_by}")

        _LOGGER.info("Search completed: %d results for '%s'", len(result.books), query)
        return result

    async def list_books(
        self,
        limit: int = 1000,
        offset: int = 0,
    ) -> Tuple[List[BookEntity], int]:
        """List all books with pagination.

        Args:
            limit: Maximum results
            offset: Result offset

        Returns:
            Tuple of (book list, total count)
        """
        _LOGGER.debug("Listing books: limit=%d, offset=%d", limit, offset)
        books, total = await self.database.async_get_all_books(limit, offset)
        _LOGGER.info("Listed %d books (total: %d)", len(books), total)
        return books, total

    async def delete_book(self, isbn: str) -> BookEntity:
        """Delete a book by ISBN.

        Args:
            isbn: ISBN to delete

        Returns:
            The deleted BookEntity

        Raises:
            ISBNValidationError: Invalid ISBN format
            BookNotFoundError: Book not found
        """
        # Validate ISBN
        validated_isbn = validate_isbn(isbn)

        # Get book before deleting (for return value and validation)
        book = await self.database.async_get_book(validated_isbn)
        if not book:
            raise BookNotFoundError(isbn=validated_isbn)

        # Delete from database
        _LOGGER.info("Deleting book: %s - %s", book.title, validated_isbn)
        deleted = await self.database.async_delete_book(validated_isbn)
        if not deleted:
            raise BookNotFoundError(isbn=validated_isbn)

        _LOGGER.info("Book deleted successfully: %s", validated_isbn)
        return book

    async def update_book(
        self,
        isbn: str,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        authors: Optional[List[str]] = None,
        publisher: Optional[str] = None,
        year: Optional[int] = None,
        description: Optional[str] = None,
        cover_url: Optional[str] = None,
        language: Optional[str] = None,
        pages: Optional[int] = None,
        location: Optional[BookLocation] = None,
    ) -> BookEntity:
        """Update book metadata.

        Only provided fields are updated; None values are ignored.

        Args:
            isbn: ISBN of book to update
            title: New title
            subtitle: New subtitle
            authors: New authors list
            publisher: New publisher
            year: New year
            description: New description
            cover_url: New cover URL
            language: New language
            pages: New page count
            location: New location

        Returns:
            The updated BookEntity

        Raises:
            ISBNValidationError: Invalid ISBN format
            BookNotFoundError: Book not found
        """
        # Validate ISBN
        validated_isbn = validate_isbn(isbn)

        # Get existing book
        book = await self.database.async_get_book(validated_isbn)
        if not book:
            raise BookNotFoundError(isbn=validated_isbn)

        # Update fields that were provided
        if title is not None:
            book.title = title
        if subtitle is not None:
            book.subtitle = subtitle
        if authors is not None:
            book.authors = authors
        if publisher is not None:
            book.publisher = publisher
        if year is not None:
            book.year = year
        if description is not None:
            book.description = description
        if cover_url is not None:
            book.cover_url = cover_url
        if language is not None:
            book.language = language
        if pages is not None:
            book.pages = pages
        if location is not None:
            book.location = location

        # Update timestamp
        book.updated_at = datetime.now(timezone.utc)

        # Save to database
        _LOGGER.info("Updating book: %s - %s", book.title, validated_isbn)
        await self.database.async_update_book(book)

        _LOGGER.info("Book updated successfully: %s", validated_isbn)
        return book

    async def update_location(
        self,
        isbn: str,
        location: BookLocation,
    ) -> BookEntity:
        """Update only the location of a book.

        Args:
            isbn: ISBN of book to update
            location: New location

        Returns:
            The updated BookEntity

        Raises:
            ISBNValidationError: Invalid ISBN format
            BookNotFoundError: Book not found
        """
        # Validate ISBN
        validated_isbn = validate_isbn(isbn)

        # Update location in database
        _LOGGER.info("Updating location for ISBN: %s", validated_isbn)
        updated = await self.database.async_update_location(validated_isbn, location)
        if not updated:
            raise BookNotFoundError(isbn=validated_isbn)

        # Get updated book
        book = await self.database.async_get_book(validated_isbn)
        if not book:
            raise BookNotFoundError(isbn=validated_isbn)

        _LOGGER.info("Location updated successfully: %s", validated_isbn)
        return book

    async def get_statistics(self) -> dict:
        """Get library statistics.

        Returns:
            Dictionary with statistics
        """
        return await self.database.async_get_database_stats()
