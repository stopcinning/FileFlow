"""Entry point.

`python -m fileflow` and the packaged .exe both land here.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
from pathlib import Path

from .log_setup import setup_logging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fileflow",
        description="A file organiser that works on real folders.",
    )
    parser.add_argument(
        "folder",
        nargs="?",
        type=Path,
        help="Folder to open on launch. Omit to pick from the sidebar.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Log to stderr as well as the log file"
    )
    parser.add_argument("--version", action="store_true", help="Print the version and exit")
    args = parser.parse_args(argv)

    from . import __version__

    if args.version:
        print(f"fileflow {__version__}")
        return 0

    log_path = setup_logging(verbose=args.verbose)
    log = logging.getLogger("fileflow")

    # Imported after logging is configured so import-time warnings are captured.
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from .ui import theme
    from .ui.main_window import MainWindow

    log.info("FileFlow %s starting", __version__)
    log.debug("log file: %s", log_path)

    QApplication.setAttribute("__qt_auto_scale_high_dpi", True)
    app = QApplication(sys.argv[:1])
    app.setApplicationName("FileFlow")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("FileFlow")

    theme.apply_theme(app, "dark")

    window = MainWindow()

    if args.folder:
        # Defer until the event loop is running, so the window is on screen
        # before a slow folder scan starts.
        QTimer.singleShot(0, lambda: window.open_folder(args.folder.expanduser()))

    # Ctrl+C in a terminal should close the app rather than being swallowed.
    signal.signal(signal.SIGINT, lambda *_: app.quit())

    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
