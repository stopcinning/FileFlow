"""Settings: preferences, and where FileFlow keeps its data."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...core.journal import data_dir, default_journal_path
from .. import theme
from ..widgets import format_count, horizontal_line, row

log = logging.getLogger("fileflow.settings")


class SettingsPage(QWidget):
    def __init__(self, window) -> None:
        super().__init__()
        self.window = window

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        layout.addLayout(self._build_header())
        layout.addWidget(horizontal_line())
        layout.addWidget(self._build_scanning())
        layout.addWidget(self._build_cleanup())
        layout.addWidget(self._build_safety())
        layout.addWidget(self._build_appearance())
        layout.addWidget(self._build_data())
        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

    # -- sections ----------------------------------------------------------

    def _build_header(self):
        box = QVBoxLayout()
        box.setSpacing(2)

        title = QLabel("Settings")
        title.setObjectName("PageTitle")

        subtitle = QLabel("Preferences are stored per user, in your data folder.")
        subtitle.setObjectName("PageSubtitle")

        box.addWidget(title)
        box.addWidget(subtitle)
        return row(box)

    def _build_scanning(self) -> QGroupBox:
        box = QGroupBox("Scanning")
        form = QFormLayout(box)
        form.setSpacing(10)

        settings = self.window.settings

        self.include_hidden = QCheckBox("Include hidden and dotfiles")
        self.include_hidden.setChecked(settings.include_hidden)
        self.include_hidden.toggled.connect(self._on_scan_option)

        self.skip_build = QCheckBox("Skip dependency and build folders")
        self.skip_build.setChecked(settings.skip_build_dirs)
        self.skip_build.setToolTip(
            "Faster on large projects, but you will not see what is inside "
            "node_modules, dist, .venv and similar folders."
        )
        self.skip_build.toggled.connect(self._on_scan_option)

        form.addRow(self.include_hidden)
        form.addRow(self.skip_build)
        return box

    def _build_cleanup(self) -> QGroupBox:
        box = QGroupBox("Cleanup suggestions")
        form = QFormLayout(box)
        form.setSpacing(10)

        self.stale_days = QSpinBox()
        self.stale_days.setRange(7, 3650)
        self.stale_days.setValue(self.window.settings.stale_days)
        self.stale_days.setSuffix(" days")
        self.stale_days.valueChanged.connect(self._on_stale_days)

        self.large_mb = QSpinBox()
        self.large_mb.setRange(1, 1024 * 128)
        self.large_mb.setValue(self.window.settings.large_file_mb)
        self.large_mb.setSuffix(" MB")
        self.large_mb.valueChanged.connect(self._on_large_mb)

        form.addRow("Flag files untouched after", self.stale_days)
        form.addRow("Treat files over this size as large", self.large_mb)
        return box

    def _build_safety(self) -> QGroupBox:
        box = QGroupBox("Safety")
        form = QFormLayout(box)
        form.setSpacing(10)

        self.confirm = QCheckBox("Ask before moving files to quarantine")
        self.confirm.setChecked(self.window.settings.confirm_before_quarantine)
        self.confirm.toggled.connect(self._on_confirm)

        self.retention = QSpinBox()
        self.retention.setRange(1, 365)
        self.retention.setValue(self.window.settings.journal_retention_days)
        self.retention.setSuffix(" days")
        self.retention.setToolTip(
            "How long changes stay undoable. Older entries are pruned when you ask."
        )
        self.retention.valueChanged.connect(self._on_retention)

        form.addRow(self.confirm)
        form.addRow("Keep undo history for", self.retention)

        note = QLabel(
            "FileFlow never deletes files as part of organising. Removals go to a "
            "quarantine folder and can be undone until the history is pruned."
        )
        note.setObjectName("Muted")
        note.setWordWrap(True)
        form.addRow(note)
        return box

    def _build_appearance(self) -> QGroupBox:
        box = QGroupBox("Appearance")
        form = QFormLayout(box)
        form.setSpacing(10)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Dark", "dark")
        self.theme_combo.addItem("Light", "light")
        self.theme_combo.setCurrentIndex(1 if self.window.settings.theme == "light" else 0)
        self.theme_combo.currentIndexChanged.connect(self._on_theme)

        form.addRow("Theme", self.theme_combo)
        return box

    def _build_data(self) -> QGroupBox:
        box = QGroupBox("Stored data")
        layout = QVBoxLayout(box)
        layout.setSpacing(8)

        self.data_label = QLabel()
        self.data_label.setObjectName("Muted")
        self.data_label.setWordWrap(True)
        self.data_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.data_label)

        open_button = QPushButton("Open data folder")
        open_button.clicked.connect(self._open_data_folder)

        reveal_log = QPushButton("Open log file")
        reveal_log.clicked.connect(self._open_log)

        layout.addLayout(row(open_button, reveal_log, spacing=8))
        self._update_data_label()
        return box

    # -- handlers ----------------------------------------------------------

    def _update_data_label(self) -> None:
        directory = data_dir()
        journal = default_journal_path()

        size = 0
        if journal.exists():
            size = journal.stat().st_size
        for suffix in ("-wal", "-shm"):
            extra = journal.with_name(journal.name + suffix)
            if extra.exists():
                size += extra.stat().st_size

        entries = self.window.journal.count(include_undone=True)
        self.data_label.setText(
            f"Settings, rules and the undo journal live in\n{directory}\n\n"
            f"{format_count(entries)} journal entries · {size / 1024:.0f} KB on disk"
        )

    def _on_scan_option(self, *_args) -> None:
        self.window.settings.include_hidden = self.include_hidden.isChecked()
        self.window.settings.skip_build_dirs = self.skip_build.isChecked()
        self.window.persist_settings()
        self.window._set_status("Rescanning with the new options…")
        self.window.rescan()

    def _on_stale_days(self, value: int) -> None:
        self.window.settings.stale_days = value
        self.window.persist_settings()

    def _on_large_mb(self, value: int) -> None:
        self.window.settings.large_file_mb = value
        self.window.persist_settings()

    def _on_confirm(self, checked: bool) -> None:
        self.window.settings.confirm_before_quarantine = checked
        self.window.persist_settings()

    def _on_retention(self, value: int) -> None:
        self.window.settings.journal_retention_days = value
        self.window.persist_settings()

    def _on_theme(self, _index: int) -> None:
        name = self.theme_combo.currentData()
        self.window.settings.theme = name
        self.window.persist_settings()
        theme.apply_theme(self.window, name)

    def _open_data_folder(self) -> None:
        self.window.reveal_in_explorer(data_dir() / "settings.json")

    def _open_log(self) -> None:
        from ...log_setup import log_file

        path = log_file()
        if path.exists():
            self.window.reveal_in_explorer(path)
        else:
            QMessageBox.information(
                self, "No log yet", f"Nothing has been logged to\n{path}"
            )
