# iOS Automatic Barcode Scanner - Complete Setup

## The Perfect Solution for iOS + Home Assistant

This setup gives you **true automatic barcode scanning** - just point your camera at a book's ISBN and it automatically detects and adds it. No manual typing, no scan buttons!

## What You'll Get

✅ **One-Tap Start** - Button in Home Assistant dashboard
✅ **Automatic Detection** - Camera automatically recognizes barcodes
✅ **Batch Scanning** - Set location once, scan many books
✅ **Real-Time Feedback** - See each book added instantly
✅ **Pure iOS** - Uses iPhone's built-in camera and text recognition
✅ **No External Apps** - Just iOS Shortcuts (built into iOS)

## Architecture

We'll use:
1. **Home Assistant Dashboard** - Start button and location controls
2. **iOS Shortcut** - Automatic barcode detection using iPhone camera
3. **Webhook** - Sends ISBNs to Home Assistant automatically
4. **Automations** - Handles the workflow

## Part 1: Home Assistant Configuration

### Step 1: Add Input Helpers

Add to your `configuration.yaml`:

```yaml
input_text:
  book_scan_room:
    name: "Scan Location - Room"
    initial: "Living Room"
    icon: mdi:home
  
  book_scan_shelf:
    name: "Scan Location - Shelf"
    initial: "Shelf 1"
    icon: mdi:bookshelf
  
  book_scan_compartment:
    name: "Scan Location - Compartment"
    initial: "Top"
    icon: mdi:book-open-variant

input_boolean:
  book_scanning_active:
    name: "Book Scanning Active"
    initial: false
    icon: mdi:barcode-scan

input_number:
  books_scanned_today:
    name: "Books Scanned Today"
    min: 0
    max: 1000
    step: 1
    icon: mdi:counter

input_datetime:
  last_book_scan_time:
    name: "Last Book Scan Time"
    has_date: true
    has_time: true
```

Restart Home Assistant after adding these.

### Step 2: Add Automation to Process Scanned Books

Add to `automations.yaml`:

```yaml
# This automation triggers when the webhook receives a scanned ISBN
- id: process_scanned_book_from_ios
  alias: "Process Scanned Book from iOS"
  description: "Automatically add scanned books to catalog"
  trigger:
    - platform: webhook
      webhook_id: ios_book_scanner
      local_only: false
  condition:
    - condition: state
      entity_id: input_boolean.book_scanning_active
      state: "on"
  action:
    # Extract ISBN from webhook
    - variables:
        scanned_isbn: "{{ trigger.json.isbn }}"
    
    # Add book to catalog with current location
    - service: library_catalog.add_book
      data:
        isbn: "{{ scanned_isbn }}"
        location:
          room: "{{ states('input_text.book_scan_room') }}"
          shelf: "{{ states('input_text.book_scan_shelf') }}"
          compartment: "{{ states('input_text.book_scan_compartment') }}"
      continue_on_error: true
      response_variable: add_result
    
    # Increment counter
    - service: input_number.increment
      target:
        entity_id: input_number.books_scanned_today
    
    # Update timestamp
    - service: input_datetime.set_datetime
      target:
        entity_id: input_datetime.last_book_scan_time
      data:
        timestamp: "{{ now().timestamp() }}"
    
    # Send success notification to iPhone
    - service: notify.mobile_app_iphone
      data:
        title: "✅ Book Added"
        message: "ISBN {{ scanned_isbn }} added to {{ states('input_text.book_scan_room') }}"
        data:
          push:
            sound: "default"
          group: "book-scanner"

# Auto-disable scanning after 1 hour of inactivity
- id: auto_disable_book_scanning
  alias: "Auto-disable Book Scanning"
  trigger:
    - platform: state
      entity_id: input_boolean.book_scanning_active
      to: "on"
      for:
        hours: 1
  action:
    - service: input_boolean.turn_off
      target:
        entity_id: input_boolean.book_scanning_active
    - service: notify.mobile_app_iphone
      data:
        title: "📚 Scanning Session Ended"
        message: "Auto-stopped after 1 hour. Added {{ states('input_number.books_scanned_today') | int }} books today."

# Reset daily counter at midnight
- id: reset_daily_book_counter
  alias: "Reset Daily Book Counter"
  trigger:
    - platform: time
      at: "00:00:00"
  action:
    - service: input_number.set_value
      target:
        entity_id: input_number.books_scanned_today
      data:
        value: 0
```

**Important:** Replace `notify.mobile_app_iphone` with your actual device name from Settings → Devices & Services → Mobile App.

### Step 3: Create Scripts for Easy Control

Add to `scripts.yaml`:

```yaml
start_book_scanning:
  alias: "Start Book Scanning"
  icon: mdi:barcode-scan
  sequence:
    - service: input_boolean.turn_on
      target:
        entity_id: input_boolean.book_scanning_active
    
    - service: notify.mobile_app_iphone
      data:
        title: "📚 Scanner Ready"
        message: "Scanning to: {{ states('input_text.book_scan_room') }} > {{ states('input_text.book_scan_shelf') }}"
        data:
          actions:
            - action: "URI"
              title: "Open Scanner"
              uri: "shortcuts://run-shortcut?name=ScanBookISBN"
          group: "book-scanner"

stop_book_scanning:
  alias: "Stop Book Scanning"
  icon: mdi:stop
  sequence:
    - service: input_boolean.turn_off
      target:
        entity_id: input_boolean.book_scanning_active
    
    - service: notify.mobile_app_iphone
      data:
        title: "✅ Scanning Complete"
        message: "Added {{ states('input_number.books_scanned_today') | int }} books today"

quick_set_living_room:
  alias: "Set Location: Living Room"
  sequence:
    - service: input_text.set_value
      target:
        entity_id: input_text.book_scan_room
      data:
        value: "Living Room"
    - service: input_text.set_value
      target:
        entity_id: input_text.book_scan_shelf
      data:
        value: "Shelf 1"
    - service: input_text.set_value
      target:
        entity_id: input_text.book_scan_compartment
      data:
        value: "Top"

quick_set_bedroom:
  alias: "Set Location: Bedroom"
  sequence:
    - service: input_text.set_value
      target:
        entity_id: input_text.book_scan_room
      data:
        value: "Bedroom"
    - service: input_text.set_value
      target:
        entity_id: input_text.book_scan_shelf
      data:
        value: "Main"
    - service: input_text.set_value
      target:
        entity_id: input_text.book_scan_compartment
      data:
        value: "Middle"

quick_set_office:
  alias: "Set Location: Office"
  sequence:
    - service: input_text.set_value
      target:
        entity_id: input_text.book_scan_room
      data:
        value: "Office"
    - service: input_text.set_value
      target:
        entity_id: input_text.book_scan_shelf
      data:
        value: "Desk Shelf"
    - service: input_text.set_value
      target:
        entity_id: input_text.book_scan_compartment
      data:
        value: "Top"
```

### Step 4: Create Dashboard

Add this card to your dashboard (or create a new view):

```yaml
type: vertical-stack
cards:
  # Header with Status
  - type: markdown
    content: |
      # 📚 Book Scanner
      {% if is_state('input_boolean.book_scanning_active', 'on') %}
      ## 🟢 SCANNING ACTIVE
      **{{ states('input_number.books_scanned_today') | int }}** books scanned today
      {% else %}
      ## ⚪ Ready
      **{{ states('input_number.books_scanned_today') | int }}** books scanned today
      {% endif %}

  # Location Preset Buttons
  - type: horizontal-stack
    cards:
      - type: button
        name: Living Room
        icon: mdi:sofa
        tap_action:
          action: call-service
          service: script.quick_set_living_room
        hold_action:
          action: none
      
      - type: button
        name: Bedroom
        icon: mdi:bed
        tap_action:
          action: call-service
          service: script.quick_set_bedroom
      
      - type: button
        name: Office
        icon: mdi:desk
        tap_action:
          action: call-service
          service: script.quick_set_office

  # Current Location Display
  - type: entities
    title: 📍 Current Location
    show_header_toggle: false
    entities:
      - entity: input_text.book_scan_room
        name: Room
      - entity: input_text.book_scan_shelf
        name: Shelf
      - entity: input_text.book_scan_compartment
        name: Compartment

  # Main Scan Button
  - type: conditional
    conditions:
      - condition: state
        entity: input_boolean.book_scanning_active
        state: "off"
    card:
      type: button
      name: 📷 Start Scanning
      icon: mdi:barcode-scan
      tap_action:
        action: call-service
        service: script.start_book_scanning
      entity: input_boolean.book_scanning_active
      show_state: false
      icon_height: 80px

  # Stop Button (when scanning)
  - type: conditional
    conditions:
      - condition: state
        entity: input_boolean.book_scanning_active
        state: "on"
    card:
      type: button
      name: 🛑 Stop Scanning
      icon: mdi:stop-circle
      tap_action:
        action: call-service
        service: script.stop_book_scanning
      entity: input_boolean.book_scanning_active
      icon_height: 80px

  # Statistics
  - type: conditional
    conditions:
      - condition: numeric_state
        entity: input_number.books_scanned_today
        above: 0
    card:
      type: entities
      title: 📊 Today's Stats
      entities:
        - entity: input_number.books_scanned_today
          name: Books Added
        - entity: input_datetime.last_book_scan_time
          name: Last Scan

  # Instructions
  - type: markdown
    content: |
      ---
      ### 📖 How to Use:
      1. **Tap location preset** (Living Room, Bedroom, etc.)
      2. **Tap "Start Scanning"**
      3. **Tap "Open Scanner"** in notification
      4. **Point camera at ISBN** - auto-detects!
      5. **Keep scanning** - all books go to same location
      6. **Tap "Stop"** when done
```

## Part 2: iOS Shortcut Setup

### Step 5: Get Your Webhook URL

Your webhook URL will be:
```
https://your-home-assistant-url/api/webhook/ios_book_scanner
```

Or if using Nabu Casa:
```
https://your-instance.ui.nabu.casa/api/webhook/ios_book_scanner
```

### Step 6: Create the iOS Shortcut

1. **Open Shortcuts app** on your iPhone
2. **Tap "+" to create new shortcut**
3. **Name it**: "ScanBookISBN"
4. **Add these actions**:

```
Action 1: "Scan QR Code or Barcode"
   - (This opens camera automatically)
   - (Recognizes barcodes automatically - no button press!)

Action 2: "Set Variable"
   - Variable Name: ScannedCode
   - Value: [Scan QR Code or Barcode output]

Action 3: "Text"
   - Text: [ScannedCode]

Action 4: "Set Variable"
   - Variable Name: CleanISBN
   - Value: [Text output]

Action 5: "Get Contents of URL"
   - URL: https://YOUR-HA-URL/api/webhook/ios_book_scanner
   - Method: POST
   - Headers:
       Content-Type: application/json
   - Request Body: JSON
   - JSON: {"isbn": "[CleanISBN]"}

Action 6: "Show Notification"
   - Title: "Book Scanned"
   - Body: "ISBN sent to Home Assistant"

Action 7: "Wait"
   - 2 seconds

Action 8: "Run Shortcut"
   - Shortcut: ScanBookISBN
   - (This loops back to scan next book automatically!)
```

**Visual Guide for Creating the Shortcut:**

```
┌─────────────────────────────┐
│ Scan QR Code or Barcode     │  ← Opens camera, auto-detects
├─────────────────────────────┤
│ Set Variable                │  ← Stores scanned code
│   ScannedCode               │
├─────────────────────────────┤
│ Text                        │  ← Converts to text
│   [ScannedCode]             │
├─────────────────────────────┤
│ Set Variable                │  ← Cleans the ISBN
│   CleanISBN                 │
├─────────────────────────────┤
│ Get Contents of URL         │  ← Sends to Home Assistant
│   POST to webhook           │
│   {"isbn": "[CleanISBN]"}   │
├─────────────────────────────┤
│ Show Notification           │  ← Confirms scan
│   "Book Scanned"            │
├─────────────────────────────┤
│ Wait 2 seconds              │  ← Brief pause
├─────────────────────────────┤
│ Run Shortcut                │  ← Loops to scan next!
│   ScanBookISBN              │
└─────────────────────────────┘
```

### Detailed Shortcut Steps with Screenshots Equivalent:

**Step 6.1**: Add "Scan QR Code or Barcode"
- Search for "Scan" in actions
- Select "Scan QR Code or Barcode"
- This will automatically open your camera

**Step 6.2**: Add "Set Variable"  
- Name: `ScannedCode`
- Value: Tap and select "QR Code or Barcode" from previous action

**Step 6.3**: Add "Text"
- Tap the text field
- Select "ScannedCode" variable

**Step 6.4**: Add another "Set Variable"
- Name: `CleanISBN`  
- Value: Select "Text" from previous action

**Step 6.5**: Add "Get Contents of URL"
- URL: `https://YOUR-HA-URL/api/webhook/ios_book_scanner`
- Method: **POST**
- Request Body: **JSON**
- Tap "Add new field" → Headers
  - Key: `Content-Type`
  - Value: `application/json`
- JSON field: `{"isbn": ""}` then tap inside quotes and insert CleanISBN variable

**Step 6.6**: Add "Show Notification"
- Title: `Book Scanned`
- Body: `ISBN [CleanISBN] sent!`

**Step 6.7**: Add "Wait"
- 2 seconds

**Step 6.8**: Add "Run Shortcut"
- Select "ScanBookISBN" (this same shortcut)
- This creates the auto-loop!

### Alternative: Simplified Shortcut (If Loop Doesn't Work)

If iOS complains about the loop, create this simpler version:

```
1. Scan QR Code or Barcode
2. Set Variable: ISBN
3. Get Contents of URL (POST to webhook with ISBN)
4. Show Notification: "Scan sent! Run again for next book"
```

Then you manually run the shortcut again for each book (still faster than typing!).

## Part 3: Usage Workflow

### Your Complete Workflow:

1. **In Home Assistant**:
   - Tap "Living Room" (or your location preset)
   - Tap "Start Scanning" button
   - Notification appears with "Open Scanner" button

2. **On iPhone**:
   - Tap "Open Scanner" in notification
   - **Camera opens automatically**
   - **Point at ISBN barcode on book**
   - **Barcode detected automatically** (no button press!)
   - **Book automatically added to Home Assistant**
   - **Camera reopens** for next book
   - Keep scanning books - they all go to the same location

3. **When Finished**:
   - Close the camera
   - Go back to Home Assistant
   - Tap "Stop Scanning"
   - See how many books you added!

## Troubleshooting

### Shortcut Not Opening
- Make sure the shortcut is named exactly "ScanBookISBN"
- Check the URI in the notification: `shortcuts://run-shortcut?name=ScanBookISBN`

### Books Not Adding
- Check Home Assistant logs
- Test webhook directly with curl:
  ```bash
  curl -X POST https://your-ha-url/api/webhook/ios_book_scanner \
    -H "Content-Type: application/json" \
    -d '{"isbn":"9780451524935"}'
  ```

### Camera Not Auto-Detecting
- Make sure you use "Scan QR Code or Barcode" action, not "Take Photo"
- Point steadily at barcode for 1-2 seconds
- Ensure good lighting

### Loop Not Working
- Some iOS versions limit recursive shortcuts
- Use the simplified version instead
- Or add to Home Screen and manually tap between scans

## Advanced: Add NFC Tag

Want to start scanning by tapping an NFC tag on your bookshelf?

1. **Write NFC tag** in Home Assistant Companion App
2. **Add this automation**:

```yaml
- id: nfc_start_book_scanning
  alias: "NFC: Start Book Scanning"
  trigger:
    - platform: tag
      tag_id: YOUR_TAG_ID
  action:
    - service: script.start_book_scanning
```

Now: **Tap NFC tag → Notification → Tap "Open Scanner" → Start scanning!**

## Tips for Best Results

✅ **Good Lighting** - Scan in well-lit areas
✅ **Steady Hand** - Hold still for 1-2 seconds  
✅ **Clean Barcodes** - Wipe dust off book covers
✅ **Right Distance** - About 10-15cm from barcode
✅ **Batch by Location** - Do one shelf at a time

## What You've Achieved

🎉 **One tap** to start scanning
🎉 **Automatic barcode detection** - no scan button
🎉 **Continuous scanning** - automatically loops
🎉 **Batch processing** - one location, many books
🎉 **Real-time feedback** - see each book added
🎉 **Pure iOS** - no third-party apps needed

---

**Ready to test?** 

1. Copy all the YAML to your Home Assistant
2. Restart Home Assistant
3. Create the iOS Shortcut
4. Test with ISBN: `9780451524935`

Let me know if you need help with any step!
