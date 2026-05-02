import sys
import re
import json
import requests
import numpy as np
from pathlib import Path
from rembg import remove
from PIL import Image
from io import BytesIO
from scipy import ndimage


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


def fetch_thumbnail(video_id: str, is_shorts: bool = False) -> Image.Image:
    candidates = []
    if is_shorts:
        # Portrait thumbnails for Shorts
        candidates += [
            f"https://i.ytimg.com/vi/{video_id}/oar2.jpg",
            f"https://i.ytimg.com/vi/{video_id}/oar1.jpg",
        ]
    candidates += [
        f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
        f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
    ]
    for url in candidates:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content)).convert("RGBA")
            print(f"  -> Source: {url.split('/')[-1]} ({img.size[0]}x{img.size[1]})")
            return img
    raise RuntimeError(f"Could not fetch thumbnail for video ID: {video_id}")


def keep_largest_component(image: Image.Image) -> Image.Image:
    alpha = np.array(image)[:, :, 3]
    mask = alpha > 10
    labeled, num_features = ndimage.label(mask)
    if num_features <= 1:
        return image
    sizes = ndimage.sum(mask, labeled, range(1, num_features + 1))
    largest_label = int(np.argmax(sizes)) + 1
    clean_mask = (labeled == largest_label)
    result = np.array(image).copy()
    result[:, :, 3] = np.where(clean_mask, result[:, :, 3], 0)
    return Image.fromarray(result, "RGBA")


def crop_to_content(image: Image.Image, padding: int = 10) -> Image.Image:
    bbox = image.getbbox()
    if not bbox:
        return image
    x0 = max(0, bbox[0] - padding)
    y0 = max(0, bbox[1] - padding)
    x1 = min(image.width, bbox[2] + padding)
    y1 = min(image.height, bbox[3] + padding)
    return image.crop((x0, y0, x1, y1))


def remove_background(image: Image.Image) -> Image.Image:
    from rembg import new_session
    session = new_session("u2net_human_seg")
    buf = BytesIO()
    image.save(buf, format="PNG")
    result = remove(buf.getvalue(), session=session)
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
            is_shorts = "shorts/" in url
            video_id = extract_video_id(url)
            print(f"  -> Video ID: {video_id}")
            thumbnail = fetch_thumbnail(video_id, is_shorts=is_shorts)
            result = remove_background(thumbnail)
            print(f"  -> Background removed")
            result = keep_largest_component(result)
            print(f"  -> Isolated main subject")
            result = crop_to_content(result)
            print(f"  -> Cropped to content ({result.size[0]}x{result.size[1]})")
            out_path = output_dir / f"{i}.png"
            result.save(out_path, "PNG")
            print(f"  -> Saved to {out_path}")
        except Exception as e:
            print(f"  x Failed: {e}")

    all_images = [p for p in output_dir.glob("*.png") if p.stem.isdigit()]
    count = max((int(p.stem) for p in all_images), default=0)
    count_path = output_dir / "count.json"
    count_path.write_text(json.dumps({"count": count}))
    print(f"Updated images/count.json: {count} images")
    print("Done.")


if __name__ == "__main__":
    main()
