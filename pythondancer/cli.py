import argparse
from pathlib import Path
import sys
from .libfun import autoval, create_actions, dump_csv, dump_funscript, load_audio_data
from .util import ffmpeg_conv

parser = argparse.ArgumentParser(
	prog="libfun",
	description="Creates funscripts from audio",
	formatter_class=argparse.ArgumentDefaultsHelpFormatter
)
parser.add_argument("audio_path", help="Path to input media")
parser.add_argument("--out_path", help="Path to export funscript")
parser.add_argument("--csv", help="Export as CSV instead of funscript", action="store_true")
parser.add_argument("-c", "--convert", help="Automatically use ffmpeg to convert input media", action="store_true")
parser.add_argument("-a", "--automap", help="Automatically find suitable pitch and energy values", action="store_true")
parser.add_argument("--no_plp", help="Disable PLP", action="store_false")
parser.add_argument("--auto_pitch", type=int, default=20, metavar="[0-100]", choices=range(0,100))
parser.add_argument("--auto_speed", type=int, default=300, metavar="[0-400]", choices=range(0,400))
parser.add_argument("--pitch", type=int, default=100, metavar="[-200-200]", choices=range(-200,200))
parser.add_argument("--energy", type=int, default=10, metavar="[0-100]", choices=range(0,100))
parser.add_argument("--overflow", type=int, default=0, metavar="[0-2]", choices=range(0,2))

args = parser.parse_args()

audioFile = Path(args.audio_path)

if (args.convert):
	print("Processing audio...")
	audioFile = Path("tmp", audioFile.with_suffix(".wav").name)
	audioFile.parent.mkdir(parents=True, exist_ok=True)

	try:
		ffmpeg_conv(args.audio_path, audioFile)
	except Exception:
		print("Failed to convert to wav!")
		sys.exit(1)

print("Loading audio...")
data = load_audio_data(audioFile, plp=not args.no_plp)

if (args.automap):
	print("Automapping...")
	pitch,energy = autoval(data, tpi=args.auto_pitch, ten=args.auto_speed)
	args.pitch = pitch
	args.energy = energy

print("Creating actions...")
actions = create_actions(
	data,
	energy_multiplier=args.energy,
	pitch_range=args.pitch,
	overflow=args.overflow
)

print("Writing...")
if (args.out_path):
	out_file = Path(args.out_path)
else:
	out_file = Path(args.audio_path)
	out_file = out_file.with_suffix(".csv" if args.csv else ".funscript")

with open(out_file, "w") as f:
	if (args.csv):
		dump_csv(f, actions)
	else:
		dump_funscript(f, actions)

print("Done!")
