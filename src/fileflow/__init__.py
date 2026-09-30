"""FileFlow — a file organiser that works on real folders.

The public surface is deliberately small. The UI layer talks to `core`, and
`core` never imports Qt, so the whole engine is testable without a display.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
