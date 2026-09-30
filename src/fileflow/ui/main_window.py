"""Main window: sidebar navigation, folder selection, and the page stack.

Owns the application state that more than one page needs — the current folder,
the scan result, the journal and the rules — and hands each page the same
controller. Pages do not talk to each other.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..core import operations
from ..core.journal import Journal, default_journal_path
from ..core.models import ScanResult
from ..core.rules import RuleEngine
from ..core.scanner import MAX_ENTRIES, ScanJob
from ..core.settings import Settings, load_rules, load_settings, save_rules, save_settings
from . import theme
from .pages.activity import ActivityPage
from .pages.duplicates import DuplicatesPage
from .pages.library import LibraryPage
from .pages.rules import RulesPage
from .pages.settings_page import SettingsPage

log = logging.getLogger("fileflow.window")

NAV = (
    ("library", "Library", "Every file in the folder you opened."),
    ("duplicates", "Duplicates", "Byte-identical files, grouped by waste."),
    ("rules", "Rules", "Matchers and actions that file your folders for you."),
    ("activity", "Activity", "Everything FileFlow has changed, and how to undo it."),
    ("settings", "Settings", "Preferences and stored data."),
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FileFlow")
        self.resize(1280, 820)
        self.setMinimumSize(960, 600)

        self.settings: Settings = load_settings()
        self.journal = Journal(default_journal_path())
        self.engine = RuleEngine(load_rules())

        self.root: Path | None = None
        self.scan: ScanResult | None = None
        self._scan_job: ScanJob | None = None
        self._scan_generation = 0

        self._build_ui()
        self._build_shortcuts()
        self._restore_folder()

        self._status = self.statusBar()
        self._status.showMessage("Open a folder to begin.")

    # -- construction ------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_sidebar())

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        right_layout.addWidget(self._build_toolbar())

        self.stack = QStackedWidget()
        self.library = LibraryPage(self)
        self.duplicates = DuplicatesPage(self)
        self.rules_page = RulesPage(self)
        self.activity = ActivityPage(self)
        self.settings_page = SettingsPage(self)

        for page in (
            self.library,
            self.duplicates,
            self.rules_page,
            self.activity,
            self.settings_page,
        ):
            self.stack.addWidget(page)

        right_layout.addWidget(self.stack, 1)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setFixedWidth(140)
        self._progress.setVisible(False)
        right_layout.addWidget(self._progress)

        layout.addWidget(right, 1)
        self.setCentralWidget(central)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(212)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 18, 12, 12)
        layout.setSpacing(4)

        title = QLabel("FileFlow")
        title.setObjectName("BrandTitle")
        layout.addWidget(title)

        subtitle = QLabel("File organiser")
        subtitle.setObjectName("BrandSubtitle")
        layout.addWidget(subtitle)
        layout.addSpacing(18)

        self._nav_buttons: dict[str, QPushButton] = {}
        for key, label, _hint in NAV:
            button = QPushButton(label)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, k=key: self.show_page(k))
            layout.addWidget(button)
            self._nav_buttons[key] = button

        layout.addStretch()

        # A keyboard-shortcut hint that reflects real bindings, rather than
        # decoration.
        hint = QLabel("Ctrl+O  open folder\nCtrl+Z  undo last change\nCtrl+R  rescan")
        hint.setObjectName("BrandSubtitle")
        layout.addWidget(hint)

        return sidebar

    def _build_toolbar(self) -> QWidget:
        bar = QFrame()
        bar.setFixedHeight(60)
        bar.setStyleSheet(
            f"background: {theme.palette()['surface']};"
            f" border-bottom: 1px solid {theme.palette()['border']};"
        )

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(10)

        self.folder_label = QLabel("No folder open")
        self.folder_label.setStyleSheet(
            f"color: {theme.palette()['text_muted']}; font-size: 12px;"
        )
        self.folder_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.open_button = QPushButton("Open folder…")
        self.open_button.setObjectName("Primary")
        self.open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_button.clicked.connect(self.choose_folder)

        self.rescan_button = QPushButton("Rescan")
        self.rescan_button.clicked.connect(self.rescan)
        self.rescan_button.setEnabled(False)

        self.undo_button = QPushButton("Undo")
        self.undo_button.setToolTip("Undo the most recent batch of changes (Ctrl+Z)")
        self.undo_button.clicked.connect(self.undo_last)
        self.undo_button.setEnabled(False)

        layout.addWidget(self.open_button)
        layout.addWidget(self.rescan_button)
        layout.addWidget(self.undo_button)
        layout.addStretch()
        layout.addWidget(self.folder_label)

        return bar

    def _build_shortcuts(self) -> None:
        QShortcut(QKeySequence.StandardKey.Open, self, self.choose_folder)
        QShortcut(QKeySequence("Ctrl+R"), self, self.rescan)
        QShortcut(QKeySequence("Ctrl+Z"), self, self.undo_last)
        QShortcut(
            QKeySequence("Ctrl+F"),
            self,
            lambda: (self.show_page("library"), self.library.focus_search()),
        )
        for index, (key, _label, _hint) in enumerate(NAV, start=1):
            QShortcut(QKeySequence(f"Ctrl+{index}"), self, lambda k=key: self.show_page(k))

    # -- navigation --------------------------------------------------------

    def show_page(self, key: str) -> None:
        index = next((i for i, (k, _l, _h) in enumerate(NAV) if k == key), 0)
        self.stack.setCurrentIndex(index)

        for k, button in self._nav_buttons.items():
            button.setChecked(k == key)

        # Duplicates are expensive to compute, so only look when opened.
        if key == "duplicates":
            self.duplicates.refresh()
        elif key == "activity":
            self.activity.refresh()

    # -- folder lifecycle --------------------------------------------------

    def choose_folder(self) -> None:
        start = str(self.root) if self.root else str(Path.home())
        chosen = QFileDialog.getExistingDirectory(self, "Choose a folder to organise", start)
        if chosen:
            self.open_folder(Path(chosen))

    def open_folder(self, path: Path) -> None:
        if not path.is_dir():
            QMessageBox.warning(self, "Cannot open", f"{path} is not a folder.")
            return

        self.root = path
        self.settings.remember_folder(path)
        save_settings(self.settings)

        self.folder_label.setText(str(path))
        self.folder_label.setToolTip(str(path))
        self.rescan_button.setEnabled(True)
        self.show_page("library")

        self.rescan()

    def _restore_folder(self) -> None:
        if not self.settings.last_folder:
            return
        candidate = Path(self.settings.last_folder)
        if candidate.is_dir():
            self.open_folder(candidate)
        else:
            log.info("last folder no longer available: %s", candidate)

    def rescan(self) -> None:
        if self.root is None:
            return

        # Supersede any scan still in flight. Without this, switching folders
        # mid-scan leaves `self.root` pointing at the new folder while
        # `self.scan` holds results from the old one, and every later operation
        # acts on paths that are not under the root it thinks it is using.
        if self._scan_job is not None:
            self._scan_job.cancel()
            self._scan_job = None

        self._progress.setVisible(True)
        self.rescan_button.setEnabled(False)
        self._set_status("Scanning…")

        self._scan_job = ScanJob(
            self.root,
            include_hidden=self.settings.include_hidden,
            skip_build_dirs=self.settings.skip_build_dirs,
        )
        self._scan_generation += 1
        QTimer.singleShot(0, lambda: self._await_scan(self._scan_generation))

    def _await_scan(self, generation: int) -> None:
        """Poll the worker thread.

        A blocking `wait()` here would freeze the window for the length of the
        scan, which is exactly what the background thread exists to avoid. A
        timer poll is unglamorous but keeps the UI responsive and cancellable.

        `generation` identifies which scan this callback belongs to. A callback
        for a superseded scan returns without touching any state.
        """
        if generation != self._scan_generation:
            return

        job = self._scan_job
        if job is None:
            return

        if not job.finished:
            QTimer.singleShot(60, lambda: self._await_scan(generation))
            return

        self._scan_job = None
        self._progress.setVisible(False)
        self.rescan_button.setEnabled(True)

        if job.error is not None:
            log.exception("scan failed", exc_info=job.error)
            self._set_status("Scan failed — see the log for details.")
            QMessageBox.critical(self, "Scan failed", str(job.error))
            return

        # A folder can have been replaced since the scan started.
        if job.result.root != self.root:
            log.info("discarding stale scan for %s", job.result.root)
            return

        self.scan = job.result
        self._after_scan()

    def _after_scan(self) -> None:
        assert self.scan is not None
        result = self.scan

        self.library.set_scan(result, self.root)
        self.duplicates.set_scan(result, self.root)
        self.rules_page.set_scan(result, self.root)
        self._refresh_undo_state()

        if result.truncated:
            self._set_status(
                f"Stopped at the {MAX_ENTRIES:,} file limit — results are partial."
            )
        elif result.cancelled:
            self._set_status("Scan cancelled.")
        else:
            skipped = len(result.skipped)
            extra = f", {skipped} skipped" if skipped else ""
            self._set_status(f"{len(result.files):,} files in {result.duration_s:.1f}s{extra}")

    def _set_status(self, message: str) -> None:
        self.statusBar().showMessage(message)

    # -- operations --------------------------------------------------------

    def _refresh_undo_state(self) -> None:
        self.undo_button.setEnabled(bool(self.journal.batches(limit=1)))
        self.activity.refresh()

    def undo_last(self) -> None:
        reverted, errors = operations.undo_last(self.journal)

        if not reverted and errors == ["nothing to undo"]:
            self._set_status("Nothing to undo.")
            return

        if errors:
            QMessageBox.warning(
                self,
                "Undo finished with errors",
                f"Reverted {reverted} change(s).\n\n" + "\n".join(errors[:10]),
            )
        else:
            self._set_status(f"Reverted {reverted} change(s).")

        # The filesystem has moved underneath us; a rescan is the only honest
        # way to bring the view back in line.
        if self.root:
            self.rescan()

    def persist_rules(self) -> None:
        save_rules(self.engine.rules)

    def persist_settings(self) -> None:
        save_settings(self.settings)

    # -- shell -------------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._scan_job is not None:
            self._scan_job.cancel()

        self.journal.close()
        super().closeEvent(event)

    def reveal_in_explorer(self, path: Path) -> None:
        """Open the containing folder in the OS file manager."""
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", "/select,", str(path)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path.parent)])
        except OSError as error:
            log.warning("could not open file manager: %s", error)
