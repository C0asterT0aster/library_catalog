"""API client for fetching book data from Open Library and Google Books."""
import asyncio
import logging
from typing import Optional, Dict, Any
from stdnum import isbn as isbn_validator
from stdnum.exceptions import ValidationError
import aiohttp

from .const import (
    OPEN_LIBRARY_API_URL,
    OPEN_LIBRARY_TIMEOUT,
    GOOGLE_BOOKS_API_URL,
    GOOGLE_BOOKS_TIMEOUT,
    HTTP_RETRIES,
    HTTP_RETRY_DELAY,
)
from .models import BookData

_LOGGER = logging.getLogger(__name__)


class ISBNValidationError(Exception):
    """Raised when ISBN validation fails."""

    pass


class BookNotFoundError(Exception):
    """Raised when book data cannot be found."""

    pass


def validate_isbn(isbn_string: str) -> str:
    """Validate and normalize ISBN string.
    
    Args:
        isbn_string: ISBN-10 or ISBN-13 string (with or without hyphens)
        
    Returns:
        Normalized ISBN-13 string
        
    Raises:
        ISBNValidationError: If ISBN is invalid
    """
    # Remove common separators
    cleaned = isbn_string.replace("-", "").replace(" ", "").upper()
    
    try:
        # Check length first
        if len(cleaned) not in (10, 13):
            raise ISBNValidationError(
                f"Invalid ISBN length: {len(cleaned)} (must be 10 or 13)"
            )
        
        # Validate ISBN (works for both ISBN-10 and ISBN-13)
        if not isbn_validator.is_valid(cleaned):
            raise ISBNValidationError(f"Invalid ISBN: {isbn_string}")
        
        # Convert to ISBN-13 if needed
        if len(cleaned) == 10:
            normalized = isbn_validator.to_isbn13(cleaned)
        else:
            normalized = cleaned
            
        return normalized
    except ISBNValidationError:
        raise
    except (ValidationError, Exception) as e:
        raise ISBNValidationError(f"ISBN validation failed: {str(e)}")


async def fetch_open_library_data(isbn: str, session: Optional[aiohttp.ClientSession] = None) -> Optional[Dict[str, Any]]:
    """Fetch book data from Open Library API.
    
    Args:
        isbn: Validated ISBN-13
        session: Optional aiohttp session (creates new if not provided)
        
    Returns:
        Raw API response dict or None if not found
    """
    url = f"{OPEN_LIBRARY_API_URL}/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    
    should_close = session is None
    if session is None:
        session = aiohttp.ClientSession()
    
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=OPEN_LIBRARY_TIMEOUT)) as response:
            if response.status == 200:
                data = await response.json()
                result = data.get(f"ISBN:{isbn}")
                if result:
                    _LOGGER.debug("Found book data in Open Library for ISBN %s", isbn)
                    return result
                else:
                    _LOGGER.debug("Book not found in Open Library for ISBN %s", isbn)
                    return None
            elif response.status == 404:
                _LOGGER.debug("Book not found in Open Library (404): %s", isbn)
                return None
            else:
                _LOGGER.warning("Open Library API returned status %d for ISBN %s", response.status, isbn)
                return None
    except asyncio.TimeoutError:
        _LOGGER.warning("Timeout fetching from Open Library for ISBN %s", isbn)
        return None
    except Exception as e:
        _LOGGER.error("Error fetching from Open Library: %s", str(e))
        return None
    finally:
        if should_close:
            await session.close()


async def fetch_google_books_data(isbn: str, session: Optional[aiohttp.ClientSession] = None) -> Optional[Dict[str, Any]]:
    """Fetch book data from Google Books API.
    
    Args:
        isbn: Validated ISBN-13
        session: Optional aiohttp session (creates new if not provided)
        
    Returns:
        Raw API response dict or None if not found
    """
    url = f"{GOOGLE_BOOKS_API_URL}?q=isbn:{isbn}"
    
    should_close = session is None
    if session is None:
        session = aiohttp.ClientSession()
    
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=GOOGLE_BOOKS_TIMEOUT)) as response:
            if response.status == 200:
                data = await response.json()
                if "items" in data and len(data["items"]) > 0:
                    result = data["items"][0]
                    _LOGGER.debug("Found book data in Google Books for ISBN %s", isbn)
                    return result
                else:
                    _LOGGER.debug("Book not found in Google Books for ISBN %s", isbn)
                    return None
            elif response.status == 403:
                _LOGGER.warning("Google Books API rate limited or quota exceeded")
                return None
            else:
                _LOGGER.warning("Google Books API returned status %d for ISBN %s", response.status, isbn)
                return None
    except asyncio.TimeoutError:
        _LOGGER.warning("Timeout fetching from Google Books for ISBN %s", isbn)
        return None
    except Exception as e:
        _LOGGER.error("Error fetching from Google Books: %s", str(e))
        return None
    finally:
        if should_close:
            await session.close()


def normalize_open_library_response(raw_data: Dict[str, Any], isbn: str) -> BookData:
    """Convert Open Library API response to BookData.
    
    Args:
        raw_data: Raw Open Library API response
        isbn: Validated ISBN-13
        
    Returns:
        BookData object
    """
    authors = []
    if "authors" in raw_data:
        for author in raw_data["authors"]:
            if isinstance(author, dict) and "name" in author:
                authors.append(author["name"])
            elif isinstance(author, str):
                authors.append(author)
    
    # Extract cover URL - Open Library returns cover ID, we need to construct URL
    cover_url = None
    if "cover" in raw_data:
        cover_id = raw_data["cover"].get("medium") or raw_data["cover"].get("small")
        if cover_id:
            cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
    
    return BookData(
        isbn=isbn,
        title=raw_data.get("title", "Unknown"),
        subtitle=raw_data.get("subtitle"),
        authors=authors,
        publisher=raw_data.get("publishers", [None])[0] if raw_data.get("publishers") else None,
        year=raw_data.get("publish_date"),
        description=raw_data.get("description"),
        cover_url=cover_url,
        language=raw_data.get("languages", [None])[0] if raw_data.get("languages") else None,
        pages=raw_data.get("number_of_pages"),
    )


def normalize_google_books_response(raw_data: Dict[str, Any], isbn: str) -> BookData:
    """Convert Google Books API response to BookData.
    
    Args:
        raw_data: Raw Google Books API response
        isbn: Validated ISBN-13
        
    Returns:
        BookData object
    """
    info = raw_data.get("volumeInfo", {})
    
    authors = info.get("authors", [])
    
    # Extract year from published date
    year = None
    if "publishedDate" in info:
        try:
            year = int(info["publishedDate"][:4])
        except (ValueError, IndexError):
            year = None
    
    # Extract cover image
    cover_url = None
    if "imageLinks" in info:
        cover_url = info["imageLinks"].get("medium") or info["imageLinks"].get("thumbnail")
    
    return BookData(
        isbn=isbn,
        title=info.get("title", "Unknown"),
        subtitle=info.get("subtitle"),
        authors=authors,
        publisher=info.get("publisher"),
        year=year,
        description=info.get("description"),
        cover_url=cover_url,
        language=info.get("language"),
        pages=info.get("pageCount"),
    )


async def get_book_data(isbn_input: str) -> BookData:
    """Fetch complete book data from APIs with fallback strategy.
    
    Args:
        isbn_input: ISBN-10 or ISBN-13 (with or without hyphens)
        
    Returns:
        BookData object
        
    Raises:
        ISBNValidationError: If ISBN is invalid
        BookNotFoundError: If book cannot be found in any API
    """
    # Validate and normalize ISBN
    isbn = validate_isbn(isbn_input)
    _LOGGER.debug("Fetching book data for ISBN %s", isbn)
    
    # Try Open Library first (more complete metadata)
    try:
        open_lib_data = await fetch_open_library_data(isbn)
        if open_lib_data:
            return normalize_open_library_response(open_lib_data, isbn)
    except Exception as e:
        _LOGGER.warning("Error processing Open Library data: %s", str(e))
    
    # Fallback to Google Books
    try:
        google_data = await fetch_google_books_data(isbn)
        if google_data:
            return normalize_google_books_response(google_data, isbn)
    except Exception as e:
        _LOGGER.warning("Error processing Google Books data: %s", str(e))
    
    # No data found in any API
    raise BookNotFoundError(f"Book not found for ISBN {isbn}")