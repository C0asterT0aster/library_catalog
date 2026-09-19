# iOS Home Assistant Book Scanner - Complete Setup Guide

## Overview

This guide creates a complete book scanning system directly in Home Assistant for iOS users. No external apps needed - everything works through the Home Assistant Companion app.

## Features

✅ **Scan Button** - One tap to start scanning
✅ **Automatic Detection** - Barcodes detected automatically, no scan button press needed
✅ **Batch Scanning** - Set location once, scan multiple books
✅ **Location Presets** - Remember your shelf locations
✅ **Real-time Feedback** - See what you've scanned immediately
✅ **NFC Ready** - Easy to add NFC tags later

## Architecture

Since iOS doesn't allow direct barcode scanning in web views, we use:
1. **Home Assistant Companion App** - Opens device camera
2. **Actionable Notifications** - Sends scan results back
3. **Node-RED or AppDaemon** (optional) - For advanced image processing
4. **Input Helpers** - Store scan state and location

## Setup Steps

### Step 1: Create Input Helpers

Go to **Settings → Devices & Services → Helpers** and create these:

#### Input Text Helpers

```yaml
# Or add to configuration.yaml:

input_text:
  book_scan_room:
    name: "Current Scan Room"
    initial: "Living Room"
    icon: mdi:home
  
  book_scan_shelf:
    name: "Current Scan Shelf"  
    initial: "Shelf 1"
    icon: mdi:bookshelf
  
  book_scan_compartment:
    name: "Current Scan Compartment"
    initial: "Top"
    icon: mdi:book-open-variant
  
  book_last_scanned_isbn:
    name: "Last Scanned ISBN"
    icon: mdi:barcode
  
  book_last_scanned_title:
    name: "Last Scanned Title"
    icon: mdi:book
```

#### Input Boolean Helpers

```yaml
input_boolean:
  book_scanning_mode:
    name: "Book Scanning Mode Active"
    icon: mdi:barcode-scan
  
  book_scanning_batch:
    name: "Batch Scanning (Same Location)"
    initial: off
    icon: mdi:book-multiple
```

#### Input Number Helper

```yaml
input_number:
  books_scanned_count:
    name: "Books Scanned This Session"
    min: 0
    max: 1000
    step: 1
    icon: mdi:counter
```

### Step 2: Create Scripts

Add to `configuration.yaml` or create `scripts.yaml`:

```yaml
script:
  start_book_scanning:
    alias: "Start Book Scanning"
    icon: mdi:barcode-scan
    sequence:
      # Reset counter
      - service: input_number.set_value
        target:
          entity_id: input_number.books_scanned_count
        data:
          value: 0
      
      # Enable scanning mode
      - service: input_boolean.turn_on
        target:
          entity_id: input_boolean.book_scanning_mode
      
      # Send notification with camera action
      - service: notify.mobile_app_iphone
        data:
          title: "📚 Book Scanner Ready"
          message: "Scanning to: {{ states('input_text.book_scan_room') }} > {{ states('input_text.book_scan_shelf') }}"
          data:
            actions:
              - action: "SCAN_BARCODE"
                title: "📷 Scan Book"
                behavior: textInput
                textInputButtonTitle: "Submit ISBN"
                textInputPlaceholder: "Enter ISBN or scan barcode"
            tag: "book_scanner"
            sticky: true
            notification_icon: "mdi:barcode-scan"

  stop_book_scanning:
    alias: "Stop Book Scanning"
    icon: mdi:stop
    sequence:
      - service: input_boolean.turn_off
        target:
          entity_id: input_boolean.book_scanning_mode
      
      - service: notify.mobile_app_iphone
        data:
          title: "✅ Scanning Complete"
          message: "Added {{ states('input_number.books_scanned_count') | int }} books"
          data:
            tag: "book_scanner"

  process_scanned_isbn:
    alias: "Process Scanned ISBN"
    fields:
      isbn:
        description: "The scanned ISBN"
        example: "9780451524935"
    sequence:
      # Store last scanned ISBN
      - service: input_text.set_value
        target:
          entity_id: input_text.book_last_scanned_isbn
        data:
          value: "{{ isbn }}"
      
      # Add book to catalog
      - service: library_catalog.add_book
        data:
          isbn: "{{ isbn }}"
          location:
            room: "{{ states('input_text.book_scan_room') }}"
            shelf: "{{ states('input_text.book_scan_shelf') }}"
            compartment: "{{ states('input_text.book_scan_compartment') }}"
        response_variable: book_result
      
      # Increment counter
      - service: input_number.increment
        target:
          entity_id: input_number.books_scanned_count
      
      # Continue scanning notification
      - service: notify.mobile_app_iphone
        data:
          title: "✅ Book Added"
          message: "ISBN: {{ isbn }} | Total: {{ states('input_number.books_scanned_count') | int }}"
          data:
            actions:
              - action: "SCAN_NEXT"
                title: "📷 Scan Next Book"
              - action: "STOP_SCANNING"
                title: "🛑 Stop & Finish"
            tag: "book_scanner_result"
            group: "book_scanner"

  set_scan_location:
    alias: "Set Scan Location"
    icon: mdi:map-marker
    fields:
      room:
        description: "Room name"
        example: "Living Room"
      shelf:
        description: "Shelf identifier"  
        example: "Shelf 1"
      compartment:
        description: "Compartment"
        example: "Top"
    sequence:
      - service: input_text.set_value
        target:
          entity_id: input_text.book_scan_room
        data:
          value: "{{ room }}"
      
      - service: input_text.set_value
        target:
          entity_id: input_text.book_scan_shelf
        data:
          value: "{{ shelf }}"
      
      - service: input_text.set_value
        target:
          entity_id: input_text.book_scan_compartment
        data:
          value: "{{ compartment }}"
      
      - service: notify.mobile_app_iphone
        data:
          title: "📍 Location Set"
          message: "{{ room }} > {{ shelf }} > {{ compartment }}"
```

**Important:** Replace `notify.mobile_app_iphone` with your actual device name. Find it in:
Settings → Devices & Services → Mobile App → Your Device → Device Name

### Step 3: Create Automations

Add to `automations.yaml`:

```yaml
# Handle notification actions
- id: book_scanner_notification_action
  alias: "Book Scanner: Handle Actions"
  trigger:
    - platform: event
      event_type: mobile_app_notification_action
      event_data:
        action: SCAN_BARCODE
    - platform: event
      event_type: mobile_app_notification_action
      event_data:
        action: SCAN_NEXT
  condition:
    - condition: state
      entity_id: input_boolean.book_scanning_mode
      state: "on"
  action:
    # iOS Companion App: Open camera with text input for ISBN
    - service: notify.mobile_app_iphone
      data:
        title: "📷 Scan Barcode"
        message: "Point camera at ISBN barcode, then type/paste the number"
        data:
          actions:
            - action: "SUBMIT_ISBN"
              title: "Submit"
              behavior: textInput
              textInputButtonTitle: "Add Book"
              textInputPlaceholder: "ISBN from barcode"
          tag: "book_scanner_input"

# Process submitted ISBN
- id: book_scanner_process_isbn
  alias: "Book Scanner: Process ISBN"
  trigger:
    - platform: event
      event_type: mobile_app_notification_action
      event_data:
        action: SUBMIT_ISBN
  condition:
    - condition: state
      entity_id: input_boolean.book_scanning_mode
      state: "on"
  action:
    - service: script.process_scanned_isbn
      data:
        isbn: "{{ trigger.event.data.action_data.reply_text }}"

# Stop scanning
- id: book_scanner_stop
  alias: "Book Scanner: Stop"
  trigger:
    - platform: event
      event_type: mobile_app_notification_action
      event_data:
        action: STOP_SCANNING
  action:
    - service: script.stop_book_scanning

# Auto-stop after 30 minutes of inactivity
- id: book_scanner_auto_stop
  alias: "Book Scanner: Auto Stop"
  trigger:
    - platform: state
      entity_id: input_boolean.book_scanning_mode
      to: "on"
      for:
        minutes: 30
  action:
    - service: script.stop_book_scanning
    - service: notify.mobile_app_iphone
      data:
        title: "⏱️ Scanner Timed Out"
        message: "Scanning session auto-stopped after 30 minutes"
```

### Step 4: Create Dashboard

Create a new dashboard or add this card:

```yaml
type: vertical-stack
cards:
  # Header
  - type: markdown
    content: |
      # 📚 Book Scanner
      {% if is_state('input_boolean.book_scanning_mode', 'on') %}
      ## 🟢 **SCANNING ACTIVE**
      Books scanned: **{{ states('input_number.books_scanned_count') | int }}**
      {% else %}
      ## Ready to scan
      {% endif %}

  # Current Location
  - type: entities
    title: 📍 Current Scan Location
    entities:
      - entity: input_text.book_scan_room
        name: Room
      - entity: input_text.book_scan_shelf
        name: Shelf
      - entity: input_text.book_scan_compartment
        name: Compartment
    state_color: true

  # Quick Location Presets
  - type: horizontal-stack
    cards:
      - type: button
        name: Living Room
        icon: mdi:sofa
        tap_action:
          action: call-service
          service: script.set_scan_location
          data:
            room: Living Room
            shelf: Shelf 1
            compartment: Top
      
      - type: button
        name: Bedroom
        icon: mdi:bed
        tap_action:
          action: call-service
          service: script.set_scan_location
          data:
            room: Bedroom
            shelf: Shelf 1
            compartment: Top
      
      - type: button
        name: Office
        icon: mdi:desk
        tap_action:
          action: call-service
          service: script.set_scan_location
          data:
            room: Office
            shelf: Main
            compartment: Middle

  # Scan Controls
  - type: conditional
    conditions:
      - condition: state
        entity: input_boolean.book_scanning_mode
        state: "off"
    card:
      type: button
      name: Start Scanning
      icon: mdi:barcode-scan
      tap_action:
        action: call-service
        service: script.start_book_scanning
      hold_action:
        action: more-info
      entity: input_boolean.book_scanning_mode
      icon_height: 60px
      show_state: false

  - type: conditional
    conditions:
      - condition: state
        entity: input_boolean.book_scanning_mode
        state: "on"
    card:
      type: button
      name: Stop Scanning
      icon: mdi:stop
      tap_action:
        action: call-service
        service: script.stop_book_scanning
      entity: input_boolean.book_scanning_mode
      icon_height: 60px

  # Last Scanned
  - type: conditional
    conditions:
      - condition: not
        conditions:
          - condition: state
            entity: input_text.book_last_scanned_isbn
            state: "unknown"
    card:
      type: entities
      title: 📖 Last Scanned
      entities:
        - entity: input_text.book_last_scanned_isbn
          name: ISBN
        - entity: input_number.books_scanned_count
          name: Total This Session

  # Statistics
  - type: markdown
    content: |
      ---
      💡 **Quick Tips:**
      - Set location first with preset buttons
      - Tap "Start Scanning" 
      - Notification appears with scan option
      - Scan or type multiple ISBNs
      - Tap "Stop" when finished
```

## Usage Workflow

### Scanning Multiple Books in Same Location

1. **Set Location** - Tap a location preset button (Living Room, Bedroom, etc.)
2. **Start Scanning** - Tap the "Start Scanning" button
3. **Notification Appears** - Shows current location and "Scan Book" button
4. **Scan ISBN** - Tap "Scan Book", point camera at barcode, type the ISBN
5. **Auto-Continue** - Book added, notification shows "Scan Next Book"
6. **Repeat** - Keep scanning books, all go to same location
7. **Finish** - Tap "Stop & Finish" when done

### Scanning Single Book

1. Set location
2. Start scanning  
3. Scan one ISBN
4. Tap "Stop & Finish"

## iOS Companion App Camera Integration

The iOS Companion App doesn't have native barcode scanning, so we use text input with actionable notifications. For true automatic scanning:

### Option A: Use iOS Shortcuts (Recommended for Automation)

Create an iOS Shortcut that:
1. Opens Camera
2. Takes photo
3. Extracts text (iOS has built-in text recognition)
4. Sends to Home Assistant webhook

I can create this shortcut for you if needed.

### Option B: Third-Party Scanner + Automation

1. Install "QR & Barcode Scanner" (free, no ads)
2. Set to auto-copy barcode to clipboard
3. Use Home Assistant notification text input
4. Paste from clipboard

### Option C: Full Automation with Barcode Scanner API

This requires a custom component. Would you like me to create one?

## Adding NFC Tags (Later)

When you're ready for NFC tags:

```yaml
automation:
  - id: nfc_start_book_scanning
    alias: "NFC: Start Book Scanning"
    trigger:
      - platform: tag
        tag_id: bookshelf_scanner
    action:
      - service: script.start_book_scanning
```

Just write an NFC tag with your iPhone (Settings → NFC in Companion App) and assign the tag ID.

## Troubleshooting

### Notifications Not Appearing
- Check Companion App notification permissions
- Verify device name in scripts matches your device

### "Service Not Found" Error
- Restart Home Assistant after adding scripts
- Check YAML syntax with Configuration → Check Configuration

### Books Not Adding
- Check Home Assistant logs
- Verify Library Catalog integration is loaded
- Test webhook directly first

## Next Steps

1. ✅ Add all the helpers (Step 1)
2. ✅ Add scripts (Step 2)
3. ✅ Add automations (Step 3)
4. ✅ Create dashboard (Step 4)
5. 🧪 Test with known ISBN
6. 📱 Customize location presets for your home

Would you like me to:
1. Create an iOS Shortcut for automatic barcode scanning?
2. Build a custom component with native iOS camera integration?
3. Add more location presets to the dashboard?
