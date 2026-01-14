from pathlib import Path

from .libfun import autoval, create_actions, dump_csv, dump_funscript, load_audio_data, render_heatmap
from .util import ffmpeg_conv, ffmpeg_check, cli_args

def cmd(args):
	if (not args.audio_path):
		print("No audio file specified!")
		return

	audioFile = Path(args.audio_path)

	if not audioFile.exists():
		print("Audio file doesn't exist!")
		return

	if (args.out_path):
		out_file = Path(args.out_path)
	else:
		out_file = Path(args.audio_path)
		out_file = out_file.with_suffix(".csv" if args.csv else ".funscript")

	if (out_file.exists() and not args.yes):
		print("Funscript already exists!")
		return

	if (args.convert):
		print("Processing audio...")
		audioFile = Path("tmp", audioFile.with_suffix(".wav").name)
		audioFile.parent.mkdir(parents=True, exist_ok=True)

		if (ffmpeg_check()):
			return

		try:
			ffmpeg_conv(args.audio_path, audioFile)
		except Exception:
			print("Failed to convert to wav!")
			return

	print("Loading audio...")
	data = load_audio_data(audioFile, plp=not args.no_plp)

	if (args.automap):
		print("Automapping...")
		pitch,energy = autoval(data, tpi=args.auto_pitch, target_speed=args.auto_speed, v2above=args.auto_per/100.0, opt=(args.auto_mod-1))
		args.pitch = pitch
		args.energy = energy

	print("Creating actions...")
	actions = create_actions(
		data,
		energy_multiplier=args.energy,
		pitch_range=args.pitch,
		overflow=args.overflow,
		amplitude_centering=args.amplitude_centering,
		center_offset=args.center_offset
	)

	print("Writing...")
	with open(out_file, "w", encoding="utf8") as f:
		if (args.csv):
			dump_csv(f, actions)
		else:
			dump_funscript(f, actions)

	if (args.heatmap):
		render_heatmap(
			data,
			args.energy,
			args.pitch,
			args.overflow,
			args.overflow,
			args.amplitude_centering,
			args.center_offset
			).savefig(
				out_file
				.with_stem(out_file.stem + "_heatmap")
				.with_suffix(".png"),
				bbox_inches="tight", pad_inches=0)

	print("Done!")

if __name__ == "__main__":
	cmd(cli_args().parse_args())
