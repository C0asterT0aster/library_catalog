"""Tests for webhook handler."""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import web
from datetime import datetime, timezone

from custom_components.library_catalog.webhook import WebhookHandler
from custom_components.library_catalog.models import BarCodeFormat, BookData, BookEntity, BookLocation
from custom_components.library_catalog.book_service import BookNotFoundError
from custom_components.library_catalog.api import BookNotFoundError as APIBookNotFoundError


class TestWebhookHandler:
    """Test webhook handler for barcode scanner."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        hass = MagicMock()
        hass.bus = MagicMock()
        hass.bus.async_fire = AsyncMock()
        hass.data = {}
        return hass

    @pytest.fixture
    def mock_book_service(self):
        """Create mock book service."""
        service = AsyncMock()
        service.get_book = AsyncMock()
        return service

    @pytest.fixture
    def webhook_handler(self, mock_hass, mock_book_service):
        """Create webhook handler instance with mocked book service."""
        # Set up mock book service in hass.data
        from custom_components.library_catalog.const import DOMAIN
        mock_hass.data[DOMAIN] = {
            "entry_1": {"book_service": mock_book_service}
        }
        return WebhookHandler(mock_hass)

    @pytest.fixture
    def sample_book_metadata(self):
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
    def sample_book_entity(self):
        """Create sample book entity."""
        location = BookLocation(room="Living Room", shelf="Shelf 1", compartment="Top")
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
            location=location,
            created_at=now,
            updated_at=now,
        )

    @pytest.mark.asyncio
    async def test_valid_isbn_new_book(self, webhook_handler, mock_book_service, sample_book_metadata):
        """Test webhook with valid ISBN for a new book (not in catalog)."""
        # Mock book not found (not in catalog)
        mock_book_service.get_book.side_effect = BookNotFoundError("9780451524935")

        # Mock metadata fetch
        with patch(
            "custom_components.library_catalog.webhook.get_book_metadata",
            return_value=sample_book_metadata,
        ):
            request = MagicMock(spec=web.Request)
            request.json = AsyncMock(
                return_value={
                    "isbn": "9780451524935",
                    "format": "ISBN13",
                }
            )

            response = await webhook_handler.handle_barcode(request)

            # Verify response
            assert response.status == 200
            response_data = json.loads(response.body)
            assert response_data["success"] is True
            assert response_data["isbn"] == "9780451524935"
            assert response_data["exists"] is False
            assert response_data["book"]["title"] == "1984"
            assert response_data["book"]["authors"] == ["George Orwell"]
            assert "add_book service" in response_data["message"]

            # Verify event was fired
            webhook_handler.hass.bus.async_fire.assert_called_once()
            call_args = webhook_handler.hass.bus.async_fire.call_args
            assert call_args[0][0] == "library_catalog_barcode_scanned"
            assert call_args[0][1]["exists"] is False

    @pytest.mark.asyncio
    async def test_valid_isbn_existing_book(self, webhook_handler, mock_book_service, sample_book_entity):
        """Test webhook with valid ISBN for a book already in catalog (duplicate)."""
        # Mock book found (already in catalog)
        mock_book_service.get_book.return_value = sample_book_entity

        request = MagicMock(spec=web.Request)
        request.json = AsyncMock(
            return_value={
                "isbn": "9780451524935",
            }
        )

        response = await webhook_handler.handle_barcode(request)

        # Verify response
        assert response.status == 200
        response_data = json.loads(response.body)
        assert response_data["success"] is True
        assert response_data["isbn"] == "9780451524935"
        assert response_data["exists"] is True
        assert response_data["book"]["title"] == "1984"
        assert response_data["book"]["location"]["room"] == "Living Room"
        assert "already in catalog" in response_data["message"]

        # Verify event was fired
        webhook_handler.hass.bus.async_fire.assert_called_once()
        call_args = webhook_handler.hass.bus.async_fire.call_args
        assert call_args[0][1]["exists"] is True

    @pytest.mark.asyncio
    async def test_invalid_isbn(self, webhook_handler):
        """Test webhook with invalid ISBN."""
        request = MagicMock(spec=web.Request)
        request.json = AsyncMock(return_value={"isbn": "invalid-isbn-123"})

        response = await webhook_handler.handle_barcode(request)

        assert response.status == 400
        response_data = json.loads(response.body)
        assert response_data["success"] is False
        assert "Invalid ISBN" in response_data["error"]

    @pytest.mark.asyncio
    async def test_missing_isbn(self, webhook_handler):
        """Test webhook with missing ISBN field."""
        request = MagicMock(spec=web.Request)
        request.json = AsyncMock(return_value={"format": "ISBN13"})

        response = await webhook_handler.handle_barcode(request)

        assert response.status == 400
        response_data = json.loads(response.body)
        assert response_data["success"] is False
        assert "Missing ISBN" in response_data["error"]

    @pytest.mark.asyncio
    async def test_metadata_provider_failure(self, webhook_handler, mock_book_service):
        """Test webhook when metadata provider fails."""
        # Mock book not found in catalog
        mock_book_service.get_book.side_effect = BookNotFoundError("9780451524935")

        # Mock metadata fetch failure
        with patch(
            "custom_components.library_catalog.webhook.get_book_metadata",
            side_effect=APIBookNotFoundError("No metadata found"),
        ):
            request = MagicMock(spec=web.Request)
            request.json = AsyncMock(return_value={"isbn": "9780451524935"})

            response = await webhook_handler.handle_barcode(request)

            # Should return 404 when metadata not found
            assert response.status == 404
            response_data = json.loads(response.body)
            assert response_data["success"] is False
            assert response_data["exists"] is False
            assert "metadata not found" in response_data["error"].lower()

    @pytest.mark.asyncio
    async def test_isbn10_conversion(self, webhook_handler, mock_book_service, sample_book_metadata):
        """Test webhook with ISBN-10 (should convert to ISBN-13)."""
        mock_book_service.get_book.side_effect = BookNotFoundError("9780451524935")

        with patch(
            "custom_components.library_catalog.webhook.get_book_metadata",
            return_value=sample_book_metadata,
        ):
            request = MagicMock(spec=web.Request)
            request.json = AsyncMock(return_value={"isbn": "0451524934"})

            response = await webhook_handler.handle_barcode(request)

            assert response.status == 200
            response_data = json.loads(response.body)
            assert response_data["success"] is True
            assert response_data["isbn"] == "9780451524935"

    @pytest.mark.asyncio
    async def test_flexible_field_names(self, webhook_handler, mock_book_service, sample_book_metadata):
        """Test webhook with alternative field names (isbn_input, code, barcode)."""
        mock_book_service.get_book.side_effect = BookNotFoundError("9780451524935")

        test_cases = [
            {"isbn_input": "9780451524935"},
            {"code": "9780451524935"},
            {"barcode": "9780451524935"},
        ]

        for payload in test_cases:
            with patch(
                "custom_components.library_catalog.webhook.get_book_metadata",
                return_value=sample_book_metadata,
            ):
                request = MagicMock(spec=web.Request)
                request.json = AsyncMock(return_value=payload)

                response = await webhook_handler.handle_barcode(request)

                assert response.status == 200
                response_data = json.loads(response.body)
                assert response_data["success"] is True
                assert response_data["isbn"] == "9780451524935"

    @pytest.mark.asyncio
    async def test_isbn_with_hyphens(self, webhook_handler, mock_book_service, sample_book_metadata):
        """Test webhook with hyphenated ISBN."""
        mock_book_service.get_book.side_effect = BookNotFoundError("9780451524935")

        with patch(
            "custom_components.library_catalog.webhook.get_book_metadata",
            return_value=sample_book_metadata,
        ):
            request = MagicMock(spec=web.Request)
            request.json = AsyncMock(return_value={"isbn": "978-0-451-52493-5"})

            response = await webhook_handler.handle_barcode(request)

            assert response.status == 200
            response_data = json.loads(response.body)
            assert response_data["success"] is True
            assert response_data["isbn"] == "9780451524935"

    @pytest.mark.asyncio
    async def test_invalid_json(self, webhook_handler):
        """Test webhook with invalid JSON."""
        request = MagicMock(spec=web.Request)
        request.json = AsyncMock(side_effect=ValueError("Invalid JSON"))

        response = await webhook_handler.handle_barcode(request)

        assert response.status == 400
        response_data = json.loads(response.body)
        assert response_data["success"] is False
        assert "Invalid JSON" in response_data["error"]

    @pytest.mark.asyncio
    async def test_empty_isbn_field(self, webhook_handler):
        """Test webhook with empty ISBN field."""
        request = MagicMock(spec=web.Request)
        request.json = AsyncMock(return_value={"isbn": ""})

        response = await webhook_handler.handle_barcode(request)

        assert response.status == 400
        response_data = json.loads(response.body)
        assert response_data["success"] is False
        assert "Missing ISBN" in response_data["error"]

    @pytest.mark.asyncio
    async def test_barcode_format_parsing(self, webhook_handler):
        """Test barcode format parsing."""
        test_cases = [
            ("ISBN10", BarCodeFormat.ISBN10),
            ("ISBN13", BarCodeFormat.ISBN13),
            ("EAN13", BarCodeFormat.EAN13),
            ("EAN", BarCodeFormat.EAN13),
            ("EAN_13", BarCodeFormat.EAN13),
            ("CODE128", BarCodeFormat.CODE128),
            ("CODE 128", BarCodeFormat.CODE128),
            ("128", BarCodeFormat.CODE128),
            ("UNKNOWN_FORMAT", BarCodeFormat.UNKNOWN),
            (None, BarCodeFormat.UNKNOWN),
            ("", BarCodeFormat.UNKNOWN),
        ]

        for format_str, expected_format in test_cases:
            result = webhook_handler._parse_barcode_format(format_str)
            assert result == expected_format

    def test_extract_field_with_valid_names(self, webhook_handler):
        """Test field extraction with valid field names."""
        data = {"isbn": "9780451524935"}
        result = webhook_handler._extract_field(data, ("isbn", "isbn_input"))
        assert result == "9780451524935"

    def test_extract_field_with_alternative_names(self, webhook_handler):
        """Test field extraction with alternative field names."""
        data = {"isbn_input": "9780451524935"}
        result = webhook_handler._extract_field(data, ("isbn", "isbn_input"))
        assert result == "9780451524935"

    def test_extract_field_with_whitespace(self, webhook_handler):
        """Test field extraction strips whitespace."""
        data = {"isbn": "  9780451524935  "}
        result = webhook_handler._extract_field(data, ("isbn",))
        assert result == "9780451524935"

    def test_extract_field_not_found(self, webhook_handler):
        """Test field extraction returns None when not found."""
        data = {"other_field": "value"}
        result = webhook_handler._extract_field(data, ("isbn", "barcode"))
        assert result is None

    def test_extract_field_empty_string(self, webhook_handler):
        """Test field extraction returns None for empty strings."""
        data = {"isbn": ""}
        result = webhook_handler._extract_field(data, ("isbn",))
        assert result is None

    @pytest.mark.asyncio
    async def test_event_fired_with_correct_data(self, webhook_handler, mock_book_service, sample_book_metadata):
        """Test that event is fired with correct data."""
        mock_book_service.get_book.side_effect = BookNotFoundError("9780451524935")

        with patch(
            "custom_components.library_catalog.webhook.get_book_metadata",
            return_value=sample_book_metadata,
        ):
            request = MagicMock(spec=web.Request)
            request.json = AsyncMock(
                return_value={
                    "isbn": "978-0-451-52493-5",
                    "format": "ISBN13",
                }
            )

            await webhook_handler.handle_barcode(request)

            # Verify event was fired with correct data
            call_args = webhook_handler.hass.bus.async_fire.call_args
            assert call_args[0][0] == "library_catalog_barcode_scanned"
            event_data = call_args[0][1]
            assert event_data["isbn"] == "9780451524935"
            assert event_data["format"] == "ISBN13"
            assert event_data["raw_isbn"] == "978-0-451-52493-5"
            assert event_data["exists"] is False
            assert event_data["title"] == "1984"

    @pytest.mark.asyncio
    async def test_exception_handling(self, webhook_handler):
        """Test error handling for unexpected exceptions."""
        request = MagicMock(spec=web.Request)
        request.json = AsyncMock(side_effect=RuntimeError("Unexpected error"))

        response = await webhook_handler.handle_barcode(request)

        assert response.status == 500
        response_data = json.loads(response.body)
        assert response_data["success"] is False
        assert "Internal server error" in response_data["error"]

    @pytest.mark.asyncio
    async def test_service_not_available(self, webhook_handler):
        """Test webhook when book service is not available."""
        # Remove book service from hass.data
        webhook_handler.hass.data.clear()

        request = MagicMock(spec=web.Request)
        request.json = AsyncMock(return_value={"isbn": "9780451524935"})

        response = await webhook_handler.handle_barcode(request)

        assert response.status == 503
        response_data = json.loads(response.body)
        assert response_data["success"] is False
        assert "not available" in response_data["error"].lower()
