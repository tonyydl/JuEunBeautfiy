# JuEunBeautify Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a YouTube browser extension (Chrome + Firefox) that overlays 李珠珢 (JuEun) images on every video thumbnail, plus a Python helper script that fetches YouTube thumbnails and removes their backgrounds locally.

**Architecture:** Fork of MrBeastify-Youtube with all branding replaced. Core extension logic is unchanged — a 100ms polling loop injects randomly-selected transparent PNG overlays onto YouTube thumbnails. A separate `prepare_images.py` script handles image sourcing via YouTube thumbnail URLs + local rembg background removal.

**Tech Stack:** JavaScript (browser extension, no framework), Python 3.13, rembg, Pillow, requests

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `jubeautify.js` | Create | Core injection loop — find thumbnails, overlay JuEun images |
| `settings.html` | Create | Extension popup UI (pink theme) |
| `settings.js` | Create | Load/save settings via chrome.storage.local |
| `manifest.json` | Create | Firefox Manifest v2 config |
| `manifest v3.json` | Create | Chrome Manifest v3 config |
| `images/flip_blacklist.json` | Create | Empty array — images safe to flip |
| `prepare_images.py` | Create | Fetch YouTube thumbnails + rembg bg removal → images/N.png |
| `README.md` | Create | Image format spec and prepare_images.py usage |

---

### Task 1: Project scaffold

**Files:**
- Create: `images/flip_blacklist.json`
- Create: `images/.gitkeep`

- [ ] **Step 1: Create images directory and flip_blacklist**

```bash
mkdir -p images
```

Create `images/flip_blacklist.json`:
```json
[]
```

- [ ] **Step 2: Create .gitkeep so images/ is tracked**

```bash
touch images/.gitkeep
```

- [ ] **Step 3: Commit**

```bash
git init
git add images/flip_blacklist.json images/.gitkeep
git commit -m "chore: scaffold project structure"
```

---

### Task 2: prepare_images.py — thumbnail fetch + background removal

**Files:**
- Create: `prepare_images.py`
- Create: `requirements.txt`

- [ ] **Step 1: Create requirements.txt**

```
rembg==2.0.57
Pillow>=10.0.0
requests>=2.31.0
```

- [ ] **Step 2: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: All packages install successfully.
> Note: If `onnxruntime` fails on Python 3.13, try `pip install onnxruntime --pre` first.

- [ ] **Step 3: Write prepare_images.py**

```python
import sys
import re
import requests
from pathlib import Path
from rembg import remove
from PIL import Image
from io import BytesIO


def extract_video_id(url: str) -> str:
    patterns = [
        r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})",
        r"shorts/([A-Za-z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Cannot extract video ID from: {url}")


def fetch_thumbnail(video_id: str) -> Image.Image:
    for quality in ("maxresdefault", "hqdefault", "mqdefault"):
        url = f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content)).convert("RGBA")
    raise RuntimeError(f"Could not fetch thumbnail for video ID: {video_id}")


def remove_background(image: Image.Image) -> Image.Image:
    buf = BytesIO()
    image.save(buf, format="PNG")
    result = remove(buf.getvalue())
    return Image.open(BytesIO(result)).convert("RGBA")


def main():
    if len(sys.argv) < 2:
        print("Usage: python prepare_images.py <youtube_url> [<youtube_url> ...]")
        sys.exit(1)

    output_dir = Path("images")
    output_dir.mkdir(exist_ok=True)

    existing = [p for p in output_dir.glob("*.png") if p.stem.isdigit()]
    next_index = max((int(p.stem) for p in existing), default=0) + 1

    urls = sys.argv[1:]
    for i, url in enumerate(urls, start=next_index):
        print(f"[{i}/{next_index + len(urls) - 1}] Processing {url}")
        try:
            video_id = extract_video_id(url)
            print(f"  → Video ID: {video_id}")
            thumbnail = fetch_thumbnail(video_id)
            print(f"  → Thumbnail fetched ({thumbnail.size[0]}x{thumbnail.size[1]})")
            result = remove_background(thumbnail)
            print(f"  → Background removed")
            out_path = output_dir / f"{i}.png"
            result.save(out_path, "PNG")
            print(f"  → Saved to {out_path}")
        except Exception as e:
            print(f"  ✗ Failed: {e}")

    print("Done.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Verify script runs with --help equivalent**

```bash
python prepare_images.py
```

Expected output:
```
Usage: python prepare_images.py <youtube_url> [<youtube_url> ...]
```

- [ ] **Step 5: Commit**

```bash
git add prepare_images.py requirements.txt
git commit -m "feat: add prepare_images.py for thumbnail fetch + bg removal"
```

---

### Task 3: jubeautify.js — core injection logic

**Files:**
- Create: `jubeautify.js`

- [ ] **Step 1: Write jubeautify.js**

```javascript
let imageCount = 0;
let recentImages = [];
let settings = { extensionIsDisabled: false, appearChance: 1.0, flipChance: 0.25 };

function loadSettings(callback) {
  chrome.storage.local.get(
    { extensionIsDisabled: false, appearChance: 1.0, flipChance: 0.25 },
    (data) => { settings = data; if (callback) callback(); }
  );
}

function pickRandomImage(total) {
  if (total === 0) return 1;
  let candidates = Array.from({ length: total }, (_, i) => i + 1)
    .filter(n => !recentImages.includes(n));
  if (candidates.length === 0) { recentImages = []; candidates = Array.from({ length: total }, (_, i) => i + 1); }
  const pick = candidates[Math.floor(Math.random() * candidates.length)];
  recentImages.push(pick);
  if (recentImages.length > 8) recentImages.shift();
  return pick;
}

function applyOverlay(thumbnail) {
  if (thumbnail.dataset.jubeautified) return;
  thumbnail.dataset.jubeautified = "1";

  if (Math.random() > settings.appearChance) return;

  const parent = thumbnail.parentElement;
  if (!parent) return;
  parent.style.position = "relative";

  const imgNum = pickRandomImage(imageCount);
  const overlay = document.createElement("img");
  overlay.src = chrome.runtime.getURL(`images/${imgNum}.png`);
  overlay.style.cssText = [
    "position:absolute",
    "bottom:0",
    "right:0",
    "height:80%",
    "width:auto",
    "pointer-events:none",
    "z-index:10",
    `transform:${Math.random() < settings.flipChance ? "scaleX(-1)" : "none"}`,
  ].join(";");

  thumbnail.insertAdjacentElement("afterend", overlay);
}

function findThumbnails() {
  const selectors = [
    "ytd-thumbnail a > yt-image > img.yt-core-image",
    'img.style-scope.yt-img-shadow[width="86"]',
    ".yt-thumbnail-view-model__image img",
    ".ytp-videowall-still-image",
  ];
  const all = [];
  for (const sel of selectors) {
    document.querySelectorAll(sel).forEach(el => all.push(el));
  }
  return all.filter(el => {
    if (el.dataset.jubeautified) return false;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return false;
    const ratio = r.width / r.height;
    return ratio > 1.2 && ratio < 2.5;
  });
}

function tick() {
  if (settings.extensionIsDisabled) return;
  findThumbnails().forEach(applyOverlay);
}

// Detect actual image count by probing URLs
function detectImageCount() {
  let count = 0;
  function probe(n) {
    const img = new Image();
    img.onload = () => { count = n; probe(n + 1); };
    img.onerror = () => { imageCount = count; };
    img.src = chrome.runtime.getURL(`images/${n}.png`);
  }
  probe(1);
}

loadSettings(() => {
  detectImageCount();
  setInterval(tick, 100);
  chrome.storage.onChanged.addListener(() => loadSettings(null));
});
```

- [ ] **Step 2: Commit**

```bash
git add jubeautify.js
git commit -m "feat: add jubeautify.js core injection logic"
```

---

### Task 4: settings.html + settings.js

**Files:**
- Create: `settings.html`
- Create: `settings.js`

- [ ] **Step 1: Write settings.html**

```html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <title>JuEunBeautify Options</title>
  <style>
    body {
      background: #F5A7C7;
      font-family: Arial, sans-serif;
      font-size: 16px;
      width: 300px;
      padding: 16px;
      margin: 0;
    }
    h2 { margin: 0 0 16px; font-size: 18px; }
    .row { margin-bottom: 12px; display: flex; align-items: center; gap: 10px; }
    label { flex: 1; }
    input[type="number"] { width: 60px; padding: 4px; }
    .toggle { position: relative; display: inline-block; width: 36px; height: 20px; }
    .toggle input { opacity: 0; width: 0; height: 0; }
    .slider {
      position: absolute; inset: 0; background: #ccc;
      border-radius: 20px; cursor: pointer; transition: .3s;
    }
    .slider:before {
      content: ""; position: absolute;
      width: 14px; height: 14px; left: 3px; bottom: 3px;
      background: white; border-radius: 50%; transition: .3s;
    }
    input:checked + .slider { background: #c2185b; }
    input:checked + .slider:before { transform: translateX(16px); }
    a.kofi { position: absolute; top: 12px; right: 12px; }
    a.kofi img { height: 24px; }
  </style>
</head>
<body>
  <h2 id="extension-title">TITLE Options</h2>
  <div class="row">
    <label for="disableExtension">Extension Enabled</label>
    <label class="toggle">
      <input type="checkbox" id="disableExtension" checked>
      <span class="slider"></span>
    </label>
  </div>
  <div class="row">
    <label for="appearChance">Appear Chance (%)</label>
    <input type="number" id="appearChance" min="0" max="100" step="5" value="100">
  </div>
  <div class="row">
    <label for="flipChance">Flip Chance (%)</label>
    <input type="number" id="flipChance" min="0" max="100" step="5" value="25">
  </div>
  <script src="settings.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write settings.js**

```javascript
function loadSettings() {
  chrome.storage.local.get(
    { extensionIsDisabled: false, appearChance: 1.0, flipChance: 0.25 },
    (data) => {
      document.getElementById("disableExtension").checked = !data.extensionIsDisabled;
      document.getElementById("appearChance").value = Math.round(data.appearChance * 100);
      document.getElementById("flipChance").value = Math.round(data.flipChance * 100);
    }
  );
}

function saveSettings() {
  chrome.storage.local.set({
    extensionIsDisabled: !document.getElementById("disableExtension").checked,
    appearChance: parseInt(document.getElementById("appearChance").value) / 100,
    flipChance: parseInt(document.getElementById("flipChance").value) / 100,
  });
}

function updateTitle() {
  const name = chrome.runtime.getManifest().name.replace(/youtube/i, "").trim();
  const el = document.getElementById("extension-title");
  el.textContent = el.textContent.replace("TITLE", name);
}

document.addEventListener("DOMContentLoaded", () => {
  loadSettings();
  updateTitle();
});
["disableExtension", "appearChance", "flipChance"].forEach(id => {
  document.getElementById(id).addEventListener("input", saveSettings);
});
```

- [ ] **Step 3: Commit**

```bash
git add settings.html settings.js
git commit -m "feat: add settings page with pink theme"
```

---

### Task 5: manifest.json (Firefox MV2)

**Files:**
- Create: `manifest.json`

- [ ] **Step 1: Write manifest.json**

```json
{
  "manifest_version": 2,
  "name": "YouTube JuEunBeautify",
  "version": "1.0.0",
  "description": "Modify YouTube thumbnails to include 李珠珢 (JuEun)",
  "icons": { "96": "icon.png" },
  "browser_action": {
    "default_icon": "icon.png",
    "default_popup": "settings.html"
  },
  "permissions": ["storage", "*://*.youtube.com/*"],
  "content_scripts": [
    {
      "matches": ["*://*.youtube.com/*"],
      "js": ["jubeautify.js"],
      "run_at": "document_idle"
    }
  ],
  "web_accessible_resources": ["images/*.png", "images/*.json"]
}
```

- [ ] **Step 2: Commit**

```bash
git add manifest.json
git commit -m "feat: add Firefox MV2 manifest"
```

---

### Task 6: manifest v3.json (Chrome MV3)

**Files:**
- Create: `manifest v3.json`

- [ ] **Step 1: Write manifest v3.json**

```json
{
  "manifest_version": 3,
  "name": "YouTube JuEunBeautify",
  "version": "1.0.0",
  "description": "Modify YouTube thumbnails to include 李珠珢 (JuEun)",
  "icons": { "96": "icon.png" },
  "action": {
    "default_icon": "icon.png",
    "default_popup": "settings.html"
  },
  "permissions": ["storage"],
  "host_permissions": ["*://*.youtube.com/*"],
  "content_scripts": [
    {
      "matches": ["*://*.youtube.com/*"],
      "js": ["jubeautify.js"],
      "run_at": "document_idle"
    }
  ],
  "web_accessible_resources": [
    {
      "resources": ["images/*.png", "images/*.json"],
      "matches": ["*://*.youtube.com/*"]
    }
  ]
}
```

- [ ] **Step 2: Commit**

```bash
git add "manifest v3.json"
git commit -m "feat: add Chrome MV3 manifest"
```

---

### Task 7: README.md

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md**

```markdown
# YouTube JuEunBeautify

Overlays images of 李珠珢 (JuEun) on every YouTube video thumbnail.

Based on [MrBeastify-Youtube](https://github.com/MagicJinn/MrBeastify-Youtube).

## Install

**Chrome:** Load `manifest v3.json` via chrome://extensions → Developer mode → Load unpacked  
**Firefox:** Load `manifest.json` via about:debugging → Load Temporary Add-on

## Prepare Images

Requires Python 3.x and `pip install -r requirements.txt` (first run downloads ~170MB rembg model).

```bash
python prepare_images.py <youtube_url_1> <youtube_url_2> ...
```

Output: `images/1.png`, `images/2.png`, ... (transparent PNG cutouts)

## Image Format

- PNG with transparent background
- Recommended width: ~400px
- Naming: sequential integers starting from `1.png`
- Add image number to `images/flip_blacklist.json` if it contains text that looks wrong when mirrored
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with install and image prep instructions"
```

---

### Task 8: Icon placeholder

**Files:**
- Create: `icon.png`

> The extension requires `icon.png` to load. Create a 96×96 pink placeholder until a real icon is available.

- [ ] **Step 1: Generate placeholder icon using Python**

```bash
python -c "
from PIL import Image, ImageDraw
img = Image.new('RGBA', (96, 96), (245, 167, 199, 255))
draw = ImageDraw.Draw(img)
draw.ellipse([8,8,88,88], fill=(194,24,91,255))
img.save('icon.png')
"
```

- [ ] **Step 2: Verify icon.png was created**

```bash
python -c "from PIL import Image; img = Image.open('icon.png'); print(img.size, img.mode)"
```

Expected: `(96, 96) RGBA`

- [ ] **Step 3: Commit**

```bash
git add icon.png
git commit -m "chore: add placeholder icon"
```

---

### Task 9: End-to-end test in browser

> Manual verification — no automated tests for browser extension UI.

- [ ] **Step 1: Run prepare_images.py with a real URL to verify full pipeline**

```bash
python prepare_images.py https://www.youtube.com/watch?v=<any_juEun_video_id>
```

Expected: `images/1.png` created with transparent background.

- [ ] **Step 2: Load extension in Chrome**

1. Open `chrome://extensions`
2. Enable Developer mode
3. Click "Load unpacked" → select this project folder
4. Verify extension icon appears in toolbar

- [ ] **Step 3: Load extension in Firefox**

1. Open `about:debugging`
2. Click "This Firefox" → "Load Temporary Add-on"
3. Select `manifest.json`
4. Verify extension icon appears

- [ ] **Step 4: Navigate to youtube.com and verify overlays appear**

Open `https://www.youtube.com` and verify 李珠珢 images appear overlaid on video thumbnails.

- [ ] **Step 5: Test settings panel**

Click extension icon → toggle Enabled off → verify overlays disappear. Toggle back on → verify they return.
