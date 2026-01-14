from . import cli
from . import ui
from . import util

def main():
	parser = util.cli_args()
	args = parser.parse_args()

	if (args.cli):
		cli.cmd(args)
	else:
		ui.ux(args)

if __name__ == "__main__":
	main()
	