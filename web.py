from flask import Flask, render_template, request, redirect, url_for, jsonify
import threading
import uuid
import time
from pytubefix import YouTube
from pytubefix.cli import on_progress
import shutil
import subprocess
import os
import tempfile
import re

app = Flask(__name__)
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# in-memory progress store: id -> {status, percent, message, file}
progress_store = {}


def _filesize_of(s):
    return getattr(s, 'filesize', None) or getattr(s, 'filesize_approx', 0) or 0


def start_download_background(url, chosen_res, store_id):
    def worker():
        try:
            progress_store[store_id]['status'] = 'starting'
            # create a fresh YouTube object with custom progress callbacks
            # We'll select streams inside the worker to have filesize info
            yt = YouTube(url)

            # find available streams
            resolutions, prog_map, vidonly_map, audio_best = list_resolutions(yt)

            # helper to update store
            def set_msg(msg):
                progress_store[store_id]['message'] = msg

            if chosen_res in prog_map:
                stream = prog_map[chosen_res]
                total = _filesize_of(stream)
                progress_store[store_id]['total'] = total
                progress_store[store_id]['downloaded'] = 0

                def on_progress(s, chunk, bytes_remaining):
                    downloaded = _filesize_of(s) - bytes_remaining
                    progress_store[store_id]['downloaded'] = downloaded
                    pct = int(downloaded * 100 / max(1, total))
                    progress_store[store_id]['percent'] = min(100, pct)

                # attach callback by creating YouTube with callback
                yt2 = YouTube(url, on_progress_callback=on_progress)
                # find matching stream again by itag or resolution
                try:
                    stream2 = yt2.streams.get_by_itag(stream.itag) if getattr(stream, 'itag', None) else None
                except Exception:
                    stream2 = None
                if not stream2:
                    # fallback: pick progressive with same resolution
                    stream2 = yt2.streams.filter(progressive=True, file_extension='mp4', res=chosen_res).first()
                set_msg('Downloading progressive...')
                out_name = safe_filename(yt.title)
                stream2.download(output_path=DOWNLOAD_DIR, filename=out_name)
                progress_store[store_id]['percent'] = 100
                progress_store[store_id]['status'] = 'finished'
                progress_store[store_id]['file'] = out_name
                set_msg('Download complete')
                return

            if chosen_res in vidonly_map:
                video_stream = vidonly_map[chosen_res]
                # determine audio stream
                audio_stream = audio_best
                vsize = _filesize_of(video_stream)
                asize = _filesize_of(audio_stream) if audio_stream else 0
                total = vsize + asize
                progress_store[store_id]['total'] = total
                progress_store[store_id]['downloaded'] = 0
                downloaded_map = {'video': 0, 'audio': 0}

                def make_callback(role):
                    def on_progress(s, chunk, bytes_remaining):
                        dl = _filesize_of(s) - bytes_remaining
                        downloaded_map[role] = dl
                        downloaded = downloaded_map['video'] + downloaded_map['audio']
                        progress_store[store_id]['downloaded'] = downloaded
                        pct = int(downloaded * 100 / max(1, total))
                        progress_store[store_id]['percent'] = min(100, pct)
                    return on_progress

                tempdir = tempfile.mkdtemp(prefix='ytdl_')
                progress_store[store_id]['status'] = 'downloading'
                set_msg('Downloading video...')

                # download video
                yt_video = YouTube(url, on_progress_callback=make_callback('video'))
                try:
                    vs = yt_video.streams.get_by_itag(video_stream.itag) if getattr(video_stream, 'itag', None) else None
                except Exception:
                    vs = None
                if not vs:
                    vs = yt_video.streams.filter(adaptive=True, file_extension='mp4', res=chosen_res).first()
                video_path = vs.download(output_path=tempdir, filename='video.mp4')

                # download audio
                audio_path = None
                if audio_stream:
                    set_msg('Downloading audio...')
                    yt_audio = YouTube(url, on_progress_callback=make_callback('audio'))
                    try:
                        auds = yt_audio.streams.get_by_itag(audio_stream.itag) if getattr(audio_stream, 'itag', None) else None
                    except Exception:
                        auds = None
                    if not auds:
                        auds = yt_audio.streams.filter(only_audio=True, file_extension='mp4').order_by('abr').desc().first()
                    audio_path = auds.download(output_path=tempdir, filename='audio.mp4')

                # merge if possible
                ffmpeg_path = shutil.which('ffmpeg')
                out_name = safe_filename(yt.title)
                out_path = os.path.join(DOWNLOAD_DIR, out_name)
                if ffmpeg_path and audio_path:
                    set_msg('Merging with ffmpeg...')
                    try:
                        subprocess.check_call([ffmpeg_path, '-y', '-i', video_path, '-i', audio_path, '-c', 'copy', out_path])
                        # cleanup
                        try:
                            os.remove(video_path)
                            os.remove(audio_path)
                            os.rmdir(tempdir)
                        except Exception:
                            pass
                        progress_store[store_id]['percent'] = 100
                        progress_store[store_id]['status'] = 'finished'
                        progress_store[store_id]['file'] = out_name
                        set_msg('Merged and saved')
                        return
                    except subprocess.CalledProcessError:
                        progress_store[store_id]['status'] = 'error'
                        set_msg('ffmpeg merge failed')
                        return
                else:
                    # move files to downloads
                    mv_video = os.path.join(DOWNLOAD_DIR, f"{yt.video_id}_video.mp4")
                    os.replace(video_path, mv_video)
                    mv_audio = None
                    if audio_path:
                        mv_audio = os.path.join(DOWNLOAD_DIR, f"{yt.video_id}_audio.mp4")
                        os.replace(audio_path, mv_audio)
                    progress_store[store_id]['percent'] = 100
                    progress_store[store_id]['status'] = 'finished'
                    progress_store[store_id]['file'] = os.path.basename(mv_video)
                    set_msg('Saved separate files')
                    return

            progress_store[store_id]['status'] = 'error'
            progress_store[store_id]['message'] = 'Chosen resolution not available'
        except Exception as e:
            progress_store[store_id]['status'] = 'error'
            progress_store[store_id]['message'] = str(e)

    t = threading.Thread(target=worker, daemon=True)
    t.start()


@app.route('/status/<id>', methods=['GET'])
def status(id):
    data = progress_store.get(id)
    if not data:
        return jsonify({'error': 'not found'}), 404
    return jsonify(data)

def safe_filename(title):
    name = f"{title}.mp4"
    name = "".join(c for c in name if c not in '/\\?%*:|\"<>')
    return name.strip() or "output.mp4"

def parse_height(res):
    if not res:
        return 0
    m = re.match(r"(\d+)", res)
    return int(m.group(1)) if m else 0

def list_resolutions(yt):
    res_set = set()
    progressive_map = {}
    video_only_map = {}
    try:
        prog_streams = yt.streams.filter(progressive=True, file_extension="mp4")
    except Exception:
        prog_streams = yt.streams.filter(progressive=True)
    for s in prog_streams:
        res = getattr(s, "resolution", None)
        if res:
            res_set.add(res)
            if res not in progressive_map:
                progressive_map[res] = s

    try:
        adaptive_streams = yt.streams.filter(adaptive=True, file_extension="mp4")
    except Exception:
        adaptive_streams = yt.streams.filter(adaptive=True)
    try:
        audio_streams = yt.streams.filter(only_audio=True, file_extension="mp4").order_by("abr").desc()
    except Exception:
        audio_streams = yt.streams.filter(only_audio=True)

    for s in adaptive_streams:
        if getattr(s, "only_audio", False):
            continue
        res = getattr(s, "resolution", None)
        if res:
            res_set.add(res)
            if res not in video_only_map:
                video_only_map[res] = s

    audio_best = None
    try:
        audio_best = audio_streams.first()
    except Exception:
        audio_best = None

    sorted_res = sorted(list(res_set), key=parse_height)
    return sorted_res, progressive_map, video_only_map, audio_best


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/api/info', methods=['POST'])
def api_info():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'missing url'}), 400
    try:
        yt = YouTube(url, on_progress_callback=on_progress)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    resolutions, prog_map, vidonly_map, audio_best = list_resolutions(yt)

    # metadata
    thumbnail = getattr(yt, 'thumbnail_url', None) or getattr(yt, 'thumbnail', None) or getattr(yt, 'thumb', None)
    length = getattr(yt, 'length', None) or getattr(yt, 'duration', None)
    author = getattr(yt, 'author', None) or getattr(yt, 'channel', None)

    def fmt_seconds(s):
        try:
            s = int(s)
        except Exception:
            return None
        h = s // 3600
        m = (s % 3600) // 60
        sec = s % 60
        if h:
            return f"{h}:{m:02d}:{sec:02d}"
        return f"{m}:{sec:02d}"

    length_str = fmt_seconds(length)

    res_list = []
    for r in resolutions:
        res_list.append({
            'res': r,
            'progressive': r in prog_map,
            'video_only': r in vidonly_map,
        })

    return jsonify({
        'title': yt.title,
        'author': author,
        'thumbnail': thumbnail,
        'length': length_str,
        'resolutions': res_list,
        'url': url,
    })


@app.route('/resolutions', methods=['POST'])
def resolutions():
    url = request.form.get('url', '').strip()
    if not url:
        return redirect(url_for('index'))
    yt = YouTube(url, on_progress_callback=on_progress)
    resolutions, prog_map, vidonly_map, audio_best = list_resolutions(yt)

    # metadata (defensive for attribute names)
    thumbnail = getattr(yt, 'thumbnail_url', None) or getattr(yt, 'thumbnail', None) or getattr(yt, 'thumb', None)
    length = getattr(yt, 'length', None) or getattr(yt, 'duration', None)
    author = getattr(yt, 'author', None) or getattr(yt, 'channel', None)

    # format length to H:MM:SS or MM:SS
    def fmt_seconds(s):
        try:
            s = int(s)
        except Exception:
            return None
        h = s // 3600
        m = (s % 3600) // 60
        sec = s % 60
        if h:
            return f"{h}:{m:02d}:{sec:02d}"
        return f"{m}:{sec:02d}"

    length_str = fmt_seconds(length)

    return render_template('resolutions.html', title=yt.title, url=url, resolutions=resolutions, prog_map=prog_map, vidonly_map=vidonly_map, thumbnail=thumbnail, length=length_str, author=author)


@app.route('/download', methods=['POST'])
def download():
    data = request.get_json() or {}
    url = data.get('url') or request.form.get('url')
    chosen_res = data.get('resolution') or request.form.get('resolution')
    if not url or not chosen_res:
        return jsonify({'error': 'missing url or resolution'}), 400

    # start background download and return id for polling
    store_id = str(uuid.uuid4())
    progress_store[store_id] = {'status': 'queued', 'percent': 0, 'message': '', 'file': None, 'total': 0, 'downloaded': 0}
    start_download_background(url, chosen_res, store_id)
    return jsonify({'id': store_id, 'status': 'started'})

    yt = YouTube(url, on_progress_callback=on_progress)
    resolutions, prog_map, vidonly_map, audio_best = list_resolutions(yt)

    out_name = safe_filename(yt.title)
    out_path = os.path.join(DOWNLOAD_DIR, out_name)

    # progressive available?
    if chosen_res in prog_map:
        stream = prog_map[chosen_res]
        stream.download(output_path=DOWNLOAD_DIR, filename=out_name)
        return f"Downloaded progressive {chosen_res} -> {out_name}"

    if chosen_res in vidonly_map:
        video_stream = vidonly_map[chosen_res]
        tempdir = tempfile.mkdtemp(prefix='ytdl_')
        video_path = video_stream.download(output_path=tempdir, filename='video.mp4')
        audio_path = None
        if audio_best:
            audio_path = audio_best.download(output_path=tempdir, filename='audio.mp4')

        ffmpeg_path = shutil.which('ffmpeg')
        if ffmpeg_path and audio_path:
            cmd = [ffmpeg_path, '-y', '-i', video_path, '-i', audio_path, '-c', 'copy', out_path]
            try:
                subprocess.check_call(cmd)
                # cleanup
                try:
                    os.remove(video_path)
                    os.remove(audio_path)
                    os.rmdir(tempdir)
                except Exception:
                    pass
                return f"Merged and saved: {out_name} (in downloads/)"
            except subprocess.CalledProcessError:
                return f"ffmpeg merge failed. Video/audio left in {tempdir}"
        else:
            # move downloaded files into downloads for user
            mv_video = os.path.join(DOWNLOAD_DIR, f"{yt.video_id}_video.mp4")
            os.replace(video_path, mv_video)
            mv_audio = None
            if audio_path:
                mv_audio = os.path.join(DOWNLOAD_DIR, f"{yt.video_id}_audio.mp4")
                os.replace(audio_path, mv_audio)
            return f"Saved files: {os.path.basename(mv_video)} {os.path.basename(mv_audio) if mv_audio else ''} (ffmpeg not found)"

    return "Selected resolution not available.", 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
