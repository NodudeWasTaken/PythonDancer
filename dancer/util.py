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

	def irange(min,max):
		return range(min, max+1)
	parser.add_argument("audio_path", nargs='?', default=None, help="Path to input media")
	parser.add_argument("--out_path", help="Path to export funscript")
	parser.add_argument("--csv", help="Export as CSV instead of funscript", action="store_true")
	parser.add_argument("-m", "--heatmap", help="Export heatmap", action="store_true")
	parser.add_argument("-c", "--convert", help="Automatically use ffmpeg to convert input media", action="store_true")
	parser.add_argument("-a", "--automap", help="Automatically find suitable pitch and energy values", action="store_true")
	parser.add_argument("-y", "--yes", help="Overwrite funscript", action="store_true")
	parser.add_argument("--no_plp", help="Disable PLP", action="store_true")
	parser.add_argument("--cli", help="Use commandline", action="store_true")
	parser.add_argument("--auto_pitch", type=int, default=20, metavar="[0-100]", choices=irange(0,100), help="Where you want the actions to generally lie in percent")
	parser.add_argument("--auto_speed", type=int, default=250, metavar="[0-400]", choices=irange(0,400), help="The target action speed in units/s")
	parser.add_argument("--auto_per", type=int, default=65, metavar="[0-100]", choices=irange(0,100), help="The target percent of actions that should have a speed above the specified speed")
	parser.add_argument("--auto_mod", type=int, default=2, metavar="[1-3]", choices=irange(1,3), help="Which optimizer to use (cmean, cmeanv2, clen)")
	parser.add_argument("--pitch", type=int, default=100, metavar="[-200-200]", choices=irange(-200,200), help="The pitch")
	parser.add_argument("--energy", type=int, default=10, metavar="[0-100]", choices=irange(0,100), help="The energy magnitude")
	parser.add_argument("--amplitude_centering", type=int, default=0, metavar="[-100-100]", choices=irange(-100,100), help="Amplitude-based centering shift")
	parser.add_argument("--overflow", type=int, default=0, metavar="[0-2]", choices=irange(0,2), help="Overflow type")
	parser.add_argument("--center_offset", type=int, default=0, metavar="[-100-100]", choices=irange(-100,100), help="Center offset shift")

	return parser

