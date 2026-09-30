"""Activity: what FileFlow changed, grouped into undoable batches."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..widgets import EmptyState, format_age, format_count, horizontal_line, row


class ActivityPage(QWidget):
    def __init__(self, window) -> None:
        super().__init__()
        self.window = window

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        layout.addLayout(self._build_header())
        layout.addWidget(horizontal_line())
        layout.addWidget(self._build_body(), 1)

    def _build_header(self):
        box = QVBoxLayout()
        box.setSpacing(2)

        title = QLabel("Activity")
        title.setObjectName("PageTitle")

        self.subtitle = QLabel("Every change FileFlow has made, newest first.")
        self.subtitle.setObjectName("PageSubtitle")

        box.addWidget(title)
        box.addWidget(self.subtitle)

        self.undo_button = QPushButton("Undo selected batch")
        self.undo_button.setObjectName("Primary")
        self.undo_button.setToolTip("Ctrl+Z undoes the most recent batch")
        self.undo_button.clicked.connect(self._undo_selected)
        self.undo_button.setEnabled(False)

        self.prune_button = QPushButton("Prune old entries")
        self.prune_button.setToolTip(
            "Drop journal entries older than the retention window."
            " They can no longer be undone."
        )
        self.prune_button.clicked.connect(self._prune)

        return row(box, None, self.prune_button, self.undo_button, spacing=10)

    def _build_body(self) -> QWidget:
        self.stack = QStackedWidget()

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(("When", "Changes", "Summary", "Batch"))
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, header.ResizeMode.Stretch)
        header.setSectionResizeMode(3, header.ResizeMode.ResizeToContents)

        self.stack.addWidget(self.table)

        self.empty = EmptyState(
            "No changes yet",
            "When FileFlow moves, renames or quarantines something, it is recorded "
            "here and can be undone.",
        )
        self.stack.addWidget(self.empty)

        return self.stack

    # -- state -------------------------------------------------------------

    def refresh(self) -> None:
        batches = self.window.journal.batches(limit=200)

        self.table.setRowCount(len(batches))
        for index, (batch_id, count, timestamp, label) in enumerate(batches):
            entries = self.window.journal.entries_for_batch(batch_id)
            summary = label if len(entries) == 1 else f"{label} and {count - 1} more"

            for column, text in enumerate(
                (format_age(timestamp), format_count(count), summary, batch_id[:8])
            ):
                item = QTableWidgetItem(text)
                if column in (0, 3):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(index, column, item)

        self.stack.setCurrentIndex(0 if batches else 1)
        self.undo_button.setEnabled(bool(batches))

        if batches:
            total = sum(count for _b, count, _t, _l in batches)
            self.subtitle.setText(
                f"{format_count(len(batches))} batches · {format_count(total)} changes. "
                "Select a row to undo it."
            )
        else:
            self.subtitle.setText("Every change FileFlow has made, newest first.")

    def _selected_batch(self) -> str | None:
        selection = self.table.selectionModel()
        if selection is None:
            return None
        rows = selection.selectedRows()
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 3)
        return item.text() if item else None

    def _undo_selected(self) -> None:
        batch = self._selected_batch()
        if batch is None:
            QMessageBox.information(self, "Nothing selected", "Select a row to undo that batch.")
            return

        entries = self.window.journal.entries_for_batch(batch)
        preview = "\n".join(f"• {e.summary}" for e in entries[:8])
        if len(entries) > 8:
            preview += f"\n• … and {len(entries) - 8} more"

        answer = QMessageBox.question(
            self,
            "Undo this batch",
            f"Put {format_count(len(entries))} change(s) back?\n\n{preview}",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        reverted, errors = self.window.journal.undo_batch(batch)

        if errors:
            QMessageBox.warning(
                self, "Undo finished with errors", f"Reverted {reverted}.\n\n" + "\n".join(errors[:10])
            )

        self.window._set_status(f"Reverted {reverted} change(s).")
        self.refresh()
        self.window._refresh_undo_state()
        if self.window.root:
            self.window.rescan()

    def _prune(self) -> None:
        days = self.window.settings.journal_retention_days
        answer = QMessageBox.question(
            self,
            "Prune history",
            f"Delete journal entries older than {days} days?\n\n"
            "Those changes can no longer be undone.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        removed = self.window.journal.prune(keep_days=days)
        self.window._set_status(f"Removed {removed} old journal entries.")
        self.refresh()
        self.window._refresh_undo_state()
