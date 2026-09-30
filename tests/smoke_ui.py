"""Offscreen smoke test: build the real window and drive it.

Not a substitute for looking at the app, but it catches the wiring mistakes that
only appear once every page is constructed together.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from fileflow.core.journal import Journal
from fileflow.log_setup import setup_logging
from fileflow.ui import theme
from fileflow.ui.main_window import MainWindow

setup_logging()

# Qt swallows exceptions raised inside slots and timer callbacks, printing them
# to stderr while the app carries on. Collect them so the smoke test cannot
# report success while something is actually broken.
_slot_errors: list[str] = []


def _hook(exc_type, exc_value, tb) -> None:
    import traceback

    _slot_errors.append("".join(traceback.format_exception(exc_type, exc_value, tb)))


sys.excepthook = _hook


def make_tree(root: Path) -> None:
    (root / "Documents").mkdir(parents=True, exist_ok=True)
    (root / "Images").mkdir(parents=True, exist_ok=True)
    (root / "node_modules" / "left-pad").mkdir(parents=True, exist_ok=True)

    (root / "invoice.pdf").write_bytes(b"%PDF-1.4\n" + b"0" * 2000)
    (root / "invoice copy.pdf").write_bytes(b"%PDF-1.4\n" + b"0" * 2000)  # exact dupe
    (root / "notes.txt").write_text("hello world")
    (root / "notes2.txt").write_text("hello world")  # exact dupe
    (root / "scratch.tmp").write_text("temp junk")
    (root / "Thumbs.db").write_bytes(b"\x00" * 40)
    (root / "photo.jpg").write_bytes(b"\xff\xd8\xff" + b"0" * 4096)
    (root / "Documents" / "report final v2.docx").write_bytes(b"docx" * 500)
    (root / "node_modules" / "left-pad" / "index.js").write_text("x" * 800)
    (root / ".hidden").write_text("should not appear")


def pump(ms: int = 250) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv[:1])
    theme.apply_theme(app, "dark")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "messy"
        root.mkdir()
        make_tree(root)

        window = MainWindow()
        # Point the journal at the temp tree so the test does not touch the
        # user's real data folder.
        window.journal.close()
        window.journal = Journal(Path(tmp) / "journal.db")
        window._refresh_undo_state()

        window.show()
        window.open_folder(root)

        # Wait for the background scan to be picked up.
        for _ in range(40):
            pump(100)
            if window._scan_job is None and window.scan is not None:
                break

        assert window.scan is not None, "scan never completed"
        print(f"scanned {len(window.scan.files)} files")
        print(f"  duplicates tab populated: {window.duplicates.list.count()}")

        failures = []

        for key in ("library", "duplicates", "rules", "activity", "settings"):
            window.show_page(key)
            pump(120)
            print(f"page {key}: ok")

        # Duplicates needs a scan of its own, which runs on a worker thread.
        window.show_page("duplicates")
        window.duplicates.start_scan()
        for _ in range(60):
            pump(100)
            if window.duplicates._worker is None:
                break
        window.duplicates._on_report.__self__  # noqa: B018
        report = window.duplicates.report
        print(f"duplicate groups found: {len(report.groups) if report else 0}")
        if not report or not report.groups:
            failures.append("expected duplicate groups for the two 'hello world' files")
        else:
            print(f"  reclaimable: {report.reclaimable} bytes")

        # Rule planning against the real scan.
        plan = window.engine.plan(window.scan.files, root=root)
        print(f"rule plan: {len(plan)} changes")
        for change in plan.changes[:3]:
            print(f"  {change.entry.name} -> {change.target}")

        # Library filtering.
        window.show_page("library")
        window.library.search.setText("invoice")
        pump(60)
        print(f"filter 'invoice': {window.library.model.rowCount()} rows")
        window.library.search.clear()
        pump(60)

        window.library.category.setCurrentIndex(1)  # Documents
        pump(60)
        documents = window.library.model.rowCount()
        print(f"filter Documents: {documents} rows")
        if documents == 0:
            failures.append("category filter returned no rows; expected the text files")

        window.library.category.setCurrentIndex(0)
        pump(60)

        # A real mutation, then a real undo.
        before = sorted(p.name for p in root.iterdir() if p.is_file())
        from fileflow.core import operations
        from fileflow.core.renamer import plan_find_replace

        entries = [f for f in window.scan.files if f.name == "notes.txt"]
        rename_plan = plan_find_replace(entries, "notes", "journal")
        applied = operations.apply_renames(rename_plan.steps, window.journal)
        print(f"renamed {applied.applied} file(s)")
        if not (root / "journal.txt").exists():
            failures.append("rename did not land on disk")

        reverted, errors = operations.undo_last(window.journal)
        print(f"undone {reverted} change(s), errors={errors}")
        after = sorted(p.name for p in root.iterdir() if p.is_file())
        if before != after:
            failures.append(f"undo did not restore: {before} != {after}")

        window.close()
        app.processEvents()

    if _slot_errors:
        failures.append(f"{len(_slot_errors)} unhandled exception(s) in Qt slots")
        for error in _slot_errors:
            print(error)

    if failures:
        print("\nFAILURES:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("\nsmoke test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
