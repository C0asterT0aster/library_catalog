"""Data models for Library Catalog integration."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum

from .validation import (
    ISBNValidator,
    BookValidator,
    LocationValidator,
    ValidationError,
)


class BarCodeFormat(Enum):
    """Supported barcode formats."""

    ISBN10 = "ISBN10"
    ISBN13 = "ISBN13"
    EAN13 = "EAN13"
    CODE128 = "CODE128"
    UNKNOWN = "UNKNOWN"


@dataclass
class BookLocation:
    """Represents a hierarchical location for a book.

    This structure supports storing structured location data without
    hardcoding available rooms, shelves, or compartments.
    Users define their own location hierarchy, which is stored with each book.
    """

    room: str
    shelf: str
    compartment: str

    def __post_init__(self):
        """Validate location fields after initialization."""
        LocationValidator.validate_location(self.room, self.shelf, self.compartment)

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary representation."""
        return {
            "room": self.room,
            "shelf": self.shelf,
            "compartment": self.compartment,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "BookLocation":
        """Create from dictionary representation.

        Raises:
            ValidationError: If location data is invalid
        """
        return cls(
            room=data.get("room", ""),
            shelf=data.get("shelf", ""),
            compartment=data.get("compartment", ""),
        )

    def __str__(self) -> str:
        """String representation: Room > Shelf > Compartment."""
        return f"{self.room} > {self.shelf} > {self.compartment}"


@dataclass
class BookData:
    """Book data as retrieved from external APIs.

    This represents raw book data from sources like Open Library or Google Books.
    Not all fields are guaranteed to be present.

    This is the external API layer - minimal validation, accepts what APIs provide.
    """

    isbn: str
    title: str
    subtitle: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    publisher: Optional[str] = None
    year: Optional[int] = None
    description: Optional[str] = None
    cover_url: Optional[str] = None
    language: Optional[str] = None
    pages: Optional[int] = None

    def __post_init__(self):
        """Basic validation for API data."""
        # Normalize ISBN
        if self.isbn:
            self.isbn = ISBNValidator.validate(self.isbn)

        # Ensure title is not empty
        if not self.title or not self.title.strip():
            raise ValidationError("Title is required")

        # Ensure at least one author
        if not self.authors or len(self.authors) == 0:
            raise ValidationError("At least one author is required")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "isbn": self.isbn,
            "title": self.title,
            "subtitle": self.subtitle,
            "authors": self.authors,
            "publisher": self.publisher,
            "year": self.year,
            "description": self.description,
            "cover_url": self.cover_url,
            "language": self.language,
            "pages": self.pages,
        }


@dataclass
class BookEntity:
    """Complete book entity stored in the database.

    This represents a book as stored in the local SQLite database,
    including location information and timestamps.

    This is the domain model - full validation, ready for persistence.

    Future extensibility: Additional fields can be added here without
    breaking existing functionality:
    - categories: List[str] - Book categories/genres
    - tags: List[str] - User-defined tags
    - rating: Optional[float] - User rating (0-5)
    - reading_status: Optional[str] - "to_read", "reading", "completed"
    - notes: Optional[str] - Personal notes
    - borrowed_by: Optional[str] - Name of person who borrowed the book
    - borrowed_date: Optional[datetime] - When book was lent out
    - series: Optional[str] - Book series name
    - series_number: Optional[int] - Position in series
    """

    isbn: str  # Primary key
    title: str
    subtitle: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    publisher: Optional[str] = None
    year: Optional[int] = None
    description: Optional[str] = None
    cover_url: Optional[str] = None
    language: Optional[str] = None
    pages: Optional[int] = None
    location: Optional[BookLocation] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        """Validate all fields after initialization."""
        # Normalize and validate ISBN
        self.isbn = ISBNValidator.validate(self.isbn)

        # Validate required fields
        BookValidator.validate_required_fields(self.isbn, self.title, self.authors)

        # Validate individual fields
        BookValidator.validate_title(self.title)
        BookValidator.validate_subtitle(self.subtitle)
        BookValidator.validate_authors(self.authors)
        BookValidator.validate_publisher(self.publisher)
        BookValidator.validate_year(self.year)
        BookValidator.validate_pages(self.pages)
        BookValidator.validate_description(self.description)
        BookValidator.validate_language(self.language)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "isbn": self.isbn,
            "title": self.title,
            "subtitle": self.subtitle,
            "authors": self.authors,
            "publisher": self.publisher,
            "year": self.year,
            "description": self.description,
            "cover_url": self.cover_url,
            "language": self.language,
            "pages": self.pages,
            "location": self.location.to_dict() if self.location else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BookEntity":
        """Create from dictionary representation."""
        location = None
        if data.get("location"):
            location = BookLocation.from_dict(data["location"])

        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        if not created_at:
            created_at = datetime.now(timezone.utc)

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        if not updated_at:
            updated_at = datetime.now(timezone.utc)

        return cls(
            isbn=data["isbn"],
            title=data["title"],
            subtitle=data.get("subtitle"),
            authors=data.get("authors", []),
            publisher=data.get("publisher"),
            year=data.get("year"),
            description=data.get("description"),
            cover_url=data.get("cover_url"),
            language=data.get("language"),
            pages=data.get("pages"),
            location=location,
            created_at=created_at,
            updated_at=updated_at,
        )

    @classmethod
    def from_book_data(
        cls, book_data: BookData, location: Optional[BookLocation] = None
    ) -> "BookEntity":
        """Create BookEntity from BookData (API response)."""
        now = datetime.now(timezone.utc)
        return cls(
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


@dataclass
class SearchResult:
    """Result from a search operation."""

    books: List[BookEntity]
    total_count: int
    query: str
    search_type: str  # "isbn", "title", "author"
    limit: int
    offset: int = 0

    def has_more(self) -> bool:
        """Check if there are more results available."""
        return self.offset + len(self.books) < self.total_count

    def next_offset(self) -> int:
        """Get the offset for the next page of results."""
        return self.offset + self.limit
