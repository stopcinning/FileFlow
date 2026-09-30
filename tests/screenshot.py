r"""Render the real window to PNGs so the UI can be reviewed without a display.

Usage:  python tests\screenshot.py [output_dir]
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# The offscreen QPA plugin exposes no fonts on Windows, so screenshots come out
# as tofu boxes. Render with the native platform unless asked otherwise.
if os.environ.get("FILEFLOW_OFFSCREEN") == "1":
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
else:
    os.environ.pop("QT_QPA_PLATFORM", None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from fileflow.core.journal import Journal
from fileflow.log_setup import setup_logging
from fileflow.ui import theme
from fileflow.ui.main_window import MainWindow

setup_logging()

out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("screenshots")
out_dir.mkdir(parents=True, exist_ok=True)


def make_tree(root: Path) -> None:
    (root / "Documents" / "Contracts").mkdir(parents=True)
    (root / "Images" / "Screenshots").mkdir(parents=True)
    (root / "node_modules" / "left-pad").mkdir(parents=True)

    files = {
        "Q3 Financial Report v4.pdf": 4_200_000,
        "invoice_08412.pdf": 118_000,
        "Screenshot 2026-09-30 at 09.18.42.png": 1_800_000,
        "Screenshot 2026-09-29 at 17.04.11.png": 1_640_000,
        "client-brief-northwind.docx": 822_000,
        "render-export-04k.mov": 184_000_000,
        "track-master-07.wav": 38_000_000,
        "scratch.tmp": 4_200,
        "Thumbs.db": 12_000,
    }
    for name, size in files.items():
        (root / name).write_bytes(b"\0" * min(size, 4096))

    (root / "Documents" / "Contracts" / "contract-acme-2026.pdf").write_bytes(b"c" * 900)
    (root / "Documents" / "notes.txt").write_text("hello")
    (root / "Documents" / "notes copy.txt").write_text("hello")
    (root / "node_modules" / "left-pad" / "index.js").write_text("x" * 900)


def pump(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv[:1])
    theme.apply_theme(app, "dark")

    tmp = tempfile.mkdtemp()
    root = Path(tmp) / "Downloads"
    root.mkdir()
    make_tree(root)

    window = MainWindow()
    window.journal.close()
    window.journal = Journal(Path(tmp) / "journal.db")
    window._refresh_undo_state()

    window.resize(1360, 860)
    window.show()
    window.open_folder(root)

    for _ in range(40):
        pump(100)
        if window._scan_job is None and window.scan is not None:
            break

    # A couple of real operations so Activity and Undo are not empty.
    from fileflow.core import operations
    from fileflow.core.duplicates import find_duplicates

    entries = [f for f in window.scan.files if f.name.startswith("Screenshot")]
    quarantine = operations.quarantine(
        entries, window.journal, root=root, reason="duplicate cleanup"
    )
    window._refresh_undo_state()
    print(f"quarantined {quarantine.applied} screenshots for the screenshot")

    window.duplicates.report = find_duplicates(window.scan.files)
    window.duplicates._on_report(window.duplicates.report)
    pump(200)

    shots = {
        "library": "library",
        "duplicates": "duplicates",
        "rules": "rules",
        "activity": "activity",
        "settings": "settings",
    }
    for key, name in shots.items():
        window.show_page(key)
        pump(220)
        target = out_dir / f"{name}.png"
        window.grab().save(str(target))
        print(f"wrote {target}")

    window.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    sys.exit(main())
