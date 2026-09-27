# Lets `python -m minigit_pkg <command>` work the same as the `minigit` command
import sys

from minigit_pkg.cli import main

sys.exit(main())
