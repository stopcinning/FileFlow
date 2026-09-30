"""Duplicates: find byte-identical files and reclaim the redundant copies.

Hashing runs on a worker thread, because it is the one operation in the app
that can take a noticeable amount of time on a real folder.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ...core import operations
from ...core.duplicates import DuplicateReport, find_duplicates
from ...core.models import ScanResult
from ..widgets import (
    EmptyState,
    StatTile,
    format_bytes,
    format_count,
    horizontal_line,
    row,
)

log = logging.getLogger("fileflow.duplicates")


class _HashWorker(QThread):
    """Runs the duplicate scan off the UI thread."""

    finished_report = Signal(object)  # DuplicateReport
    progressed = Signal(int, int)
    failed = Signal(str)

    def __init__(self, entries: list, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._entries = entries

    def run(self) -> None:
        try:
            report = find_duplicates(
                self._entries,
                progress=lambda done, total: self.progressed.emit(done, total),
            )
        except Exception as error:
            log.exception("duplicate scan failed")
            self.failed.emit(str(error))
            return

        self.finished_report.emit(report)


class DuplicatesPage(QWidget):
    def __init__(self, window) -> None:
        super().__init__()
        self.window = window
        self.root: Path | None = None
        self.report: DuplicateReport | None = None
        self._worker: _HashWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        layout.addLayout(self._build_header())
        layout.addLayout(self._build_stats())
        layout.addWidget(horizontal_line())
        layout.addWidget(self._build_body(), 1)

    # -- chrome ------------------------------------------------------------

    def _build_header(self):
        box = QVBoxLayout()
        box.setSpacing(2)

        title = QLabel("Duplicates")
        title.setObjectName("PageTitle")

        self.subtitle = QLabel("Byte-identical files, grouped by the space they waste.")
        self.subtitle.setObjectName("PageSubtitle")

        box.addWidget(title)
        box.addWidget(self.subtitle)

        self.scan_button = QPushButton("Find duplicates")
        self.scan_button.setObjectName("Primary")
        self.scan_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_button.clicked.connect(self.start_scan)
        self.scan_button.setEnabled(False)

        self.quarantine_button = QPushButton("Quarantine selected")
        self.quarantine_button.setObjectName("Danger")
        self.quarantine_button.setToolTip(
            "Move the redundant copies to quarantine."
            " The oldest copy in each group is kept."
        )
        self.quarantine_button.clicked.connect(self.quarantine_selected)
        self.quarantine_button.setEnabled(False)

        return row(box, None, self.quarantine_button, self.scan_button, spacing=10)

    def _build_stats(self):
        self.tile_groups = StatTile("Duplicate groups")
        self.tile_files = StatTile("Redundant copies")
        self.tile_waste = StatTile("Reclaimable")

        for tile in (self.tile_groups, self.tile_files, self.tile_waste):
            tile.setMinimumWidth(160)

        return row(self.tile_groups, self.tile_files, self.tile_waste, spacing=24)

    def _build_body(self) -> QWidget:
        self.stack = QStackedWidget()

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._on_group_selected)
        self.list.setAlternatingRowColors(True)

        self.detail = QListWidget()
        self.detail.setAlternatingRowColors(True)

        self.detail_hint = QLabel("Select a group to see the files in it.")
        self.detail_hint.setObjectName("Muted")
        self.detail_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)
        right_layout.addWidget(self.detail)
        right_layout.addWidget(self.detail_hint)

        splitter.addWidget(self._pane("Groups", self.list))
        splitter.addWidget(self._pane("Files in the selected group", right))
        splitter.setSizes([380, 420])

        self.stack.addWidget(splitter)

        self.empty = EmptyState(
            "Nothing scanned yet",
            "Open a folder in the Library tab, then come back and find duplicates.",
            "Go to Library",
        )
        self.empty.clicked.connect(lambda: self.window.show_page("library"))
        self.stack.addWidget(self.empty)

        self.busy = QLabel("Hashing files…")
        self.busy.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.busy.setObjectName("Muted")
        self.stack.addWidget(self.busy)

        return self.stack

    def _pane(self, title: str, widget: QWidget) -> QWidget:
        pane = QWidget()
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = QLabel(title)
        label.setObjectName("Muted")
        layout.addWidget(label)
        layout.addWidget(widget, 1)
        return pane

    # -- state -------------------------------------------------------------

    def set_scan(self, result: ScanResult, root: Path | None) -> None:
        self.root = root
        self.report = None
        self.list.clear()
        self.detail.clear()

        if not result.files:
            self.stack.setCurrentIndex(1)
            self.scan_button.setEnabled(False)
            return

        self.stack.setCurrentIndex(0)
        self.scan_button.setEnabled(True)
        self._reset_stats()

    def _reset_stats(self) -> None:
        for tile in (self.tile_groups, self.tile_files, self.tile_waste):
            tile.set_value("—")

    def refresh(self) -> None:
        """Called when the tab is opened. Nothing to do unless a scan is running."""
        if self._worker is not None and self._worker.isRunning():
            self.stack.setCurrentIndex(2)

    # -- scanning ----------------------------------------------------------

    def start_scan(self) -> None:
        if self.window.scan is None or self._worker is not None:
            return

        self.scan_button.setEnabled(False)
        self.quarantine_button.setEnabled(False)
        self.stack.setCurrentIndex(2)
        self.subtitle.setText("Reading file contents to compare them…")

        self._worker = _HashWorker(list(self.window.scan.files), self)
        self._worker.progressed.connect(self._on_progress)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished_report.connect(self._on_report)
        self._worker.finished.connect(self._on_worker_done)
        self._worker.start()

    def _on_progress(self, done: int, total: int) -> None:
        if total:
            self.busy.setText(f"Hashing {done:,} of {total:,} candidate files…")
        else:
            self.busy.setText("No files share a size, so there is nothing to compare.")

    def _on_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Duplicate scan failed", message)
        self.subtitle.setText("The scan failed. See the log for details.")

    def _on_report(self, report: DuplicateReport) -> None:
        self.report = report
        self.list.clear()
        self.detail.clear()

        for group in report.groups:
            names = [f.name for f in group.files]
            text = (
                f"{format_bytes(group.wasted)} wasted · {len(group.files)} copies\n"
                + "\n".join(f"    {n}" for n in names[:3])
            )
            if len(names) > 3:
                text += f"\n    … and {len(names) - 3} more"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, group)
            self.list.addItem(item)

        self.tile_groups.set_value(format_count(len(report.groups)))
        self.tile_files.set_value(format_count(report.total_redundant_files))
        self.tile_waste.set_value(format_bytes(report.reclaimable))

        self.quarantine_button.setEnabled(bool(report.groups))
        self.stack.setCurrentIndex(0)

        if not report.groups:
            self.subtitle.setText("No byte-identical files found.")
        elif report.skipped_large:
            self.subtitle.setText(
                f"{format_count(len(report.groups))} groups. "
                f"{report.skipped_large} very large file(s) were skipped rather than read."
            )
        else:
            self.subtitle.setText(
                f"{format_count(len(report.groups))} groups, "
                f"{format_bytes(report.reclaimable)} reclaimable. "
                f"Compared {format_count(report.hashed)} files."
            )

    def _on_worker_done(self) -> None:
        self._worker = None
        self.scan_button.setEnabled(self.window.scan is not None)
        QTimer.singleShot(0, self._ensure_view)

    def _ensure_view(self) -> None:
        if self._worker is None and self.stack.currentIndex() == 2:
            self.stack.setCurrentIndex(0 if self.list.count() else 1)

    # -- selection ---------------------------------------------------------

    def _on_group_selected(self, current: int) -> None:
        self.detail.clear()

        item = self.list.item(current) if current >= 0 else None
        if item is None:
            self.detail_hint.setVisible(True)
            return

        group = item.data(Qt.ItemDataRole.UserRole)
        keep = group.keep
        self.detail_hint.setVisible(False)

        header = QListWidgetItem(f"{format_bytes(group.size)} each")
        header.setFlags(Qt.ItemFlag.NoItemFlags)
        self.detail.addItem(header)

        for entry in group.files:
            is_keep = entry == keep
            label = "keep  " if is_keep else "dupe  "
            marker = "✓ oldest" if is_keep else "redundant"
            self.detail.addItem(QListWidgetItem(f"{label}{entry.name}  ({marker})"))

    def _selected_groups(self) -> list:
        return [
            self.list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.list.count())
        ]

    # -- operations --------------------------------------------------------

    def quarantine_selected(self) -> None:
        if self.report is None or self.root is None:
            return

        targets: list = []
        for group in self._selected_groups():
            targets.extend(group.redundant)

        if not targets:
            return

        size = sum(e.size for e in targets)
        answer = QMessageBox.question(
            self,
            "Quarantine redundant copies",
            f"Move {format_count(len(targets))} redundant copies "
            f"({format_bytes(size)}) to quarantine?\n\n"
            "The oldest copy in each group is kept. Undo restores everything.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        result = operations.quarantine(
            targets, self.window.journal, root=self.root, reason="duplicate cleanup"
        )

        if result.errors:
            QMessageBox.warning(
                self,
                "Finished with errors",
                result.summary() + "\n\n" + "\n".join(result.errors[:10]),
            )

        self.window._set_status(result.summary())
        self.window._refresh_undo_state()
        self.report = None
        self.list.clear()
        self.detail.clear()
        self.detail_hint.setVisible(True)
        self._reset_stats()
        self.window.rescan()
