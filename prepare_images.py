import sys
import re
import json
import subprocess
import tempfile
import os
import requests
import numpy as np
from pathlib import Path
from rembg import remove, new_session
from PIL import Image
from io import BytesIO
from scipy import ndimage
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


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


def keep_largest_component(image: Image.Image, min_ratio: float = 0.15) -> Image.Image:
    """Keep all components >= min_ratio * largest component size.
    Removes small text/logo artifacts while preserving props and hands."""
    alpha = np.array(image)[:, :, 3]
    mask = alpha > 10
    labeled, num_features = ndimage.label(mask)
    if num_features <= 1:
        return image
    sizes = np.array([ndimage.sum(mask, labeled, i + 1) for i in range(num_features)])
    threshold = sizes.max() * min_ratio
    keep_labels = np.where(sizes >= threshold)[0] + 1
    clean_mask = np.isin(labeled, keep_labels)
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


def process_and_save(image: Image.Image, out_path: Path, model: str = "isnet-general-use"):
    session = new_session(model)
    buf = BytesIO()
    image.save(buf, format="PNG")
    result_bytes = remove(buf.getvalue(), session=session)
    result = Image.open(BytesIO(result_bytes)).convert("RGBA")
    print(f"  -> Background removed")
    result = keep_largest_component(result)
    result = crop_to_content(result)
    print(f"  -> Cropped to content ({result.size[0]}x{result.size[1]})")
    result.save(out_path, "PNG")
    print(f"  -> Saved to {out_path}")


def update_count(output_dir: Path):
    all_images = [p for p in output_dir.glob("*.png") if p.stem.isdigit()]
    indices = sorted(int(p.stem) for p in all_images)
    (output_dir / "count.json").write_text(json.dumps({"images": indices}))
    print(f"Updated images/count.json: {indices}")


def next_index(output_dir: Path) -> int:
    existing = [p for p in output_dir.glob("*.png") if p.stem.isdigit()]
    return max((int(p.stem) for p in existing), default=0) + 1


# ── Thumbnail mode ────────────────────────────────────────────────────────────

def cmd_thumbnail(urls: list[str], model: str = "birefnet-portrait"):
    output_dir = Path("images")
    output_dir.mkdir(exist_ok=True)
    idx = next_index(output_dir)
    for i, url in enumerate(urls, start=idx):
        print(f"[{i}] Processing {url}")
        try:
            is_shorts = "shorts/" in url
            video_id = extract_video_id(url)
            print(f"  -> Video ID: {video_id}")
            thumbnail = fetch_thumbnail(video_id, is_shorts=is_shorts)
            process_and_save(thumbnail, output_dir / f"{i}.png", model=model)
        except Exception as e:
            print(f"  x Failed: {e}")
    update_count(output_dir)


# ── Frames mode ───────────────────────────────────────────────────────────────

def download_video(url: str, out_path: Path):
    print(f"  -> Downloading video (low quality)...")
    subprocess.run([
        sys.executable, "-m", "yt_dlp",
        "-f", "bestvideo[height<=480][ext=mp4]/bestvideo[height<=480]/best[height<=480]",
        "--no-playlist",
        "-o", str(out_path),
        url,
    ], check=True, capture_output=True)


def parse_time(t: str) -> str:
    """Accept 1m30s, 1:30, 90s, 90 → ffmpeg-compatible hh:mm:ss string."""
    t = t.strip()
    # Already hh:mm:ss or mm:ss
    if re.match(r"^\d+:\d+(:\d+)?$", t):
        return t
    # e.g. 1m30s, 2m, 45s
    m = re.match(r"^(?:(\d+)m)?(?:(\d+)s?)?$", t)
    if m:
        minutes = int(m.group(1) or 0)
        seconds = int(m.group(2) or 0)
        return f"{minutes * 60 + seconds}"
    raise ValueError(f"Cannot parse time: {t}")


def extract_frames(video_path: Path, frames_dir: Path, fps: float = 1.0,
                   start: str = None, end: str = None):
    frames_dir.mkdir(parents=True, exist_ok=True)
    out_pattern = str(frames_dir / "%04d.jpg")
    cmd = [FFMPEG, "-y"]
    if start:
        cmd += ["-ss", parse_time(start)]
    cmd += ["-i", str(video_path)]
    if end:
        cmd += ["-to", parse_time(end)]
    cmd += ["-vf", f"fps={fps}", "-q:v", "2", out_pattern]
    subprocess.run(cmd, check=True, capture_output=True)
    return sorted(frames_dir.glob("*.jpg"))


def open_folder(path: Path):
    os.startfile(str(path))


def score_frame(path: Path) -> float:
    """Score a frame: higher = sharper + better brightness."""
    img = Image.open(path).convert("L")  # grayscale
    arr = np.array(img, dtype=float)
    # Laplacian approximation for sharpness
    laplacian = (
        arr[:-2, 1:-1] + arr[2:, 1:-1] +
        arr[1:-1, :-2] + arr[1:-1, 2:] -
        4 * arr[1:-1, 1:-1]
    )
    sharpness = laplacian.var()
    # Penalize over/under-exposed frames
    mean = arr.mean()
    brightness_score = 1.0 - abs(mean - 128) / 128
    return sharpness * brightness_score


def auto_pick(frames: list[Path], n: int) -> list[int]:
    """Pick n well-distributed sharp frames. Returns 1-based frame numbers."""
    print(f"  -> Scoring {len(frames)} frames...")
    # Divide into n buckets, pick best from each
    bucket_size = max(1, len(frames) // n)
    selected = []
    for b in range(n):
        start_i = b * bucket_size
        end_i = start_i + bucket_size if b < n - 1 else len(frames)
        bucket = frames[start_i:end_i]
        best = max(bucket, key=score_frame)
        frame_num = int(best.stem)
        selected.append(frame_num)
        print(f"  -> Bucket {b+1}/{n}: picked frame {frame_num:04d}.jpg")
    return selected


def cmd_frames(url: str, fps: float = 1.0, start: str = None, end: str = None,
               pick: str = None, auto: int = None, model: str = "birefnet-portrait"):
    output_dir = Path("images")
    output_dir.mkdir(exist_ok=True)

    video_id = extract_video_id(url)
    frames_dir = Path("frames") / video_id
    video_file = frames_dir / "video.mp4"

    if not any(frames_dir.glob("*.jpg")):
        frames_dir.mkdir(parents=True, exist_ok=True)
        try:
            download_video(url, video_file)
        except subprocess.CalledProcessError as e:
            print(f"Download failed: {e.stderr.decode()}")
            return
        frames = extract_frames(video_file, frames_dir, fps, start=start, end=end)
        if video_file.exists():
            video_file.unlink()
        print(f"  -> {len(frames)} frames extracted to {frames_dir}/")
    else:
        frames = sorted(frames_dir.glob("*.jpg"))
        print(f"  -> Using existing {len(frames)} frames in {frames_dir}/")

    print(f"\nFrames folder: {frames_dir.resolve()}")
    open_folder(frames_dir.resolve())

    if auto:
        selected = auto_pick(frames, auto)
    elif pick:
        print(f"Using --pick: {pick}")
        selected = [int(n.strip()) for n in pick.split(",") if n.strip().isdigit()]
    else:
        print("\nFrames are numbered 0001.jpg, 0002.jpg ...")
        raw = input("Enter frame numbers (comma-separated, e.g. 5,12,30): ").strip()
        if not raw:
            print("No frames selected. Re-run with --pick or --auto N.")
            return
        selected = [int(n.strip()) for n in raw.split(",") if n.strip().isdigit()]
    idx = next_index(output_dir)

    for frame_num in selected:
        frame_path = frames_dir / f"{frame_num:04d}.jpg"
        if not frame_path.exists():
            print(f"  x Frame {frame_num:04d}.jpg not found, skipping")
            continue
        print(f"[{idx}] Processing frame {frame_num:04d}.jpg")
        try:
            image = Image.open(frame_path).convert("RGBA")
            process_and_save(image, output_dir / f"{idx}.png", model=model)
            idx += 1
        except Exception as e:
            print(f"  x Failed: {e}")

    update_count(output_dir)


# ── Entry point ───────────────────────────────────────────────────────────────

def pop_arg(args: list, flag: str):
    """Remove --flag value from args list and return (value, new_args)."""
    if flag in args:
        i = args.index(flag)
        val = args[i + 1]
        args = [a for j, a in enumerate(args) if j != i and j != i + 1]
        return val, args
    return None, args


def usage():
    print("Usage:")
    print("  Thumbnail mode:")
    print("    python prepare_images.py <youtube_url> [...]")
    print()
    print("  Frames mode:")
    print("    python prepare_images.py --frames <youtube_url> [options]")
    print()
    print("  Options:")
    print("    --fps 2          frames per second (default: 1)")
    print("    --start 1m30s    start time (supports 1m30s, 1:30, 90s, 90)")
    print("    --end 2m         end time")
    print("    --pick 5,12,30   frame numbers to process (skips interactive prompt)")
    print("    --auto 6         auto-pick N best frames (no interaction needed)")
    sys.exit(1)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        usage()

    if args[0] == "--frames":
        if len(args) < 2:
            usage()
        fps_val, args = pop_arg(args, "--fps")
        start_val, args = pop_arg(args, "--start")
        end_val, args = pop_arg(args, "--end")
        pick_val, args = pop_arg(args, "--pick")
        auto_val, args = pop_arg(args, "--auto")
        model_val, args = pop_arg(args, "--model")
        fps = float(fps_val) if fps_val else 1.0
        cmd_frames(args[1], fps=fps, start=start_val, end=end_val,
                   pick=pick_val, auto=int(auto_val) if auto_val else None,
                   model=model_val or "birefnet-portrait")
    else:
        model_val, args = pop_arg(args, "--model")
        cmd_thumbnail(args, model=model_val or "birefnet-portrait")

    print("Done.")
