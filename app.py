"""
YouTube Downloader (terminal)

- Downloads via yt-dlp (including 4K/60fps)
- No need to install ffmpeg on the system: it comes from the static-ffmpeg package
- Files are saved to the user's Downloads (~/Downloads) folder
"""

import sys
from pathlib import Path

try:
    import static_ffmpeg

    # Adds ffmpeg + ffprobe binaries to PATH; yt-dlp finds them automatically.
    static_ffmpeg.add_paths()
except Exception:
    # If static-ffmpeg is missing, fall back to a system-installed ffmpeg if present.
    pass

from yt_dlp import YoutubeDL


# Quality options: (height, display name). mp3 is added separately.
QUALITY_NAMES = {
    4320: "8K (4320p)",
    2160: "4K (2160p)",
    1440: "2K (1440p)",
    1080: "1080p",
    720: "720p",
    480: "480p",
    360: "360p",
    240: "240p",
    144: "144p",
}


def downloads_dir():
    """The user's Downloads folder (created if it doesn't exist)."""
    d = Path.home() / "Downloads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def format_duration(seconds):
    if not seconds:
        return "unknown"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def probe(url):
    """Fetches the video info and available format list without downloading."""
    with YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
        return ydl.extract_info(url, download=False)


def available_qualities(info):
    """
    Returns the heights that actually exist for this video and whether
    60fps is available at each height. -> {height: has_60fps}
    """
    found = {}
    for f in info.get("formats", []):
        if f.get("vcodec") in (None, "none"):
            continue  # skip audio-only streams
        h = f.get("height")
        if not h:
            continue
        is60 = (f.get("fps") or 0) >= 50
        found[h] = found.get(h, False) or is60
    return found


def build_menu(info):
    """Builds the list of options to show on screen."""
    quals = available_qualities(info)
    # Sort from highest to lowest
    items = []
    for h in sorted(quals.keys(), reverse=True):
        name = QUALITY_NAMES.get(h, f"{h}p")
        fps_tag = " 60fps" if quals[h] else ""
        items.append({
            "kind": "video",
            "height": h,
            "has60": quals[h],
            "label": f"{name}{fps_tag}",
        })
    items.append({"kind": "mp3", "label": "MP3 (audio only)"})
    return items


def quality_label(height, has60):
    """Quality tag appended to the filename, e.g. '2160p60'."""
    return f"{height}p60" if has60 else f"{height}p"


def progress_hook(d):
    """Shows a simple single-line progress bar."""
    if d.get("status") == "downloading":
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        downloaded = d.get("downloaded_bytes", 0)
        pct = (downloaded / total) if total else 0
        filled = int(pct * 20)
        bar = "█" * filled + "░" * (20 - filled)
        print(f"\rDownloading [{bar}] {pct * 100:3.0f}%", end="", flush=True)
    elif d.get("status") == "finished":
        print(f"\rDownloading [{'█' * 20}] 100%")


def postproc_hook(d):
    """Prints a short message when merging / mp3 conversion starts."""
    if d.get("status") == "started":
        name = d.get("postprocessor", "")
        if name == "Merger":
            print("Merging audio and video...")
        elif name == "FFmpegExtractAudio":
            print("Converting to MP3...")


def download(url, choice, out_dir):
    base = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,  # disable yt-dlp's noisy default output
        "progress_hooks": [progress_hook],
        "postprocessor_hooks": [postproc_hook],
    }

    if choice["kind"] == "mp3":
        outtmpl = str(out_dir / "%(title)s [mp3].%(ext)s")
        opts = {
            **base,
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }],
        }
    else:
        h = choice["height"]
        label = quality_label(h, choice["has60"])
        # Codec priority:
        #  1) H.264 (avc1) -> plays everywhere incl. QuickTime (available <=1080p)
        #  2) AV1 (av01)   -> for 2K/4K; native mp4, plays in VLC/IINA
        #  3) others       -> last resort (VP9 etc.)
        # yt-dlp prefers 60fps by default at the same height.
        fmt = (
            f"bestvideo[height={h}][vcodec^=avc1]+bestaudio[ext=m4a]/"
            f"bestvideo[height={h}][vcodec^=av01]+bestaudio/"
            f"bestvideo[height={h}]+bestaudio/"
            f"best[height={h}]/best[height<={h}]"
        )
        outtmpl = str(out_dir / f"%(title)s [{label}].%(ext)s")
        opts = {
            **base,
            "format": fmt,
            "outtmpl": outtmpl,
            "merge_output_format": "mp4",
        }

    with YoutubeDL(opts) as ydl:
        ydl.download([url])


def main():
    print("=== YouTube Downloader ===\n")

    url = ""
    while not url:
        url = input("YouTube link: ").strip()
        if not url:
            print("Please enter a valid link.")

    print("\nFetching video info...\n")
    try:
        info = probe(url)
    except Exception as e:
        print(f"Error: could not fetch video info. ({e})")
        sys.exit(1)

    print(f"Title    : {info.get('title', 'unknown')}")
    print(f"Channel  : {info.get('uploader', 'unknown')}")
    print(f"Duration : {format_duration(info.get('duration'))}\n")

    menu = build_menu(info)
    if len(menu) == 1:  # mp3 only
        print("Warning: no downloadable video quality found.\n")

    print("Quality options:")
    for i, item in enumerate(menu, start=1):
        print(f" {i}) {item['label']}")

    choice = None
    while choice is None:
        sel = input(f"\nChoice (1-{len(menu)}): ").strip()
        if sel.isdigit() and 1 <= int(sel) <= len(menu):
            choice = menu[int(sel) - 1]
        else:
            print("Invalid choice.")

    out_dir = downloads_dir()
    print(f"\nDownloading -> {out_dir}\n")
    try:
        download(url, choice, out_dir)
    except Exception as e:
        print(f"\nError: download failed. ({e})")
        sys.exit(1)

    print(f"\nDone! File saved to '{out_dir}'.")


if __name__ == "__main__":
    main()
