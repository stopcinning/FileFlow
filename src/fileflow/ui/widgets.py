"""Shared widgets: byte formatting, stat tiles, empty states, a file table model.

Kept in one module because each of these is small and they are used by more
than one page.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPoint, Qt, Signal
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QMenu,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..core.models import Category, FileEntry
from . import theme

UNITS = ("B", "KB", "MB", "GB", "TB", "PB")

# Role the model publishes the FileEntry on, so context menus and click
# handlers can get at the real object instead of reconstructing it from text.
ENTRY_ROLE = Qt.ItemDataRole.UserRole + 1


def format_bytes(value: float, *, precise: bool = False) -> str:
    """Human-readable size, decimal units, matching Windows Explorer."""
    if value < 0:
        return "—"
    if value == 0:
        return "0 B"

    size = float(value)
    unit = UNITS[0]
    for candidate in UNITS:
        unit = candidate
        if abs(size) < 1000 or candidate == UNITS[-1]:
            break
        size /= 1000.0

    if unit == "B":
        return f"{int(size)} B"
    return f"{size:.2f} {unit}" if precise else f"{size:.1f} {unit}"


def format_count(value: int) -> str:
    return f"{value:,}"


def format_age(timestamp: float) -> str:
    """Relative while that is useful, absolute once it stops being."""
    delta = datetime.now().timestamp() - timestamp

    if delta < 60:
        return "just now"
    if delta < 3600:
        return f"{int(delta // 60)}m ago"
    if delta < 86_400:
        return f"{int(delta // 3600)}h ago"
    if delta < 604_800:
        return f"{int(delta // 86_400)}d ago"

    return datetime.fromtimestamp(timestamp).strftime("%d %b %Y")


def elide_middle(text: str, limit: int = 48) -> str:
    if len(text) <= limit:
        return text
    keep = max(1, (limit - 1) // 2)
    return f"{text[:keep]}…{text[-keep:]}"


class StatTile(QFrame):
    """A single number with a caption. Used in the library header."""

    def __init__(self, label: str, value: str = "—", parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._value = QLabel(value)
        self._value.setObjectName("StatValue")

        self._label = QLabel(label)
        self._label.setObjectName("StatLabel")

        layout.addWidget(self._value)
        layout.addWidget(self._label)

    def set_value(self, value: str) -> None:
        self._value.setText(value)

    def set_label(self, label: str) -> None:
        self._label.setText(label)


class EmptyState(QWidget):
    """Shown instead of an empty table.

    Explains what to do rather than just reporting that there is nothing here,
    and offers the one action that fixes it when there is an obvious one.
    """

    clicked = Signal()

    def __init__(
        self,
        title: str,
        detail: str = "",
        action_text: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)

        heading = QLabel(title)
        heading.setObjectName("PageTitle")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(heading)

        if detail:
            body = QLabel(detail)
            body.setObjectName("Muted")
            body.setWordWrap(True)
            body.setAlignment(Qt.AlignmentFlag.AlignCenter)
            body.setMaximumWidth(440)
            layout.addWidget(body, alignment=Qt.AlignmentFlag.AlignHCenter)

        if action_text:
            button = QPushButton(action_text)
            button.setObjectName("Primary")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(self.clicked)
            layout.addSpacing(6)
            layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignHCenter)


class FileTableModel(QAbstractTableModel):
    """Table model over a list of `FileEntry`.

    Filtering is done in Python rather than through a proxy. The sets are small
    enough that a second pass is cheaper than the indirection, and it lets the
    text filter and the category filter compose without a proxy subclass.
    """

    COLUMNS = ("Name", "Folder", "Size", "Modified", "Type")

    activated = Signal(object)  # FileEntry

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._all: list[FileEntry] = []
        self._shown: list[FileEntry] = []
        self._root: Path | None = None

    # -- population --------------------------------------------------------

    def set_entries(self, entries: list[FileEntry], root: Path | None = None) -> None:
        self.beginResetModel()
        self._all = list(entries)
        self._shown = list(entries)
        self._root = root
        self.endResetModel()

    def clear(self) -> None:
        self.set_entries([], None)

    def entry_at(self, row: int) -> FileEntry | None:
        if 0 <= row < len(self._shown):
            return self._shown[row]
        return None

    @property
    def entries(self) -> list[FileEntry]:
        return list(self._shown)

    @property
    def total_entries(self) -> int:
        return len(self._all)

    def filter(
        self,
        *,
        text: str = "",
        category: Category | None = None,
        min_size: int = 0,
    ) -> None:
        needle = text.strip().lower()

        def keep(entry: FileEntry) -> bool:
            if category is not None and entry.category is not category:
                return False
            if entry.size < min_size:
                return False
            if needle:
                haystack = f"{entry.name} {entry.parent}".lower()
                if needle not in haystack:
                    return False
            return True

        self.beginResetModel()
        self._shown = [e for e in self._all if keep(e)]
        self.endResetModel()

    # -- Qt model interface ------------------------------------------------

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._shown)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        entry = self._shown[index.row()]
        column = index.column()

        if role == ENTRY_ROLE:
            return entry

        if role == Qt.ItemDataRole.DisplayRole:
            return {
                0: entry.name,
                1: self._relative_folder(entry),
                2: format_bytes(entry.size),
                3: format_age(entry.mtime),
                4: entry.category.value,
            }.get(column)

        if role == Qt.ItemDataRole.TextAlignmentRole and column == 2:
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        if role == Qt.ItemDataRole.ToolTipRole:
            return (
                f"{entry.path}\n"
                f"{format_bytes(entry.size, precise=True)}"
                f" · modified {entry.modified:%Y-%m-%d %H:%M}"
            )

        if role == Qt.ItemDataRole.ForegroundRole and column in (1, 2, 3, 4):
            return QColor(theme.palette()["text_muted"])

        return None

    def headerData(self, section: int, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.COLUMNS[section]
        return section + 1

    def _relative_folder(self, entry: FileEntry) -> str:
        if self._root is None:
            return str(entry.parent)
        try:
            relative = entry.parent.relative_to(self._root)
        except ValueError:
            return str(entry.parent)
        return "." if str(relative) == "." else str(relative)


def attach_context_menu(view: QWidget, actions_for) -> None:
    """Right-click menu on a table or list.

    `actions_for(index)` returns `[(label, handler), ...]`, where a label of
    `None` inserts a separator.
    """

    def show(position: QPoint) -> None:
        index = view.indexAt(position)
        if not index.isValid():
            return

        menu = QMenu(view)
        for label, handler in actions_for(index):
            if label is None:
                menu.addSeparator()
                continue
            action = QAction(label, view)
            action.triggered.connect(lambda _checked=False, h=handler: h(index))
            menu.addAction(action)

        if menu.actions():
            menu.exec(view.viewport().mapToGlobal(position))

    view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    view.customContextMenuRequested.connect(show)


def horizontal_line() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    line.setStyleSheet(f"background: {theme.palette()['border']}; border: none;")
    return line


def grow(widget: QWidget) -> QWidget:
    widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    return widget


def row(
    *items, spacing: int = 8, margins: tuple[int, int, int, int] = (0, 0, 0, 0)
) -> QHBoxLayout:
    """Horizontal layout.

    Accepts widgets, nested layouts, or `None` for a stretch. Handling all three
    at the call site reads better than interleaving `addWidget`/`addLayout`/
    `addStretch` by hand.
    """
    layout = QHBoxLayout()
    layout.setSpacing(spacing)
    layout.setContentsMargins(*margins)

    for item in items:
        if item is None:
            layout.addStretch()
        elif isinstance(item, QLayout):
            layout.addLayout(item)
        else:
            layout.addWidget(item)

    return layout


__all__ = [
    "ENTRY_ROLE",
    "EmptyState",
    "FileTableModel",
    "StatTile",
    "attach_context_menu",
    "elide_middle",
    "format_age",
    "format_bytes",
    "format_count",
    "grow",
    "horizontal_line",
    "row",
]
