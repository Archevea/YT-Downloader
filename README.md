# YouTube Downloader

A simple, terminal-based YouTube downloader. It uses `yt-dlp` and can download every quality up to **4K / 60fps**. You **don't need to install ffmpeg** on your system — everything is handled automatically.

## Features

- Paste a link → see the video's **title, channel, and duration**
- Lists the qualities that **actually exist** for that video: 4K / 2K / 1080p / 720p / 480p / 360p / 240p / 144p and **MP3**
- Automatically prefers **60fps** when available
- 1080p and below download as **H.264** (plays in any player, including QuickTime)
- Files are saved to your **Downloads** (`~/Downloads`) folder
- Filename format: `Title [quality].mp4` — e.g. `Video [2160p60].mp4`

## Requirements

- **Python 3.10 or newer** (this is the only requirement)
- No ffmpeg needed — the `static-ffmpeg` package downloads the required binaries automatically.

---

## Quick Start (recommended)

The included run scripts set up the virtual environment and install dependencies on the first run, then launch directly on subsequent runs.

### Windows

**Double-click** `run.bat` — or run it in a terminal (CMD / PowerShell):

```bat
run.bat
```

### macOS

Open a terminal in the project folder and run:

```bash
./run.sh
```

> If you get a "permission denied" error the first time: run `chmod +x run.sh` and try again.

### Linux

```bash
./run.sh
```

The first run may take a bit longer because the ffmpeg binary is downloaded; subsequent runs are fast.

---

## Manual Usage

If you prefer to set things up by hand instead of using the scripts:

### Windows (PowerShell)

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

> If PowerShell blocks script execution, allow it for the current session:
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force`

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

---

## How It Works

1. The program asks for a **YouTube link**.
2. It shows the video's **title / channel / duration**.
3. It lists the **qualities** available for that video; you pick a number.
4. The file is downloaded, audio and video are merged automatically, and it's saved to your **Downloads** folder.

## Player Note (resolutions above 1080p)

YouTube offers **H.264** up to 1080p; those files play in any player, including **QuickTime**. However, for resolutions **above 1080p (2K / 4K)** YouTube only provides the **VP9 / AV1** codecs.

**On macOS, QuickTime cannot play VP9 / AV1** — you'll get audio only, with no picture. For any file above 1080p, open it with a free player instead:

- **[IINA](https://iina.io)** — macOS-native, recommended
- **[VLC](https://www.videolan.org)** — works everywhere, reliable fallback

On **Windows / Linux**, use **[VLC](https://www.videolan.org)** for these files as well (on Windows the built-in player may also need codec extensions for AV1/VP9).

This is a **codec compatibility** issue — the file is not corrupted.

## About ffmpeg

This project does **not** install ffmpeg on your system. The `static-ffmpeg` package downloads a real ffmpeg binary into the virtual environment (`venv`) and uses it temporarily while the program runs. That's why the `ffmpeg` command won't work in your terminal — this is normal; ffmpeg is scoped to this app only and never touches your system.
