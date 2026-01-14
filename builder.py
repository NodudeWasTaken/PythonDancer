import requests
import sys
import subprocess
import io
import shutil
import os
import zipfile


print("Fetching binaries...")
os.system(f"{sys.executable} scripts/fetch_binaries.py")

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

print("Done!")