# JuEunBeautify — Design Spec

**Date:** 2026-05-02  
**Status:** Approved

## Overview

A YouTube browser extension that overlays images of 李珠珢 (JuEun) on top of every video thumbnail, based on the MrBeastify-Youtube extension by MagicJinn.

## Approach

Fork/replicate the original MrBeastify extension with minimal changes:
- Replace all MrBeast branding with JuEunBeautify / 李珠珢
- Replace images with 李珠珢 PNG cutouts
- Update color scheme to pink
- Keep all core logic identical

## File Structure

```
JuEunBeautify/
├── manifest.json            # Firefox Manifest v2
├── manifest v3.json         # Chrome Manifest v3
├── jubeautify.js            # Core injection logic (renamed from mrbeastify.js)
├── settings.html            # Extension settings popup
├── settings.js              # Settings load/save logic
├── icon.png                 # Extension toolbar icon
├── images/
│   ├── 1.png                # 李珠珢 cutout image #1
│   ├── 2.png                # 李珠珢 cutout image #2
│   ├── ...                  # Additional images numbered sequentially
│   └── flip_blacklist.json  # List of image numbers that should NOT be flipped
└── README.md                # Image format/naming specification for contributors
```

## Core Mechanism

Identical to original MrBeastify:

1. Every 100ms, scan YouTube page for unprocessed video thumbnails
2. CSS selectors used:
   - `ytd-thumbnail a > yt-image > img.yt-core-image`
   - `img.style-scope.yt-img-shadow[width="86"]`
   - `.yt-thumbnail-view-model__image img`
   - `.ytp-videowall-still-image`
3. For each new thumbnail, randomly select a JuEun image and inject it as an absolutely-positioned overlay
4. Non-repeating random selection (tracks last 8 used images)
5. Optional horizontal flip (respecting `flip_blacklist.json`)

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| Extension Enabled | true | Master toggle |
| Appear Chance | 100% | Probability overlay appears on each thumbnail |
| Flip Chance | 25% | Probability image is horizontally flipped |

Settings persisted via `chrome.storage.local`, compatible with both Chrome and Firefox.

## Branding

| Item | Value |
|------|-------|
| Extension name | `YouTube JuEunBeautify` |
| Main JS file | `jubeautify.js` |
| Settings page background | `#F5A7C7` (pink) |
| Description | `Modify YouTube thumbnails to include 李珠珢 (JuEun)` |

## Browser Support

- **Firefox**: `manifest.json` (Manifest v2)
- **Chrome / Chromium**: `manifest v3.json` (Manifest v3)

Both manifests point to `jubeautify.js` as the content script and expose `images/*.png` + `images/*.json` as web-accessible resources.

## Image Requirements (for README)

- Format: PNG with transparent background
- Style: Cutout portrait of 李珠珢 (no rectangular background)
- Recommended width: ~400px
- Naming: `1.png`, `2.png`, ... sequential integers, no gaps
- If an image contains text that looks wrong when mirrored, add its number to `flip_blacklist.json`

## Image Preparation Pipeline

A separate Python helper script (`prepare_images.py`) handles image sourcing and background removal:

1. User provides a list of YouTube video URLs
2. Script fetches each video's thumbnail via `https://img.youtube.com/vi/<VIDEO_ID>/maxresdefault.jpg`
3. Each thumbnail is processed by **rembg** (local, no API key needed, Python 3.13)
4. Output saved as `images/1.png`, `images/2.png`, ... sequentially

**Dependencies:**
- `rembg` — local background removal using U2Net model
- `Pillow` — image processing
- `requests` — thumbnail download

**Usage:**
```bash
pip install rembg Pillow requests
python prepare_images.py <youtube_url_1> <youtube_url_2> ...
```

Model (~170MB) downloads automatically on first run.

## Out of Scope

- Image management UI in settings page
- Any functionality beyond the original MrBeastify feature set
