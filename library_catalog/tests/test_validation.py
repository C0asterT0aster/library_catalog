"""Tests for validation utilities."""
import pytest
from custom_components.library_catalog.validation import (
    ISBNValidator,
    BookValidator,
    LocationValidator,
    ValidationError,
)


class TestISBNValidator:
    """Test ISBN validation."""

    def test_validate_valid_isbn13(self):
        """Test validation of valid ISBN-13."""
        result = ISBNValidator.validate("978-3-16-148410-0")
        assert result == "9783161484100"

    def test_validate_valid_isbn10(self):
        """Test validation of valid ISBN-10 and conversion to ISBN-13."""
        result = ISBNValidator.validate("0-306-40615-2")
        assert len(result) == 13
        assert result.startswith("978")

    def test_validate_isbn_without_hyphens(self):
        """Test validation of ISBN without hyphens."""
        result = ISBNValidator.validate("9783161484100")
        assert result == "9783161484100"

    def test_validate_empty_isbn(self):
        """Test that empty ISBN raises error."""
        with pytest.raises(ValidationError, match="ISBN cannot be empty"):
            ISBNValidator.validate("")

    def test_validate_invalid_length(self):
        """Test that invalid length raises error."""
        with pytest.raises(ValidationError, match="ISBN must be 10 or 13 digits"):
            ISBNValidator.validate("12345")

    def test_validate_invalid_checksum(self):
        """Test that invalid checksum raises error."""
        with pytest.raises(ValidationError, match="Invalid ISBN"):
            ISBNValidator.validate("9783161484101")  # Invalid checksum

    def test_clean_isbn(self):
        """Test ISBN cleaning."""
        assert ISBNValidator.clean_isbn("978-3-16-148410-0") == "9783161484100"
        assert ISBNValidator.clean_isbn("978 3 16 148410 0") == "9783161484100"
        assert ISBNValidator.clean_isbn("978-3-16-148410-x") == "978316148410X"

    def test_format_isbn13(self):
        """Test ISBN-13 formatting."""
        formatted = ISBNValidator.format_isbn13("9783161484100")
        assert "-" in formatted
        assert formatted.startswith("978-")


class TestBookValidator:
    """Test book field validation."""

    def test_validate_required_fields_success(self):
        """Test successful validation of required fields."""
        BookValidator.validate_required_fields(
            isbn="9783161484100",
            title="Test Book",
            authors=["Test Author"]
        )
        # Should not raise

    def test_validate_missing_isbn(self):
        """Test that missing ISBN raises error."""
        with pytest.raises(ValidationError, match="ISBN is required"):
            BookValidator.validate_required_fields(
                isbn="",
                title="Test",
                authors=["Author"]
            )

    def test_validate_missing_title(self):
        """Test that missing title raises error."""
        with pytest.raises(ValidationError, match="Title is required"):
            BookValidator.validate_required_fields(
                isbn="9783161484100",
                title="",
                authors=["Author"]
            )

    def test_validate_missing_authors(self):
        """Test that missing authors raises error."""
        with pytest.raises(ValidationError, match="At least one author is required"):
            BookValidator.validate_required_fields(
                isbn="9783161484100",
                title="Test",
                authors=[]
            )

    def test_validate_title_success(self):
        """Test successful title validation."""
        BookValidator.validate_title("Valid Title")
        # Should not raise

    def test_validate_title_too_long(self):
        """Test that too long title raises error."""
        long_title = "x" * 501
        with pytest.raises(ValidationError, match="Title too long"):
            BookValidator.validate_title(long_title)

    def test_validate_subtitle_success(self):
        """Test successful subtitle validation."""
        BookValidator.validate_subtitle("Valid Subtitle")
        BookValidator.validate_subtitle(None)
        # Should not raise

    def test_validate_subtitle_too_long(self):
        """Test that too long subtitle raises error."""
        long_subtitle = "x" * 501
        with pytest.raises(ValidationError, match="Subtitle too long"):
            BookValidator.validate_subtitle(long_subtitle)

    def test_validate_authors_success(self):
        """Test successful authors validation."""
        BookValidator.validate_authors(["Author 1", "Author 2"])
        # Should not raise

    def test_validate_authors_empty_list(self):
        """Test that empty authors list raises error."""
        with pytest.raises(ValidationError, match="At least one author is required"):
            BookValidator.validate_authors([])

    def test_validate_authors_too_many(self):
        """Test that too many authors raises error."""
        many_authors = [f"Author {i}" for i in range(21)]
        with pytest.raises(ValidationError, match="Too many authors"):
            BookValidator.validate_authors(many_authors)

    def test_validate_authors_empty_name(self):
        """Test that empty author name raises error."""
        with pytest.raises(ValidationError, match="Author .* cannot be empty"):
            BookValidator.validate_authors(["Valid Author", ""])

    def test_validate_authors_name_too_long(self):
        """Test that too long author name raises error."""
        long_name = "x" * 201
        with pytest.raises(ValidationError, match="Author .* name too long"):
            BookValidator.validate_authors([long_name])

    def test_validate_year_success(self):
        """Test successful year validation."""
        BookValidator.validate_year(2020)
        BookValidator.validate_year(None)
        # Should not raise

    def test_validate_year_invalid_type(self):
        """Test that invalid year type raises error."""
        with pytest.raises(ValidationError, match="Year must be an integer"):
            BookValidator.validate_year("2020")

    def test_validate_year_out_of_range(self):
        """Test that out of range year raises error."""
        with pytest.raises(ValidationError, match="Year out of range"):
            BookValidator.validate_year(500)

        with pytest.raises(ValidationError, match="Year out of range"):
            BookValidator.validate_year(3000)

    def test_validate_pages_success(self):
        """Test successful pages validation."""
        BookValidator.validate_pages(300)
        BookValidator.validate_pages(None)
        # Should not raise

    def test_validate_pages_invalid_type(self):
        """Test that invalid pages type raises error."""
        with pytest.raises(ValidationError, match="Page count must be an integer"):
            BookValidator.validate_pages("300")

    def test_validate_pages_negative(self):
        """Test that negative pages raises error."""
        with pytest.raises(ValidationError, match="Page count must be positive"):
            BookValidator.validate_pages(-10)

    def test_validate_pages_too_high(self):
        """Test that too high page count raises error."""
        with pytest.raises(ValidationError, match="Page count too high"):
            BookValidator.validate_pages(20000)

    def test_validate_description_success(self):
        """Test successful description validation."""
        BookValidator.validate_description("Valid description")
        BookValidator.validate_description(None)
        # Should not raise

    def test_validate_description_too_long(self):
        """Test that too long description raises error."""
        long_desc = "x" * 5001
        with pytest.raises(ValidationError, match="Description too long"):
            BookValidator.validate_description(long_desc)

    def test_validate_language_success(self):
        """Test successful language validation."""
        BookValidator.validate_language("en")
        BookValidator.validate_language("de-DE")
        BookValidator.validate_language(None)
        # Should not raise

    def test_validate_language_too_long(self):
        """Test that too long language code raises error."""
        with pytest.raises(ValidationError, match="Language code too long"):
            BookValidator.validate_language("x" * 11)


class TestLocationValidator:
    """Test location validation."""

    def test_validate_location_success(self):
        """Test successful location validation."""
        LocationValidator.validate_location("Living Room", "Shelf 1", "Top")
        # Should not raise

    def test_validate_location_empty_room(self):
        """Test that empty room raises error."""
        with pytest.raises(ValidationError, match="Room cannot be empty"):
            LocationValidator.validate_location("", "Shelf", "Top")

    def test_validate_location_empty_shelf(self):
        """Test that empty shelf raises error."""
        with pytest.raises(ValidationError, match="Shelf cannot be empty"):
            LocationValidator.validate_location("Room", "", "Top")

    def test_validate_location_empty_compartment(self):
        """Test that empty compartment raises error."""
        with pytest.raises(ValidationError, match="Compartment cannot be empty"):
            LocationValidator.validate_location("Room", "Shelf", "")

    def test_validate_location_room_too_long(self):
        """Test that too long room name raises error."""
        long_room = "x" * 101
        with pytest.raises(ValidationError, match="Room name too long"):
            LocationValidator.validate_location(long_room, "Shelf", "Top")

    def test_validate_location_shelf_too_long(self):
        """Test that too long shelf name raises error."""
        long_shelf = "x" * 101
        with pytest.raises(ValidationError, match="Shelf name too long"):
            LocationValidator.validate_location("Room", long_shelf, "Top")

    def test_validate_location_compartment_too_long(self):
        """Test that too long compartment name raises error."""
        long_compartment = "x" * 101
        with pytest.raises(ValidationError, match="Compartment name too long"):
            LocationValidator.validate_location("Room", "Shelf", long_compartment)
