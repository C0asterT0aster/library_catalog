#!/usr/bin/env python3
"""
Test Script for Library Catalog Integration
Run this from your Home Assistant config directory to test the integration

Usage:
    python test_library_integration.py
"""

import asyncio
import aiohttp
import json
from typing import Optional

# Configuration
HA_URL = "http://localhost:8123"  # Change if needed
HA_TOKEN = "YOUR_LONG_LIVED_ACCESS_TOKEN"  # Get from Profile → Long-Lived Access Tokens

# Test data
TEST_BOOKS = [
    {
        "isbn": "9780451524935",
        "title": "1984",
        "author": "George Orwell",
        "location": {"room": "Living Room", "shelf": "Shelf 1", "compartment": "Top"}
    },
    {
        "isbn": "9780747532699",
        "title": "Harry Potter and the Philosopher's Stone",
        "author": "J.K. Rowling",
        "location": {"room": "Bedroom", "shelf": "Kids Shelf", "compartment": "Middle"}
    },
    {
        "isbn": "9780547928227",
        "title": "The Hobbit",
        "author": "J.R.R. Tolkien",
        "location": {"room": "Living Room", "shelf": "Shelf 1", "compartment": "Bottom"}
    },
]


class LibraryTester:
    """Test the Library Catalog integration."""

    def __init__(self, url: str, token: str):
        self.url = url.rstrip('/')
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def call_service(self, domain: str, service: str, data: dict) -> dict:
        """Call a Home Assistant service."""
        url = f"{self.url}/api/services/{domain}/{service}"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    raise Exception(f"Service call failed: {response.status} - {text}")

    async def test_add_book(self, book: dict) -> bool:
        """Test adding a book."""
        print(f"\n📚 Testing: Add book '{book['title']}'")
        print(f"   ISBN: {book['isbn']}")

        try:
            result = await self.call_service(
                "library_catalog",
                "add_book",
                {
                    "isbn": book["isbn"],
                    "location": book["location"]
                }
            )
            print(f"   ✅ Success! Book added.")
            return True
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return False

    async def test_search(self, query: str, search_by: str = "title") -> bool:
        """Test searching for books."""
        print(f"\n🔍 Testing: Search by {search_by} for '{query}'")

        try:
            result = await self.call_service(
                "library_catalog",
                "search",
                {
                    "query": query,
                    "search_by": search_by,
                    "limit": 10
                }
            )

            # Note: Search results might be in response data
            print(f"   ✅ Search completed")
            return True
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return False

    async def test_delete_book(self, isbn: str) -> bool:
        """Test deleting a book."""
        print(f"\n🗑️  Testing: Delete book with ISBN {isbn}")

        try:
            result = await self.call_service(
                "library_catalog",
                "delete_book",
                {"isbn": isbn}
            )
            print(f"   ✅ Book deleted")
            return True
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return False

    async def test_webhook(self, isbn: str) -> bool:
        """Test webhook endpoint."""
        print(f"\n📡 Testing: Webhook with ISBN {isbn}")

        url = f"{self.url}/api/webhook/library_catalog_scanner"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json={"isbn": isbn},
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"   ✅ Webhook accepted: {data}")
                        return True
                    else:
                        text = await response.text()
                        print(f"   ❌ Webhook failed: {response.status} - {text}")
                        return False
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return False

    async def run_all_tests(self):
        """Run all tests."""
        print("="*60)
        print("  Library Catalog Integration Test Suite")
        print("="*60)
        print(f"\nHome Assistant URL: {self.url}")
        print(f"Testing with {len(TEST_BOOKS)} books\n")

        results = {
            "add": [],
            "search": [],
            "delete": [],
            "webhook": []
        }

        # Test 1: Add books
        print("\n" + "="*60)
        print("Test 1: Adding Books")
        print("="*60)
        for book in TEST_BOOKS:
            success = await self.test_add_book(book)
            results["add"].append(success)
            await asyncio.sleep(1)  # Rate limiting

        # Test 2: Search by title
        print("\n" + "="*60)
        print("Test 2: Search by Title")
        print("="*60)
        success = await self.test_search("Harry", "title")
        results["search"].append(success)

        # Test 3: Search by author
        print("\n" + "="*60)
        print("Test 3: Search by Author")
        print("="*60)
        success = await self.test_search("Orwell", "author")
        results["search"].append(success)

        # Test 4: Search by ISBN
        print("\n" + "="*60)
        print("Test 4: Search by ISBN")
        print("="*60)
        success = await self.test_search("9780451524935", "isbn")
        results["search"].append(success)

        # Test 5: Webhook
        print("\n" + "="*60)
        print("Test 5: Webhook")
        print("="*60)
        success = await self.test_webhook("9780061120084")  # To Kill a Mockingbird
        results["webhook"].append(success)

        # Test 6: Delete books (cleanup)
        print("\n" + "="*60)
        print("Test 6: Deleting Books (Cleanup)")
        print("="*60)
        for book in TEST_BOOKS:
            success = await self.test_delete_book(book["isbn"])
            results["delete"].append(success)
            await asyncio.sleep(0.5)

        # Summary
        print("\n" + "="*60)
        print("  Test Summary")
        print("="*60)
        print(f"\n✅ Add Books:    {sum(results['add'])}/{len(results['add'])} passed")
        print(f"✅ Search:       {sum(results['search'])}/{len(results['search'])} passed")
        print(f"✅ Delete Books: {sum(results['delete'])}/{len(results['delete'])} passed")
        print(f"✅ Webhook:      {sum(results['webhook'])}/{len(results['webhook'])} passed")

        total_passed = sum(sum(r) for r in results.values())
        total_tests = sum(len(r) for r in results.values())

        print(f"\n📊 Overall: {total_passed}/{total_tests} tests passed")

        if total_passed == total_tests:
            print("\n🎉 All tests passed! Your integration is working perfectly!")
        else:
            print("\n⚠️  Some tests failed. Check the output above for details.")


async def main():
    """Main entry point."""
    print("\n" + "="*60)
    print("  Setup Instructions")
    print("="*60)
    print("\n1. Go to your Home Assistant Profile")
    print("2. Scroll to 'Long-Lived Access Tokens'")
    print("3. Click 'Create Token'")
    print("4. Copy the token")
    print("5. Edit this file and paste the token in HA_TOKEN")
    print("6. Update HA_URL if Home Assistant is not on localhost")
    print("\n" + "="*60)

    if HA_TOKEN == "YOUR_LONG_LIVED_ACCESS_TOKEN":
        print("\n❌ ERROR: Please set HA_TOKEN first!")
        print("   Edit this file and add your Home Assistant access token.")
        return

    input("\nPress ENTER to start tests...")

    tester = LibraryTester(HA_URL, HA_TOKEN)
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
