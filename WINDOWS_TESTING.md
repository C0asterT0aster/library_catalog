# Windows PowerShell - Webhook Testing Guide

## Connection Error: "Cannot establish connection with remote server"

### Common Causes

1. **Home Assistant not running** on that IP
2. **Wrong IP address**
3. **Firewall blocking** the connection
4. **Home Assistant on different port**

### ✅ Step 1: Verify Home Assistant is Reachable

Try opening in your browser:
```
http://192.168.178.96:8123
```

**Expected Result:** You should see the Home Assistant login page.

**If it doesn't work:**
- Home Assistant might be on a different IP
- Check your Home Assistant URL in the Companion App
- Or check your router for the correct IP

### ✅ Step 2: Find Your Home Assistant URL

**Option A: From Companion App**
1. Open Home Assistant Companion App on iPhone
2. Settings → Connection
3. Check the "Internal URL"
4. Use that URL in the PowerShell command

**Option B: Check Router**
1. Open your router admin page (usually `192.168.178.1`)
2. Look for connected devices
3. Find "homeassistant" or your Home Assistant device
4. Note the IP address

**Option C: From Home Assistant**
1. If you can access Home Assistant
2. Settings → System → Network
3. Check the IP address shown

### ✅ Step 3: Test Basic Connectivity

**PowerShell:**
```powershell
Test-NetConnection -ComputerName 192.168.178.96 -Port 8123
```

**Expected Output:**
```
TcpTestSucceeded : True
```

**If False:**
- Home Assistant is not running
- Wrong IP address
- Firewall blocking port 8123

### ✅ Step 4: Try Accessing Home Assistant API

Once you've confirmed the correct URL, test the API:

```powershell
Invoke-WebRequest -Uri "http://YOUR_CORRECT_IP:8123/api/" -Method GET
```

**Expected:** Should return some JSON response (even if unauthorized).

## PowerShell Testing Commands

### Problem with curl in PowerShell

In Windows PowerShell, `curl` is an alias for `Invoke-WebRequest` with different syntax.

### ✅ Solution 1: PowerShell Invoke-WebRequest (Recommended)

```powershell
Invoke-WebRequest -Uri "http://YOUR_HA_IP:8123/api/webhook/ios_book_scanner" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"isbn":"9780451524935"}'
```

Or shorter:

```powershell
$body = '{"isbn":"9780451524935"}'
Invoke-WebRequest -Uri "http://YOUR_HA_IP:8123/api/webhook/ios_book_scanner" -Method POST -ContentType "application/json" -Body $body
```

### ✅ Solution 2: Use Real curl

If you want to use real curl syntax:

```powershell
curl.exe -X POST http://YOUR_HA_IP:8123/api/webhook/ios_book_scanner -H "Content-Type: application/json" -d "{\"isbn\":\"9780451524935\"}"
```

**Important:** Note the escaped quotes (`\"`) in PowerShell!

### ✅ Solution 3: Use Git Bash

Open **Git Bash** (if installed) and use Linux syntax:

```bash
curl -X POST http://YOUR_HA_IP:8123/api/webhook/ios_book_scanner \
  -H "Content-Type: application/json" \
  -d '{"isbn":"9780451524935"}'
```

## Alternative Testing Methods

### 1. Browser Developer Console (Easiest!)

1. Open Home Assistant in your browser
2. Press **F12** to open Developer Tools
3. Go to **Console** tab
4. Paste this JavaScript:

```javascript
fetch('http://YOUR_HA_IP:8123/api/webhook/ios_book_scanner', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({isbn: '9780451524935'})
})
.then(r => r.json())
.then(d => console.log(d))
```

### 2. Home Assistant Developer Tools (No curl needed!)

This is the **easiest way** to test:

1. Open Home Assistant
2. Enable scanning mode:
   - Go to **Developer Tools** → **States**
   - Find `input_boolean.book_scanning_active`
   - Click on it and turn it **ON**

3. Simulate the webhook by calling the service directly:
   - Go to **Developer Tools** → **Services**
   - Service: `library_catalog.add_book`
   - Service data:
   ```yaml
   isbn: "9780451524935"
   location:
     room: "Living Room"
     shelf: "Shelf 1"
     compartment: "Top"
   ```
   - Click **Call Service**

This tests if the integration works without testing the webhook!

### 3. Postman or Insomnia

If installed:
- **URL:** `http://YOUR_HA_IP:8123/api/webhook/ios_book_scanner`
- **Method:** POST
- **Headers:** `Content-Type: application/json`
- **Body:** `{"isbn":"9780451524935"}`

## What You Should See

### ✅ Success (200 OK)

```json
{
  "success": true,
  "isbn": "9780451524935",
  "format": "UNKNOWN",
  "exists": false,
  "book": {
    "title": "1984",
    "authors": ["George Orwell"],
    ...
  },
  "message": "Book metadata retrieved. Use add_book service with location to store."
}
```

### ❌ Error Examples

**Scanning not active:**
```json
{
  "success": false,
  "error": "Scanning mode not active"
}
```

**Integration not loaded:**
```json
{
  "success": false,
  "error": "Service not available"
}
```

**Book not found:**
```json
{
  "success": false,
  "error": "Book metadata not found for ISBN ...",
  "isbn": "...",
  "exists": false
}
```

## Complete Test Flow

### Step 1: Enable Scanning Mode

Easiest via UI:
1. **Developer Tools** → **States**
2. Find `input_boolean.book_scanning_active`
3. Turn it **ON**

### Step 2: Test the Webhook

**PowerShell (once you have correct IP):**
```powershell
$response = Invoke-WebRequest -Uri "http://YOUR_HA_IP:8123/api/webhook/ios_book_scanner" -Method POST -ContentType "application/json" -Body '{"isbn":"9780451524935"}'
$response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

This shows you the formatted response!

### Step 3: Verify Book Was Added

Go to Home Assistant:
- **Developer Tools** → **Services**
- Service: `library_catalog.search`
- Data: `{"query": "1984", "search_by": "title"}`
- **Call Service**

You should see the book "1984"!

## Troubleshooting

### Error: "Cannot establish connection"

**Check 1: Is Home Assistant running?**
```powershell
Test-NetConnection -ComputerName YOUR_HA_IP -Port 8123
```

**Check 2: Correct IP address?**
- Open Home Assistant in browser
- Check URL bar for correct IP
- Update your command with the correct IP

**Check 3: Firewall?**
- Windows Firewall might be blocking
- Try from another device on same network
- Check if you can access HA from browser

### Error: "Service not available"

- Library Catalog integration not installed
- Integration not loaded (restart needed)
- Check: Settings → Devices & Services → Library Catalog should be listed

### Error: "Scanning mode not active"

- `input_boolean.book_scanning_active` is OFF
- Helpers not created (go back to Step 1 of setup)

### View Logs

**PowerShell:**
```powershell
Invoke-WebRequest -Uri "http://YOUR_HA_IP:8123/api/error_log"
```

Or in UI:
- **Settings** → **System** → **Logs**
- Search for "webhook" or "library_catalog"

## Quick Reference

### PowerShell One-Liner (Copy & Paste Ready)

```powershell
Invoke-WebRequest -Uri "http://YOUR_HA_IP:8123/api/webhook/ios_book_scanner" -Method POST -ContentType "application/json" -Body '{"isbn":"9780451524935"}' | Select-Object -ExpandProperty Content
```

### With Variables for Better Readability

```powershell
$haUrl = "http://YOUR_HA_IP:8123"
$webhookPath = "/api/webhook/ios_book_scanner"
$isbn = "9780451524935"
$body = "{`"isbn`":`"$isbn`"}"

$response = Invoke-WebRequest -Uri "$haUrl$webhookPath" -Method POST -ContentType "application/json" -Body $body
$response.Content
```

## Recommended: Skip curl, Test via Home Assistant UI

The easiest way to test without dealing with curl/PowerShell:

1. ✅ Enable scanning: Developer Tools → States → `input_boolean.book_scanning_active` → ON
2. ✅ Add a book: Developer Tools → Services → `library_catalog.add_book` with data
3. ✅ Verify it worked: Developer Tools → Services → `library_catalog.search`

Once that works, you know:
- Integration is installed ✅
- Automation works ✅
- Database works ✅

Then create the iOS Shortcut - it will use the same webhook endpoint!

## Next Steps

After confirming Home Assistant URL:
1. ✅ Update the URL in the PowerShell command
2. ✅ Test the webhook
3. ✅ If it works, update iOS Shortcut with correct URL
4. ✅ Start scanning books!

If webhook still doesn't work but services do:
- The integration works
- Just use the services directly from iOS Shortcuts
- Or create automation triggered differently (NFC tag, button, etc.)
