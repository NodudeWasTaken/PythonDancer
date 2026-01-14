import os
import sys
import platform
import requests
import tarfile
import zipfile
import shutil
import io

LINUX_URL = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
WIN_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

BIN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist")

def download_file(url):
    print(f"Downloading {url}...")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        return io.BytesIO(r.content)

def setup_linux():
    # Only support amd64 for now as per the common static build usage
    # If user is on arm, this might fail, but standard linux boxes are usually amd64
    content = download_file(LINUX_URL)
    print("Extracting tar.xz...")
    with tarfile.open(fileobj=content, mode="r:xz") as tar:
        for member in tar.getmembers():
            if member.name.endswith("/ffmpeg"):
                member.name = "ffmpeg" # Flatten path
                tar.extract(member, path=BIN_DIR)
                print(f"Extracted {member.name} to {BIN_DIR}")
                break
    
    # Make executable
    ffmpeg_path = os.path.join(BIN_DIR, "ffmpeg")
    os.chmod(ffmpeg_path, 0o755)

def setup_windows():
    content = download_file(WIN_URL)
    print("Extracting zip...")
    with zipfile.ZipFile(content) as z:
        for file in z.infolist():
            if file.filename.endswith("ffmpeg.exe"):
                 # We need to extract it, but zipfile extracts with full path.
                 # Let's extract to a temp file then move.
                 with z.open(file.filename) as zf, open(os.path.join(BIN_DIR, "ffmpeg.exe"), "wb") as f:
                     shutil.copyfileobj(zf, f)
                 print(f"Extracted ffmpeg.exe to {BIN_DIR}")
                 break

def main():
    if not os.path.exists(BIN_DIR):
        os.makedirs(BIN_DIR)

    system = platform.system()
    print(f"Detected OS: {system}")

    if system == "Linux":
        if os.path.exists(os.path.join(BIN_DIR, "ffmpeg")):
            print("FFmpeg already exists in bin/, skipping download.")
            return
        setup_linux()
    elif system == "Windows":
        if os.path.exists(os.path.join(BIN_DIR, "ffmpeg.exe")):
             print("FFmpeg already exists in bin/, skipping download.")
             return
        setup_windows()
    else:
        print(f"Unsupported OS for auto-download: {system}")
        print("Please manually place ffmpeg binary in proj/bin/")

if __name__ == "__main__":
    main()
