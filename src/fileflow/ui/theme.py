"""Application-wide styling.

A single stylesheet rather than per-widget inline styles. The palette is
defined once here so the sidebar, tables and dialogs cannot drift apart, and
so light and dark stay in step.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

# Neutral, slightly cool greys. A file tool spends most of its life looking at
# lists, so the chrome stays quiet and the filenames carry the contrast.
DARK = {
    "bg": "#14161a",
    "surface": "#1b1e24",
    "surface_alt": "#21252c",
    "border": "#2a2f38",
    "text": "#e6e9ee",
    "text_muted": "#8b93a1",
    "text_faint": "#5d6572",
    "accent": "#6d8cff",
    "accent_hover": "#8099ff",
    "accent_text": "#ffffff",
    "success": "#46b880",
    "warning": "#d9a441",
    "danger": "#e05c5c",
    "selection": "#2b3350",
}

LIGHT = {
    "bg": "#f6f7f9",
    "surface": "#ffffff",
    "surface_alt": "#f0f2f5",
    "border": "#dfe3e8",
    "text": "#1b1e24",
    "text_muted": "#5d6572",
    "text_faint": "#8b93a1",
    "accent": "#4263eb",
    "accent_hover": "#3350d8",
    "accent_text": "#ffffff",
    "success": "#2f8f63",
    "warning": "#a9761a",
    "danger": "#c33c3c",
    "selection": "#dde4ff",
}

_current: dict[str, str] = dict(DARK)


def palette() -> dict[str, str]:
    return dict(_current)


def apply_theme(app: QApplication, name: str = "dark") -> None:
    """Apply the named theme. Unknown names fall back to dark."""
    global _current

    _current = dict(LIGHT if name == "light" else DARK)

    app.setStyleSheet(_build_stylesheet(_current))

    qpalette = QPalette()
    qpalette.setColor(QPalette.ColorRole.Window, QColor(_current["bg"]))
    qpalette.setColor(QPalette.ColorRole.WindowText, QColor(_current["text"]))
    qpalette.setColor(QPalette.ColorRole.Base, QColor(_current["surface"]))
    qpalette.setColor(QPalette.ColorRole.Text, QColor(_current["text"]))
    qpalette.setColor(QPalette.ColorRole.Highlight, QColor(_current["selection"]))
    qpalette.setColor(QPalette.ColorRole.HighlightedText, QColor(_current["text"]))
    app.setPalette(qpalette)


def _build_stylesheet(c: dict[str, str]) -> str:
    return f"""
    QWidget {{
        background: {c["bg"]};
        color: {c["text"]};
        font-size: 13px;
    }}

    /* Labels must not paint the window colour, or every one of them shows up
       as an opaque block against a differently-coloured parent such as the
       sidebar. */
    QLabel {{
        background: transparent;
    }}

    QFrame#Sidebar {{
        background: {c["surface"]};
        border-right: 1px solid {c["border"]};
    }}

    QLabel#BrandTitle {{
        font-size: 16px;
        font-weight: 600;
        color: {c["text"]};
    }}

    QLabel#BrandSubtitle {{
        font-size: 11px;
        color: {c["text_faint"]};
    }}

    QLabel#PageTitle {{
        font-size: 20px;
        font-weight: 600;
    }}

    QLabel#PageSubtitle, QLabel#Muted {{
        color: {c["text_muted"]};
        font-size: 12px;
    }}

    QLabel#StatValue {{
        font-size: 22px;
        font-weight: 600;
    }}

    QLabel#StatLabel {{
        color: {c["text_muted"]};
        font-size: 11px;
    }}

    QPushButton#NavButton {{
        background: transparent;
        border: none;
        border-radius: 6px;
        padding: 8px 12px;
        text-align: left;
        color: {c["text_muted"]};
    }}

    QPushButton#NavButton:hover {{
        background: {c["surface_alt"]};
        color: {c["text"]};
    }}

    QPushButton#NavButton:checked {{
        background: {c["selection"]};
        color: {c["text"]};
        font-weight: 600;
    }}

    QPushButton {{
        background: {c["surface_alt"]};
        border: 1px solid {c["border"]};
        border-radius: 6px;
        padding: 6px 14px;
        color: {c["text"]};
    }}

    QPushButton:hover {{
        border-color: {c["text_faint"]};
    }}

    QPushButton:disabled {{
        color: {c["text_faint"]};
        border-color: {c["border"]};
    }}

    QPushButton#Primary {{
        background: {c["accent"]};
        border-color: {c["accent"]};
        color: {c["accent_text"]};
        font-weight: 600;
    }}

    QPushButton#Primary:hover {{
        background: {c["accent_hover"]};
        border-color: {c["accent_hover"]};
    }}

    QPushButton#Primary:disabled {{
        background: {c["surface_alt"]};
        border-color: {c["border"]};
        color: {c["text_faint"]};
    }}

    QPushButton#Danger {{
        color: {c["danger"]};
        border-color: {c["border"]};
    }}

    QPushButton#Danger:hover:!disabled {{
        background: {c["danger"]};
        border-color: {c["danger"]};
        color: {c["accent_text"]};
    }}

    /* An id selector outranks a bare `:disabled`, so without this a disabled
       danger button still reads as clickable. */
    QPushButton#Danger:disabled {{
        color: {c["text_faint"]};
        border-color: {c["border"]};
        background: {c["surface_alt"]};
    }}

    QLineEdit, QComboBox, QSpinBox, QPlainTextEdit, QTextEdit {{
        background: {c["surface"]};
        border: 1px solid {c["border"]};
        border-radius: 6px;
        padding: 6px 8px;
        selection-background-color: {c["accent"]};
    }}

    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
        border-color: {c["accent"]};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}

    QComboBox QAbstractItemView {{
        background: {c["surface"]};
        border: 1px solid {c["border"]};
        selection-background-color: {c["selection"]};
        outline: none;
    }}

    QTableView, QTreeView, QListView {{
        background: {c["surface"]};
        alternate-background-color: {c["surface_alt"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        gridline-color: {c["border"]};
        selection-background-color: {c["selection"]};
        selection-color: {c["text"]};
        outline: none;
    }}

    QTableView::item, QTreeView::item, QListView::item {{
        padding: 5px 8px;
        border: none;
    }}

    QTableView::item:selected, QTreeView::item:selected,
    QListView::item:selected {{
        background: {c["selection"]};
    }}

    QHeaderView::section {{
        background: {c["surface_alt"]};
        color: {c["text_muted"]};
        border: none;
        border-bottom: 1px solid {c["border"]};
        padding: 7px 8px;
        font-size: 11px;
        font-weight: 600;
    }}

    QHeaderView::section:first {{
        border-top-left-radius: 8px;
    }}

    QHeaderView::section:last {{
        border-top-right-radius: 8px;
    }}

    QGroupBox {{
        border: 1px solid {c["border"]};
        border-radius: 8px;
        margin-top: 14px;
        padding: 12px;
        font-weight: 600;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 4px;
        color: {c["text_muted"]};
        font-size: 11px;
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 2px;
    }}

    QScrollBar::handle:vertical {{
        background: {c["border"]};
        border-radius: 5px;
        min-height: 30px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {c["text_faint"]};
    }}

    QScrollBar::add-line, QScrollBar::sub-line {{
        height: 0;
        width: 0;
    }}

    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        margin: 2px;
    }}

    QScrollBar::handle:horizontal {{
        background: {c["border"]};
        border-radius: 5px;
        min-width: 30px;
    }}

    QStatusBar {{
        background: {c["surface"]};
        border-top: 1px solid {c["border"]};
        color: {c["text_muted"]};
    }}

    QToolTip {{
        background: {c["surface_alt"]};
        color: {c["text"]};
        border: 1px solid {c["border"]};
        padding: 4px 6px;
    }}

    QProgressBar {{
        background: {c["surface_alt"]};
        border: none;
        border-radius: 3px;
        height: 6px;
        text-align: center;
        color: transparent;
    }}

    QProgressBar::chunk {{
        background: {c["accent"]};
        border-radius: 3px;
    }}

    QMenu {{
        background: {c["surface"]};
        border: 1px solid {c["border"]};
        border-radius: 6px;
        padding: 4px;
    }}

    QMenu::item {{
        padding: 6px 20px;
        border-radius: 4px;
    }}

    QMenu::item:selected {{
        background: {c["selection"]};
    }}
    """
