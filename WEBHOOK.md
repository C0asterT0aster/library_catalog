# Barcode Scanner Webhook Documentation

## Overview

The Library Catalog integration provides a webhook endpoint for barcode scanners to add books to your library. This webhook validates ISBNs, checks for duplicates, fetches metadata, and provides complete book information - but does **not** store the book automatically. Storage requires a physical location which must be provided through the `add_book` service or UI.

## Webhook Endpoint

**URL**: `/api/webhook/library_catalog_scanner`

**Method**: `POST`

**Content-Type**: `application/json`

## Request Format

The webhook accepts flexible field names to accommodate different barcode scanner apps:

### Minimal Request (Recommended)
```json
{
  "isbn": "9780451524935"
}
```

### With Format Specification
```json
{
  "isbn": "9780451524935",
  "format": "ISBN13"
}
```

### Alternative Field Names
The webhook accepts any of these field names for the ISBN:
- `isbn`
- `isbn_input`
- `code`
- `barcode`

And any of these for the format:
- `format`
- `barcode_format`
- `type`

**Examples:**
```json
{"code": "9780451524935"}
{"barcode": "9780451524935", "barcode_format": "EAN13"}
{"isbn_input": "978-0-451-52493-5"}
```

## Response Format

### Success - New Book (Not in Catalog)
```json
{
  "success": true,
  "isbn": "9780451524935",
  "format": "ISBN13",
  "exists": false,
  "book": {
    "title": "1984",
    "subtitle": "A Novel",
    "authors": ["George Orwell"],
    "publisher": "Signet Classic",
    "year": 1949,
    "description": "A dystopian novel...",
    "cover_url": "https://covers.openlibrary.org/b/id/...",
    "language": "en",
    "pages": 328
  },
  "message": "Book metadata retrieved. Use add_book service with location to store."
}
```

### Success - Existing Book (Already in Catalog)
```json
{
  "success": true,
  "isbn": "9780451524935",
  "format": "ISBN13",
  "exists": true,
  "book": {
    "title": "1984",
    "subtitle": "A Novel",
    "authors": ["George Orwell"],
    "publisher": "Signet Classic",
    "year": 1949,
    "description": "A dystopian novel...",
    "cover_url": "https://covers.openlibrary.org/b/id/...",
    "language": "en",
    "pages": 328,
    "location": {
      "room": "Living Room",
      "shelf": "Shelf 1",
      "compartment": "Top"
    }
  },
  "message": "Book already in catalog"
}
```

### Error Responses

#### Invalid ISBN (400)
```json
{
  "success": false,
  "error": "Invalid ISBN: Invalid checksum"
}
```

#### Missing ISBN (400)
```json
{
  "success": false,
  "error": "Missing ISBN/barcode field"
}
```

#### Invalid JSON (400)
```json
{
  "success": false,
  "error": "Invalid JSON payload"
}
```

#### Metadata Not Found (404)
```json
{
  "success": false,
  "error": "Book metadata not found for ISBN 9780451524935",
  "isbn": "9780451524935",
  "exists": false
}
```

#### Service Unavailable (503)
```json
{
  "success": false,
  "error": "Service not available"
}
```

## Workflow

1. **Scanner sends barcode** → Webhook receives ISBN
2. **Validation** → ISBN format validated and normalized
3. **Duplicate check** → Database checked for existing book
4. **If exists** → Return book with current location
5. **If new** → Fetch metadata from Open Library/Google Books
6. **Return data** → Complete book information returned
7. **Storage** → User must call `add_book` service with location to store

## Home Assistant Event

The webhook fires a `library_catalog_barcode_scanned` event that can be used in automations:

```yaml
automation:
  - alias: "Notify on Book Scan"
    trigger:
      - platform: event
        event_type: library_catalog_barcode_scanned
    action:
      - service: notify.mobile_app
        data:
          title: "Book Scanned"
          message: "{{ trigger.event.data.title }} - ISBN: {{ trigger.event.data.isbn }}"
```

**Event Data:**
- `isbn`: Normalized ISBN-13
- `format`: Barcode format (ISBN10, ISBN13, EAN13, etc.)
- `raw_isbn`: Original scanned value
- `exists`: Boolean - whether book is already in catalog
- `title`: Book title (if available)

## Testing with curl

### Test Valid ISBN
```bash
curl -X POST http://homeassistant.local:8123/api/webhook/library_catalog_scanner \
  -H "Content-Type: application/json" \
  -d '{"isbn":"9780451524935"}'
```

### Test with Format
```bash
curl -X POST http://homeassistant.local:8123/api/webhook/library_catalog_scanner \
  -H "Content-Type: application/json" \
  -d '{"isbn":"9780451524935","format":"ISBN13"}'
```

### Test ISBN-10 (Auto-converts to ISBN-13)
```bash
curl -X POST http://homeassistant.local:8123/api/webhook/library_catalog_scanner \
  -H "Content-Type: application/json" \
  -d '{"isbn":"0451524934"}'
```

### Test Invalid ISBN
```bash
curl -X POST http://homeassistant.local:8123/api/webhook/library_catalog_scanner \
  -H "Content-Type: application/json" \
  -d '{"isbn":"invalid"}'
```

## Mobile Barcode Scanner Apps

### iOS - Barcodescanner (Free)

1. Install "Barcodescanner" from App Store
2. Open Settings → Webhook
3. Set URL: `http://YOUR_HA_IP:8123/api/webhook/library_catalog_scanner`
4. Set Method: `POST`
5. Set Body Template:
   ```
   {"isbn":"{{barcode}}"}
   ```

### Android - Binary Eye (Free, Open Source)

1. Install "Binary Eye" from F-Droid or Play Store
2. Open Settings → Custom Action
3. Set URL: `http://YOUR_HA_IP:8123/api/webhook/library_catalog_scanner`
4. Set Request Body:
   ```json
   {"isbn":"BARCODE"}
   ```
5. Enable "Send as POST"

### Generic HTTP Request Apps

Any app that can send HTTP POST requests will work. Use:
- **URL**: `http://YOUR_HA_IP:8123/api/webhook/library_catalog_scanner`
- **Method**: POST
- **Headers**: `Content-Type: application/json`
- **Body**: `{"isbn":"YOUR_SCANNED_CODE"}`

Replace `YOUR_HA_IP` with your Home Assistant IP address or domain name.

## Security Considerations

1. **Authentication**: The webhook uses Home Assistant's webhook system which provides secure access without exposing authentication tokens
2. **HTTPS**: For external access, always use HTTPS (via Nabu Casa or reverse proxy)
3. **Rate Limiting**: Consider Home Assistant's built-in rate limiting for public-facing instances
4. **Validation**: All inputs are validated before processing
5. **No Auto-Storage**: Books are NOT automatically stored - location must be provided separately, preventing unauthorized additions

## Integration with add_book Service

After scanning, you can store the book using:

```yaml
service: library_catalog.add_book
data:
  isbn: "9780451524935"
  location:
    room: "Living Room"
    shelf: "Shelf 1"
    compartment: "Top"
```

Or use the manual entry service if metadata fetch failed:

```yaml
service: library_catalog.add_book_manual
data:
  isbn: "9780451524935"
  title: "1984"
  authors: ["George Orwell"]
  location:
    room: "Living Room"
    shelf: "Shelf 1"
    compartment: "Top"
```

## Troubleshooting

### Webhook not responding
- Verify URL is correct (include `/api/webhook/` prefix)
- Check Home Assistant logs for errors
- Ensure integration is loaded
- Test with curl first

### "Service not available" error
- Integration may not be fully initialized
- Check that config entry is set up
- Restart Home Assistant

### "Metadata not found" errors
- ISBN may be invalid or not in provider databases
- Use `add_book_manual` service to add book with manual metadata
- Check internet connectivity

### Scanner app not working
- Verify URL is accessible from scanner device
- Check firewall settings
- Test webhook with curl from same network
- Ensure Content-Type header is set to application/json
