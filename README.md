# YouTube JuEunBeautify

Overlays images of 李珠珢 (JuEun) on every YouTube video thumbnail.

Based on [MrBeastify-Youtube](https://github.com/MagicJinn/MrBeastify-Youtube).

## Install

**Chrome:** Load `manifest v3.json` via `chrome://extensions` → Developer mode → Load unpacked

**Firefox:** Load `manifest.json` via `about:debugging` → This Firefox → Load Temporary Add-on

## Prepare Images

1. Install dependencies (first run downloads ~170MB rembg model):

```bash
pip install -r requirements.txt
```

2. Run with YouTube video URLs:

```bash
python prepare_images.py <youtube_url_1> <youtube_url_2> ...
```

Output: `images/1.png`, `images/2.png`, ... (transparent PNG cutouts)

## Image Format

- PNG with transparent background
- Recommended width: ~400px
- Naming: sequential integers starting from `1.png`
- Add image number to `images/flip_blacklist.json` if it contains text that looks wrong when mirrored

Example `flip_blacklist.json`:
```json
[2, 5]
```
