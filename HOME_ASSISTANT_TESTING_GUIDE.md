# Home Assistant Testing Guide - Library Catalog

## 🚀 Quick Start - Testing Your Library Catalog

### Step 1: Installation Check

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for **"Library Catalog"**
4. If you see it, click it and configure
5. Give your library a name (e.g., "My Library")

---

## 📚 How to Add Books

You have **3 ways** to add books to your library:

### Method 1: Using Services (Developer Tools)

1. Go to **Developer Tools** → **Services**
2. Select service: `library_catalog.add_book`
3. Use this YAML:

```yaml
service: library_catalog.add_book
data:
  isbn: "9780451524935"  # Example: 1984 by George Orwell
  location:
    room: "Living Room"
    shelf: "Bookshelf 1"
    compartment: "Top Shelf"
```

#### Try These Test ISBNs:
```yaml
# Test Book 1: 1984 by George Orwell
isbn: "9780451524935"

# Test Book 2: Harry Potter and the Philosopher's Stone
isbn: "9780747532699"

# Test Book 3: The Hobbit
isbn: "9780547928227"

# Test Book 4: To Kill a Mockingbird
isbn: "9780061120084"

# Test Book 5: The Great Gatsby
isbn: "9780743273565"
```

---

### Method 2: Using Automations

Create an automation to add books easily!

**File:** Save as `automations.yaml` or add via UI

```yaml
# Automation 1: Add Book Button
- id: add_book_button
  alias: "Library: Add Book via Button"
  trigger:
    - platform: event
      event_type: library_add_book_button_pressed
  action:
    - service: library_catalog.add_book
      data:
        isbn: "{{ trigger.event.data.isbn }}"
        location:
          room: "{{ trigger.event.data.room | default('Living Room') }}"
          shelf: "{{ trigger.event.data.shelf | default('Main Shelf') }}"
          compartment: "{{ trigger.event.data.compartment | default('Middle') }}"

# Automation 2: Search Books
- id: search_books
  alias: "Library: Search Books"
  trigger:
    - platform: event
      event_type: library_search_books
  action:
    - service: library_catalog.search
      data:
        query: "{{ trigger.event.data.query }}"
        search_by: "{{ trigger.event.data.search_by | default('title') }}"
        limit: 50
      response_variable: search_results
    - service: persistent_notification.create
      data:
        title: "Library Search Results"
        message: "Found {{ search_results.books | length }} books"
```

---

### Method 3: Using Scripts

Create reusable scripts for common tasks!

**File:** Save as `scripts.yaml` or add via UI

```yaml
# Script 1: Add Book Quickly
add_book_quick:
  alias: "Add Book to Library"
  fields:
    isbn:
      description: "Book ISBN (10 or 13 digits)"
      example: "9780451524935"
    room:
      description: "Room name"
      example: "Living Room"
      default: "Living Room"
    shelf:
      description: "Shelf name"
      example: "Bookshelf 1"
      default: "Main Shelf"
    compartment:
      description: "Compartment/Section"
      example: "Top"
      default: "Middle"
  sequence:
    - service: library_catalog.add_book
      data:
        isbn: "{{ isbn }}"
        location:
          room: "{{ room }}"
          shelf: "{{ shelf }}"
          compartment: "{{ compartment }}"
    - service: persistent_notification.create
      data:
        title: "Book Added!"
        message: "Book with ISBN {{ isbn }} added to {{ room }}/{{ shelf }}/{{ compartment }}"

# Script 2: Search Books by Title
search_books_by_title:
  alias: "Search Books by Title"
  fields:
    query:
      description: "Search term"
      example: "Harry Potter"
  sequence:
    - service: library_catalog.search
      data:
        query: "{{ query }}"
        search_by: "title"
        limit: 20
      response_variable: results
    - service: persistent_notification.create
      data:
        title: "Search: {{ query }}"
        message: "Found {{ results.books | length }} books"

# Script 3: Search Books by Author
search_books_by_author:
  alias: "Search Books by Author"
  fields:
    query:
      description: "Author name"
      example: "George Orwell"
  sequence:
    - service: library_catalog.search
      data:
        query: "{{ query }}"
        search_by: "author"
        limit: 20
      response_variable: results
    - service: persistent_notification.create
      data:
        title: "Books by {{ query }}"
        message: "Found {{ results.books | length }} books"

# Script 4: Delete Book
delete_book:
  alias: "Delete Book from Library"
  fields:
    isbn:
      description: "Book ISBN to delete"
      example: "9780451524935"
  sequence:
    - service: library_catalog.delete_book
      data:
        isbn: "{{ isbn }}"
    - service: persistent_notification.create
      data:
        title: "Book Deleted"
        message: "Book with ISBN {{ isbn }} removed from library"
```

---

## 🎮 Testing Dashboard

Create a Lovelace dashboard to interact with your library!

**File:** Add to your `ui-lovelace.yaml` or create via UI

```yaml
title: Library Catalog
views:
  - title: My Library
    path: library
    icon: mdi:book-open-page-variant
    cards:
      # Card 1: Add Book
      - type: entities
        title: Add Book to Library
        entities:
          - type: button
            name: Add "1984" by George Orwell
            icon: mdi:book-plus
            tap_action:
              action: call-service
              service: library_catalog.add_book
              service_data:
                isbn: "9780451524935"
                location:
                  room: "Living Room"
                  shelf: "Bookshelf 1"
                  compartment: "Top"
          
          - type: button
            name: Add "Harry Potter" 
            icon: mdi:book-plus
            tap_action:
              action: call-service
              service: library_catalog.add_book
              service_data:
                isbn: "9780747532699"
                location:
                  room: "Bedroom"
                  shelf: "Kids Shelf"
                  compartment: "Middle"

          - type: button
            name: Add "The Hobbit"
            icon: mdi:book-plus
            tap_action:
              action: call-service
              service: library_catalog.add_book
              service_data:
                isbn: "9780547928227"
                location:
                  room: "Living Room"
                  shelf: "Bookshelf 1"
                  compartment: "Bottom"

      # Card 2: Search Books
      - type: entities
        title: Search Library
        entities:
          - type: button
            name: Search for "Orwell"
            icon: mdi:book-search
            tap_action:
              action: call-service
              service: script.search_books_by_author
              service_data:
                query: "Orwell"

          - type: button
            name: Search for "Harry"
            icon: mdi:book-search
            tap_action:
              action: call-service
              service: script.search_books_by_title
              service_data:
                query: "Harry"

      # Card 3: Library Stats (when sensors are added)
      - type: markdown
        title: Library Information
        content: |
          ## 📚 Your Library Catalog

          Use the buttons above to:
          - ➕ Add books by ISBN
          - 🔍 Search your collection
          - 📊 View statistics

          ### Features:
          - Automatic metadata from Open Library & Google Books
          - Track book locations (room/shelf/compartment)
          - Search by title, author, or ISBN
          - No API keys needed!
```

---

## 🧪 Step-by-Step Testing Guide

### Test 1: Add Your First Book

1. Go to **Developer Tools** → **Services**
2. Select `library_catalog.add_book`
3. Paste this:
   ```yaml
   service: library_catalog.add_book
   data:
     isbn: "9780451524935"
     location:
       room: "Test Room"
       shelf: "Test Shelf"
       compartment: "Test Compartment"
   ```
4. Click **Call Service**
5. You should see a success message!

### Test 2: Search for Your Book

1. Go to **Developer Tools** → **Services**
2. Select `library_catalog.search`
3. Paste this:
   ```yaml
   service: library_catalog.search
   data:
     query: "1984"
     search_by: "title"
     limit: 10
   ```
4. Click **Call Service**
5. Check the response - you should see your book!

### Test 3: Delete a Book

1. Go to **Developer Tools** → **Services**
2. Select `library_catalog.delete_book`
3. Paste this:
   ```yaml
   service: library_catalog.delete_book
   data:
     isbn: "9780451524935"
   ```
4. Click **Call Service**
5. Book should be removed!

---

## 📡 Webhook Testing (For Barcode Scanners)

If you have a barcode scanner app on your phone:

### Webhook URL:
```
http://YOUR_HOME_ASSISTANT_IP:8123/api/webhook/library_catalog_scanner
```

### Test with curl:
```bash
curl -X POST http://YOUR_HOME_ASSISTANT_IP:8123/api/webhook/library_catalog_scanner \
  -H "Content-Type: application/json" \
  -d '{"isbn": "9780451524935"}'
```

### Test with PowerShell (Windows):
```powershell
Invoke-RestMethod -Uri "http://YOUR_HOME_ASSISTANT_IP:8123/api/webhook/library_catalog_scanner" `
  -Method Post `
  -Body '{"isbn": "9780451524935"}' `
  -ContentType "application/json"
```

---

## 🐛 Troubleshooting

### Issue: Integration not showing up

**Solution:**
1. Restart Home Assistant
2. Clear browser cache
3. Check `custom_components/library_catalog/` exists
4. Check Home Assistant logs: **Settings** → **System** → **Logs**

### Issue: Book not found

**Solution:**
- Try a different ISBN (some books might not be in Open Library or Google Books)
- Check internet connection
- Verify ISBN is valid (10 or 13 digits)

### Issue: Service not working

**Solution:**
1. Check integration is installed: **Settings** → **Devices & Services**
2. Look for errors in logs
3. Verify ISBN format (no spaces or hyphens needed)

---

## 📊 What Happens When You Add a Book?

1. ✅ ISBN is validated
2. 🌐 Open Library API is queried
3. 🔄 If insufficient data, Google Books is queried
4. 🧠 Data is merged intelligently
5. 💾 Book is saved to SQLite database
6. ✨ Metadata includes:
   - Title & Subtitle
   - Author(s)
   - Publisher
   - Publication Year
   - Description
   - Cover Image URL
   - Language
   - Page Count
   - Your location (room/shelf/compartment)

---

## 📖 More ISBN Examples for Testing

```yaml
# Classic Literature
"9780141439518"  # Pride and Prejudice - Jane Austen
"9780486280615"  # Frankenstein - Mary Shelley
"9780141182605"  # Dracula - Bram Stoker

# Modern Fiction
"9780316769174"  # The Catcher in the Rye - J.D. Salinger
"9780061120084"  # To Kill a Mockingbird - Harper Lee
"9780062316097"  # Sapiens - Yuval Noah Harari

# Science Fiction
"9780345391803"  # The Hitchhiker's Guide to the Galaxy
"9780441013593"  # Dune - Frank Herbert
"9780553293357"  # Foundation - Isaac Asimov

# Fantasy
"9780547928227"  # The Hobbit - J.R.R. Tolkien
"9780747532699"  # Harry Potter 1 - J.K. Rowling
"9780765311788"  # Mistborn - Brandon Sanderson
```

---

## 🎯 Next Steps

1. ✅ Add a few test books
2. ✅ Try searching by title, author, ISBN
3. ✅ Create automation for quick adds
4. ✅ Build a dashboard for your library
5. ✅ Set up webhook for barcode scanning

Happy cataloging! 📚
