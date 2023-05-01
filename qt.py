
from dancer.cli import cmd
from dancer.ui import ux
from dancer.util import cli_args

parser = cli_args()
args = parser.parse_args()

if (args.cli):
	cmd(args)
else:
	ux(args)
