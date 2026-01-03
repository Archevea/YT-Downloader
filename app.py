from pytubefix import YouTube
from pytubefix.cli import on_progress
import shutil
import subprocess
from pytubefix import YouTube
from pytubefix.cli import on_progress
import shutil
import subprocess
import os
import tempfile
import sys
import re


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
			# prefer higher bitrate progressive for same resolution
			if res not in progressive_map:
				progressive_map[res] = s

	try:
		adaptive_streams = yt.streams.filter(adaptive=True, file_extension="mp4")
	except Exception:
		adaptive_streams = yt.streams.filter(adaptive=True)
	# get audio-only separately
	try:
		audio_streams = yt.streams.filter(only_audio=True, file_extension="mp4").order_by("abr").desc()
	except Exception:
		audio_streams = yt.streams.filter(only_audio=True)

	for s in adaptive_streams:
		# skip audio-only here
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

	# return sorted list by numeric height
	sorted_res = sorted(list(res_set), key=parse_height)
	return sorted_res, progressive_map, video_only_map, audio_best


def main():
	# Require the user to enter a YouTube URL (no default)
	while True:
		url = input("YouTube URL: ").strip()
		if url:
			break
		print("Please enter a valid YouTube URL.")

	yt = YouTube(url, on_progress_callback=on_progress)
	print(f"Title: {yt.title}")

	resolutions, prog_map, vidonly_map, audio_best = list_resolutions(yt)
	if not resolutions:
		print("No video resolutions found. Exiting.")
		return

	print("Available resolutions:")
	for i, r in enumerate(resolutions, start=1):
		tags = []
		if r in prog_map:
			tags.append("progressive")
		if r in vidonly_map:
			tags.append("video-only")
		print(f" {i}) {r} [{' & '.join(tags)}]")

	choice = input(f"Choose resolution number (1-{len(resolutions)}) [default {len(resolutions)}]: ")
	try:
		idx = int(choice) - 1 if choice.strip() else len(resolutions) - 1
		if idx < 0 or idx >= len(resolutions):
			raise ValueError
	except Exception:
		print("Invalid choice.")
		return

	chosen_res = resolutions[idx]
	print(f"Selected: {chosen_res}")

	# Prefer progressive (contains audio) if available
	if chosen_res in prog_map:
		stream = prog_map[chosen_res]
		out_name = safe_filename(yt.title)
		print(f"Downloading progressive stream ({chosen_res}) -> {out_name}")
		stream.download(filename=out_name)
		print("Download completed!")
		return

	# else try video-only + audio merge
	if chosen_res in vidonly_map:
		video_stream = vidonly_map[chosen_res]
		tempdir = tempfile.mkdtemp(prefix="ytdl_")
		print(f"Downloading video-only to temp: {tempdir}")
		video_path = video_stream.download(output_path=tempdir, filename="video.mp4")

		audio_path = None
		if audio_best:
			print("Downloading best audio stream...")
			audio_path = audio_best.download(output_path=tempdir, filename="audio.mp4")

		out_name = safe_filename(yt.title)
		ffmpeg_path = shutil.which("ffmpeg")
		if ffmpeg_path and audio_path:
			cmd = [ffmpeg_path, "-y", "-i", video_path, "-i", audio_path, "-c", "copy", out_name]
			print("Merging with ffmpeg...")
			try:
				subprocess.check_call(cmd)
				print(f"Saved merged file: {out_name}")
			except subprocess.CalledProcessError:
				print("ffmpeg merge failed. Video/audio files saved:")
				print(video_path)
				print(audio_path)
		else:
			print("ffmpeg not found or audio missing. Saved files:")
			print(video_path)
			if audio_path:
				print(audio_path)
			else:
				print("No audio stream available to merge.")

		# cleanup temp when merged
		if ffmpeg_path and audio_path:
			try:
				os.remove(video_path)
				os.remove(audio_path)
				os.rmdir(tempdir)
			except Exception:
				pass

		print("Done.")
		return

	print("Selected resolution not available as progressive or adaptive video.")


if __name__ == "__main__":
	main()