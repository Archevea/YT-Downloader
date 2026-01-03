
# YouTube Downloader

A small YouTube video downloader with both a web interface and a command-line interface.

Summary
- The project provides a web UI (`web.py`) and a CLI tool (`app.py`). It lists available video resolutions and downloads either a progressive stream (video + audio) or a video-only stream combined with an audio stream (merged via `ffmpeg` if available).

Features
- Web interface: paste a YouTube URL, pick a resolution, and track download progress.
- CLI: interactive terminal downloader with resolution selection.
- Downloads are saved to the `downloads/` folder inside the project.

Requirements
- Python 3.8 or newer
- `ffmpeg` for merging video-only + audio streams. If `ffmpeg` is not available, video and audio files may be left separate.

Dependencies
- Install Python dependencies from `requirements.txt` (Flask, pytubefix, etc.).

Installation (Windows - PowerShell)

```powershell
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

> **Note:** The `Set-ExecutionPolicy` command above only affects the current PowerShell session and reverts when you close the terminal.

Installing FFmpeg
- Winget: `winget install -e --id Gyan.FFmpeg`.

Running the web interface

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\venv\Scripts\Activate.ps1
python web.py
```

> **Note:** The `Set-ExecutionPolicy` command above only affects the current PowerShell session.

- Open your browser at `http://localhost:5000`.
- Paste a YouTube URL, click "Get Resolutions", choose a resolution, and press "Download".

Using the CLI

```powershell
python app.py
```

- The CLI will ask for a YouTube URL and let you choose a resolution to download.

Where files are saved
- Files are saved to the `downloads/` directory in the project root. If `ffmpeg` is unavailable, separate video/audio files will be saved instead of a merged MP4.

Troubleshooting
- Dependency errors: re-run `pip install -r requirements.txt` and review the error output.
- FFmpeg not found: verify `ffmpeg -version` works in PowerShell and that `ffmpeg` is on your PATH.
- Browser caching: if your changes to CSS/JS are not appearing, force reload (Ctrl+F5) or open DevTools and disable cache.
- Permission issues: ensure the `downloads/` directory is writable by your user.

Development notes
- The web server is started with `app.run(host='0.0.0.0', port=5000, debug=True)` in `web.py`. Change host/port or `debug` as needed.
- Static assets are served from the `static/` directory. After editing CSS/JS, refresh the browser.

Contributing & License
- This project is provided as-is for learning/demo purposes.
