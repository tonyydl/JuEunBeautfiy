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
            print(f"  -> Video ID: {video_id}")
            thumbnail = fetch_thumbnail(video_id)
            print(f"  -> Thumbnail fetched ({thumbnail.size[0]}x{thumbnail.size[1]})")
            result = remove_background(thumbnail)
            print(f"  -> Background removed")
            out_path = output_dir / f"{i}.png"
            result.save(out_path, "PNG")
            print(f"  -> Saved to {out_path}")
        except Exception as e:
            print(f"  x Failed: {e}")

    print("Done.")


if __name__ == "__main__":
    main()
