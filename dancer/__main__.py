from .cli import cmd
from .ui import ux
from .util import cli_args

if __name__ == "__main__":
	parser = cli_args()
	args = parser.parse_args()

	if (args.cli):
		cmd(args)
	else:
		ux(args)
