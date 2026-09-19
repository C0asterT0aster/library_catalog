# Quick Start Guide: Barcode Scanner Setup

## Testing the Webhook

### 1. Find Your Home Assistant URL

First, determine your Home Assistant URL:
- **Local network**: `http://homeassistant.local:8123` or `http://192.168.x.x:8123`
- **Nabu Casa**: `https://your-instance.ui.nabu.casa`
- **Custom domain**: Your configured URL

### 2. Test with curl (From Computer)

Open a terminal and run:

```bash
# Replace with your Home Assistant URL
curl -X POST http://homeassistant.local:8123/api/webhook/library_catalog_scanner \
  -H "Content-Type: application/json" \
  -d '{"isbn":"9780451524935"}'
```

You should see a JSON response with book information.

## Mobile Scanner Apps

### Android: Binary Eye (Recommended)

**Why Binary Eye?**
- Free and open source
- No ads or tracking
- Supports custom HTTP actions
- Available on F-Droid and Google Play

**Setup Steps:**

1. **Install Binary Eye**
   - From F-Droid: https://f-droid.org/packages/de.markusfisch.android.binaryeye/
   - Or Google Play Store: Search "Binary Eye"

2. **Configure Custom Action**
   - Open Binary Eye
   - Tap the three dots (⋮) → Settings
   - Scroll down to "Custom action"
   - Enable "Custom action"
   - Configure:
     - **URL Template**: `http://YOUR_HA_IP:8123/api/webhook/library_catalog_scanner`
     - **POST data**: `{"isbn":"BARCODE"}`
     - Enable **"Send as POST"**
     - Add header: `Content-Type: application/json`

3. **Scan a Book**
   - Open Binary Eye
   - Point camera at ISBN barcode
   - After scan, tap "Custom Action" button
   - Binary Eye will send the ISBN to Home Assistant

**Example Configuration:**
```
URL: http://YOUR_HA_IP:8123/api/webhook/library_catalog_scanner
POST data: {"isbn":"BARCODE"}
☑ Send as POST
Headers:
  Content-Type: application/json
```

### Android: QR & Barcode Scanner (Alternative)

1. Install "QR & Barcode Scanner" by Gamma Play
2. Go to Settings → Actions
3. Add Web Action:
   - URL: `http://YOUR_HA_IP:8123/api/webhook/library_catalog_scanner`
   - Method: POST
   - Body: `{"isbn":"%s"}`

### iOS: Barcode Scanner + Shortcuts

**Option 1: Using HTTP Shortcuts (Free)**

1. Install "HTTP Shortcuts" from App Store
2. Create new shortcut:
   - Method: POST
   - URL: `http://YOUR_HA_IP:8123/api/webhook/library_catalog_scanner`
   - Body: `{"isbn":"[SCAN_RESULT]"}`
   - Content-Type: application/json

**Option 2: Using Barcodescanner (Paid but better UX)**

1. Install "Barcodescanner" from App Store
2. Settings → Webhook Configuration
3. Set:
   - URL: `http://YOUR_HA_IP:8123/api/webhook/library_catalog_scanner`
   - Method: POST
   - Body: `{"isbn":"{{barcode}}"}`

## Home Assistant Voice Assistant Integration

### Voice Command: "Scan Book"

You want to say "scan" and have Home Assistant automatically open the camera? Here's how:

### Solution 1: Home Assistant Companion App Script

Create a script that your voice assistant can trigger:

```yaml
# configuration.yaml or scripts.yaml
script:
  scan_book_barcode:
    alias: "Scan Book Barcode"
    sequence:
      - service: notify.mobile_app_your_phone
        data:
          message: "Open camera to scan book ISBN"
          data:
            actions:
              - action: "URI"
                title: "Open Scanner"
                uri: "app://de.markusfisch.android.binaryeye"  # Android Binary Eye
                # For iOS with HTTP Shortcuts:
                # uri: "shortcuts://run-shortcut?name=ScanBook"
```

Then add an assist action:

```yaml
# configuration.yaml
assist_pipeline:
  actions:
    - name: "scan book"
      phrase: "scan a book"
      action:
        service: script.scan_book_barcode
```

### Solution 2: Full Automation with Camera Entity

If you have a camera entity (like ESP32-CAM), you can automate the entire flow:

```yaml
automation:
  - id: voice_scan_book
    alias: "Voice: Scan Book with Camera"
    trigger:
      - platform: conversation
        command: "scan a book"
    action:
      # Take snapshot from camera
      - service: camera.snapshot
        target:
          entity_id: camera.your_esp32_cam
        data:
          filename: /config/www/scans/latest_scan.jpg
      
      # Send to image processing (requires custom component or Node-RED)
      - service: notify.persistent_notification
        data:
          title: "Book Scan"
          message: "Processing barcode scan..."

      # This would require a custom integration or Node-RED to:
      # 1. Process the image with ZXing or similar
      # 2. Extract ISBN
      # 3. Call the webhook
```

### Solution 3: NFC Tag Trigger (Easiest!)

Place an NFC tag on your bookshelf:

```yaml
automation:
  - id: nfc_scan_books
    alias: "NFC: Scan Books"
    trigger:
      - platform: tag
        tag_id: bookshelf_scanner  # Your NFC tag ID
    action:
      - service: notify.mobile_app_your_phone
        data:
          message: "Ready to scan books"
          data:
            actions:
              - action: "URI"
                title: "Open Scanner"
                uri: "app://de.markusfisch.android.binaryeye"
```

**How to use:**
1. Add NFC tag to Home Assistant (Companion App → Tags)
2. Tap NFC tag with phone
3. Notification appears with "Open Scanner" button
4. Tap button → Binary Eye opens automatically

## Fully Automatic Workflow (Advanced)

For a truly automatic "scan and store" workflow, you need to handle the location assignment. Here's a complete solution:

### Step 1: Create Input Helpers for Default Location

```yaml
# configuration.yaml
input_text:
  book_scan_room:
    name: "Default Scan Room"
    initial: "Living Room"
  
  book_scan_shelf:
    name: "Default Scan Shelf"
    initial: "Shelf 1"
  
  book_scan_compartment:
    name: "Default Scan Compartment"
    initial: "Top"
```

### Step 2: Automation to Auto-Store Scanned Books

```yaml
automation:
  - id: auto_store_scanned_book
    alias: "Auto-store Scanned Books"
    trigger:
      - platform: event
        event_type: library_catalog_barcode_scanned
        event_data:
          exists: false  # Only for new books
    action:
      # Store the book with default location
      - service: library_catalog.add_book
        data:
          isbn: "{{ trigger.event.data.isbn }}"
          location:
            room: "{{ states('input_text.book_scan_room') }}"
            shelf: "{{ states('input_text.book_scan_shelf') }}"
            compartment: "{{ states('input_text.book_scan_compartment') }}"
      
      # Notify success
      - service: notify.mobile_app_your_phone
        data:
          title: "Book Added!"
          message: "{{ trigger.event.data.title }} added to {{ states('input_text.book_scan_room') }}"
          data:
            notification_icon: mdi:book-plus
```

### Step 3: Voice Control for Location

```yaml
script:
  set_scan_location:
    alias: "Set Book Scan Location"
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
      - service: notify.mobile_app_your_phone
        data:
          message: "Scan location set to {{ room }} > {{ shelf }} > {{ compartment }}"
```

Now you can say: "Set scan location to bedroom shelf 2 top"

### Complete Workflow:

1. **Say**: "Set scan location to Living Room Shelf 1 Top"
2. **Tap NFC tag** on bookshelf (or say "scan book")
3. **Binary Eye opens** automatically
4. **Scan ISBN** barcode on book
5. **Book is automatically added** to your catalog
6. **Get notification** confirming addition

## Dashboard Card for Quick Access

Add this to your dashboard:

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Book Scanner
    entities:
      - input_text.book_scan_room
      - input_text.book_scan_shelf
      - input_text.book_scan_compartment
  
  - type: button
    name: Open Scanner
    icon: mdi:barcode-scan
    tap_action:
      action: call-service
      service: notify.mobile_app_your_phone
      data:
        message: command_activity
        data:
          intent_package_name: de.markusfisch.android.binaryeye
          intent_action: android.intent.action.MAIN
```

## Troubleshooting

### "Connection Failed" in Scanner App
- Make sure you're on the same network as Home Assistant
- Use IP address instead of homeassistant.local
- Check firewall settings

### Webhook Not Responding
```bash
# Test from your phone's browser
# Visit this URL and check for errors:
http://YOUR_HA_IP:8123/api/webhook/library_catalog_scanner
```

### Check Home Assistant Logs
Settings → System → Logs
Search for "library_catalog" or "webhook"

## Next Steps

1. Install Binary Eye on Android (or HTTP Shortcuts on iOS)
2. Configure the webhook URL
3. Scan a test ISBN: `9780451524935` (1984 by George Orwell)
4. Check Home Assistant Developer Tools → Events (listen for `library_catalog_barcode_scanned`)
5. Set up automation to auto-store books
6. Add NFC tag for quick access

Would you like me to help you set up any of these automations?
