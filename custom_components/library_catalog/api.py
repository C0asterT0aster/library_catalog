import aiohttp
import asyncio
import logging

from .const import OPEN_LIBRARY_API_URL, GOOGLE_BOOKS_API_URL

_LOGGER = logging.getLogger(__name__)

async def fetch_open_library_data(isbn):
    """Fetch book data from Open Library API using ISBN."""
    url = f"{OPEN_LIBRARY_API_URL}/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data.get(f'ISBN:{isbn}', None)
            else:
                _LOGGER.error("Failed to fetch data from Open Library API: %s", response.status)
                return None

async def fetch_google_books_data(isbn):
    """Fetch book data from Google Books API using ISBN."""
    url = f"{GOOGLE_BOOKS_API_URL}?q=isbn:{isbn}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if 'items' in data:
                    return data['items'][0]
                else:
                    _LOGGER.warning("No data found for ISBN %s in Google Books API", isbn)
                    return None
            else:
                _LOGGER.error("Failed to fetch data from Google Books API: %s", response.status)
                return None

async def get_book_data(isbn):
    """Get book data from Open Library or Google Books API."""
    book_data = await fetch_open_library_data(isbn)
    if book_data is None:
        book_data = await fetch_google_books_data(isbn)
    return book_data