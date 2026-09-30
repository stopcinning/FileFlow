"""Logging setup.

Writes to the platform data directory rather than the working directory: a
packaged .exe can be run from anywhere, and the user's home folder is the only
place guaranteed to be writable.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

LOG_NAME = "fileflow"
_MAX_BYTES = 512 * 1024
_BACKUP_COUNT = 2

_configured = False


def log_file() -> Path:
    from .core.journal import data_dir

    return data_dir() / "fileflow.log"


def setup_logging(*, verbose: bool = False) -> Path:
    """Configure logging once. Safe to call more than once."""
    global _configured

    if _configured:
        return log_file()

    root = logging.getLogger(LOG_NAME)
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    # Do not propagate to the root logger: a packaged app has no console, and
    # the default handler would print to a window that does not exist.
    root.propagate = False

    try:
        path = log_file()
        path.parent.mkdir(parents=True, exist_ok=True)

        handler = logging.handlers.RotatingFileHandler(
            path, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
        )
        root.addHandler(handler)
    except OSError:
        # A read-only or missing data directory should not stop the app from
        # starting; it just means no log file this run.
        root.addHandler(logging.NullHandler())

    if verbose and sys.stderr is not None:
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        root.addHandler(console)

    _configured = True
    return log_file()


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"{LOG_NAME}.{name}" if name else LOG_NAME)
