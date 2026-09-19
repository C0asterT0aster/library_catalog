# HACS Update Setup Guide

## Problem

HACS doesn't show an update button because there are no GitHub releases.

## Solution: Create GitHub Releases

### Step 1: Create Your First Release (v0.1.0)

1. Go to your GitHub repository: https://github.com/C0asterT0aster/library_catalog
2. Click **Releases** (right side of the page)
3. Click **Create a new release**
4. Fill in:
   - **Tag version**: `v0.1.0` (must start with `v`!)
   - **Release title**: `v0.1.0 - Initial Release`
   - **Description**:
   
   ```markdown
   ## 🎉 Initial Release - v0.1.0
   
   ### ✅ Working Features
   - Add books by ISBN (automatic metadata from Open Library/Google Books)
   - Manual book entry (offline mode)
   - Search books (by title, author, ISBN, location)
   - Delete books
   - Update book locations
   - Location tracking (room/shelf/compartment)
   - SQLite database with full-text search
   - Multi-library support
   - Home Assistant services integration
   - Webhook endpoint for barcode scanners
   
   ### 🚧 In Development
   - Camera scanning from mobile notifications
   - Multi-device notification optimization
   
   ### 📋 Requirements
   - Home Assistant 2023.1.0 or newer
   - Python 3.10+
   
   ### 📦 Installation
   Via HACS:
   1. HACS → Integrations → Explore & Download
   2. Search "Library Catalog"
   3. Install
   4. Restart Home Assistant
   5. Settings → Devices & Services → Add Integration → Library Catalog
   
   ### 📚 Documentation
   - [Setup Guide](https://github.com/C0asterT0aster/library_catalog/blob/main/SETUP_GUIDE.md)
   - [Webhook API](https://github.com/C0asterT0aster/library_catalog/blob/main/WEBHOOK.md)
   - [Development Guide](https://github.com/C0asterT0aster/library_catalog/blob/main/DEVELOPMENT.md)
   ```

5. Check **Set as a pre-release** (since it's still in development)
6. Click **Publish release**

### Step 2: HACS Will Now Detect Updates

After creating the release:
- HACS checks GitHub releases every 24 hours
- When you create v0.2.0, HACS will show "Update Available"
- Users can click the update button!

### Step 3: For Future Updates

When you want to release an update:

1. **Update version numbers** in both files:
   - `custom_components/library_catalog/manifest.json` → `"version": "0.2.0"`
   - `hacs.json` → `"version": "0.2.0"`

2. **Commit and push:**
   ```bash
   git add custom_components/library_catalog/manifest.json hacs.json
   git commit -m "chore: Bump version to 0.2.0"
   git push
   ```

3. **Create GitHub Release:**
   - Go to Releases → Create new release
   - Tag: `v0.2.0`
   - Title: `v0.2.0 - What Changed`
   - Description: List changes
   - Publish

4. **HACS automatically detects the new version!**

## Version Numbering (Semantic Versioning)

Use this pattern: `MAJOR.MINOR.PATCH`

- **0.1.0** - Initial release
- **0.1.1** - Bug fixes (patch)
- **0.2.0** - New features (minor)
- **1.0.0** - Stable release (major)

Examples:
- `0.1.0` → `0.1.1`: Fixed notification bug
- `0.1.1` → `0.2.0`: Added camera scanning
- `0.2.0` → `1.0.0`: Stable, production-ready

## Quick Commands

### Create a Release (After committing changes)

```bash
# 1. Tag the commit
git tag -a v0.1.0 -m "Initial release"

# 2. Push tag to GitHub
git push origin v0.1.0

# 3. Then create the release on GitHub with this tag
```

Or do it entirely on GitHub (easier):
- No commands needed
- Just use the web interface

## Testing HACS Updates

After creating your first release:

1. **In Home Assistant:**
   - HACS → Integrations
   - Find "Library Catalog"
   - Should show current version: v0.1.0

2. **To test updates:**
   - Bump version to 0.1.1 in both files
   - Commit and push
   - Create release v0.1.1 on GitHub
   - Wait a few minutes (or restart HA)
   - HACS should show "Update available"
   - Click update button!

## Current Status

**Your repository:**
- ✅ Has `hacs.json`
- ✅ Has version in `manifest.json`
- ❌ Missing: GitHub releases

**After creating v0.1.0 release:**
- ✅ HACS can track versions
- ✅ Update button will appear
- ✅ Users can easily update

## Automation (Optional - For Later)

You can automate releases with GitHub Actions, but for now, manual releases are fine!

## Summary

**What you need to do RIGHT NOW:**

1. Go to: https://github.com/C0asterT0aster/library_catalog/releases
2. Click "Create a new release"
3. Tag: `v0.1.0`
4. Title: `v0.1.0 - Initial Release`
5. Copy description from above
6. Check "pre-release"
7. Publish
8. Done! HACS can now track updates!

**For next update:**
1. Change version in manifest.json and hacs.json
2. Commit and push
3. Create new release on GitHub
4. HACS shows update button automatically!

---

**No more manual uninstall/reinstall needed!** 🎉
