import io
import sys
import shutil
import requests
import subprocess
from zipfile import ZipFile

def ffmpeg_check():
	try:
		subprocess.check_call([
			"ffmpeg","-version"
		])
	except FileNotFoundError:
		#TODO: Report back from here
		print("FFMpeg was missing")
		if (sys.platform in ["win32","cygwin","msys"]):
			download_ffmpeg()
		else:
			print("Please install ffmpeg using your package manager!")
			print("Suggestions:")
			print("Official Website: https://ffmpeg.org/download.html")
			print("Ubuntu/Debian: sudo apt install ffmpeg")
			print("Arch/Manjaro: sudo pacman -S ffmpeg")
			print("Homebrew: brew install ffmpeg")
			return True

	return False

def download_ffmpeg():
	with requests.get("https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip") as r:
		with ZipFile(io.BytesIO(r.content)) as z:
			for file in z.infolist():
				if ("ffmpeg.exe" in file.filename):
					with z.open(file.filename) as zf:
						with open("ffmpeg.exe", "wb") as f:
							shutil.copyfileobj(zf, f)
							break