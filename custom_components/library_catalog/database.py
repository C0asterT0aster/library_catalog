"""Database abstraction layer for Library Catalog integration."""
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import json

import aiosqlite

from .const import (
    DB_FILE_NAME,
    DB_SCHEMA_VERSION,
    DB_TIMEOUT,
    CONF_ISBN,
    ERROR_DATABASE_ERROR,
    LOGGER_NAME,
)
from .models import BookEntity, BookLocation, SearchResult

_LOGGER = logging.getLogger(LOGGER_NAME)


class LibraryCatalogDatabase:
    """Manages SQLite database operations for Library Catalog integration.
    
    Features:
    - Async operations with aiosqlite
    - Schema versioning for future migrations
    - CRUD operations for books
    - Efficient search operations
    - Location hierarchy support
    """

    def __init__(self, hass_config_path: Path) -> None:
        """Initialize database manager.
        
        Args:
            hass_config_path: Path to Home Assistant config directory
        """
        self.config_path = hass_config_path
        self.db_path = self.config_path / DB_FILE_NAME
        self._connection: Optional[aiosqlite.Connection] = None
        self._initialized = False

    @property
    def connection(self) -> Optional[aiosqlite.Connection]:
        """Get current database connection."""
        return self._connection

    async def async_initialize(self) -> None:
        """Initialize database connection and create schema if needed."""
        try:
            self._connection = await aiosqlite.connect(
                str(self.db_path),
                timeout=DB_TIMEOUT,
            )
            # Enable foreign keys
            await self._connection.execute("PRAGMA foreign_keys = ON")
            await self._connection.commit()

            # Create schema if not exists
            await self._create_schema()
            self._initialized = True
            _LOGGER.info("Database initialized at %s", self.db_path)
        except Exception as e:
            _LOGGER.error("Failed to initialize database: %s", e)
            raise

    async def async_close(self) -> None:
        """Close database connection."""
        if self._connection:
            try:
                await self._connection.close()
                self._connection = None
                self._initialized = False
                _LOGGER.info("Database connection closed")
            except Exception as e:
                _LOGGER.error("Error closing database: %s", e)

    async def _create_schema(self) -> None:
        """Create database schema if it doesn't exist."""
        if not self._connection:
            raise RuntimeError("Database not initialized")

        # Check schema version
        try:
            cursor = await self._connection.execute(
                "SELECT version FROM schema_version LIMIT 1"
            )
            row = await cursor.fetchone()
            if row and row[0] == DB_SCHEMA_VERSION:
                _LOGGER.debug("Schema is current version %d", DB_SCHEMA_VERSION)
                return
            else:
                _LOGGER.warning("Schema version mismatch, attempting migration")
        except sqlite3.OperationalError:
            _LOGGER.debug("Schema version table not found, creating schema")

        # Create schema
        schema_sql = f"""
        -- Schema version tracking
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Books table
        CREATE TABLE IF NOT EXISTS books (
            isbn TEXT PRIMARY KEY NOT NULL,
            title TEXT NOT NULL,
            subtitle TEXT,
            authors TEXT NOT NULL,  -- JSON array stored as string
            publisher TEXT,
            year INTEGER,
            description TEXT,
            cover_url TEXT,
            language TEXT,
            pages INTEGER,
            room TEXT,
            shelf TEXT,
            compartment TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        -- Search indices for performance (designed for 10k+ books)
        CREATE INDEX IF NOT EXISTS idx_books_title 
            ON books(title COLLATE NOCASE);
        
        CREATE INDEX IF NOT EXISTS idx_books_authors 
            ON books(authors);
        
        CREATE INDEX IF NOT EXISTS idx_books_isbn 
            ON books(isbn);
        
        CREATE INDEX IF NOT EXISTS idx_books_publisher 
            ON books(publisher COLLATE NOCASE);
        
        CREATE INDEX IF NOT EXISTS idx_books_year 
            ON books(year);
        
        CREATE INDEX IF NOT EXISTS idx_books_room 
            ON books(room COLLATE NOCASE);
        
        CREATE INDEX IF NOT EXISTS idx_books_created_at 
            ON books(created_at);

        -- Full-text search virtual table (for efficient text searching)
        CREATE VIRTUAL TABLE IF NOT EXISTS books_fts USING fts5(
            title,
            authors,
            description,
            content=books,
            content_rowid=rowid
        );
        """

        try:
            await self._connection.executescript(schema_sql)
            
            # Insert schema version
            await self._connection.execute(
                "DELETE FROM schema_version"
            )
            await self._connection.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (DB_SCHEMA_VERSION,),
            )
            await self._connection.commit()
            _LOGGER.info("Database schema created (version %d)", DB_SCHEMA_VERSION)
        except Exception as e:
            _LOGGER.error("Failed to create schema: %s", e)
            raise

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    async def async_add_book(self, book: BookEntity) -> None:
        """Add a new book to the database.
        
        Args:
            book: BookEntity to add
            
        Raises:
            RuntimeError: If database not initialized
            sqlite3.IntegrityError: If ISBN already exists
        """
        if not self._connection:
            raise RuntimeError("Database not initialized")

        try:
            authors_json = json.dumps(book.authors)
            
            await self._connection.execute(
                """
                INSERT INTO books (
                    isbn, title, subtitle, authors, publisher, year,
                    description, cover_url, language, pages,
                    room, shelf, compartment, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    book.isbn,
                    book.title,
                    book.subtitle,
                    authors_json,
                    book.publisher,
                    book.year,
                    book.description,
                    book.cover_url,
                    book.language,
                    book.pages,
                    book.location.room if book.location else None,
                    book.location.shelf if book.location else None,
                    book.location.compartment if book.location else None,
                    book.created_at.isoformat(),
                    book.updated_at.isoformat(),
                ),
            )
            await self._connection.commit()
            _LOGGER.debug("Book added: %s (%s)", book.title, book.isbn)
        except sqlite3.IntegrityError as e:
            _LOGGER.error("Book already exists: %s", book.isbn)
            raise
        except Exception as e:
            _LOGGER.error("Failed to add book: %s", e)
            raise

    async def async_get_book(self, isbn: str) -> Optional[BookEntity]:
        """Get a book by ISBN.
        
        Args:
            isbn: ISBN to retrieve
            
        Returns:
            BookEntity if found, None otherwise
        """
        if not self._connection:
            raise RuntimeError("Database not initialized")

        try:
            cursor = await self._connection.execute(
                "SELECT * FROM books WHERE isbn = ?",
                (isbn,),
            )
            row = await cursor.fetchone()
            
            if not row:
                return None
            
            return self._row_to_book_entity(row)
        except Exception as e:
            _LOGGER.error("Failed to get book: %s", e)
            raise

    async def async_update_book(self, book: BookEntity) -> None:
        """Update an existing book.
        
        Args:
            book: BookEntity to update
            
        Raises:
            RuntimeError: If database not initialized
        """
        if not self._connection:
            raise RuntimeError("Database not initialized")

        try:
            book.updated_at = datetime.now(timezone.utc)
            authors_json = json.dumps(book.authors)
            
            await self._connection.execute(
                """
                UPDATE books SET
                    title = ?, subtitle = ?, authors = ?, publisher = ?,
                    year = ?, description = ?, cover_url = ?, language = ?,
                    pages = ?, room = ?, shelf = ?, compartment = ?,
                    updated_at = ?
                WHERE isbn = ?
                """,
                (
                    book.title,
                    book.subtitle,
                    authors_json,
                    book.publisher,
                    book.year,
                    book.description,
                    book.cover_url,
                    book.language,
                    book.pages,
                    book.location.room if book.location else None,
                    book.location.shelf if book.location else None,
                    book.location.compartment if book.location else None,
                    book.updated_at.isoformat(),
                    book.isbn,
                ),
            )
            await self._connection.commit()
            _LOGGER.debug("Book updated: %s (%s)", book.title, book.isbn)
        except Exception as e:
            _LOGGER.error("Failed to update book: %s", e)
            raise

    async def async_delete_book(self, isbn: str) -> bool:
        """Delete a book by ISBN.

        Args:
            isbn: ISBN to delete

        Returns:
            True if book was deleted, False if not found
        """
        if not self._connection:
            raise RuntimeError("Database not initialized")

        try:
            cursor = await self._connection.execute(
                "DELETE FROM books WHERE isbn = ?",
                (isbn,),
            )
            await self._connection.commit()

            if cursor.rowcount > 0:
                _LOGGER.debug("Book deleted: %s", isbn)
                return True
            return False
        except Exception as e:
            _LOGGER.error("Failed to delete book: %s", e)
            raise

    async def async_update_location(
        self, isbn: str, location: Optional[BookLocation]
    ) -> bool:
        """Update only the location of a book.

        Args:
            isbn: ISBN of the book to update
            location: New location (None to clear location)

        Returns:
            True if book was updated, False if not found

        Raises:
            RuntimeError: If database not initialized
        """
        if not self._connection:
            raise RuntimeError("Database not initialized")

        try:
            cursor = await self._connection.execute(
                """
                UPDATE books SET
                    room = ?,
                    shelf = ?,
                    compartment = ?,
                    updated_at = ?
                WHERE isbn = ?
                """,
                (
                    location.room if location else None,
                    location.shelf if location else None,
                    location.compartment if location else None,
                    datetime.now(timezone.utc).isoformat(),
                    isbn,
                ),
            )
            await self._connection.commit()

            if cursor.rowcount > 0:
                _LOGGER.debug("Location updated for ISBN: %s", isbn)
                return True
            return False
        except Exception as e:
            _LOGGER.error("Failed to update location: %s", e)
            raise

    async def async_get_all_books(
        self, limit: int = 1000, offset: int = 0
    ) -> Tuple[List[BookEntity], int]:
        """Get all books with pagination.
        
        Args:
            limit: Maximum number of results
            offset: Result offset for pagination
            
        Returns:
            Tuple of (books list, total count)
        """
        if not self._connection:
            raise RuntimeError("Database not initialized")

        try:
            # Get total count
            cursor = await self._connection.execute(
                "SELECT COUNT(*) FROM books"
            )
            total_row = await cursor.fetchone()
            total_count = total_row[0] if total_row else 0

            # Get paginated results
            cursor = await self._connection.execute(
                """
                SELECT * FROM books
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
            rows = await cursor.fetchall()
            books = [self._row_to_book_entity(row) for row in rows]
            
            return books, total_count
        except Exception as e:
            _LOGGER.error("Failed to get all books: %s", e)
            raise

    async def async_get_book_count(self) -> int:
        """Get total number of books in database.
        
        Returns:
            Total book count
        """
        if not self._connection:
            raise RuntimeError("Database not initialized")

        try:
            cursor = await self._connection.execute(
                "SELECT COUNT(*) FROM books"
            )
            row = await cursor.fetchone()
            return row[0] if row else 0
        except Exception as e:
            _LOGGER.error("Failed to get book count: %s", e)
            raise

    # =========================================================================
    # Search Operations (optimized for large libraries)
    # =========================================================================

    async def async_search_by_isbn(
        self, isbn: str, limit: int = 50, offset: int = 0
    ) -> SearchResult:
        """Search for books by ISBN.
        
        Args:
            isbn: ISBN to search for (exact match)
            limit: Maximum results
            offset: Result offset
            
        Returns:
            SearchResult with matching books
        """
        if not self._connection:
            raise RuntimeError("Database not initialized")

        try:
            # Exact ISBN match
            cursor = await self._connection.execute(
                "SELECT COUNT(*) FROM books WHERE isbn LIKE ?",
                (f"%{isbn}%",),
            )
            count_row = await cursor.fetchone()
            total_count = count_row[0] if count_row else 0

            cursor = await self._connection.execute(
                """
                SELECT * FROM books WHERE isbn LIKE ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (f"%{isbn}%", limit, offset),
            )
            rows = await cursor.fetchall()
            books = [self._row_to_book_entity(row) for row in rows]

            return SearchResult(
                books=books,
                total_count=total_count,
                query=isbn,
                search_type="isbn",
                limit=limit,
                offset=offset,
            )
        except Exception as e:
            _LOGGER.error("Failed to search by ISBN: %s", e)
            raise

    async def async_search_by_title(
        self, title: str, limit: int = 50, offset: int = 0
    ) -> SearchResult:
        """Search for books by title (partial, case-insensitive).
        
        Args:
            title: Title to search for
            limit: Maximum results
            offset: Result offset
            
        Returns:
            SearchResult with matching books
        """
        if not self._connection:
            raise RuntimeError("Database not initialized")

        try:
            query_pattern = f"%{title}%"
            
            cursor = await self._connection.execute(
                "SELECT COUNT(*) FROM books WHERE title COLLATE NOCASE LIKE ?",
                (query_pattern,),
            )
            count_row = await cursor.fetchone()
            total_count = count_row[0] if count_row else 0

            cursor = await self._connection.execute(
                """
                SELECT * FROM books WHERE title COLLATE NOCASE LIKE ?
                ORDER BY title ASC
                LIMIT ? OFFSET ?
                """,
                (query_pattern, limit, offset),
            )
            rows = await cursor.fetchall()
            books = [self._row_to_book_entity(row) for row in rows]

            return SearchResult(
                books=books,
                total_count=total_count,
                query=title,
                search_type="title",
                limit=limit,
                offset=offset,
            )
        except Exception as e:
            _LOGGER.error("Failed to search by title: %s", e)
            raise

    async def async_search_by_author(
        self, author: str, limit: int = 50, offset: int = 0
    ) -> SearchResult:
        """Search for books by author (partial match in authors list).
        
        Args:
            author: Author name to search for
            limit: Maximum results
            offset: Result offset
            
        Returns:
            SearchResult with matching books
        """
        if not self._connection:
            raise RuntimeError("Database not initialized")

        try:
            # Search in authors JSON field using LIKE
            query_pattern = f"%{author}%"
            
            cursor = await self._connection.execute(
                """
                SELECT COUNT(*) FROM books 
                WHERE authors COLLATE NOCASE LIKE ?
                """,
                (query_pattern,),
            )
            count_row = await cursor.fetchone()
            total_count = count_row[0] if count_row else 0

            cursor = await self._connection.execute(
                """
                SELECT * FROM books 
                WHERE authors COLLATE NOCASE LIKE ?
                ORDER BY title ASC
                LIMIT ? OFFSET ?
                """,
                (query_pattern, limit, offset),
            )
            rows = await cursor.fetchall()
            books = [self._row_to_book_entity(row) for row in rows]

            return SearchResult(
                books=books,
                total_count=total_count,
                query=author,
                search_type="author",
                limit=limit,
                offset=offset,
            )
        except Exception as e:
            _LOGGER.error("Failed to search by author: %s", e)
            raise

    async def async_search_by_room(
        self, room: str, limit: int = 1000, offset: int = 0
    ) -> SearchResult:
        """Search for books by location room.
        
        Args:
            room: Room name to search for
            limit: Maximum results
            offset: Result offset
            
        Returns:
            SearchResult with matching books
        """
        if not self._connection:
            raise RuntimeError("Database not initialized")

        try:
            query_pattern = f"%{room}%"
            
            cursor = await self._connection.execute(
                """
                SELECT COUNT(*) FROM books 
                WHERE room COLLATE NOCASE LIKE ?
                """,
                (query_pattern,),
            )
            count_row = await cursor.fetchone()
            total_count = count_row[0] if count_row else 0

            cursor = await self._connection.execute(
                """
                SELECT * FROM books 
                WHERE room COLLATE NOCASE LIKE ?
                ORDER BY room, shelf, compartment
                LIMIT ? OFFSET ?
                """,
                (query_pattern, limit, offset),
            )
            rows = await cursor.fetchall()
            books = [self._row_to_book_entity(row) for row in rows]

            return SearchResult(
                books=books,
                total_count=total_count,
                query=room,
                search_type="room",
                limit=limit,
                offset=offset,
            )
        except Exception as e:
            _LOGGER.error("Failed to search by room: %s", e)
            raise

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _row_to_book_entity(self, row: Tuple) -> BookEntity:
        """Convert database row to BookEntity.
        
        Args:
            row: Database row tuple
            
        Returns:
            BookEntity object
        """
        # Unpack row (columns must match query order)
        (
            isbn,
            title,
            subtitle,
            authors_json,
            publisher,
            year,
            description,
            cover_url,
            language,
            pages,
            room,
            shelf,
            compartment,
            created_at_str,
            updated_at_str,
        ) = row

        # Parse authors from JSON
        try:
            authors = json.loads(authors_json) if authors_json else []
        except json.JSONDecodeError:
            _LOGGER.warning("Failed to parse authors for ISBN %s", isbn)
            authors = []

        # Parse timestamps
        created_at = datetime.fromisoformat(created_at_str)
        updated_at = datetime.fromisoformat(updated_at_str)

        # Create location if all fields are present
        location = None
        if room and shelf and compartment:
            location = BookLocation(room=room, shelf=shelf, compartment=compartment)

        return BookEntity(
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
            location=location,
            created_at=created_at,
            updated_at=updated_at,
        )

    async def async_export_all_books(self) -> List[Dict[str, Any]]:
        """Export all books as dictionaries (for diagnostics/backup).
        
        Returns:
            List of book dictionaries
        """
        if not self._connection:
            raise RuntimeError("Database not initialized")

        try:
            books, _ = await self.async_get_all_books(limit=100000)
            return [book.to_dict() for book in books]
        except Exception as e:
            _LOGGER.error("Failed to export books: %s", e)
            raise

    async def async_get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics.
        
        Returns:
            Dictionary with database stats
        """
        if not self._connection:
            raise RuntimeError("Database not initialized")

        try:
            count = await self.async_get_book_count()
            
            # Get database file size
            db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
            
            # Get date range of books
            cursor = await self._connection.execute(
                """
                SELECT MIN(created_at), MAX(created_at) FROM books
                """
            )
            row = await cursor.fetchone()
            oldest = row[0] if row and row[0] else None
            newest = row[1] if row and row[1] else None

            return {
                "total_books": count,
                "database_size_bytes": db_size,
                "oldest_book_added": oldest,
                "newest_book_added": newest,
                "database_path": str(self.db_path),
                "schema_version": DB_SCHEMA_VERSION,
            }
        except Exception as e:
            _LOGGER.error("Failed to get database stats: %s", e)
            raise
