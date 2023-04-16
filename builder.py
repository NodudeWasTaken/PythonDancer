import requests
import io
import shutil
import os
import zipfile

print("Download UPX")
with requests.get("https://github.com/upx/upx/releases/download/v4.0.2/upx-4.0.2-win64.zip") as r:
	with zipfile.ZipFile(io.BytesIO(r.content)) as z:
		for file in z.infolist():
			if ("upx.exe" in file.filename):
				with z.open(file.filename) as zf:
					with open("upx.exe", "wb") as f:
						shutil.copyfileobj(zf, f)
						break

print("Building")
os.system("pyinstaller qt.spec")

print("Download FFMpeg")
with requests.get("https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip") as r:
	with zipfile.ZipFile(io.BytesIO(r.content)) as z:
		for file in z.infolist():
			if ("ffmpeg.exe" in file.filename):
				with z.open(file.filename) as zf:
					with open("dist/ffmpeg.exe", "wb") as f:
						shutil.copyfileobj(zf, f)
						break

print("Done!")