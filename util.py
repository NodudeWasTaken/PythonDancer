import subprocess

def ffmpeg_check():
	try:
		subprocess.check_call([
			"ffmpeg","-version"
		])
	except FileNotFoundError:
		#TODO: Report back from here
		print("FFMpeg was missing")
		print("Please install ffmpeg using your package manager!")
		print("Suggestions:")
		print("Official Website: https://ffmpeg.org/download.html")
		print("Ubuntu/Debian: sudo apt install ffmpeg")
		print("Arch/Manjaro: sudo pacman -S ffmpeg")
		print("Homebrew: brew install ffmpeg")
		return True

	return False

def ffmpeg_conv(input, output):
	subprocess.check_call([
		"ffmpeg",
		"-y",
		"-i", input,
		"-map", "0:a",
		"-ar", "48000",
		output
	])
