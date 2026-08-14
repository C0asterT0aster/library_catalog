# Library Catalog Integration

A Home Assistant custom integration for managing your physical book collection using ISBN barcodes.

[![GitHub release](https://img.shields.io/github/release/C0asterT0aster/library_catalog.svg)](https://github.com/C0asterT0aster/library_catalog/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![HACS](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)

## Features

- **ISBN Barcode Scanning**: Quickly add books by scanning their ISBN barcodes
- **Multiple Data Sources**: Fetches book metadata from Open Library API with automatic fallback to Google Books
- **Local Database**: Stores book data in a local SQLite database for fast access
- **Comprehensive Search**: Search by title, author, ISBN, or location
- **Location Tracking**: Organize books by room, shelf, and compartment
- **Dashboard Integration**: Display book covers and location information
- **Webhook Support**: Accept barcode scanner input via HTTP webhook
- **Multi-Library Support**: Manage multiple independent book libraries through separate config entries
- **User-Configurable Locations**: Define your own room, shelf, and compartment hierarchy

## Installation

### Via HACS (Recommended)

1. Open Home Assistant and go to HACS > Integrations
2. Click "Explore & Download Repositories"
3. Search for "Library Catalog"
4. Click "Download"
5. Restart Home Assistant
6. Go to Settings > Devices & Services > Create Integration
7. Search for "Library Catalog" and complete the setup

### Manual Installation

1. Download the repository as a ZIP file
2. Extract to your Home Assistant `config/custom_components/` directory
3. Ensure the structure is: `config/custom_components/library_catalog/`
4. Restart Home Assistant
5. Go to Settings > Devices & Services > Create Integration
6. Search for "Library Catalog" and complete the setup

## Configuration

After installation, the integration will appear in Home Assistant integrations. The configuration is minimal - the integration works out of the box without additional configuration.

### Services

#### `library_catalog.add_book`

Add a book to your library by ISBN.

**Parameters:**
- `isbn` (required, string): The ISBN-10 or ISBN-13 barcode
- `location.room` (optional, string): Room name
- `location.shelf` (optional, string): Shelf name
- `location.compartment` (optional, string): Compartment/Section name

**Example:**
```yaml
service: library_catalog.add_book
data:
  isbn: "9783442478951"
  location:
    room: "Living Room"
    shelf: "Shelf 1"
    compartment: "Top"
```

#### `library_catalog.search`

Search for books in your library.

**Parameters:**
- `query` (required, string): Search term
- `search_by` (optional, string): Search type - "title", "author", or "isbn" (default: "title")
- `limit` (optional, number): Maximum results (default: 50, max: 1000)

**Example:**
```yaml
service: library_catalog.search
data:
  query: "Python"
  search_by: "title"
  limit: 10
```

#### `library_catalog.delete_book`

Remove a book from your library.

**Parameters:**
- `isbn` (required, string): The ISBN to delete

**Example:**
```yaml
service: library_catalog.delete_book
data:
  isbn: "9783442478951"
```

## Webhook Integration

The integration provides a webhook endpoint for barcode scanners:

**Webhook Path**: `/api/webhook/library_catalog_scanner`

**Supported Formats:**

Simple ISBN format:
```json
{
  "isbn": "9783442478951"
}
```

Scanner with format specification:
```json
{
  "code": "9783442478951",
  "format": "EAN_13"
}
```

Alternative field names:
```json
{
  "barcode": "9783442478951",
  "format": "EAN-13"
}
```

## Database

The integration uses SQLite for local storage at `/config/library_catalog.db`.

### Supported Book Fields

- ISBN (primary key)
- Title & Subtitle
- Authors (multiple)
- Publisher
- Publication Year
- Description
- Cover URL
- Language
- Number of Pages
- Location (Room, Shelf, Compartment)
- Created/Updated Timestamps

### Performance

The database is optimized for libraries with 10,000+ books:

- **7 Performance Indexes** for fast searches
- **Full-Text Search** virtual table (FTS5) support
- **Pagination Support** for large result sets
- **Case-Insensitive Search** for comfortable user experience

## Architecture

```
custom_components/library_catalog/
├── __init__.py              # Integration setup & lifecycle
├── const.py                 # Constants & configuration
├── manifest.json            # Integration metadata
├── config_flow.py           # Configuration UI
├── models.py                # Data models
├── database.py              # Database abstraction layer
├── api.py                   # External API clients
├── coordinator.py           # Data update coordinator
├── services.py              # Service definitions
├── webhook.py               # Webhook handlers
├── strings.json             # Localization strings
└── translations/            # Language translations
    ├── de.json
    └── en.json
```

## Development

### Requirements

- Python 3.10+
- Home Assistant 2023.1.0+
- aiohttp >= 3.8.0
- aiosqlite >= 0.17.0
- python-stdnum >= 1.17

### Installation from Source

```bash
git clone https://github.com/C0asterT0aster/library_catalog.git
cd library_catalog
pip install -r requirements.txt
```

### Project Structure

The project is developed incrementally with each commit representing a logical feature:

1. **Commit 1.1**: Core Constants & Configuration
2. **Commit 1.2**: Database Layer & Models
3. **Commit 1.3**: API Client Layer
4. **Commit 1.4**: Config Flow
5. **Commit 2.1**: Core Integration Setup
6. **Commit 2.2**: Services Registration
7. **Commit 3.1**: Barcode Webhook
8. **Commit 3.2**: Diagnostics
9. *More features in progress...*

### Testing

Run tests with:
```bash
python -m pytest tests/
```

Lint code with:
```bash
python -m flake8 custom_components/library_catalog
```

## API Sources

### Open Library

- **URL**: https://openlibrary.org/api/books
- **Rate Limit**: Reasonable
- **Format**: JSON

### Google Books

- **URL**: https://www.googleapis.com/books/v1/volumes
- **Rate Limit**: 100 QPS
- **Format**: JSON

## Future Features

- 📊 Library statistics and analytics
- 🏷️ Book tagging and categorization
- 📚 Book loan tracking
- 🖼️ Local cover image caching
- 📤 Import/Export functionality
- 🌍 Multi-library synchronization
- 📱 Mobile app integration

## Supported Languages

- 🇩🇪 German (Deutsch)
- 🇬🇧 English

Contributions for additional languages are welcome!

## Troubleshooting

### Books not appearing after adding

1. Check the Home Assistant logs for errors
2. Verify ISBN format (10 or 13 digits)
3. Ensure internet connection for API lookups
4. Check database file permissions at `/config/library_catalog.db`

### Webhook not working

1. Verify webhook URL includes the full path
2. Test with curl: `curl -X POST http://homeassistant.local:8123/api/webhook/library_catalog_scanner -H "Content-Type: application/json" -d '{"isbn":"9783442478951"}'`
3. Check Home Assistant logs for webhook errors

### Slow searches with large libraries

1. The database is indexed for performance
2. Limit search results (e.g., limit: 100)
3. Use specific search terms instead of wildcards
4. Consider splitting libraries into separate config entries

## Support

- 📝 [GitHub Issues](https://github.com/C0asterT0aster/library_catalog/issues)
- 💬 [Home Assistant Community](https://community.home-assistant.io/)
- 📖 [Home Assistant Integration Documentation](https://developers.home-assistant.io/docs/creating_integration_manifest/)

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Home Assistant](https://www.home-assistant.io/) for the amazing platform
- [Open Library](https://openlibrary.org/) for free book data
- [Google Books API](https://books.google.com/books) for backup data
- Contributors and community members for feedback and testing

---

**Made with ❤️ for Home Assistant enthusiasts who love books.**
