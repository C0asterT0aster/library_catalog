# Home Assistant In-App Barcode Scanner

## What You Want

✅ Click button in Home Assistant dashboard  
✅ Camera opens **in Home Assistant app**  
✅ Scan barcode  
✅ Book automatically added  
✅ **Stay in Home Assistant app** - no Shortcuts app!

## Solution: Use HA Companion App Notifications

The Home Assistant Companion App can open the camera via actionable notifications with text input!

## Complete Setup

### Step 1: Input Helpers (Already Done!)

You already have these from previous steps:
- `input_text.book_scan_room`
- `input_text.book_scan_shelf`
- `input_text.book_scan_compartment`
- `input_boolean.book_scanning_active`
- `input_number.books_scanned_today`

### Step 2: Create Scripts

Add to `scripts.yaml`:

```yaml
start_book_scanning_in_app:
  alias: "Start Book Scanning (In-App)"
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
    
    # Send notification with text input
    - service: notify.mobile_app_YOUR_DEVICE
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
          persistent: true

stop_book_scanning_in_app:
  alias: "Stop Book Scanning (In-App)"
  icon: mdi:stop
  sequence:
    - service: input_boolean.turn_off
      target:
        entity_id: input_boolean.book_scanning_active
    
    - service: notify.mobile_app_YOUR_DEVICE
      data:
        title: "✅ Scanning Complete"
        message: "Added {{ states('input_number.books_scanned_today') | int }} books"
        data:
          tag: "book_scanner"
```

**IMPORTANT:** Replace `mobile_app_YOUR_DEVICE` with your device name!

### Step 3: Add Automation

Add to `automations.yaml` (or via UI without leading `-`):

```yaml
- id: handle_in_app_book_scan
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
    # Get the ISBN from notification input
    - variables:
        scanned_isbn: "{{ trigger.event.data.reply_text }}"
    
    # Add book to catalog
    - service: library_catalog.add_book
      data:
        isbn: "{{ scanned_isbn }}"
        location:
          room: "{{ states('input_text.book_scan_room') }}"
          shelf: "{{ states('input_text.book_scan_shelf') }}"
          compartment: "{{ states('input_text.book_scan_compartment') }}"
      continue_on_error: true
    
    # Increment counter
    - service: input_number.increment
      target:
        entity_id: input_number.books_scanned_today
    
    # Send success notification with option to scan next
    - service: notify.mobile_app_YOUR_DEVICE
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

- id: handle_stop_scanning_action
  alias: "Handle Stop Scanning Action"
  trigger:
    - platform: event
      event_type: mobile_app_notification_action
      event_data:
        action: STOP_SCANNING
  action:
    - service: script.stop_book_scanning_in_app
  mode: single
```

### Step 4: Create Dashboard

Add this card to your dashboard:

```yaml
type: vertical-stack
cards:
  # Header
  - type: markdown
    content: |
      # 📚 Book Scanner (In-App)
      {% if is_state('input_boolean.book_scanning_active', 'on') %}
      ## 🟢 **SCANNING ACTIVE**
      Books scanned: **{{ states('input_number.books_scanned_today') | int }}**
      {% else %}
      ## Ready to scan
      {% endif %}

  # Location Presets
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

  # Current Location
  - type: entities
    title: 📍 Current Location
    entities:
      - entity: input_text.book_scan_room
        name: Room
      - entity: input_text.book_scan_shelf
        name: Shelf
      - entity: input_text.book_scan_compartment
        name: Compartment

  # Main Button
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
        service: script.start_book_scanning_in_app
      icon_height: 80px
      entity: input_boolean.book_scanning_active

  # Stop Button
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
        service: script.stop_book_scanning_in_app
      icon_height: 80px

  # Stats
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

  # Instructions
  - type: markdown
    content: |
      ---
      ### 📖 How to Use:
      1. **Set location** (tap preset button)
      2. **Tap "Start Scanning"**
      3. **Notification appears** on iPhone
      4. **Tap "Scan ISBN"** in notification
      5. **Camera opens** in HA app
      6. **Point at barcode** - type the ISBN
      7. **Tap "Add Book"**
      8. **Repeat** for more books
      9. **Tap "Stop"** when done
```

## How It Works

### Your Workflow:

1. **In Home Assistant Dashboard:**
   - Tap "Living Room" button to set location
   - Tap "📷 Start Scanning" button

2. **Notification appears on iPhone:**
   - Shows current location
   - Has "📷 Scan ISBN" button

3. **Tap "Scan ISBN":**
   - Text input field appears
   - You can type or use iPhone camera to scan
   - iOS will recognize the barcode automatically if you point camera at it

4. **Type/Scan the ISBN:**
   - Enter the ISBN number
   - Tap "Add Book"

5. **Book is Added:**
   - Success notification appears
   - Shows "📷 Scan Next" button
   - Or "🛑 Stop" button

6. **Keep Scanning:**
   - Tap "Scan Next" to add more books
   - All go to the same location

7. **Finish:**
   - Tap "Stop" when done
   - See total count of books added

## iOS Camera Barcode Recognition

When you tap in the text input field in the notification:
1. Your keyboard appears
2. If you have iOS 15+, point your camera at a barcode
3. iOS automatically recognizes text/barcodes
4. Tap the recognized ISBN to paste it
5. Tap "Add Book"

This is **built into iOS** - no special app needed!

## Testing

### Step 1: Add Scripts and Automation
Copy the YAML above to Home Assistant

### Step 2: Restart Home Assistant
Settings → System → Restart

### Step 3: Add Dashboard Card
Create a new view or add to existing dashboard

### Step 4: Test!
1. Tap "Start Scanning" in dashboard
2. Check iPhone for notification
3. Tap "Scan ISBN"
4. Type test ISBN: `9780451524935`
5. Tap "Add Book"
6. Book should be added!

## Advantages of This Method

✅ **Everything in Home Assistant app**  
✅ **No Shortcuts app needed**  
✅ **Persistent notifications** - don't disappear  
✅ **iOS barcode recognition** built-in  
✅ **Simple workflow** - button → notification → camera  
✅ **Batch scanning** - keep adding books  
✅ **Real-time feedback** - see count update  

## Troubleshooting

### Notification doesn't appear
- Check device name in scripts matches your iPhone
- Check notification permissions for HA app
- Try: Settings → Notifications → Home Assistant → Allow Notifications

### "Scan ISBN" doesn't open camera
- It opens text input field
- Use iOS camera above keyboard to scan barcode
- Or manually type the ISBN

### Camera doesn't recognize barcode
- Make sure you have good lighting
- Hold steady for 1-2 seconds
- iOS 15+ required for auto-recognition
- Or just type the ISBN manually

### Book not added
- Check `input_boolean.book_scanning_active` is ON
- Check Library Catalog integration is loaded
- Check logs: Settings → System → Logs

## Next Steps

1. ✅ Copy scripts to `scripts.yaml`
2. ✅ Copy automation to automations.yaml (or create via UI)
3. ✅ Replace `mobile_app_YOUR_DEVICE` with your device name
4. ✅ Restart Home Assistant
5. ✅ Add dashboard card
6. ✅ Test with button!

This is **much simpler** than the iOS Shortcuts method and keeps everything in Home Assistant! 🎉
