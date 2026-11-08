from PyQt6.QtCore import QByteArray, Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer

SVG_PATHS = {
    "grip": """
        <circle cx="9" cy="6" r="1.3" fill="{color}"/>
        <circle cx="15" cy="6" r="1.3" fill="{color}"/>
        <circle cx="9" cy="12" r="1.3" fill="{color}"/>
        <circle cx="15" cy="12" r="1.3" fill="{color}"/>
        <circle cx="9" cy="18" r="1.3" fill="{color}"/>
        <circle cx="15" cy="18" r="1.3" fill="{color}"/>
    """,
    "select": """
        <path d="M4 8V6a2 2 0 0 1 2-2h2" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
        <path d="M4 16v2a2 2 0 0 0 2 2h2" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
        <path d="M16 4h2a2 2 0 0 1 2 2v2" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
        <path d="M16 20h2a2 2 0 0 0 2-2v-2" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
        <rect x="3" y="3" width="3" height="3" rx="0.5" fill="{color}"/>
        <rect x="18" y="3" width="3" height="3" rx="0.5" fill="{color}"/>
        <rect x="3" y="18" width="3" height="3" rx="0.5" fill="{color}"/>
        <rect x="18" y="18" width="3" height="3" rx="0.5" fill="{color}"/>
    """,
    "cursor": """
        <path d="M5.5 3.5L18.5 11L12 13L9.5 19.5L5.5 3.5Z" stroke="{color}" stroke-width="1.8" stroke-linejoin="round"/>
    """,
    "rect": """
        <rect x="4" y="5" width="16" height="14" rx="2" stroke="{color}" stroke-width="1.8"/>
    """,
    "ellipse": """
        <ellipse cx="12" cy="12" rx="8.5" ry="7" stroke="{color}" stroke-width="1.8"/>
    """,
    "line": """
        <line x1="5" y1="19" x2="19" y2="5" stroke="{color}" stroke-width="1.9" stroke-linecap="round"/>
    """,
    "arrow": """
        <line x1="5" y1="19" x2="18.5" y2="5.5" stroke="{color}" stroke-width="1.9" stroke-linecap="round"/>
        <polyline points="10 5 19 5 19 14" stroke="{color}" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>
    """,
    "pen": """
        <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" stroke="{color}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="14" y1="6" x2="18" y2="10" stroke="{color}" stroke-width="1.6"/>
    """,
    "highlighter": """
        <path d="M9 11l-6 6v3h3l6-6" stroke="{color}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M22 12l-4.6 4.6a2 2 0 0 1-2.8 0l-5.2-5.2a2 2 0 0 1 0-2.8L14 4" stroke="{color}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="4" y1="21" x2="14" y2="21" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
    """,
    "text": """
        <path d="M5 6V4h14v2" stroke="{color}" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="12" y1="4" x2="12" y2="20" stroke="{color}" stroke-width="1.9" stroke-linecap="round"/>
        <line x1="9" y1="20" x2="15" y2="20" stroke="{color}" stroke-width="1.9" stroke-linecap="round"/>
    """,
    "callout": """
        <path d="M20 14a2 2 0 0 1-2 2H8l-4 4V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v8z" stroke="{color}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
    """,
    "step": """
        <circle cx="12" cy="12" r="8.5" stroke="{color}" stroke-width="1.8"/>
        <path d="M10.5 9.5L12.2 8v8" stroke="{color}" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>
    """,
    "blur": """
        <line x1="4" y1="9" x2="14" y2="19" stroke="{color}" stroke-width="1.7" stroke-linecap="round"/>
        <line x1="4" y1="14" x2="9" y2="19" stroke="{color}" stroke-width="1.7" stroke-linecap="round"/>
        <line x1="5" y1="5" x2="18" y2="18" stroke="{color}" stroke-width="1.7" stroke-linecap="round"/>
        <line x1="10" y1="5" x2="19" y2="14" stroke="{color}" stroke-width="1.7" stroke-linecap="round"/>
        <line x1="15" y1="5" x2="19" y2="9" stroke="{color}" stroke-width="1.7" stroke-linecap="round"/>
    """,
    "pixelate": """
        <rect x="4" y="4" width="16" height="16" rx="2" stroke="{color}" stroke-width="1.6"/>
        <line x1="9.3" y1="4" x2="9.3" y2="20" stroke="{color}" stroke-width="1.3"/>
        <line x1="14.6" y1="4" x2="14.6" y2="20" stroke="{color}" stroke-width="1.3"/>
        <line x1="4" y1="9.3" x2="20" y2="9.3" stroke="{color}" stroke-width="1.3"/>
        <line x1="4" y1="14.6" x2="20" y2="14.6" stroke="{color}" stroke-width="1.3"/>
    """,
    "magnifier": """
        <circle cx="11" cy="11" r="6.5" stroke="{color}" stroke-width="1.8"/>
        <line x1="16" y1="16" x2="20.5" y2="20.5" stroke="{color}" stroke-width="1.9" stroke-linecap="round"/>
        <line x1="11" y1="8.5" x2="11" y2="13.5" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="8.5" y1="11" x2="13.5" y2="11" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>
    """,
    "undo": """
        <path d="M3 9h11a5 5 0 0 1 0 10H9" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        <polyline points="7 5 3 9 7 13" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
    """,
    "copy": """
        <rect x="9" y="9" width="11" height="11" rx="2" stroke="{color}" stroke-width="1.8"/>
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
    """,
    "check": """
        <polyline points="20 6 9 17 4 12" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
    """,
    "heart": """
        <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" fill="{color}"/>
    """,
    "save": """
        <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" stroke="{color}" stroke-width="1.75" stroke-linejoin="round"/>
        <polyline points="17 21 17 13 7 13 7 21" stroke="{color}" stroke-width="1.6" stroke-linejoin="round"/>
        <polyline points="7 3 7 8 15 8" stroke="{color}" stroke-width="1.6" stroke-linejoin="round"/>
    """,
    "close": """
        <line x1="6" y1="6" x2="18" y2="18" stroke="{color}" stroke-width="1.9" stroke-linecap="round"/>
        <line x1="18" y1="6" x2="6" y2="18" stroke="{color}" stroke-width="1.9" stroke-linecap="round"/>
    """,
    "minimize": """
        <line x1="6" y1="12" x2="18" y2="12" stroke="{color}" stroke-width="1.9" stroke-linecap="round"/>
    """,
    "monitor": """
        <rect x="3" y="4" width="18" height="12" rx="2" stroke="{color}" stroke-width="1.8"/>
        <line x1="8" y1="20" x2="16" y2="20" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
        <line x1="12" y1="16" x2="12" y2="20" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
    """,
    "folder": """
        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" stroke="{color}" stroke-width="1.75" stroke-linejoin="round"/>
    """,
    "sliders": """
        <line x1="4" y1="6" x2="20" y2="6" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
        <line x1="4" y1="12" x2="20" y2="12" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
        <line x1="4" y1="18" x2="20" y2="18" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
        <circle cx="9" cy="6" r="2.3" fill="#1E1F23" stroke="{color}" stroke-width="1.8"/>
        <circle cx="15" cy="12" r="2.3" fill="#1E1F23" stroke="{color}" stroke-width="1.8"/>
        <circle cx="10" cy="18" r="2.3" fill="#1E1F23" stroke="{color}" stroke-width="1.8"/>
    """,
    "image": """
        <rect x="3" y="4" width="18" height="16" rx="2.5" stroke="{color}" stroke-width="1.8"/>
        <circle cx="8.5" cy="9.5" r="1.8" stroke="{color}" stroke-width="1.6"/>
        <path d="M21 15l-4.5-4.5L7 20" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
    """,
    "palette": """
        <path d="M12 3a9 9 0 0 0 0 18c1.65 0 3-1.35 3-3 0-.78-.3-1.48-.78-2-.47-.5-.72-1.15-.72-1.85 0-1.46 1.19-2.65 2.65-2.65H18a3 3 0 0 0 3-3c0-3.04-4.03-5.5-9-5.5z" stroke="{color}" stroke-width="1.8" stroke-linejoin="round"/>
        <circle cx="7.5" cy="10.5" r="1.2" fill="{color}"/>
        <circle cx="10.5" cy="7.5" r="1.2" fill="{color}"/>
        <circle cx="14.5" cy="7.5" r="1.2" fill="{color}"/>
    """,
    "keyboard": """
        <rect x="2.5" y="5" width="19" height="14" rx="2.5" stroke="{color}" stroke-width="1.8"/>
        <line x1="6" y1="9" x2="7.5" y2="9" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
        <line x1="11" y1="9" x2="13" y2="9" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
        <line x1="16.5" y1="9" x2="18" y2="9" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
        <line x1="6" y1="12.5" x2="8.5" y2="12.5" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
        <line x1="15.5" y1="12.5" x2="18" y2="12.5" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
        <line x1="8" y1="16" x2="16" y2="16" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
    """
}

_ICON_CACHE: dict[tuple[str, str, int], QIcon] = {}


def get_icon(name: str, color: str = "#E5E5EA", size: int = 20) -> QIcon:
    key = (name, color, size)
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]

    body = SVG_PATHS.get(name, SVG_PATHS["rect"]).format(color=color)
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">{body}</svg>'

    dpr = 2
    px_size = size * dpr
    pixmap = QPixmap(px_size, px_size)
    pixmap.fill(Qt.GlobalColor.transparent)

    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(painter)
    painter.end()

    pixmap.setDevicePixelRatio(dpr)
    icon = QIcon(pixmap)
    _ICON_CACHE[key] = icon
    return icon
