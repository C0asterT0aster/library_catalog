"""Constants for Library Catalog integration."""
from typing import Final

# ============================================================================
# INTEGRATION BASICS
# ============================================================================
DOMAIN: Final = "library_catalog"
INTEGRATION_NAME: Final = "Library Catalog"
INTEGRATION_VERSION: Final = "0.1.0"
ISSUE_TRACKER: Final = "https://github.com/yourusername/library_catalog/issues"
DOCUMENTATION: Final = "https://github.com/yourusername/library_catalog"

# ============================================================================
# DATABASE & STORAGE
# ============================================================================
DB_FILE_NAME: Final = "library_catalog.db"
DB_SCHEMA_VERSION: Final = 1
DB_TIMEOUT: Final = 30.0  # seconds for database operations

# Cover storage (future enhancement)
COVER_CACHE_DIR: Final = "library_catalog"
COVER_URL_ONLY_V1: Final = True  # v1 stores URLs only, no local caching yet

# ============================================================================
# SERVICE NAMES & IDS
# ============================================================================
SERVICE_ADD_BOOK: Final = "add_book"
SERVICE_SEARCH: Final = "search"
SERVICE_DELETE_BOOK: Final = "delete_book"

# ============================================================================
# SERVICE PARAMETERS / CONFIGURATION KEYS
# ============================================================================
# Book data fields
CONF_ISBN: Final = "isbn"
CONF_TITLE: Final = "title"
CONF_SUBTITLE: Final = "subtitle"
CONF_AUTHORS: Final = "authors"
CONF_PUBLISHER: Final = "publisher"
CONF_YEAR: Final = "year"
CONF_DESCRIPTION: Final = "description"
CONF_COVER_URL: Final = "cover_url"
CONF_LANGUAGE: Final = "language"
CONF_PAGES: Final = "pages"

# Location fields (hierarchical structure)
CONF_LOCATION: Final = "location"
CONF_ROOM: Final = "room"
CONF_SHELF: Final = "shelf"
CONF_COMPARTMENT: Final = "compartment"

# Search query fields
CONF_QUERY: Final = "query"
CONF_SEARCH_BY: Final = "search_by"  # "title", "author", "isbn"
CONF_LIMIT: Final = "limit"

# Barcode/webhook fields
CONF_BARCODE: Final = "barcode"
CONF_ISBN_INPUT: Final = "isbn_input"
CONF_BARCODE_FORMAT: Final = "barcode_format"

# Config Entry fields
CONF_NAME: Final = "name"

# ============================================================================
# API ENDPOINTS & TIMEOUTS
# ============================================================================
# Open Library
OPEN_LIBRARY_API_URL: Final = "https://openlibrary.org"
OPEN_LIBRARY_TIMEOUT: Final = 10  # seconds

# Google Books
GOOGLE_BOOKS_API_URL: Final = "https://www.googleapis.com/books/v1/volumes"
GOOGLE_BOOKS_TIMEOUT: Final = 10  # seconds
GOOGLE_BOOKS_MAX_RESULTS: Final = 5

# General HTTP settings
HTTP_TIMEOUT: Final = 10
HTTP_RETRIES: Final = 3
HTTP_RETRY_DELAY: Final = 1  # seconds

# ============================================================================
# ISBN & BARCODE VALIDATION
# ============================================================================
ISBN10_LENGTH: Final = 10
ISBN13_LENGTH: Final = 13
ISBN10_PREFIX: Final = "978"  # Prefix for converting ISBN-10 to ISBN-13
ISBN_VALID_CHARACTERS: Final = "0123456789-X"  # Plus hyphen for formatting

# Barcode format detection
BARCODE_FORMAT_ISBN10: Final = "ISBN10"
BARCODE_FORMAT_ISBN13: Final = "ISBN13"
BARCODE_FORMAT_EAN13: Final = "EAN13"  # EAN-13 is compatible with ISBN-13
BARCODE_FORMAT_CODE128: Final = "CODE128"
BARCODE_FORMAT_UNKNOWN: Final = "UNKNOWN"

# ============================================================================
# SEARCH SETTINGS
# ============================================================================
SEARCH_DEFAULT_LIMIT: Final = 50
SEARCH_MAX_LIMIT: Final = 1000
SEARCH_MIN_QUERY_LENGTH: Final = 2
SEARCH_RESULTS_TIMEOUT: Final = 5  # seconds

# ============================================================================
# COORDINATOR & DATA UPDATES
# ============================================================================
UPDATE_INTERVAL: Final = 1800  # 30 minutes in seconds
# The coordinator periodically refreshes book data stats/counts
# Individual book lookups happen on-demand via services

# ============================================================================
# WEBHOOK CONFIGURATION
# ============================================================================
WEBHOOK_ID: Final = "library_catalog_scanner"
WEBHOOK_PATH: Final = f"/api/webhook/{WEBHOOK_ID}"

# Webhook request field detection (tolerant parsing)
WEBHOOK_FIELD_ISBN: Final = ("isbn", "isbn_input", "code", "barcode")
WEBHOOK_FIELD_FORMAT: Final = ("format", "barcode_format", "type")

# ============================================================================
# LOCATION HIERARCHY (DEFAULT STRUCTURE - USER-CONFIGURABLE)
# ============================================================================
# These are default suggestions; users can customize entirely
DEFAULT_ROOMS: Final = [
    "Living Room",
    "Bedroom",
    "Office",
    "Kitchen",
    "Library",
    "Study",
]

DEFAULT_SHELF_LEVELS: Final = [
    "Shelf 1",
    "Shelf 2",
    "Shelf 3",
    "Shelf 4",
    "Shelf 5",
]

DEFAULT_COMPARTMENTS: Final = [
    "Top",
    "Upper Middle",
    "Middle",
    "Lower Middle",
    "Bottom",
]

# ============================================================================
# ERROR & WARNING MESSAGES
# ============================================================================
# ISBN/Barcode errors
ERROR_INVALID_ISBN: Final = "Invalid ISBN provided"
ERROR_ISBN_FORMAT_NOT_SUPPORTED: Final = "Barcode format not supported"
ERROR_INVALID_BARCODE: Final = "Invalid or unreadable barcode"
ERROR_ISBN_CHECKSUM_FAILED: Final = "ISBN checksum validation failed"

# Book errors
ERROR_BOOK_NOT_FOUND: Final = "Book not found"
ERROR_BOOK_ALREADY_EXISTS: Final = "Book already exists in the catalog"
ERROR_BOOK_FETCH_FAILED: Final = "Failed to fetch book data from APIs"
ERROR_BOOK_DELETE_FAILED: Final = "Failed to delete book"

# API errors
ERROR_API_UNREACHABLE: Final = "Unable to reach book data API"
ERROR_API_RATE_LIMITED: Final = "API rate limit reached, please try again later"
ERROR_API_INVALID_RESPONSE: Final = "Invalid response from book data API"

# Database errors
ERROR_DATABASE_ERROR: Final = "Database operation failed"
ERROR_DATABASE_LOCKED: Final = "Database is locked, please try again"

# Search errors
ERROR_SEARCH_INVALID_QUERY: Final = "Invalid search query"
ERROR_SEARCH_NO_RESULTS: Final = "No books found matching your query"

# Location errors
ERROR_INVALID_LOCATION: Final = "Invalid location specified"

# Webhook errors
ERROR_WEBHOOK_INVALID_PAYLOAD: Final = "Invalid webhook payload"
ERROR_WEBHOOK_NO_ISBN_FOUND: Final = "No ISBN found in webhook payload"

# ============================================================================
# SUCCESS & INFO MESSAGES
# ============================================================================
MSG_BOOK_ADDED_SUCCESS: Final = "Book added successfully"
MSG_BOOK_DELETED_SUCCESS: Final = "Book deleted successfully"
MSG_BOOK_UPDATED_SUCCESS: Final = "Book updated successfully"

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
LOGGER_NAME: Final = "library_catalog"
LOG_LEVEL_DEFAULT: Final = "INFO"

# ============================================================================
# DIAGNOSTICS
# ============================================================================
DIAG_DATABASE_STATUS: Final = "database_status"
DIAG_BOOK_COUNT: Final = "book_count"
DIAG_API_STATS: Final = "api_statistics"
DIAG_LAST_UPDATE: Final = "last_update"
DIAG_CONFIGURATION: Final = "configuration"

# ============================================================================
# FEATURE FLAGS
# ============================================================================
FEATURE_BARCODE_WEBHOOK: Final = True
FEATURE_SEARCH: Final = True
FEATURE_MULTI_LIBRARY: Final = True  # Architecture supports multiple entries
FEATURE_COVER_CACHING: Final = False  # v1: URLs only
FEATURE_BOOK_LOANS: Final = False  # Future feature
FEATURE_STATISTICS: Final = False  # Future feature

# ============================================================================
# DATA VALIDATION & LIMITS
# ============================================================================
ISBN_CHECK_ENABLED: Final = True
TITLE_MAX_LENGTH: Final = 500
SUBTITLE_MAX_LENGTH: Final = 500
AUTHOR_MAX_LENGTH: Final = 200  # per author
AUTHORS_MAX_COUNT: Final = 20
PUBLISHER_MAX_LENGTH: Final = 200
DESCRIPTION_MAX_LENGTH: Final = 5000
LANGUAGE_CODE_LENGTH: Final = 5  # e.g., "en-US", "de-DE"
PAGES_MAX: Final = 10000

# ============================================================================
# MANIFEST CONFIGURATION (for reference)
# ============================================================================
# These values should match manifest.json
MANIFEST_VERSION: Final = "0.1.0"
MANIFEST_HOMEASSISTANT_MIN: Final = "2023.1.0"
MANIFEST_IOT_CLASS: Final = "local_polling"