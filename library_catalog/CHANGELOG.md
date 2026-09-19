# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Camera scanning integration for mobile devices
- Barcode recognition in notifications
- Additional metadata providers
- Book cover caching
- Import/export functionality

## [0.1.0] - 2026-09-19

### Added
- Initial release of Library Catalog integration
- Add books by ISBN with automatic metadata fetching from Open Library and Google Books
- Manual book entry for offline use
- Search functionality (by title, author, ISBN, location)
- Delete books from catalog
- Update book locations
- Location tracking with hierarchical structure (room/shelf/compartment)
- SQLite database with full-text search (FTS5)
- Multi-library support (multiple config entries)
- Six Home Assistant services:
  - `library_catalog.add_book` - Add book via ISBN lookup
  - `library_catalog.add_book_manual` - Manual entry
  - `library_catalog.search` - Search books
  - `library_catalog.delete_book` - Remove book
  - `library_catalog.update_location` - Change book location
  - `library_catalog.reload_database` - Refresh coordinator
- Webhook endpoint for barcode scanners (`/api/webhook/ios_book_scanner`)
- Dashboard integration with input helpers
- Actionable notifications for mobile devices
- Business logic service layer (LibraryBookService)
- Comprehensive test suite (50+ tests)
- Complete documentation:
  - Setup guide
  - Webhook API reference
  - Development guide
  - Camera limitations explanation
  - Windows testing guide

### Known Issues
- Camera cannot be triggered from actionable notifications (iOS/Android limitation)
- Manual ISBN entry required for mobile scanning
- Open Library API occasionally unavailable

### Technical Details
- Python 3.10+ required
- Home Assistant 2023.1.0+ required
- Dependencies:
  - aiohttp >= 3.8.0
  - aiosqlite >= 0.17.0
  - python-stdnum >= 1.17

### Documentation
- README.md with feature overview
- SETUP_GUIDE.md for step-by-step installation
- WEBHOOK.md for API documentation
- DEVELOPMENT.md for architecture details
- CAMERA_LIMITATIONS.md for technical constraints
- HACS_UPDATES.md for release management

---

## Version History

- **0.1.0** - Initial release (2026-09-19)
  - Core functionality implemented
  - All services working
  - Documentation complete
  - Marked as pre-release (under development)

---

## How to Update

### For Users
Updates appear automatically in HACS when new releases are published:
1. HACS → Integrations → Library Catalog
2. Click "Update" button when available
3. Restart Home Assistant

### For Developers
See HACS_UPDATES.md for release process.

---

## Support

- Report bugs: https://github.com/C0asterT0aster/library_catalog/issues
- Documentation: https://github.com/C0asterT0aster/library_catalog
- Discussions: https://github.com/C0asterT0aster/library_catalog/discussions
