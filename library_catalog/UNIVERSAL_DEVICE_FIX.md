# Universal Multi-Device Scanner Scripts

These scripts work with ANY device automatically - no device name needed!

## Problem with Device-Specific Notifications

The old method required `notify.mobile_app_YOUR_DEVICE` which had to be changed for each device.

## ✅ Solution: Use notify.notify (Universal)

Use `notify.notify` which sends to ALL devices, or create a notification group.

## Method 1: Universal Scripts (Send to All Devices)

Replace your scripts with these:

### scripts.yaml

```yaml
start_book_scanning:
  alias: "Start Book Scanning"
  icon: mdi:barcode-scan
  sequence:
    # Reset counter
    - service: input_number.set_value
      target:
        entity_id: input_number.books_scanned_today
      data:
        value: 0
    
    # Enable scanning mode
    - service: input_boolean.turn_on
      target:
        entity_id: input_boolean.book_scanning_active
    
    # Send notification to all mobile devices
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

## Method 2: Create Notification Group (Best for Multiple Devices)

### Step 1: Find Your Notification Services

1. Go to **Developer Tools** → **Services**
2. Start typing "notify."
3. You'll see all available notify services, for example:
   - `notify.notify` (all devices)
   - `notify.mobile_app_iphone_von_malte`
   - `notify.mobile_app_ipad`
   - etc.

### Step 2: Create Notification Group

Add to `configuration.yaml`:

```yaml
notify:
  - name: book_scanner_devices
    platform: group
    services:
      - service: mobile_app_iphone_von_malte
      - service: mobile_app_ipad
      # Add more devices here
```

### Step 3: Use the Group in Scripts

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
    
    # Use the notification group
    - service: notify.book_scanner_devices
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
    
    - service: notify.book_scanner_devices
      data:
        title: "✅ Scanning Complete"
        message: "Added {{ states('input_number.books_scanned_today') | int }} books"
        data:
          tag: "book_scanner"
```

## Update Automation Too

Your automation also needs the same change:

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
  # Changed to notify.notify
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

## Quick Fix Instructions

### Option A: Use notify.notify (Easiest - 2 minutes)

1. Open `scripts.yaml`
2. Replace ALL instances of `notify.mobile_app_YOUR_DEVICE` with `notify.notify`
3. Save
4. Go to **Developer Tools** → **YAML** → **Reload Scripts**
5. Edit your automation (Settings → Automations → Handle In-App Book Scan)
6. Replace `notify.mobile_app_YOUR_DEVICE` with `notify.notify`
7. Save
8. Test!

### Option B: Create Notification Group (Better for multiple devices - 5 minutes)

1. Add notification group to `configuration.yaml` (see above)
2. Restart Home Assistant
3. Update scripts to use `notify.book_scanner_devices`
4. Update automation to use `notify.book_scanner_devices`
5. Test!

## Why This is Better

✅ **Works with any device** - no hardcoded device names  
✅ **Supports multiple devices** - send to iPhone, iPad, etc.  
✅ **Easy to add new devices** - just add to the group  
✅ **No configuration needed** - `notify.notify` works immediately  

## Testing

After making changes:

1. Go to **Developer Tools** → **Services**
2. Service: `notify.notify`
3. Service data:
   ```yaml
   title: "Test"
   message: "This should appear on all your devices!"
   ```
4. Click **Call Service**
5. Check your iPhone - you should see the notification!

Then test the scanner:
1. Tap "Start Scanning" button
2. Notification should appear
3. Tap "Scan ISBN"
4. Enter test ISBN: `9780451524935`
5. Should work!

## Complete Updated Files

### scripts.yaml (Complete)

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

Just copy this entire file to replace your `scripts.yaml`!
