# Universal Scanner - iOS & Android Support

## Current Limitation

**Important:** iOS and Android handle actionable notifications differently!

### What Works Now ✅
- Dashboard button to start scanning
- Notification appears on device
- Text input field for ISBN
- Manual ISBN entry works perfectly
- Book gets added to catalog

### What Doesn't Work Yet 🚧
- **No automatic camera** in the notification
- **No barcode auto-recognition** in the text field
- User must **manually type** the ISBN

## Why No Camera?

### iOS Limitations
- Actionable notifications with `textInput` behavior only provide a text field
- No camera can be triggered from the notification itself
- iOS Shortcuts would be needed (separate app)
- iOS Live Text in keyboard can scan but requires manual activation

### Android Limitations
- Similar to iOS - actionable notifications don't support camera triggers
- Would need a separate barcode scanner app integration
- Or use Intent to launch camera app (complex, device-specific)

## Current Workaround (Both Platforms)

Users can manually type the ISBN from the book:

1. Tap "Start Scanning" in Home Assistant
2. Notification appears
3. Tap "Scan ISBN"
4. **Look at book and type the ISBN manually**
5. Tap "Add Book"
6. Book is added!

**This works but is not ideal.** 

## Better Solutions (To Be Implemented)

### Solution 1: Use Mobile App Camera (Recommended for Future)

Home Assistant Companion App has camera capabilities but they're not accessible via actionable notifications.

**Requires:** Custom component or app update to expose camera to notifications.

### Solution 2: Deep Link to Camera App

Create a button that opens the device camera via deep link:

**iOS:**
```yaml
tap_action:
  action: url
  url: "shortcuts://run-shortcut?name=ScanBarcode"
```

**Android:**
```yaml
tap_action:
  action: url
  url: "intent://scan/#Intent;scheme=zxing;package=com.google.zxing.client.android;end"
```

**Problem:** Requires third-party apps and complex setup.

### Solution 3: QR Code Input Helper

Instead of barcode scanning:
1. Generate QR code labels for your books (with ISBN)
2. Scan QR code with Home Assistant camera
3. Process via automation

**Problem:** Requires printing QR codes for all books.

### Solution 4: NFC Tags

Use NFC tags on bookshelves:
1. Tap NFC tag to set location
2. Open simple input dialog
3. Type ISBN
4. Done

**This might actually be simpler than camera scanning!**

## Recommended Current Workflow

### Setup (One-Time)

Follow SETUP_GUIDE.md to configure dashboard and scripts.

### Daily Use

**Option A: Manual Entry (Simplest)**
1. Click "Start Scanning" in dashboard
2. Notification appears on phone
3. Click "Scan ISBN"
4. Look at book spine/back
5. Type the 13-digit ISBN (ignore dashes)
6. Click "Add Book"
7. Repeat for more books

**Option B: Use Separate Scanner App**
1. Install any barcode scanner app (iOS: "QR Scanner", Android: "Barcode Scanner")
2. Scan ISBN with that app
3. Copy the number
4. Click notification "Scan ISBN"
5. Paste the ISBN
6. Click "Add Book"

**Option C: Use Home Assistant Dashboard (Desktop)**
1. Open Home Assistant on computer
2. Use dashboard input fields
3. Type ISBN directly
4. Much faster on keyboard!

## What We CAN Do Now

✅ **Add books manually** - Fast with keyboard  
✅ **Search books** - By title, author, ISBN, location  
✅ **Organize** - Room, shelf, compartment tracking  
✅ **Batch operations** - Set location once, add multiple books  
✅ **Statistics** - Track library growth  
✅ **Offline mode** - Manual book entry when APIs are down  

## Future Improvements Needed

To get true camera scanning working:

1. **Home Assistant App Update** - Add camera support to actionable notifications
2. **Custom Component** - Build ML Kit / Vision API integration
3. **External Scanner Integration** - Integrate with ZXing or similar
4. **Progressive Web App** - Custom camera web interface

## Community Input Welcome!

If you have ideas or want to contribute camera integration, please:
1. Check GitHub Issues
2. Join discussion at: https://github.com/C0asterT0aster/library_catalog/discussions
3. Submit PRs for camera integration solutions

## Realistic Expectations

For now, this integration is best used with:
- **Manual ISBN entry** (surprisingly fast with keyboard)
- **Desktop/tablet** for bulk entry
- **Mobile for quick additions** (type 13 digits)

True camera scanning would require significant development work or waiting for Home Assistant app updates.

## Alternative: Use Dedicated Barcode Scanner

Many users find it faster to:
1. Buy a USB/Bluetooth barcode scanner (~$30)
2. Connect to computer
3. Scan books - scanner types ISBN into text field instantly
4. Add to Home Assistant via dashboard

This is actually **faster and more reliable** than phone camera scanning!

## Summary

| Feature | Status | Platform |
|---------|--------|----------|
| Manual ISBN entry | ✅ Works | All |
| Add/Search/Delete | ✅ Works | All |
| Location tracking | ✅ Works | All |
| Dashboard | ✅ Works | All |
| Actionable notifications | ✅ Works | iOS, Android |
| Camera from notification | ❌ Not possible | iOS, Android |
| Separate scanner app | ✅ Workaround | iOS, Android |
| Hardware scanner | ✅ Best solution | Desktop |

## Updated Documentation

See SETUP_GUIDE.md for:
- Current working features
- Manual ISBN entry workflow
- Dashboard setup
- Multi-device support

The guide has been updated to reflect realistic expectations.
