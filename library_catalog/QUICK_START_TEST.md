# Quick Start Test Guide - iOS Book Scanner

## 🚀 Fast Setup (15 Minutes)

Follow these steps to test your book scanner right now.

## Step 1: Add Configuration to Home Assistant (5 minutes)

### 1.1 Open Configuration File

1. Go to Home Assistant
2. Click **Settings** → **Add-ons**
3. Install **File Editor** or **Studio Code Server** if you don't have it
4. Or use SSH/SFTP to edit files

### 1.2 Add Input Helpers

Open your `configuration.yaml` and add this at the bottom:

```yaml
# Book Scanner Configuration
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

### 1.3 Save and Restart

1. **Save** the file
2. Go to **Settings** → **System** → **Restart** 
3. Click **Check Configuration** first to verify no errors
4. Then **Restart Home Assistant**
5. Wait 1-2 minutes for restart

## Step 2: Verify Helpers Created (1 minute)

After restart:

1. Go to **Settings** → **Devices & Services** → **Helpers**
2. You should see:
   - "Scan Location - Room"
   - "Scan Location - Shelf"
   - "Scan Location - Compartment"
   - "Book Scanning Active"
   - "Books Scanned Today"
   - "Last Book Scan Time"

✅ If you see all of these, continue to Step 3!

## Step 3: Find Your Device Name (1 minute)

You need your exact device name for notifications:

1. Go to **Settings** → **Devices & Services**
2. Click on **Mobile App**
3. Find your iPhone in the list
4. Click on it
5. Look at the top - you'll see something like:
   - `mobile_app_iphone`
   - `mobile_app_your_phone`
   - `mobile_app_johns_iphone`

📝 **Write this down** - you'll need it in Step 4!

## Step 4: Add Automation (3 minutes)

### 4.1 Open Automations File

Option A: **Via UI (Easier)**
1. Go to **Settings** → **Automations & Scenes**
2. Click **Create Automation** → **Create new automation**
3. Click the **⋮** (three dots) top right
4. Click **Edit in YAML**

Option B: **Via File Editor**
1. Open `automations.yaml` in File Editor
2. Go to the end of the file

### 4.2 Copy This Automation

**Replace `mobile_app_iphone` with YOUR device name from Step 3!**

```yaml
- id: process_scanned_book_from_ios_test
  alias: "Process Scanned Book from iOS (Test)"
  description: "Test automation for book scanning"
  trigger:
    - platform: webhook
      webhook_id: ios_book_scanner
      local_only: false
  condition:
    - condition: state
      entity_id: input_boolean.book_scanning_active
      state: "on"
  action:
    # Extract ISBN
    - variables:
        scanned_isbn: "{{ trigger.json.isbn }}"
    
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
    
    # Update timestamp
    - service: input_datetime.set_datetime
      target:
        entity_id: input_datetime.last_book_scan_time
      data:
        timestamp: "{{ now().timestamp() }}"
    
    # Send notification (REPLACE device name!)
    - service: notify.mobile_app_iphone
      data:
        title: "✅ Book Added"
        message: "ISBN {{ scanned_isbn }} added to {{ states('input_text.book_scan_room') }}"
```

### 4.3 Save

- If using UI: Click **Save**
- If using File Editor: Save the file

The automation is active immediately - no restart needed!

## Step 5: Test with Webhook (2 minutes)

Let's test if everything works before creating the iOS shortcut.

### 5.1 Get Your Home Assistant URL

Find your URL:
- **Local**: `http://homeassistant.local:8123` or `http://192.168.x.x:8123`
- **Nabu Casa**: `https://yourname.ui.nabu.casa`
- **Custom domain**: Your configured URL

### 5.2 Enable Scanning Mode

1. Go to **Developer Tools** → **States**
2. Find `input_boolean.book_scanning_active`
3. Click on it
4. Toggle it to **ON**

### 5.3 Test Webhook with curl

Open a terminal (on your computer or in Home Assistant Terminal):

```bash
# Replace YOUR_HA_URL with your actual URL!
curl -X POST http://YOUR_HA_URL:8123/api/webhook/ios_book_scanner \
  -H "Content-Type: application/json" \
  -d '{"isbn":"9780451524935"}'
```

**Example:**
```bash
curl -X POST http://homeassistant.local:8123/api/webhook/ios_book_scanner \
  -H "Content-Type: application/json" \
  -d '{"isbn":"9780451524935"}'
```

### 5.4 Check Results

**You should see:**
1. ✅ A notification on your iPhone saying "Book Added"
2. ✅ The counter `books_scanned_today` increased to 1
3. ✅ The book "1984" in your library catalog

**Check the book was added:**
- Go to **Developer Tools** → **Services**
- Service: `library_catalog.search`
- Service data: `{"query": "1984", "search_by": "title"}`
- Click **Call Service**
- You should see the book in the results!

## Step 6: Create iOS Shortcut (3 minutes)

Now that the webhook works, create the iOS shortcut:

### 6.1 Open Shortcuts App

Open the **Shortcuts** app on your iPhone.

### 6.2 Create New Shortcut

1. Tap **+** (top right)
2. Tap **Add Action**

### 6.3 Add Actions (Step by Step)

**Action 1: Scan QR Code or Barcode**
1. Search for "scan"
2. Tap **Scan QR Code or Barcode**

**Action 2: Set Variable**
1. Tap **+** below the scan action
2. Search for "set variable"
3. Tap **Set Variable**
4. Name it: `ISBN`
5. Tap the variable value → Select **QR Code or Barcode** from menu

**Action 3: Get Contents of URL**
1. Tap **+**
2. Search for "get contents"
3. Tap **Get Contents of URL**
4. Configure:
   - **URL**: `http://YOUR_HA_URL:8123/api/webhook/ios_book_scanner`
   - Tap **Show More**
   - **Method**: Change to **POST**
   - **Request Body**: Change to **JSON**
   - **JSON field**: Delete what's there, type `{"isbn":""}`, then tap between the quotes and insert the **ISBN** variable
   - Tap **Headers** → **Add new field**
     - Key: `Content-Type`
     - Value: `application/json`

**Action 4: Show Notification**
1. Tap **+**
2. Search for "show notification"
3. Tap **Show Notification**
4. Title: `Book Scanned`
5. Body: Tap and select **ISBN** variable

**Action 5: Wait**
1. Tap **+**
2. Search for "wait"
3. Tap **Wait**
4. Set to **2** seconds

**Action 6: Run Shortcut (Loop)**
1. Tap **+**
2. Search for "run shortcut"
3. Tap **Run Shortcut**
4. Select **This Shortcut** (circular arrow icon)

### 6.4 Name and Save

1. Tap the name at the top
2. Change to: `ScanBookISBN`
3. Tap **Done**

## Step 7: Test the Complete Workflow! (2 minutes)

### 7.1 Enable Scanning

1. Open Home Assistant app on iPhone
2. Go to **Developer Tools** → **States**
3. Find `input_boolean.book_scanning_active`
4. Turn it **ON**

### 7.2 Run the Shortcut

1. Open **Shortcuts** app
2. Tap **ScanBookISBN**
3. Camera should open!
4. Point at a book's ISBN barcode
5. Wait 1-2 seconds for detection
6. You should see "Book Scanned" notification
7. Camera reopens for next book!

### 7.3 Verify in Home Assistant

Check:
- `books_scanned_today` counter increased
- Books appear in your catalog

## Troubleshooting

### ❌ "Shortcut Not Found" Error
- Make sure the shortcut is named exactly `ScanBookISBN`
- No spaces, capital letters matter!

### ❌ No Notification on iPhone
- Check your device name is correct in the automation
- Go to Settings → Notifications → Home Assistant → Ensure enabled

### ❌ "Service Not Available" Error
- Make sure Library Catalog integration is installed
- Check Settings → Devices & Services → Library Catalog

### ❌ Webhook Returns Error
- Check Home Assistant logs: Settings → System → Logs
- Search for "webhook" or "library_catalog"

### ❌ Camera Doesn't Open
- Make sure you used "Scan QR Code or Barcode" not "Take Photo"
- Check iOS privacy settings for Shortcuts → Camera access

### ❌ Loop Doesn't Work
- Some iOS versions don't allow recursive shortcuts
- Remove Action 6 (Run Shortcut)
- Manually tap the shortcut again for each book

## Next Steps

Once testing works:

1. ✅ Create the full dashboard (from IOS_AUTOMATIC_SCANNER.md)
2. ✅ Add the scripts for easy start/stop buttons
3. ✅ Add location preset buttons
4. ✅ Later: Add NFC tag support

## Quick Reference - Your URLs

**Webhook URL:**
```
http://YOUR_HA_URL:8123/api/webhook/ios_book_scanner
```

**Test ISBN:**
```
9780451524935
```
(This is "1984" by George Orwell - should work if your APIs are reachable)

**Webhook Test Command:**
```bash
curl -X POST http://YOUR_HA_URL:8123/api/webhook/ios_book_scanner \
  -H "Content-Type: application/json" \
  -d '{"isbn":"9780451524935"}'
```

---

## 🎯 Success Checklist

- [ ] Configuration added to `configuration.yaml`
- [ ] Home Assistant restarted
- [ ] Helpers visible in Settings
- [ ] Device name identified
- [ ] Automation added
- [ ] Scanning mode enabled
- [ ] Webhook test successful (curl)
- [ ] Book appeared in catalog
- [ ] Notification received on iPhone
- [ ] iOS Shortcut created
- [ ] Shortcut test successful
- [ ] Camera auto-scans barcodes

**All checked?** 🎉 You're ready to scan your entire library!

Need help with any step? Check the logs or ask!
