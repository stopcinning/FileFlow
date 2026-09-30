"""Library: the file listing, and the operations you can run on a selection."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ...core import operations
from ...core.models import Category, FileEntry, ScanResult
from ..widgets import (
    ENTRY_ROLE,
    EmptyState,
    FileTableModel,
    StatTile,
    attach_context_menu,
    format_bytes,
    format_count,
    horizontal_line,
    row,
)

log = logging.getLogger("fileflow.library")

CATEGORY_ORDER = (
    Category.DOCUMENTS,
    Category.IMAGES,
    Category.VIDEO,
    Category.AUDIO,
    Category.ARCHIVES,
    Category.CODE,
    Category.DESIGN,
    Category.OTHER,
)


class LibraryPage(QWidget):
    def __init__(self, window) -> None:
        super().__init__()
        self.window = window
        self.root: Path | None = None
        self._entries: list[FileEntry] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        layout.addLayout(self._build_header())
        layout.addLayout(self._build_stats())
        layout.addWidget(horizontal_line())
        layout.addLayout(self._build_filter())
        layout.addWidget(self._build_body(), 1)

    # -- chrome ------------------------------------------------------------

    def _build_header(self):
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title = QLabel("Library")
        title.setObjectName("PageTitle")

        self.subtitle = QLabel("Open a folder to see what is in it.")
        self.subtitle.setObjectName("PageSubtitle")

        title_box.addWidget(title)
        title_box.addWidget(self.subtitle)

        self.sort_button = QPushButton("Sort into folders")
        self.sort_button.setObjectName("Primary")
        self.sort_button.setToolTip(
            "Move every file into a folder named after its type. Fully reversible."
        )
        self.sort_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sort_button.clicked.connect(self.sort_into_folders)
        self.sort_button.setEnabled(False)

        self.backup_button = QPushButton("Back up selection…")
        self.backup_button.setToolTip("Copy the selected files to another folder")
        self.backup_button.clicked.connect(self.backup_selection)
        self.backup_button.setEnabled(False)

        return row(title_box, None, self.backup_button, self.sort_button, spacing=10)

    def _build_stats(self):
        self.tile_files = StatTile("Files")
        self.tile_size = StatTile("Total size")
        self.tile_folders = StatTile("Folders")
        self.tile_stale = StatTile("Untouched 90d+")

        for tile in (self.tile_files, self.tile_size, self.tile_folders, self.tile_stale):
            tile.setMinimumWidth(150)

        return row(self.tile_files, self.tile_size, self.tile_folders, self.tile_stale, spacing=24)

    def _build_filter(self):
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter by name or folder…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._apply_filter)
        self.search.setMaximumWidth(420)

        self.category = QComboBox()
        self.category.addItem("All types", None)
        for category in CATEGORY_ORDER:
            self.category.addItem(category.value, category)
        self.category.currentIndexChanged.connect(self._apply_filter)

        self.selection_label = QLabel("")
        self.selection_label.setObjectName("Muted")

        self.remove_button = QPushButton("Remove to quarantine")
        self.remove_button.setObjectName("Danger")
        self.remove_button.setToolTip(
            "Move the selected files to the quarantine folder."
            " Undoable from Activity."
        )
        self.remove_button.clicked.connect(self.quarantine_selection)
        self.remove_button.setEnabled(False)

        return row(self.search, self.category, self.selection_label, None, self.remove_button)

    def _build_body(self) -> QWidget:
        self.stack = QStackedWidget()

        self.model = FileTableModel(self)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.doubleClicked.connect(self._on_activated)
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column, width in ((1, 220), (2, 90), (3, 110), (4, 100)):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)
            self.table.setColumnWidth(column, width)

        self.stack.addWidget(self.table)

        self.empty = EmptyState(
            "No folder open",
            "Choose a folder and FileFlow will read it."
            " Nothing is changed until you ask.",
            "Open folder…",
        )
        self.empty.clicked.connect(self.window.choose_folder)
        self.stack.addWidget(self.empty)

        attach_context_menu(
            self.table,
            lambda _index: [
                ("Back up to…", lambda _i: self.backup_entries(self._selected())),
                (None, None),
                ("Remove to quarantine", lambda _i: self.quarantine_entries(self._selected())),
                ("Show in file manager", self._reveal_selection),
            ],
        )

        return self.stack

    # -- state -------------------------------------------------------------

    def set_scan(self, result: ScanResult, root: Path | None) -> None:
        self.root = root
        self._entries = result.files
        self.model.set_entries(result.files, root)

        self.stack.setCurrentIndex(0 if result.files else 1)
        self.sort_button.setEnabled(bool(result.files))
        self.backup_button.setEnabled(bool(result.files))

        self.subtitle.setText(
            f"{format_count(len(result.files))} files · {format_bytes(result.total_size)}"
            if result.files
            else "This folder has no files in it."
        )

        self._update_stats(result)
        self._apply_filter()

    def _update_stats(self, result: ScanResult) -> None:
        self.tile_files.set_value(format_count(len(result.files)))
        self.tile_size.set_value(format_bytes(result.total_size))
        self.tile_folders.set_value(format_count(result.directories))

        cutoff = 90 * 86_400
        stale = sum(1 for f in result.files if f.mtime < cutoff)
        self.tile_stale.set_value(format_count(stale))
        self.tile_stale.setToolTip(
            f"{format_count(stale)} files not modified in the last 90 days"
        )

    def focus_search(self) -> None:
        self.search.setFocus()
        self.search.selectAll()

    # -- filtering ---------------------------------------------------------

    def _apply_filter(self) -> None:
        # Qt round-trips combo userData as a plain str, so a StrEnum member
        # comes back as its value rather than as the member. Comparing with
        # `is` against that string would silently filter out every row.
        raw = self.category.currentData()
        category = Category(raw) if raw is not None else None

        self.model.filter(text=self.search.text(), category=category)
        self._update_selection_label()

    # -- selection ---------------------------------------------------------

    def _selected(self) -> list[FileEntry]:
        rows = {index.row() for index in self.table.selectionModel().selectedRows()}
        return [e for e in (self.model.entry_at(r) for r in sorted(rows)) if e is not None]

    def _on_activated(self, index) -> None:
        entry = index.data(ENTRY_ROLE)
        if entry:
            self.window.reveal_in_explorer(entry.path)

    def _reveal_selection(self, _index) -> None:
        entries = self._selected()
        if entries:
            self.window.reveal_in_explorer(entries[0].path)

    def _on_selection_changed(self, *_args) -> None:
        self._update_selection_label()

    def _update_selection_label(self) -> None:
        chosen = self._selected()
        count = len(chosen)

        if count == 0:
            self.selection_label.setText("")
            self.remove_button.setEnabled(False)
            self.backup_button.setEnabled(bool(self.model.entries))
            return

        size = sum(e.size for e in chosen)
        self.selection_label.setText(f"{format_count(count)} selected · {format_bytes(size)}")
        self.remove_button.setEnabled(True)
        self.backup_button.setEnabled(True)

    # -- operations --------------------------------------------------------

    def sort_into_folders(self) -> None:
        if self.root is None:
            return

        movable = [
            e for e in self._entries if e.path.parent != self.root / e.category.value
        ]

        if not movable:
            self.window._set_status("Everything is already in a category folder.")
            return

        answer = QMessageBox.question(
            self,
            "Sort into folders",
            f"Move {format_count(len(movable))} files into folders named after "
            f"their type?\n\nThis can be undone from the Activity tab.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        result = operations.sort_into_categories(movable, self.window.journal, root=self.root)
        self._report(result)

    def quarantine_entries(self, entries: list[FileEntry]) -> None:
        if not entries or self.root is None:
            return

        if self.window.settings.confirm_before_quarantine:
            size = sum(e.size for e in entries)
            answer = QMessageBox.question(
                self,
                "Move to quarantine",
                f"Move {format_count(len(entries))} files ({format_bytes(size)}) to the "
                "quarantine folder?\n\nNothing is deleted. Undo restores them.",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        result = operations.quarantine(
            entries, self.window.journal, root=self.root, reason="selected in library"
        )
        self._report(result)

    def backup_entries(self, entries: list[FileEntry]) -> None:
        if not entries:
            return

        destination = QFileDialog.getExistingDirectory(self, "Back up to")
        if not destination:
            return

        result = operations.copy_backups(entries, Path(destination))
        self._report(result, rescan=False)

    def backup_selection(self) -> None:
        self.backup_entries(self._selected())

    def quarantine_selection(self) -> None:
        self.quarantine_entries(self._selected())

    def _report(self, result, *, rescan: bool = True) -> None:
        if result.errors:
            QMessageBox.warning(
                self,
                "Finished with errors",
                result.summary() + "\n\n" + "\n".join(result.errors[:10]),
            )
        self.window._set_status(result.summary())
        self.window._refresh_undo_state()

        if rescan and self.window.root:
            self.window.rescan()
