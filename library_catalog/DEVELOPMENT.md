# Development Guide

This document describes the architecture and development process for Library Catalog.

## Development Guidelines

### Documentation Standards

**IMPORTANT: All documentation must be written in English.**

✅ **Required:**
- All `.md` files in English
- Code comments in English
- Commit messages in English
- Variable names in English
- Error messages in English

❌ **Not Allowed:**
- German or other languages in documentation
- Mixed language documentation
- Non-English commit messages

**Rationale:** 
- Open source projects use English as the universal language
- Makes the project accessible to international contributors
- Standard practice in the Home Assistant community

### Before Committing

Check that:
- [ ] All documentation is in English
- [ ] No sensitive information (see Security section below)
- [ ] Code examples use placeholders (YOUR_DEVICE, YOUR_IP, etc.)
- [ ] YAML syntax is correct for both UI and file formats
- [ ] Tests pass
- [ ] Changes are synced to library_catalog/ directory

---

## Security & Privacy Guidelines

### Information to Keep Private

When developing or sharing code, **never commit** these items to public repositories:

❌ **Personal Information:**
- Real names in examples (use "John Doe", "YOUR_NAME")
- Personal email addresses
- Phone numbers
- Personal device names in examples

❌ **Network Information:**
- Local IP addresses (use `192.168.x.x` or `YOUR_HA_IP`)
- Port numbers (except standard ones like 8123)
- Domain names (use `your-instance.ui.nabu.casa`)
- WiFi SSIDs

❌ **Credentials & Tokens:**
- API keys (use `YOUR_API_KEY`)
- Access tokens (use `YOUR_ACCESS_TOKEN`)
- Passwords
- Webhook secrets
- OAuth tokens

❌ **System Paths:**
- User directories (use `path/to/directory`)
- Absolute paths with usernames
- Drive letters with personal folders

✅ **Safe to Keep:**
- Copyright name in LICENSE file
- GitHub username
- Public repository URLs
- Example ISBNs (9780451524935)
- Generic example data

### Sanitization Checklist

Before committing documentation:

1. **Replace specific IPs** → `YOUR_HA_IP` or `192.168.x.x`
2. **Replace device names** → `mobile_app_your_phone`
3. **Replace domains** → `your-instance.ui.nabu.casa`
4. **Replace paths** → `path/to/directory`
5. **Check for names** in examples → Use generic names
6. **Review logs** for sensitive data before sharing

### Example Sanitization

**Before:**
```yaml
- service: notify.mobile_app_maltes_iphone
  data:
    message: "Connected to 192.168.1.100"
```

**After:**
```yaml
- service: notify.mobile_app_your_phone
  data:
    message: "Connected to YOUR_HA_IP"
```

---

## Architecture Overview

### Components

```
Library Catalog Integration
├── Models Layer (models.py)
│   ├── BookLocation - Hierarchical location structure
│   ├── BookData - API response data
│   ├── BookEntity - Database entity
│   ├── SearchResult - Search result wrapper
│   └── BarCodeFormat - Barcode type enumeration
│
├── Database Layer (database.py)
│   └── LibraryCatalogDatabase - Async SQLite manager
│       ├── CRUD Operations
│       ├── Search Operations
│       └── Utility Methods
│
├── API Layer (api.py)
│   ├── ISBN Validation
│   ├── Open Library Client
│   ├── Google Books Client
│   └── Fallback Logic
│
├── Business Logic Layer (book_service.py)
│   └── LibraryBookService - Service layer
│       ├── add_book_by_isbn - ISBN workflow
│       ├── add_book_manual - Manual entry
│       ├── search_books - Search operations
│       ├── update_location - Location management
│       └── Exception handling
│
├── Home Assistant Integration
│   ├── Config Flow (config_flow.py)
│   ├── Coordinator (coordinator.py)
│   ├── Services (services.py)
│   ├── Webhook (webhook.py)
│   └── Init (__init__.py)
│
├── Configuration
│   ├── Constants (const.py)
│   ├── Manifest (manifest.json)
│   └── Strings (strings.json)
│
└── Support
    ├── Diagnostics (diagnostics.py)
    ├── Tests (tests/)
    └── Documentation (README.md, etc.)
```

## Design Principles

### 1. Async-First
All I/O operations are asynchronous:
- Database operations use `aiosqlite`
- API calls use `aiohttp`
- No blocking operations in main thread

### 2. Type Safety
Complete type hints throughout:
```python
async def async_add_book(self, book: BookEntity) -> None:
    """Type hints on every function."""
```

### 3. Separation of Concerns
- **Models**: Data structures only
- **Database**: Persistence layer
- **API**: External service communication
- **Book Service**: Business logic (independent of Home Assistant)
- **Services**: Home Assistant integration (thin wrappers)

### 4. Scalability
Designed for 10,000+ book libraries:
- 7 performance indexes on common search fields
- FTS5 virtual table for full-text search
- Pagination support (LIMIT/OFFSET)
- Efficient query construction

### 5. Extensibility
Future features prepared without redesign:
- Location hierarchy ready for complex structures
- Cover URL architecture ready for local caching
- Schema versioning for migrations
- Feature flags in constants

### 6. User-Configurable
No hardcoded values:
- Rooms, shelves, compartments defined by users
- Custom locations stored with books
- Flexible location hierarchy

## Database Schema

### books table
```sql
CREATE TABLE books (
    isbn TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    subtitle TEXT,
    authors TEXT,  -- JSON array
    publisher TEXT,
    year INTEGER,
    description TEXT,
    cover_url TEXT,
    language TEXT,
    pages INTEGER,
    room TEXT,
    shelf TEXT,
    compartment TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
)
```

### Indexes
```sql
CREATE INDEX idx_books_title ON books(title);
CREATE INDEX idx_books_authors ON books(authors);
CREATE INDEX idx_books_year ON books(year);
CREATE INDEX idx_books_room ON books(room);
CREATE INDEX idx_books_shelf ON books(shelf);
CREATE INDEX idx_books_created_at ON books(created_at);
CREATE INDEX idx_books_updated_at ON books(updated_at);
```

### Full-Text Search
```sql
CREATE VIRTUAL TABLE books_fts USING fts5(
    isbn,
    title,
    subtitle,
    authors,
    description,
    content=books
)
```

## API Integration

### Open Library API
Primary metadata source:
```python
URL = "https://openlibrary.org/api/books"
PARAMS = {"bibkeys": f"ISBN:{isbn}", "format": "json", "jscmd": "data"}
```

Response provides:
- Title, subtitle
- Authors (with keys)
- Publishers
- Publish date
- Cover URLs (S, M, L sizes)
- Number of pages
- Subjects

### Google Books API
Fallback source when Open Library fails:
```python
URL = "https://www.googleapis.com/books/v1/volumes"
PARAMS = {"q": f"isbn:{isbn}"}
```

Response provides similar data in different format.

## Service Layer Architecture

### LibraryBookService

Business logic separated from Home Assistant:

```python
class LibraryBookService:
    """Business logic for book management."""
    
    async def add_book_by_isbn(self, isbn: str, location: BookLocation) -> BookEntity:
        """Complete ISBN workflow:
        1. Validate ISBN
        2. Check duplicates
        3. Fetch metadata
        4. Create entity
        5. Store in database
        """
    
    async def add_book_manual(self, isbn: str, title: str, ...) -> BookEntity:
        """Manual entry for offline operation."""
    
    async def search_books(self, query: str, search_by: str) -> SearchResult:
        """Delegate to appropriate search method."""
```

**Why separate?**
- Testable without Home Assistant
- Reusable across different interfaces
- Clear business logic boundaries
- Easy to mock for testing

### Home Assistant Services

Thin wrappers around service layer:

```python
async def add_book_service(call: ServiceCall) -> None:
    """Home Assistant service handler.
    
    1. Extract parameters from call
    2. Get book_service instance
    3. Delegate to book_service.add_book_by_isbn()
    4. Fire Home Assistant event
    5. Handle errors
    """
```

## Webhook Architecture

### Security Model

The webhook uses Home Assistant's built-in webhook system:

```python
from homeassistant.components import webhook

webhook.async_register(
    hass,
    DOMAIN,
    "Library Catalog Scanner",
    WEBHOOK_ID,
    handler.handle_barcode,
)
```

**Security features:**
- No authentication tokens needed
- Home Assistant handles auth
- Rate limiting built-in
- HTTPS support via Home Assistant

### Workflow

1. **Receive barcode** via POST to `/api/webhook/library_catalog_scanner`
2. **Validate payload** - Check JSON format, ISBN present
3. **Normalize ISBN** - Convert ISBN-10 to ISBN-13
4. **Check duplicates** - Query database
5. **Fetch metadata** - If new book, call APIs
6. **Return result** - Complete book data + exists status
7. **Fire event** - `library_catalog_barcode_scanned` for automations

**Important:** The webhook does NOT store books automatically. Storage requires a physical location which must be provided via the `add_book` service.

## Error Handling

### Custom Exceptions

```python
class BookServiceError(Exception):
    """Base exception."""
    pass

class DuplicateISBNError(BookServiceError):
    """ISBN already exists."""
    def __init__(self, isbn: str, existing_book: BookEntity):
        self.isbn = isbn
        self.existing_book = existing_book

class BookNotFoundError(BookServiceError):
    """Book not found."""
    def __init__(self, isbn: str):
        self.isbn = isbn
```

### Error Propagation

1. **Service Layer** - Raises typed exceptions
2. **Home Assistant Services** - Catches and converts to ValueError
3. **User** - Sees friendly error message

## Testing Strategy

### Unit Tests (tests/)

- **test_models.py** - Data model validation
- **test_database.py** - Database operations
- **test_api.py** - API client mocking
- **test_book_service.py** - Business logic (14 tests)
- **test_webhook.py** - Webhook handlers (19 tests)

### Test Coverage

Current: **50+ tests** covering:
- ✅ ISBN validation (10, 13, invalid)
- ✅ Duplicate detection
- ✅ Metadata fetching (success, failure)
- ✅ Search operations (title, author, ISBN, room)
- ✅ Location management
- ✅ Webhook payload validation
- ✅ Error handling

### Running Tests

```bash
# All tests
python -m pytest tests/

# Specific test file
python -m pytest tests/test_webhook.py -v

# With coverage
python -m pytest tests/ --cov=custom_components/library_catalog
```

## Code Style

### Type Hints
Required on all functions:
```python
async def async_get_book(self, isbn: str) -> Optional[BookEntity]:
    """Every parameter and return value typed."""
```

### Docstrings
Google style:
```python
def function(param: str) -> int:
    """Short description.
    
    Longer description if needed.
    
    Args:
        param: Parameter description
        
    Returns:
        Return value description
        
    Raises:
        ValueError: When raised
    """
```

### Logging
Appropriate levels:
```python
_LOGGER.debug("Detailed information")
_LOGGER.info("Normal operation")
_LOGGER.warning("Recoverable issue")
_LOGGER.error("Error occurred")
```

## Configuration Constants

All constants in `const.py`:
- Service names
- API endpoints
- Timeouts
- Limits
- Error messages
- Feature flags

Example:
```python
SERVICE_ADD_BOOK: Final = "add_book"
OPEN_LIBRARY_TIMEOUT: Final = 10
SEARCH_DEFAULT_LIMIT: Final = 50
```

## Home Assistant Integration

### Config Flow
User-friendly setup:
1. User adds integration
2. Enters library name (optional)
3. Integration creates entry
4. Database initialized
5. Services registered

### Coordinator
Manages data refresh:
```python
class LibraryCatalogCoordinator(DataUpdateCoordinator):
    """Update coordinator for library statistics."""
    
    async def _async_update_data(self) -> dict:
        """Fetch library stats every 30 minutes."""
```

### Services
Six services available:
1. `add_book` - Add via ISBN with API lookup
2. `add_book_manual` - Add with manual metadata
3. `search` - Search books
4. `delete_book` - Remove book
5. `update_location` - Change book location
6. `reload_database` - Refresh coordinator

### Events
Integration fires events for automations:
- `library_catalog_book_added`
- `library_catalog_book_deleted`
- `library_catalog_location_updated`
- `library_catalog_barcode_scanned`
- `library_catalog_database_reloaded`

## Development Workflow

### 1. Feature Development
```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes
# Write tests
# Run tests

# Commit
git commit -m "feat: Add new feature"
git push origin feature/new-feature
```

### 2. Testing
```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_webhook.py::TestWebhookHandler::test_valid_isbn -v

# Check coverage
pytest tests/ --cov=custom_components/library_catalog --cov-report=html
```

### 3. Documentation
Update relevant docs:
- README.md for user-facing changes
- DEVELOPMENT.md for architecture changes
- Docstrings for code changes
- CHANGELOG.md for version history

### 4. Commit Messages
Follow conventional commits:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `test:` - Test changes
- `refactor:` - Code restructure
- `chore:` - Maintenance

## Deployment

### HACS Installation
Users install via HACS:
1. HACS → Integrations → Explore & Download
2. Search "Library Catalog"
3. Download
4. Restart Home Assistant
5. Add integration via UI

### Manual Installation
Copy to custom_components:
```
config/
└── custom_components/
    └── library_catalog/
        ├── __init__.py
        ├── manifest.json
        └── ...
```

## Future Enhancements

### Planned Features
- Local cover image caching
- Book loan tracking
- Reading statistics
- Book recommendations
- Series management
- Import/Export
- Multi-library sync

### Database Migration
Version tracking in place:
```python
DB_SCHEMA_VERSION = 1  # Increment for migrations
```

Future migration handler will:
1. Check current version
2. Run necessary migrations
3. Update version number

## Performance Considerations

### Database Optimization
- Indexes on search fields
- FTS5 for text search
- LIMIT/OFFSET pagination
- Connection pooling

### API Rate Limiting
- Respect provider limits
- Fallback to secondary provider
- Cache responses (future)

### Memory Management
- Stream large result sets
- Pagination for UI display
- Async operations prevent blocking

## Contributing

See CONTRIBUTING.md for:
- Code of conduct
- How to report issues
- Pull request process
- Development setup

---

## Quick Reference

### Key Files
- `const.py` - All constants (101 items)
- `models.py` - Data structures
- `database.py` - SQLite operations
- `api.py` - External APIs
- `book_service.py` - Business logic
- `services.py` - HA services
- `webhook.py` - Barcode endpoint

### Key Commands
```bash
# Run tests
pytest tests/

# Check YAML
ha core check

# View logs
ha core logs

# Restart
ha core restart
```

### Useful Links
- [Home Assistant Dev Docs](https://developers.home-assistant.io/)
- [Async Programming](https://docs.python.org/3/library/asyncio.html)
- [Open Library API](https://openlibrary.org/developers/api)
- [Google Books API](https://developers.google.com/books)
