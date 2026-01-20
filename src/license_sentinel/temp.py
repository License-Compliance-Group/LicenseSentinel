#!/usr/bin/env python3
"""
Wrapper to launch the textual GUI located in `interface/gui.py`.
Run this from the `src` folder (project root for imports).
"""
<<<<<<<< HEAD:src/license_sentinel/temp.py
from .interface import gui
========
from interface import gui
>>>>>>>> a86f4d6dcfed8750b005e34b4fd68ce35b6173cf:src/licensesentinel.py


def main():
    gui.LicenseSentinelUI().run()


if __name__ == "__main__":
    main()
