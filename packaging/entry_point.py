"""Entry script for the packaged executable.

Deliberately separate from `fileflow/__main__.py`. PyInstaller runs the entry
script as a top-level module, so a script whose imports are relative
(`from .log_setup import ...`) has no parent package to resolve them against
and dies before reaching any of its own code.

This launcher uses an absolute import, which works with `pathex` pointing at
`src/`.
"""

import sys

from fileflow.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
