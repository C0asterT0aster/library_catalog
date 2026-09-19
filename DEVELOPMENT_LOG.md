# Development Log - Library Catalog Integration

**Project:** Home Assistant Custom Integration for Physical Book Library Management  
**Repository:** https://github.com/C0asterT0aster/library_catalog  
**Current Version:** 0.1.0  
**Last Updated:** 2026-09-19

---

## 1. Current Project State & Architecture

### ✅ Completed Features

#### Core Integration
- ✅ Full Home Assistant integration lifecycle (`__init__.py`)
- ✅ Config flow setup (no API keys required)
- ✅ SQLite database with aiosqlite (async operations)
- ✅ DataUpdateCoordinator for state management
- ✅ Proper initialization and cleanup (database connection management)
- ✅ HACS-compatible structure

#### Metadata Providers
- ✅ **Open Library API** (primary provider)
- ✅ **Google Books API** (secondary/fallback provider, no API key needed)
- ✅ Intelligent fallback strategy with metadata merging
- ✅ Sufficiency checks (requires real authors + at least one additional field)
- ✅ Automatic metadata merging (prefers real authors, longer descriptions, fills missing fields)

#### Services (All Functional)
- ✅ `library_catalog.add_book` - Add books by ISBN with location
- ✅ `library_catalog.search` - Search by title, author, ISBN, or room
- ✅ `library_catalog.delete_book` - Remove books from catalog

#### Database Layer
- ✅ Full CRUD operations for books
- ✅ Efficient search with multiple indices
- ✅ Location hierarchy support (room → shelf → compartment)
- ✅ Full-text search (FTS5) for large libraries (10k+ books)
- ✅ Schema versioning for future migrations
- ✅ Optimized queries with proper indexing

#### Data Models
- ✅ `BookData` - API layer model with validation
- ✅ `BookEntity` - Database layer with timestamps and location
- ✅ `BookLocation` - Hierarchical location (room/shelf/compartment)
- ✅ `SearchResult` - Search response with pagination
- ✅ ISBN validation via python-stdnum (normalizes to ISBN-13)

#### Webhook Integration
- ✅ Webhook endpoint for barcode scanners
- ✅ URL: `/api/webhook/library_catalog_scanner`
- ✅ Fires Home Assistant events for automation triggers

#### Testing
- ✅ 36 unit tests (all passing)
- ✅ Google Books API tests (20 tests)
- ✅ Metadata provider tests (16 tests)
- ✅ Mocked Home Assistant modules for isolated testing
- ✅ Test coverage for error handling, retries, rate limiting

### 🚧 Not Yet Implemented

- ⬜ Sensor entities (book count, last added book, etc.)
- ⬜ Binary sensor entities (library status)
- ⬜ Device entities (library as device)
- ⬜ Cover image caching (v1 stores URLs only)
- ⬜ Book loan tracking
- ⬜ Statistics/analytics entities
- ⬜ Multi-library support UI (architecture supports it, UI doesn't expose it yet)
- ⬜ Diagnostics integration

---

## 2. Configuration & Authentication Method

### Config Flow (`config_flow.py`)

**Configuration Method:** Simplified, no API keys required

```python
# User Input (Optional)
- Library Name (default: "My Library")
```

**Why No API Keys?**
- Open Library API: No authentication required
- Google Books API: Public access endpoint, no key needed for basic queries
- Simplifies setup for end users

**Entry Creation:**
- Unique ID: `library_catalog_{library_name_normalized}`
- Aborts if duplicate library name exists
- Stores only the library name in config entry data

**Version:** ConfigFlow VERSION = 1

---

## 3. Implemented Entities & Platforms

### Current Status: No Entities Yet

The integration currently operates as a **service-only integration** with no entities exposed to Home Assistant UI.

### Planned Entities (Future)

**Sensor Platform:**
- `sensor.library_catalog_book_count` - Total books in library
- `sensor.library_catalog_last_added` - Most recently added book
- `sensor.library_catalog_authors` - Number of unique authors
- `sensor.library_catalog_publishers` - Number of unique publishers

**Binary Sensor Platform:**
- `binary_sensor.library_catalog_database` - Database connection status

---

## 4. Recent Decisions & Constraints

### Architectural Decisions

#### 1. **Dual Metadata Provider Strategy** (2026-09-19)
**Decision:** Implement Open Library as primary, Google Books as fallback  
**Rationale:**
- Open Library has better structured data but sometimes incomplete
- Google Books fills gaps when Open Library has insufficient data
- Sufficiency = real authors + at least one other field
- Intelligent merging prevents "Unknown Author" pollution

**Implementation:**
- `MetadataFetcher` class coordinates fallback logic
- Merging prefers real authors, longer descriptions
- Fills missing fields from secondary source

#### 2. **Service-Only Integration (Current State)** (2026-09-19)
**Decision:** Start with services, add entities later  
**Rationale:**
- Services provide immediate functionality (add/search/delete)
- Entities require more UI consideration
- Users can interact via Developer Tools, scripts, automations
- Database and API layer fully functional without entities

#### 3. **SQLite with Full-Text Search** (Initial Design)
**Decision:** Use SQLite with FTS5 virtual table  
**Rationale:**
- Local storage, no external database required
- aiosqlite provides async operations
- FTS5 enables efficient text search for large collections
- Schema versioning allows future migrations
- Designed to scale to 10,000+ books

#### 4. **Location Hierarchy: Room → Shelf → Compartment** (Initial Design)
**Decision:** Three-level location hierarchy  
**Rationale:**
- Flexible enough for various home layouts
- User-definable (not enforced from predefined lists)
- All three fields required for a complete location
- Supports search by room for "where is this book?"

#### 5. **ISBN-13 Normalization** (Initial Design)
**Decision:** Always normalize ISBN-10 to ISBN-13  
**Rationale:**
- ISBN-13 is the modern standard (since 2007)
- Simpler to store one format
- python-stdnum handles conversion automatically
- Both ISBN-10 and ISBN-13 accepted as input

#### 6. **No API Key Requirement** (2026-09-19)
**Decision:** Use public endpoints only  
**Rationale:**
- Lower barrier to entry for users
- Open Library is fully public
- Google Books public endpoint sufficient for metadata lookup
- If rate limits become an issue, can add optional API key in future

### Known Constraints

1. **Google Books Rate Limiting**
   - Public endpoint: ~1000 requests/day (estimated)
   - Exponential backoff implemented for 429 errors
   - Solution: Retry logic + fallback to Open Library first

2. **Cover Images**
   - v0.1.0: URLs only, no local caching
   - May have HTTPS issues with some older Open Library URLs
   - Automatic HTTP→HTTPS upgrade implemented
   - Future: Download and cache locally

3. **Test Environment**
   - Home Assistant modules mocked in tests
   - Cannot test actual HA integration lifecycle in pytest
   - Must test manually in Home Assistant instance

4. **Dual Directory Structure**
   - Code exists in `custom_components/library_catalog/` AND `library_catalog/custom_components/library_catalog/`
   - Must sync changes between both locations
   - Root is authoritative, subdirectory is for testing/development

---

## 5. Active Context & Next Steps

### Current State (2026-09-19)

**Status:** ✅ Integration is fully functional for core book management

**What Works:**
- ✅ User can add books via `library_catalog.add_book` service
- ✅ User can search books via `library_catalog.search` service
- ✅ User can delete books via `library_catalog.delete_book` service
- ✅ Webhook accepts barcode scanner input
- ✅ Metadata fetched automatically from Open Library + Google Books
- ✅ Database stores all book data with locations
- ✅ All 36 unit tests passing

**Recent Fixes (2026-09-19):**
- Fixed broken `__init__.py` - was empty `pass` statement, now properly initializes database and registers services
- Fixed broken `services.py` - had placeholder schemas and empty handlers, now fully implemented
- Fixed broken `coordinator.py` - missing database parameter, now properly wired
- Added all missing Home Assistant module mocks to test suite

### Testing Instructions for User

To test the integration in Home Assistant:

1. **Restart Home Assistant** after pulling latest changes
2. **Verify Integration is Loaded:**
   - Go to Settings → Devices & Services
   - Look for "Library Catalog" integration
   - If not present, check Home Assistant logs for errors

3. **Test Adding a Book:**
   ```yaml
   # Go to Developer Tools → Services
   # Select service: library_catalog.add_book
   
   service: library_catalog.add_book
   data:
     isbn: "9780451524935"  # 1984 by George Orwell
     location:
       room: "Living Room"
       shelf: "Bookshelf 1"
       compartment: "Top"
   ```

4. **Test Searching:**
   ```yaml
   # Select service: library_catalog.search
   
   service: library_catalog.search
   data:
     query: "Orwell"
     search_by: "author"
     limit: 50
   ```

5. **Check Database:**
   - Database location: `<HA_CONFIG_DIR>/library_catalog.db`
   - Should be created automatically on first book add

### Next Steps (Priority Order)

#### Immediate (User Requested)
1. **User Testing** - User needs to test in their Home Assistant instance
2. **Bug Fixes** - Address any issues found during testing

#### Short-Term
1. **Add Sensor Entities** - Display book count, last added book
2. **Create Update Location Service** - Allow moving books without re-adding
3. **Add Diagnostic Info** - Help debug issues

#### Medium-Term
1. **Implement Cover Image Caching** - Store covers locally
2. **Add Binary Sensors** - Database status, sync status
3. **Create Statistics** - Books per room, author distribution
4. **Build Lovelace Cards** - Custom UI for library browsing

#### Long-Term
1. **Book Loan Tracking** - Lend books to people, track due dates
2. **Reading List Management** - Mark books as read/unread
3. **Book Recommendations** - Based on collection
4. **Multi-Library Support UI** - Expose multiple library config entries

---

## 6. Files & Structure Reference

### Key Files

```
custom_components/library_catalog/
├── __init__.py              # Integration entry point (FIXED 2026-09-19)
├── manifest.json            # Integration metadata
├── config_flow.py           # UI configuration flow (WORKING)
├── const.py                 # All constants and config keys
├── coordinator.py           # DataUpdateCoordinator (FIXED 2026-09-19)
├── services.py              # Service handlers (FIXED 2026-09-19)
├── database.py              # SQLite operations (WORKING)
├── api.py                   # Open Library client (WORKING)
├── google_books.py          # Google Books client (WORKING)
├── metadata_providers.py    # Fallback & merge logic (WORKING)
├── models.py                # Data models & validation (WORKING)
├── validation.py            # ISBN & field validators (WORKING)
└── webhook.py               # Barcode webhook handler (WORKING)

tests/
├── conftest.py              # Pytest config & HA mocks (UPDATED 2026-09-19)
├── test_google_books.py     # 20 tests - ALL PASSING
└── test_metadata_providers.py  # 16 tests - ALL PASSING

Documentation/
├── DEVELOPMENT_LOG.md       # This file (long-term memory)
├── HOME_ASSISTANT_TESTING_GUIDE.md  # User testing instructions
├── ha-config-examples.yaml  # Sample scripts & automations
└── test_library_integration.py  # Integration test script
```

### Database Schema

```sql
-- Books table
CREATE TABLE books (
    isbn TEXT PRIMARY KEY NOT NULL,
    title TEXT NOT NULL,
    subtitle TEXT,
    authors TEXT NOT NULL,  -- JSON array
    publisher TEXT,
    year INTEGER,
    description TEXT,
    cover_url TEXT,
    language TEXT,
    pages INTEGER,
    room TEXT,
    shelf TEXT,
    compartment TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- Full-text search
CREATE VIRTUAL TABLE books_fts USING fts5(
    title, authors, description,
    content=books, content_rowid=rowid
);

-- Indices on title, authors, isbn, publisher, year, room, created_at
```

---

## 7. Git Workflow & Version Control

### Recent Commits
- `8c93e42` - fix: Implement complete integration lifecycle with working services (2026-09-19)
- `216a57c` - Previous work on metadata providers
- `af73fe8` - Sync complete book data model and validation
- `11f6abe` - Fix config_flow for Home Assistant 2026 compatibility

### Branch Strategy
- **main** - Stable, tested code
- Feature branches: Not currently used (direct to main for now)

### Testing Before Push
- Automated via `test-and-push.py` (local script, not in repo)
- Runs pytest suite before allowing push
- Only pushes if all tests pass

---

## 8. Dependencies

### Required Packages (from manifest.json)
```json
"requirements": [
  "aiohttp>=3.8.0",
  "aiosqlite>=0.17.0",
  "python-stdnum>=1.17"
]
```

### Home Assistant Version
- **Minimum:** 2023.1.0
- **Tested On:** 2026.x (user's current version)

---

## 9. Known Issues & Workarounds

### Issue 1: Dual Directory Structure
**Problem:** Code exists in both `custom_components/` and `library_catalog/custom_components/`  
**Workaround:** Must copy files between directories during development  
**Solution:** User should use `custom_components/` directory for actual HA installation

### Issue 2: Line Ending Warnings (Windows)
**Problem:** Git warns about LF → CRLF conversion  
**Impact:** Cosmetic only, does not affect functionality  
**Workaround:** Ignore warnings or configure `.gitattributes`

### Issue 3: Some ISBNs Not Found
**Problem:** Not all books are in Open Library or Google Books  
**Workaround:** Try alternate ISBN format (ISBN-10 vs ISBN-13)  
**Future:** Add more metadata providers (WorldCat, Library of Congress)

---

## 10. Change Log

### v0.1.0 (2026-09-19) - Initial Release
- ✅ Core integration lifecycle
- ✅ Three services: add_book, search, delete_book
- ✅ Dual metadata providers with intelligent fallback
- ✅ SQLite database with full-text search
- ✅ Webhook for barcode scanners
- ✅ 36 passing unit tests
- ✅ Complete testing documentation
- ✅ HACS compatible with proper manifest

**Status:** Deployed and working in Home Assistant

### Known Issues (2026-09-19)

#### API Connectivity Issues
The integration itself works correctly, but may encounter external API failures:

1. **Open Library timeouts:**
   - Error: `Cannot connect to host openlibrary.org:443 ssl:default [Connection reset by peer]`
   - Cause: Network connectivity issues or Open Library service problems
   - Impact: Primary metadata provider unavailable
   - Workaround: Automatic fallback to Google Books

2. **Google Books rate limiting:**
   - Error: `Google Books API rate limited (429)`
   - Cause: Too many requests in short time (public endpoint limits)
   - Impact: Secondary provider unavailable after ~10-20 requests
   - Workaround: Wait 10-15 minutes for rate limit to reset

3. **Both APIs unavailable:**
   - Error: `BookNotFoundError: Failed to fetch book metadata for ISBN`
   - When: Both Open Library AND Google Books fail
   - Impact: Cannot add books via ISBN
   - Solution needed: Manual book entry service (see Next Steps)

**All integration code is working correctly** - the errors are external API availability issues, not code bugs.

---

## 11. Quick Reference: Testing the Integration

### Installation

**Via HACS (Recommended):**
1. Add this repository as a custom repository in HACS
2. Search for "Library Catalog" in HACS → Integrations
3. Click Install
4. Restart Home Assistant
5. Add integration via UI: Settings → Devices & Services → Add Integration → "Library Catalog"

**Manual Installation:**
1. Copy `custom_components/library_catalog/` to your Home Assistant `config/custom_components/`
2. Restart Home Assistant
3. Add integration via UI: Settings → Devices & Services → Add Integration → "Library Catalog"

### Updating the Integration

**Via HACS:**
1. Go to HACS → Integrations → Library Catalog
2. Click "Redownload" or wait for update notification
3. Go to Settings → Devices & Services
4. Remove the "Library Catalog" integration
5. Restart Home Assistant
6. Re-add the integration: Settings → Devices & Services → Add Integration → "Library Catalog"

**Note:** Removing and re-adding the integration is necessary to reload all code changes. The database file (`library_catalog.db`) persists, so your books are not deleted.

### Test ISBNs (Verified Working)
```
9780451524935  # 1984 - George Orwell
9780747532699  # Harry Potter and the Philosopher's Stone - J.K. Rowling
9780547928227  # The Hobbit - J.R.R. Tolkien
9780061120084  # To Kill a Mockingbird - Harper Lee
9780743273565  # The Great Gatsby - F. Scott Fitzgerald
```

### Webhook Testing (Barcode Scanner)
```bash
# Using curl (replace YOUR_HA_IP with actual IP)
curl -X POST http://YOUR_HA_IP:8123/api/webhook/library_catalog_scanner \
  -H "Content-Type: application/json" \
  -d '{"isbn": "9780451524935"}'
```

### Check Logs
```bash
# In Home Assistant
Settings → System → Logs
# Filter by: library_catalog
```

---

## 12. Contact & Support

- **GitHub Issues:** https://github.com/C0asterT0aster/library_catalog/issues
- **Developer:** C0asterT0aster
- **AI Assistant:** Claude (Anthropic)

---

*This file serves as long-term memory across conversation resets. Update it whenever significant progress is made.*
