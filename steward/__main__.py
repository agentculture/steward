"""Allow running steward as ``python -m steward``."""

import sys

from steward.cli import main

if __name__ == "__main__":
    sys.exit(main())
