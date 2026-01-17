#!/usr/bin/env python3
"""
Wrapper to launch the textual GUI located in `interface/gui.py`.
Run this from the `src` folder (project root for imports).
"""
from .interface import gui


def main():
    gui.LicenseSentinelUI().run()


if __name__ == "__main__":
    main()
