# Development Guide

This document describes the architecture and development process for Library Catalog.

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
├── Home Assistant Integration
│   ├── Config Flow (config_flow.py)
│   ├── Coordinator (coordinator.py)
│   ├── Services (services.py)
│   ├── Webhook (webhook.py)
│   └── Init (\_\_init\_\_.py)
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

### 3. Scalability
Designed for 10,000+ book libraries:
- 7 performance indexes on common search fields
- FTS5 virtual table for full-text search
- Pagination support (LIMIT/OFFSET)
- Efficient query construction

### 4. Extensibility
Future features prepared without redesign:
- Location hierarchy ready for complex structures
- Cover URL architecture ready for local caching
- Schema versioning for migrations
- Feature flags in constants

### 5. User-Configurable
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
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

### Indexes
- `idx_books_title` - For title searches
- `idx_books_authors` - For author searches
- `idx_books_isbn` - For ISBN lookups
- `idx_books_publisher` - For publisher filtering
- `idx_books_year` - For year-based queries
- `idx_books_room` - For location-based dashboard queries
- `idx_books_created_at` - For sorting/pagination

### Full-Text Search
```sql
CREATE VIRTUAL TABLE books_fts USING fts5(
    title,
    authors,
    description,
    content=books
)
```

## API Integration

### Open Library
- **Endpoint**: `https://openlibrary.org/api/books`
- **Query**: `?bibkeys=ISBN:XXXX&format=json&jscmd=data`
- **Timeout**: 10 seconds
- **Fallback**: Google Books if no result

### Google Books
- **Endpoint**: `https://www.googleapis.com/books/v1/volumes`
- **Query**: `?q=isbn:XXXX`
- **Timeout**: 10 seconds
- **Rate Limit**: 100 QPS

### ISBN Validation
- Supports ISBN-10 and ISBN-13
- ISBN-10 converted to ISBN-13
- Checksum validation using `python-stdnum`
- Tolerant barcode parsing for scanners

## Service Definitions

### library_catalog.add_book
```yaml
Service: library_catalog.add_book
Parameters:
  isbn: string (required)
  location:
    room: string (optional)
    shelf: string (optional)
    compartment: string (optional)
Returns:
  isbn: string
  title: string
  authors: list
  # ... all book fields
```

### library_catalog.search
```yaml
Service: library_catalog.search
Parameters:
  query: string (required)
  search_by: string (optional: title, author, isbn)
  limit: number (optional, max 1000)
Returns:
  results: list of books
  total_count: number
  query: string
  search_type: string
  has_more: boolean
```

### library_catalog.delete_book
```yaml
Service: library_catalog.delete_book
Parameters:
  isbn: string (required)
Returns:
  success: boolean
  isbn: string
```

## Webhook Integration

### Endpoint
`/api/webhook/library_catalog_scanner`

### Supported Input Formats

All these formats are automatically detected and normalized:
```json
{"isbn": "9783442478951"}
{"code": "9783442478951", "format": "EAN_13"}
{"barcode": "9783442478951", "format": "EAN-13"}
```

### Processing Flow
1. Extract ISBN/barcode from payload
2. Remove formatting characters
3. Validate ISBN-10 or ISBN-13
4. Convert ISBN-10 to ISBN-13
5. Look up in database or fetch from APIs
6. Store in database

## Data Flow

### Adding a Book
```
1. User calls library_catalog.add_book service
2. ISBN validation occurs
3. API lookup (Open Library or Google Books)
4. Data normalization
5. Database insertion
6. Return book details
```

### Searching for Books
```
1. User calls library_catalog.search service
2. Query passed to database search method
3. Appropriate index used for query type
4. Pagination applied (LIMIT/OFFSET)
5. Results returned with total count
```

### Webhook Barcode
```
1. Scanner sends POST to webhook endpoint
2. Payload parsed and ISBN extracted
3. ISBN normalized
4. Checked if already in database
5. If not found, fetch from APIs
6. Store in database with timestamp
```

## Development Phases

### Phase 1: Infrastructure ✅
- Commit 1.1: Constants & Configuration
- Commit 1.2: Database Layer & Models
- Commit 1.3: API Client Layer

### Phase 2: Integration
- Commit 2.1: Config Flow
- Commit 2.2: Core Integration Setup
- Commit 2.3: Services Registration

### Phase 3: Interaction
- Commit 3.1: Barcode Webhook
- Commit 3.2: Diagnostics

### Phase 4: Frontend
- Commit 4.1: Book Data Models
- Commit 4.2: Entity Definitions

### Phase 5: Polish
- Commit 5.1: Localization
- Commit 5.2: Documentation

### Phase 6: Quality
- Commit 6.1: Unit Tests
- Commit 6.2: Integration Tests
- Commit 6.3: HACS Validation

## Error Handling

### Strategy
- All async operations wrapped in try/catch
- Errors logged with context
- User-friendly error messages in services
- Webhook errors return appropriate HTTP status

### Common Errors
- `ISBN_CHECKSUM_FAILED` - Invalid ISBN
- `BOOK_ALREADY_EXISTS` - Duplicate ISBN
- `API_UNREACHABLE` - No internet connection
- `API_RATE_LIMITED` - Too many requests
- `DATABASE_ERROR` - Database operation failed

## Testing Strategy

### Unit Tests
- Test each class independently
- Mock external dependencies (APIs, database)
- Verify error handling

### Integration Tests
- Test service workflows end-to-end
- Verify database persistence
- Test webhook payload parsing

### Manual Testing Checklist
- Add book via service
- Search with different query types
- Delete book
- Test webhook with scanner payloads
- Verify location storage
- Check database file creation

## Performance Optimization

### Database Queries
- Use indexed columns in WHERE clauses
- Limit result sets with pagination
- Case-insensitive searches use COLLATE NOCASE
- Full-text search for complex queries

### API Calls
- Retry failed requests (exponential backoff)
- Cache API responses when appropriate
- Parallel requests where possible

### Memory
- Stream database results
- Avoid loading entire library into memory
- Paginate large result sets

## Security Considerations

### Database
- SQLite with file-level permissions
- Foreign key constraints enabled
- No SQL injection (parameterized queries)
- Timeout protection (30 seconds)

### API
- HTTPS for external APIs
- Timeout on all HTTP requests
- Rate limiting awareness

### Webhook
- Webhook token required (Home Assistant built-in)
- Input validation on all webhook data
- Normalized input to prevent injection

## Logging

### Logger
- All classes use consistent logger: `LOGGER_NAME` from const.py
- Log levels: DEBUG, INFO, WARNING, ERROR

### Debug Output
```python
import logging
logger = logging.getLogger("library_catalog")
logger.debug("Detailed debug info")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error with exception", exc_info=True)
```

## Version Management

### Schema Versioning
- Current version: 1
- Future migrations will increment
- Version stored in `schema_version` table

### Feature Flags
- Located in `const.py`
- Easy to disable features for debugging
- Prepared for future features

## Getting Started with Development

1. **Setup Environment**
   ```bash
   git clone https://github.com/YOUR_USERNAME/library_catalog.git
   cd library_catalog/library_catalog
   pip install -r requirements.txt
   ```

2. **Understand Architecture**
   - Read const.py for all constants
   - Review models.py for data structures
   - Study database.py for persistence

3. **Make Changes**
   - Follow code style guidelines
   - Add type hints
   - Add docstrings
   - Keep async throughout

4. **Test Thoroughly**
   - Write tests for new functionality
   - Run existing tests
   - Test in Home Assistant environment

5. **Document**
   - Update README if needed
   - Add docstrings
   - Update this guide if architecture changes

## Future Enhancements

- Book loans tracking
- Library statistics
- Local cover cache
- Import/export functionality
- Mobile app integration
- Multi-library sync

See `const.py` for `FEATURE_*` flags.
