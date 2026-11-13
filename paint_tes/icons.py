"""Small code-native SVG toolbar icons; no platform icon-theme dependency."""

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

PATHS = {
    "new": '<path d="M6 3h8l5 5v13H6zM14 3v6h5M9 14h7M12.5 10.5v7"/>',
    "open": '<path d="M3 20V6h7l2 3h9v3M3 20l4-8h15l-4 8z"/>',
    "save": '<path d="M4 3h14l3 3v15H4zM8 3v6h9V3M8 21v-8h9v8"/>',
    "undo": '<path d="m8 5-5 5 5 5M3 10h10c8 0 9 10 1 10"/>',
    "redo": '<path d="m16 5 5 5-5 5M21 10H11C3 10 2 20 10 20"/>',
    "fit": '<path d="M8 3H3v5M16 3h5v5M21 16v5h-5M8 21H3v-5M7 8h10v8H7z"/>',
    "actual": '<path d="M5 7h3v10M5 17h6M15 7h3v10M15 17h6"/>',
    "settings": '<path d="M4 6h16M4 12h16M4 18h16"/><circle cx="8" cy="6" r="2"/><circle cx="16" cy="12" r="2"/><circle cx="10" cy="18" r="2"/>',
    "hand": '<path d="M7 11V6a1.5 1.5 0 0 1 3 0v4-7a1.5 1.5 0 0 1 3 0v7-5a1.5 1.5 0 0 1 3 0v6-3a1.5 1.5 0 0 1 3 0v7c0 5-3 7-7 7-3 0-5-3-7-6l-2-3c-1-2 2-3 3-1l1 1"/>',
    "rectangle": '<rect x="4" y="5" width="16" height="14" stroke-dasharray="3 3"/>',
    "ellipse": '<ellipse cx="12" cy="12" rx="9" ry="7" stroke-dasharray="3 3"/>',
    "lasso": '<path d="M8 17c-6-1-7-8-2-11 6-4 15-2 15 4 0 5-5 8-10 8-4 0-6 3-3 4 3 0 3-5 0-6-2-1-3 1-2 2" stroke-dasharray="3 1"/>',
    "polygon": '<path d="m4 5 13-2 4 12-10 6-9-8z" stroke-dasharray="3 2"/>',
    "brush": '<path d="m10 14 9-12 3 3-10 11M10 14c-4-2-5 3-7 5 4 2 9 1 9-3z"/>',
    "eraser": '<path d="m4 13 10-10 8 8-10 10H8zM9 8l8 8M12 21h10"/>',
    "color": '<path d="M12 3c-12 0-13 18-2 18 6 0-2-6 3-6h4c8 0 5-12-5-12z"/><circle cx="7" cy="9" r="1"/><circle cx="11" cy="6" r="1"/><circle cx="16" cy="7" r="1"/><circle cx="18" cy="11" r="1"/>',
}


def icon(name):
    result = QIcon()
    for mode, color in ((QIcon.Mode.Normal, "#eed9bc"), (QIcon.Mode.Disabled, "#796c5d")):
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><g fill="none" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{PATHS[name]}</g></svg>'
        for size in (24, 48):
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            QSvgRenderer(QByteArray(svg.encode())).render(painter)
            painter.end()
            result.addPixmap(pixmap, mode)
    return result
