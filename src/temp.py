#!/usr/bin/env python3
"""
Wrapper to launch the textual GUI located in `interface/gui.py`.
Run this from the `src` folder (project root for imports).
"""
from pathlib import Path
import sys

# Ensure project root is on sys.path so absolute imports like `src.*` work
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from interface import gui


def main():
    gui.LicenseSentinelUI().run()


if __name__ == "__main__":
    main()
