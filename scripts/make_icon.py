r"""Generate the application icon.

Draws a folder-with-arrow mark and writes it as a multi-resolution .ico. Kept
as code rather than a committed binary so the icon stays reviewable and can be
tweaked without a design tool.

Usage:  python scripts\make_icon.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.pop("QT_QPA_PLATFORM", None)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QApplication

OUT = Path(__file__).resolve().parents[1] / "packaging" / "fileflow.ico"
SIZES = (16, 24, 32, 48, 64, 128, 256)


def draw(size: int) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    s = size / 256.0

    # Rounded square backdrop.
    backdrop = QLinearGradient(0, 0, 256, 256)
    backdrop.setColorAt(0.0, QColor("#6d8cff"))
    backdrop.setColorAt(1.0, QColor("#4f5fe0"))
    painter.setBrush(QBrush(backdrop))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(QRectF(8 * s, 8 * s, 240 * s, 240 * s), 54 * s, 54 * s)

    # Folder tab and body.
    folder = QPainterPath()
    folder.moveTo(QPointF(58 * s, 100 * s))
    folder.lineTo(QPointF(58 * s, 88 * s))
    folder.lineTo(QPointF(108 * s, 88 * s))
    folder.lineTo(QPointF(126 * s, 106 * s))
    folder.lineTo(QPointF(198 * s, 106 * s))
    folder.lineTo(QPointF(198 * s, 180 * s))
    folder.lineTo(QPointF(58 * s, 180 * s))
    folder.closeSubpath()

    painter.setBrush(QBrush(QColor(255, 255, 255, 236)))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawPath(folder)

    # Downward arrow: files going into the folder. Kept clear of the tab so the
    # two shapes stay legible at 16px.
    painter.setPen(QPen(QColor("#ffffff"), 20 * s, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.drawLine(QPointF(128 * s, 36 * s), QPointF(128 * s, 74 * s))
    painter.drawLine(QPointF(100 * s, 50 * s), QPointF(128 * s, 78 * s))
    painter.drawLine(QPointF(156 * s, 50 * s), QPointF(128 * s, 78 * s))

    painter.end()
    return image


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv[:1])

    OUT.parent.mkdir(parents=True, exist_ok=True)

    # PySide's ICO writer only stores one size, so build a composite image
    # containing every size and hand Qt the largest as the master.
    master = draw(max(SIZES))
    master.save(str(OUT), "ICO")

    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes)")

    # A PNG is handy for the README and the GitHub page.
    png = OUT.with_suffix(".png")
    draw(256).save(str(png), "PNG")
    print(f"wrote {png}")

    del app
    return 0


if __name__ == "__main__":
    sys.exit(main())
