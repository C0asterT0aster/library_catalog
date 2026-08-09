"""Tests for webhook handler."""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import web
from custom_components.library_catalog.webhook import WebhookHandler
from custom_components.library_catalog.models import BarCodeFormat


class TestWebhookHandler:
    """Test webhook handler for barcode scanner."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        hass = MagicMock()
        hass.bus = MagicMock()
        hass.bus.async_fire = AsyncMock()
        return hass

    @pytest.fixture
    def webhook_handler(self, mock_hass):
        """Create webhook handler instance."""
        return WebhookHandler(mock_hass)

    @pytest.mark.asyncio
    async def test_valid_isbn13_webhook(self, webhook_handler):
        """Test webhook with valid ISBN-13."""
        # Create mock request
        request = MagicMock(spec=web.Request)
        request.json = AsyncMock(
            return_value={
                "isbn": "9780451524935",
                "format": "ISBN13",
            }
        )

        # Call handler
        response = await webhook_handler.handle_barcode(request)

        # Verify response
        assert response.status == 200
        response_data = json.loads(response.body)
        assert response_data["success"] is True
        assert response_data["isbn"] == "9780451524935"
        assert response_data["format"] == "ISBN13"

        # Verify event was fired
        webhook_handler.hass.bus.async_fire.assert_called_once()

    @pytest.mark.asyncio
    async def test_isbn10_conversion_webhook(self, webhook_handler):
        """Test webhook with ISBN-10 (should convert to ISBN-13)."""
        request = MagicMock(spec=web.Request)
        request.json = AsyncMock(
            return_value={
                "isbn": "0451524934",
            }
        )

        response = await webhook_handler.handle_barcode(request)

        assert response.status == 200
        response_data = json.loads(response.body)
        assert response_data["success"] is True
        assert response_data["isbn"] == "9780451524935"

    @pytest.mark.asyncio
    async def test_flexible_field_names(self, webhook_handler):
        """Test webhook with alternative field names."""
        test_cases = [
            {"isbn_input": "9780451524935"},
            {"code": "9780451524935"},
            {"barcode": "9780451524935"},
        ]

        for payload in test_cases:
            request = MagicMock(spec=web.Request)
            request.json = AsyncMock(return_value=payload)

            response = await webhook_handler.handle_barcode(request)

            assert response.status == 200
            response_data = json.loads(response.body)
            assert response_data["success"] is True

    @pytest.mark.asyncio
    async def test_isbn_with_hyphens(self, webhook_handler):
        """Test webhook with hyphenated ISBN."""
        request = MagicMock(spec=web.Request)
        request.json = AsyncMock(
            return_value={
                "isbn": "978-0-451-52493-5",
            }
        )

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
    async def test_invalid_isbn(self, webhook_handler):
        """Test webhook with invalid ISBN."""
        request = MagicMock(spec=web.Request)
        request.json = AsyncMock(return_value={"isbn": "invalid-isbn"})

        response = await webhook_handler.handle_barcode(request)

        assert response.status == 400
        response_data = json.loads(response.body)
        assert response_data["success"] is False
        assert "Invalid ISBN" in response_data["error"]

    @pytest.mark.asyncio
    async def test_barcode_format_parsing(self, webhook_handler):
        """Test barcode format parsing."""
        test_cases = [
            ("ISBN10", BarCodeFormat.ISBN10),
            ("ISBN13", BarCodeFormat.ISBN13),
            ("EAN13", BarCodeFormat.EAN13),
            ("EAN", BarCodeFormat.EAN13),
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

    @pytest.mark.asyncio
    async def test_event_fired_with_correct_data(self, webhook_handler):
        """Test that event is fired with correct data."""
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
        assert call_args[0][0] == "library_catalog_barcode_received"
        event_data = call_args[0][1]
        assert event_data["isbn"] == "9780451524935"
        assert event_data["format"] == "ISBN13"
        assert event_data["raw_isbn"] == "978-0-451-52493-5"

    @pytest.mark.asyncio
    async def test_exception_handling(self, webhook_handler):
        """Test error handling for unexpected exceptions."""
        request = MagicMock(spec=web.Request)
        request.json = AsyncMock(side_effect=RuntimeError("Unexpected error"))

        response = await webhook_handler.handle_barcode(request)

        assert response.status == 500
        response_data = json.loads(response.body)
        assert response_data["success"] is False

    @pytest.mark.asyncio
    async def test_empty_isbn_field(self, webhook_handler):
        """Test webhook with empty ISBN field."""
        request = MagicMock(spec=web.Request)
        request.json = AsyncMock(return_value={"isbn": ""})

        response = await webhook_handler.handle_barcode(request)

        assert response.status == 400
        response_data = json.loads(response.body)
        assert response_data["success"] is False
