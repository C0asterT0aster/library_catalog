# Library Catalog - Setup Guide

> **⚠️ IMPORTANT: Camera Scanning Not Available Yet**
> 
> This guide sets up a **manual ISBN entry system** via mobile notifications.
> **Camera/barcode scanning from notifications is not yet possible** due to iOS and Android limitations.
> 
> **What Works:**
> - ✅ Dashboard button to start scanning
> - ✅ Notification appears on phone
> - ✅ Text input field for ISBN
> - ✅ Manual ISBN entry (type the number)
> - ✅ Book automatically added to catalog
> 
> **What Doesn't Work:**
> - ❌ Camera doesn't open from notification
> - ❌ No barcode auto-recognition in text field
> 
> **Workaround:** Manually type the ISBN from the book (13 digits, no dashes).
> 
> See CAMERA_LIMITATIONS.md for technical details and future solutions.

---

## What You're Building

A complete in-app barcode scanner for your Home Assistant that lets you:
- Click a button in Home Assistant dashboard
- Scan book barcodes directly in the Home Assistant app
- Automatically add books to your catalog
- All without leaving Home Assistant!

## Prerequisites

✅ Home Assistant installed and running  
✅ Library Catalog integration installed via HACS  
✅ Home Assistant Companion App on iPhone  
✅ 15 minutes of time  

## Step 1: Create Input Helpers (5 minutes)

These store your scanning state and location.

### Via Configuration File (Recommended)

1. Open Home Assistant
2. Go to **Settings** → **Add-ons** → **File editor** (install if needed)
3. Open `configuration.yaml`
4. Add this at the bottom:

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

5. **Save** the file
6. Go to **Settings** → **System** → **Check Configuration**
7. If OK, click **Restart**
8. Wait 2 minutes for restart

### Verify Helpers Were Created

After restart:
1. Go to **Settings** → **Devices & Services** → **Helpers**
2. You should see:
   - ✅ Scan Location - Room
   - ✅ Scan Location - Shelf
   - ✅ Scan Location - Compartment
   - ✅ Book Scanning Active
   - ✅ Books Scanned Today
   - ✅ Last Book Scan Time

## Step 2: Find Your Notification Service (1 minute)

You need to know which notification service to use.

### Option A: Use notify.notify (Easiest - Works for Everyone)

Use `notify.notify` which sends to **all mobile devices** automatically.

**Skip to Step 3 and use `notify.notify` instead of `mobile_app_YOUR_DEVICE`!**

### Option B: Find Your Specific Device (If you want device-specific)

1. Go to **Developer Tools** → **Services**
2. Start typing "notify."
3. You'll see services like:
   - `notify.notify` ← Use this one!
   - `notify.mobile_app_iphone_von_malte` ← Or this for specific device
4. Note the exact name

**Recommendation:** Use `notify.notify` - it's universal and works with multiple devices!

## Step 3: Add Scripts (3 minutes)

Scripts control the scanning workflow.

1. In File editor, open or create `scripts.yaml`
2. Add this code:

```yaml
start_book_scanning:
  alias: "Start Book Scanning"
  icon: mdi:barcode-scan
  sequence:
    - service: input_number.set_value
      target:
        entity_id: input_number.books_scanned_today
      data:
        value: 0
    
    - service: input_boolean.turn_on
      target:
        entity_id: input_boolean.book_scanning_active
    
    - service: notify.notify
      data:
        title: "📚 Book Scanner Ready"
        message: "Location: {{ states('input_text.book_scan_room') }} > {{ states('input_text.book_scan_shelf') }}"
        data:
          actions:
            - action: "SCAN_BOOK_ISBN"
              title: "📷 Scan ISBN"
              behavior: "textInput"
              textInputButtonTitle: "Add Book"
              textInputPlaceholder: "Scan or type ISBN"
          tag: "book_scanner"
          group: "book_scanner"

stop_book_scanning:
  alias: "Stop Book Scanning"
  icon: mdi:stop
  sequence:
    - service: input_boolean.turn_off
      target:
        entity_id: input_boolean.book_scanning_active
    
    - service: notify.notify
      data:
        title: "✅ Scanning Complete"
        message: "Added {{ states('input_number.books_scanned_today') | int }} books"
        data:
          tag: "book_scanner"
```

3. **IMPORTANT:** No device name needed - `notify.notify` works for all devices!

4. **Save** the file
5. Go to **Developer Tools** → **YAML** → **Reload Scripts**

## Step 4: Add Automation (3 minutes)

### Method A: Via UI (Easier)

1. Go to **Settings** → **Automations & Scenes**
2. Click **Create Automation** → **Create new automation**
3. Click **⋮** (three dots) → **Edit in YAML**
4. **Delete everything**
5. Paste this code (**WITHOUT leading dash**):

```yaml
id: handle_in_app_book_scan
alias: "Handle In-App Book Scan"
description: "Process ISBN from actionable notification"
trigger:
  - platform: event
    event_type: mobile_app_notification_action
    event_data:
      action: SCAN_BOOK_ISBN
condition:
  - condition: state
    entity_id: input_boolean.book_scanning_active
    state: "on"
action:
  - variables:
      scanned_isbn: "{{ trigger.event.data.reply_text }}"
  - service: library_catalog.add_book
    data:
      isbn: "{{ scanned_isbn }}"
      location:
        room: "{{ states('input_text.book_scan_room') }}"
        shelf: "{{ states('input_text.book_scan_shelf') }}"
        compartment: "{{ states('input_text.book_scan_compartment') }}"
    continue_on_error: true
  - service: input_number.increment
    target:
      entity_id: input_number.books_scanned_today
  - service: input_datetime.set_datetime
    target:
      entity_id: input_datetime.last_book_scan_time
    data:
      timestamp: "{{ now().timestamp() }}"
  - service: notify.notify
    data:
      title: "✅ Book Added!"
      message: "ISBN: {{ scanned_isbn }} | Total: {{ states('input_number.books_scanned_today') | int }}"
      data:
        actions:
          - action: "SCAN_BOOK_ISBN"
            title: "📷 Scan Next"
            behavior: "textInput"
            textInputButtonTitle: "Add Book"
            textInputPlaceholder: "Scan or type ISBN"
          - action: "STOP_SCANNING"
            title: "🛑 Stop"
        tag: "book_scanner_result"
        group: "book_scanner"
mode: single
```

6. **IMPORTANT:** No device name needed - `notify.notify` sends to all devices!
7. Click **Save**

### Add Second Automation (Stop Button)

Repeat the same process with this code:

```yaml
id: handle_stop_scanning_action
alias: "Handle Stop Scanning"
trigger:
  - platform: event
    event_type: mobile_app_notification_action
    event_data:
      action: STOP_SCANNING
action:
  - service: script.stop_book_scanning
mode: single
```

## Step 5: Create Dashboard (2 minutes)

1. Go to **Overview** (your main dashboard)
2. Click **⋮** (three dots) → **Edit Dashboard**
3. Click **+ Add Card**
4. Choose **Manual** card type
5. Paste this:

```yaml
type: vertical-stack
cards:
  - type: markdown
    content: |
      # 📚 Book Scanner
      {% if is_state('input_boolean.book_scanning_active', 'on') %}
      ## 🟢 **SCANNING ACTIVE**
      Books scanned: **{{ states('input_number.books_scanned_today') | int }}**
      {% else %}
      ## Ready to scan
      {% endif %}

  - type: horizontal-stack
    cards:
      - type: button
        name: Living Room
        icon: mdi:sofa
        tap_action:
          action: call-service
          service: input_text.set_value
          service_data:
            entity_id: input_text.book_scan_room
            value: Living Room
      
      - type: button
        name: Bedroom
        icon: mdi:bed
        tap_action:
          action: call-service
          service: input_text.set_value
          service_data:
            entity_id: input_text.book_scan_room
            value: Bedroom
      
      - type: button
        name: Office
        icon: mdi:desk
        tap_action:
          action: call-service
          service: input_text.set_value
          service_data:
            entity_id: input_text.book_scan_room
            value: Office

  - type: entities
    title: 📍 Current Location
    entities:
      - entity: input_text.book_scan_room
        name: Room
      - entity: input_text.book_scan_shelf
        name: Shelf
      - entity: input_text.book_scan_compartment
        name: Compartment

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
      icon_height: 80px

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
      icon_height: 80px

  - type: conditional
    conditions:
      - condition: numeric_state
        entity: input_number.books_scanned_today
        above: 0
    card:
      type: entities
      title: 📊 Today
      entities:
        - entity: input_number.books_scanned_today
          name: Books Added

  - type: markdown
    content: |
      ---
      ### 📖 How to Use:
      1. Tap location button (Living Room, etc.)
      2. Tap "Start Scanning"
      3. Notification appears on iPhone
      4. Tap "Scan ISBN" in notification
      5. Point camera at barcode - iOS recognizes it
      6. Tap recognized ISBN to paste
      7. Tap "Add Book"
      8. Repeat or tap "Stop"
```

6. Click **Save**

## Step 6: Test! (2 minutes)

Now test your scanner!

### Test Workflow:

1. **In Home Assistant dashboard:**
   - Tap **Living Room** button (sets location)
   - Tap **📷 Start Scanning** button

2. **Check your iPhone:**
   - You should see a notification: "📚 Book Scanner Ready"
   - It shows your location: "Living Room > Shelf 1"
   - Has a button: "📷 Scan ISBN"

3. **Tap "Scan ISBN":**
   - Text input field appears
   - Type this test ISBN: `9780451524935`
   - Tap "Add Book"

4. **Check iPhone again:**
   - New notification: "✅ Book Added!"
   - Shows ISBN and count
   - Has buttons: "📷 Scan Next" and "🛑 Stop"

5. **Verify book was added:**
   - Go to **Developer Tools** → **Services**
   - Service: `library_catalog.search`
   - Service data: `{"query": "1984", "search_by": "title"}`
   - Click **Call Service**
   - You should see the book "1984" by George Orwell!

6. **Stop scanning:**
   - Tap "🛑 Stop" in notification
   - Or tap **Stop Scanning** button in dashboard

## How to Scan Real Books

**Current Method (Manual Entry):**

1. Start scanning (tap button in dashboard)
2. Notification appears on your phone
3. Tap "Scan ISBN" in notification
4. Text field appears
5. **Look at book spine or back cover**
6. **Find the barcode** (usually labeled ISBN with 13 digits)
7. **Type the 13-digit number** (example: 9780451524935)
8. Ignore dashes if present (978-0-451-52493-5 → 9780451524935)
9. Tap "Add Book"
10. Book is added automatically!
11. Notification shows "Scan Next" - repeat for more books

**Tips for Faster Entry:**
- Use good lighting to read the ISBN clearly
- ISBNs are usually on back cover bottom or book spine
- Type only numbers, skip dashes
- Most modern books have 13-digit ISBN (starts with 978 or 979)
- If wrong ISBN, book won't be found - try again

**Alternative: Use a Computer**
- Open Home Assistant on desktop/laptop
- Use Developer Tools → Services → library_catalog.add_book
- Much faster to type with keyboard!

**Future:** Camera scanning will be added when technical limitations are resolved.

## Troubleshooting

### No notification appears
- Check notification settings: iPhone Settings → Notifications → Home Assistant → Allow
- Check device name is correct in scripts
- Restart Home Assistant app

### "Service not found" error
- Library Catalog integration not installed
- Go to Settings → Devices & Services → Add Integration → Library Catalog

### Camera doesn't recognize barcode
- Need iOS 15 or later for auto-recognition
- Make sure barcode is clear and well-lit
- Or just type the ISBN manually

### Book not added
- Check `input_boolean.book_scanning_active` is ON
- Check logs: Settings → System → Logs (search "library_catalog")
- Test manually via Developer Tools → Services

## What You Built

✅ Dashboard with location presets  
✅ One-tap scanning button  
✅ Notifications with text input  
✅ Automatic book addition  
✅ Batch scanning (multiple books, same location)  
✅ Real-time counter  
✅ All in Home Assistant app!  

## Next Steps

- Customize location presets for your home
- Add more room/shelf options
- Create automations (e.g., notify when library reaches 100 books)
- Explore the search feature

## Need Help?

- Check WEBHOOK.md for webhook details
- Check DEVELOPMENT.md for integration architecture
- Check GitHub issues: https://github.com/C0asterT0aster/library_catalog/issues

---

**Enjoy building your digital library! 📚**
