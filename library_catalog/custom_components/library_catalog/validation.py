"""Validation utilities for Library Catalog models."""
import re
from typing import Optional
from stdnum import isbn as isbn_validator
from stdnum.exceptions import ValidationError as StdnumValidationError


class ValidationError(Exception):
    """Raised when model validation fails."""
    pass


class ISBNValidator:
    """ISBN validation utilities."""

    # Regex patterns for ISBN formats
    ISBN10_PATTERN = re.compile(r'^(?:\d{9}[\dX]|\d{1,5}-\d{1,7}-\d{1,7}-[\dX])$')
    ISBN13_PATTERN = re.compile(r'^(?:97[89]\d{10}|97[89]-\d{1,5}-\d{1,7}-\d{1,7}-\d)$')

    @staticmethod
    def clean_isbn(isbn: str) -> str:
        """Remove hyphens and spaces from ISBN.

        Args:
            isbn: ISBN string with possible formatting

        Returns:
            Cleaned ISBN string
        """
        return isbn.replace("-", "").replace(" ", "").upper()

    @classmethod
    def validate(cls, isbn: str) -> str:
        """Validate and normalize ISBN.

        Args:
            isbn: ISBN-10 or ISBN-13 string

        Returns:
            Normalized ISBN-13 string

        Raises:
            ValidationError: If ISBN is invalid
        """
        if not isbn:
            raise ValidationError("ISBN cannot be empty")

        # Clean the ISBN
        cleaned = cls.clean_isbn(isbn)

        # Check length
        if len(cleaned) not in (10, 13):
            raise ValidationError(
                f"ISBN must be 10 or 13 digits, got {len(cleaned)}"
            )

        # Validate using stdnum
        try:
            if not isbn_validator.is_valid(cleaned):
                raise ValidationError(f"Invalid ISBN: {isbn}")
        except StdnumValidationError as e:
            raise ValidationError(f"ISBN validation failed: {str(e)}")

        # Convert to ISBN-13 if needed
        if len(cleaned) == 10:
            try:
                normalized = isbn_validator.to_isbn13(cleaned)
            except Exception as e:
                raise ValidationError(f"Failed to convert ISBN-10 to ISBN-13: {str(e)}")
        else:
            normalized = cleaned

        return normalized

    @staticmethod
    def format_isbn13(isbn: str) -> str:
        """Format ISBN-13 with hyphens for display.

        Args:
            isbn: 13-digit ISBN string

        Returns:
            Formatted ISBN string (e.g., 978-3-16-148410-0)
        """
        if len(isbn) != 13:
            return isbn
        return f"{isbn[:3]}-{isbn[3]}-{isbn[4:6]}-{isbn[6:12]}-{isbn[12]}"


class BookValidator:
    """Validation for book fields."""

    # Field length limits
    MAX_TITLE_LENGTH = 500
    MAX_SUBTITLE_LENGTH = 500
    MAX_AUTHOR_LENGTH = 200
    MAX_AUTHORS_COUNT = 20
    MAX_PUBLISHER_LENGTH = 200
    MAX_DESCRIPTION_LENGTH = 5000
    MAX_LANGUAGE_LENGTH = 10
    MAX_PAGES = 10000
    MIN_YEAR = 1000
    MAX_YEAR = 2100

    @classmethod
    def validate_required_fields(cls, isbn: str, title: str, authors: list) -> None:
        """Validate required fields.

        Args:
            isbn: ISBN string
            title: Book title
            authors: List of author names

        Raises:
            ValidationError: If required fields are missing or invalid
        """
        if not isbn or not isbn.strip():
            raise ValidationError("ISBN is required")

        if not title or not title.strip():
            raise ValidationError("Title is required")

        if not authors or len(authors) == 0:
            raise ValidationError("At least one author is required")

    @classmethod
    def validate_title(cls, title: str) -> None:
        """Validate title field.

        Args:
            title: Book title

        Raises:
            ValidationError: If title is invalid
        """
        if not title or not title.strip():
            raise ValidationError("Title cannot be empty")

        if len(title) > cls.MAX_TITLE_LENGTH:
            raise ValidationError(
                f"Title too long: {len(title)} chars (max {cls.MAX_TITLE_LENGTH})"
            )

    @classmethod
    def validate_subtitle(cls, subtitle: Optional[str]) -> None:
        """Validate subtitle field.

        Args:
            subtitle: Book subtitle

        Raises:
            ValidationError: If subtitle is invalid
        """
        if subtitle and len(subtitle) > cls.MAX_SUBTITLE_LENGTH:
            raise ValidationError(
                f"Subtitle too long: {len(subtitle)} chars (max {cls.MAX_SUBTITLE_LENGTH})"
            )

    @classmethod
    def validate_authors(cls, authors: list) -> None:
        """Validate authors list.

        Args:
            authors: List of author names

        Raises:
            ValidationError: If authors list is invalid
        """
        if not authors or len(authors) == 0:
            raise ValidationError("At least one author is required")

        if len(authors) > cls.MAX_AUTHORS_COUNT:
            raise ValidationError(
                f"Too many authors: {len(authors)} (max {cls.MAX_AUTHORS_COUNT})"
            )

        for i, author in enumerate(authors):
            if not author or not author.strip():
                raise ValidationError(f"Author {i+1} cannot be empty")

            if len(author) > cls.MAX_AUTHOR_LENGTH:
                raise ValidationError(
                    f"Author {i+1} name too long: {len(author)} chars (max {cls.MAX_AUTHOR_LENGTH})"
                )

    @classmethod
    def validate_publisher(cls, publisher: Optional[str]) -> None:
        """Validate publisher field.

        Args:
            publisher: Publisher name

        Raises:
            ValidationError: If publisher is invalid
        """
        if publisher and len(publisher) > cls.MAX_PUBLISHER_LENGTH:
            raise ValidationError(
                f"Publisher name too long: {len(publisher)} chars (max {cls.MAX_PUBLISHER_LENGTH})"
            )

    @classmethod
    def validate_year(cls, year: Optional[int]) -> None:
        """Validate publication year.

        Args:
            year: Publication year

        Raises:
            ValidationError: If year is invalid
        """
        if year is not None:
            if not isinstance(year, int):
                raise ValidationError("Year must be an integer")

            if year < cls.MIN_YEAR or year > cls.MAX_YEAR:
                raise ValidationError(
                    f"Year out of range: {year} (must be between {cls.MIN_YEAR} and {cls.MAX_YEAR})"
                )

    @classmethod
    def validate_pages(cls, pages: Optional[int]) -> None:
        """Validate page count.

        Args:
            pages: Number of pages

        Raises:
            ValidationError: If page count is invalid
        """
        if pages is not None:
            if not isinstance(pages, int):
                raise ValidationError("Page count must be an integer")

            if pages <= 0:
                raise ValidationError("Page count must be positive")

            if pages > cls.MAX_PAGES:
                raise ValidationError(
                    f"Page count too high: {pages} (max {cls.MAX_PAGES})"
                )

    @classmethod
    def validate_description(cls, description: Optional[str]) -> None:
        """Validate description field.

        Args:
            description: Book description

        Raises:
            ValidationError: If description is invalid
        """
        if description and len(description) > cls.MAX_DESCRIPTION_LENGTH:
            raise ValidationError(
                f"Description too long: {len(description)} chars (max {cls.MAX_DESCRIPTION_LENGTH})"
            )

    @classmethod
    def validate_language(cls, language: Optional[str]) -> None:
        """Validate language code.

        Args:
            language: Language code (e.g., 'en', 'de', 'en-US')

        Raises:
            ValidationError: If language code is invalid
        """
        if language and len(language) > cls.MAX_LANGUAGE_LENGTH:
            raise ValidationError(
                f"Language code too long: {len(language)} chars (max {cls.MAX_LANGUAGE_LENGTH})"
            )


class LocationValidator:
    """Validation for book location fields."""

    MAX_ROOM_LENGTH = 100
    MAX_SHELF_LENGTH = 100
    MAX_COMPARTMENT_LENGTH = 100

    @classmethod
    def validate_location(cls, room: str, shelf: str, compartment: str) -> None:
        """Validate location fields.

        Args:
            room: Room name
            shelf: Shelf name
            compartment: Compartment name

        Raises:
            ValidationError: If any location field is invalid
        """
        if not room or not room.strip():
            raise ValidationError("Room cannot be empty")

        if not shelf or not shelf.strip():
            raise ValidationError("Shelf cannot be empty")

        if not compartment or not compartment.strip():
            raise ValidationError("Compartment cannot be empty")

        if len(room) > cls.MAX_ROOM_LENGTH:
            raise ValidationError(
                f"Room name too long: {len(room)} chars (max {cls.MAX_ROOM_LENGTH})"
            )

        if len(shelf) > cls.MAX_SHELF_LENGTH:
            raise ValidationError(
                f"Shelf name too long: {len(shelf)} chars (max {cls.MAX_SHELF_LENGTH})"
            )

        if len(compartment) > cls.MAX_COMPARTMENT_LENGTH:
            raise ValidationError(
                f"Compartment name too long: {len(compartment)} chars (max {cls.MAX_COMPARTMENT_LENGTH})"
            )
