# Automatic Setup Guide

## 🚀 One-Click Setup (NEW!)

Instead of manually copying YAML files, you can now **automatically set up everything** with one service call!

### Quick Setup (5 Minutes)

1. **Install the integration via HACS**
2. **Go to Developer Tools → Services**
3. **Call this service:**
   ```yaml
   service: library_catalog.auto_setup
   ```
4. **Click "Call Service"**
5. **Check the notification** - it will tell you what to do next
6. **⚠️ RESTART HOME ASSISTANT** (Settings → System → Restart)
7. **Wait 2 minutes for restart**
8. **Add dashboard card** (see below)
9. **Done!** ✅

The service automatically creates:
- ✅ All input helpers in `configuration.yaml` (room, shelf, compartment, counters)
- ✅ Scripts in `scripts.yaml` (`start_book_adding`, `stop_book_adding`)
- ✅ Automations in `automations.yaml` (handle add book, handle stop)

**IMPORTANT:** Input helpers require a Home Assistant restart to become active!

---

## What Gets Created

### Input Helpers
- `input_text.book_scan_room` - Current room (default: "Living Room")
- `input_text.book_scan_shelf` - Current shelf (default: "Shelf 1")
- `input_text.book_scan_compartment` - Current compartment (default: "Top")
- `input_boolean.book_scanning_active` - Is adding mode active?
- `input_number.books_scanned_today` - Counter for books added
- `input_datetime.last_book_scan_time` - Timestamp of last addition

### Scripts
- `script.start_book_adding` - Starts the book adding workflow
- `script.stop_book_adding` - Stops and shows summary

### Automations
- **Library Catalog - Handle Add Book** - Processes ISBN from notification
- **Library Catalog - Handle Stop** - Handles stop button

---

## After Setup

### Add the Dashboard Card

1. Go to **Overview** → **Edit Dashboard**
2. **Add Card** → **Manual**
3. Paste the YAML from `SETUP_GUIDE.md` (Step 5)
4. **Save**

### Start Using It!

1. **Click location button** (Living Room, Bedroom, etc.)
2. **Click "Start Adding Books"**
3. **Notification appears on your phone**
4. **Click "➕ Add Book"**
5. **Text field appears - type ISBN** (13 digits)
6. **Click "Add"**
7. **Book is added automatically!** ✅
8. **Notification shows "Add Another" - repeat or Stop**

---

## What Changed from Manual Setup

### Old Way (Manual)
- Copy YAML to `configuration.yaml`
- Restart Home Assistant
- Copy YAML to `scripts.yaml`
- Reload scripts
- Copy YAML to `automations.yaml` (2 automations)
- Reload automations
- Total: 15-20 minutes

### New Way (Automatic)
1. Call `library_catalog.auto_setup`
2. Wait 10 seconds
3. Add dashboard card
4. Done!
**Total: 2 minutes** ⚡

---

## Text Changes

### What You'll See Now:

**Before:**
- "📷 Scan ISBN" → "📷 Scan"
- "Book Scanner Ready"
- Script name: `start_book_scanning`

**Now:**
- "➕ Add Book" → Text input field appears
- "Add Books" (clearer purpose)
- Script name: `start_book_adding`
- Button says "Add" instead of "Scan"
- Placeholder: "Enter ISBN (13 digits)"

**Much clearer that it's a text input, not a camera!**

---

## Troubleshooting

### Service not found
- Make sure Library Catalog integration is installed via HACS
- Restart Home Assistant after installation

### Helpers already exist
- No problem! The service will skip existing helpers
- Check the notification for details

### Automations not working
- Go to Settings → Automations & Scenes
- Find "Library Catalog - Handle Add Book"
- Make sure it's **enabled** (toggle on)

### Text input doesn't appear
- iOS: Make sure notifications are enabled in iPhone Settings
- Android: Check notification permissions for Home Assistant app
- Try clicking the notification action twice if it doesn't appear

### Book not added
- Check `input_boolean.book_scanning_active` is ON
- Verify ISBN is 13 digits (or 10 for older books)
- Check logs: Settings → System → Logs (search "library_catalog")

---

## Manual Setup (If Needed)

If you prefer manual setup or the auto-setup fails, see **SETUP_GUIDE.md** for step-by-step YAML configuration.

---

## Next Steps

1. **Customize locations:** Change room names in the dashboard
2. **Test it:** Add a book with ISBN `9780451524935` (test book)
3. **Search your library:** Use `library_catalog.search` service
4. **Check stats:** View `input_number.books_scanned_today`

---

**Ready to build your digital library!** 📚
