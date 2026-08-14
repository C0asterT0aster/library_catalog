"""Tests for models module."""
import pytest
from custom_components.library_catalog.models import (
    BookLocation,
    BookData,
    BookEntity,
    SearchResult,
    BarCodeFormat,
)
from datetime import datetime


class TestBookLocation:
    """Test BookLocation model."""

    def test_create_book_location(self):
        """Test creating a BookLocation instance."""
        loc = BookLocation(room="Living Room", shelf="Top", compartment="Left")
        assert loc.room == "Living Room"
        assert loc.shelf == "Top"
        assert loc.compartment == "Left"

    def test_book_location_to_dict(self):
        """Test converting BookLocation to dict."""
        loc = BookLocation(room="Bedroom", shelf="Middle", compartment="Center")
        data = loc.to_dict()
        assert data["room"] == "Bedroom"
        assert data["shelf"] == "Middle"

    def test_book_location_from_dict(self):
        """Test creating BookLocation from dict."""
        data = {"room": "Kitchen", "shelf": "Lower", "compartment": "Right"}
        loc = BookLocation.from_dict(data)
        assert loc.room == "Kitchen"

    def test_book_location_str(self):
        """Test string representation."""
        loc = BookLocation(room="A", shelf="B", compartment="C")
        assert str(loc) == "A > B > C"


class TestBookData:
    """Test BookData model."""

    def test_create_book_data(self):
        """Test creating a BookData instance."""
        book = BookData(
            isbn="9780743273565",
            title="The Great Gatsby",
            authors=["F. Scott Fitzgerald"],
        )
        assert book.isbn == "9780743273565"
        assert book.title == "The Great Gatsby"

    def test_book_data_optional_fields(self):
        """Test BookData with optional fields."""
        book = BookData(
            isbn="9780451524935",
            title="1984",
            authors=["George Orwell"],  # Required field
            subtitle="A Novel",
            publisher="Signet Classics",
            year=1949,
            pages=328,
            language="en",
        )
        assert book.subtitle == "A Novel"
        assert book.year == 1949


class TestSearchResult:
    """Test SearchResult model."""

    def test_create_search_result(self):
        """Test creating a SearchResult instance."""
        book1 = BookData(isbn="9780743273565", title="Book 1", authors=["Author 1"])
        book2 = BookData(isbn="9780451524935", title="Book 2", authors=["Author 2"])

        result = SearchResult(
            books=[book1, book2],
            total_count=42,
            query="gatsby",
            search_type="title",
            limit=10,
            offset=0,
        )

        assert len(result.books) == 2
        assert result.total_count == 42
        assert result.has_more()

    def test_search_result_pagination(self):
        """Test SearchResult pagination helpers."""
        book1 = BookData(isbn="9780743273565", title="Book 1", authors=["Author"])

        result = SearchResult(
            books=[book1],
            total_count=100,
            query="test",
            search_type="title",
            limit=10,
            offset=0,
        )

        assert result.has_more()
        assert result.next_offset() == 10


class TestBarCodeFormat:
    """Test BarCodeFormat enum."""

    def test_barcode_formats(self):
        """Test all barcode format values."""
        assert BarCodeFormat.ISBN10.value == "ISBN10"
        assert BarCodeFormat.ISBN13.value == "ISBN13"
        assert BarCodeFormat.EAN13.value == "EAN13"
        assert BarCodeFormat.CODE128.value == "CODE128"
        assert BarCodeFormat.UNKNOWN.value == "UNKNOWN"
