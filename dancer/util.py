import argparse
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

def ffmpeg_conv(in_file, out_file):
	subprocess.check_call([
		"ffmpeg",
		"-y",
		"-i", in_file,
		"-map", "0:a",
		"-ar", "48000",
		out_file
	])

def cli_args():
	parser = argparse.ArgumentParser(
		prog="libfun",
		description="Creates funscripts from audio",
		formatter_class=argparse.ArgumentDefaultsHelpFormatter
	)

	parser.add_argument("audio_path", nargs='?', default=None, help="Path to input media")
	parser.add_argument("--out_path", help="Path to export funscript")
	parser.add_argument("--csv", help="Export as CSV instead of funscript", action="store_true")
	parser.add_argument("-m", "--heatmap", help="Export heatmap", action="store_true")
	parser.add_argument("-c", "--convert", help="Automatically use ffmpeg to convert input media", action="store_true")
	parser.add_argument("-a", "--automap", help="Automatically find suitable pitch and energy values", action="store_true")
	parser.add_argument("-y", "--yes", help="Overwrite funscript", action="store_true")
	parser.add_argument("--no_plp", help="Disable PLP", action="store_false")
	parser.add_argument("--cli", help="Use commandline", action="store_true")
	parser.add_argument("--auto_pitch", type=int, default=20, metavar="[0-100]", choices=range(0,100))
	parser.add_argument("--auto_speed", type=int, default=250, metavar="[0-400]", choices=range(0,400))
	parser.add_argument("--pitch", type=int, default=100, metavar="[-200-200]", choices=range(-200,200))
	parser.add_argument("--energy", type=int, default=10, metavar="[0-100]", choices=range(0,100))
	parser.add_argument("--overflow", type=int, default=0, metavar="[0-2]", choices=range(0,2))

	return parser

