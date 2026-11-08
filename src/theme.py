import colorsys
from dataclasses import dataclass
from PIL import Image, ImageFilter, ImageOps
from PyQt6.QtGui import QImage, QPixmap, QColor

DEFAULT_ACCENT = "#2563EB"
ACCENT_PRESETS = ["#2563EB", "#7C3AED", "#DB2777", "#EA580C", "#16A34A", "#0891B2"]


@dataclass
class Palette:
    accent: str = DEFAULT_ACCENT
    accent_hover: str = "#1D4ED8"
    on_accent: str = "#FFFFFF"
    tint: tuple = (26, 27, 32)
    base: tuple = (16, 17, 20)


CURRENT = Palette()


def _clamp(v, lo=0, hi=255):
    return int(max(lo, min(hi, v)))


def _hex(rgb) -> str:
    return "#%02X%02X%02X" % tuple(_clamp(c) for c in rgb)


def _hls(h, l, s) -> tuple:
    return tuple(_clamp(round(c * 255)) for c in colorsys.hls_to_rgb(h, l, s))


def rgba(rgb, a) -> str:
    return f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {a})"


def palette_from_accent(accent_hex: str, tint=None) -> Palette:
    c = QColor(accent_hex)
    r, g, b = c.red(), c.green(), c.blue()
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    hover = _hls(h, max(0.0, l - 0.08), s)
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    on_accent = "#111214" if luminance > 175 else "#FFFFFF"
    if tint is None:
        tint = _hls(h, 0.11, min(s, 0.16))
    base = tuple(_clamp(v * 0.62) for v in tint)
    return Palette(_hex((r, g, b)), _hex(hover), on_accent, tint, base)


def extract_palette(img: Image.Image) -> Palette:
    small = img.convert("RGB").resize((40, 40), Image.Resampling.BILINEAR)
    quant = small.quantize(colors=8, method=Image.Quantize.MEDIANCUT)
    pal = quant.getpalette() or []
    colors = quant.getcolors() or []
    total = sum(c for c, _ in colors) or 1

    best, best_score = None, -1.0
    for count, idx in colors:
        r, g, b = pal[idx * 3: idx * 3 + 3]
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if l < 0.12 or l > 0.92:
            continue
        score = s * (0.35 + count / total) * (1.0 - abs(l - 0.5))
        if score > best_score:
            best_score, best = score, (h, l, s)

    avg = small.resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
    ah, _al, a_s = colorsys.rgb_to_hls(*(v / 255 for v in avg))
    tint = _hls(ah, 0.12, min(a_s, 0.30))

    if best is None or best[2] < 0.12:
        return palette_from_accent(DEFAULT_ACCENT, tint)
    h, l, s = best
    accent = _hls(h, min(0.62, max(0.50, l)), max(0.55, min(0.85, s)))
    return palette_from_accent(_hex(accent), tint)


def load_fitted(path: str, size: tuple[int, int]):
    try:
        img = Image.open(path)
        img.draft("RGB", (size[0] * 2, size[1] * 2))
        img = ImageOps.exif_transpose(img).convert("RGB")
        return ImageOps.fit(img, size, Image.Resampling.LANCZOS)
    except Exception:
        return None


def pil_to_pixmap(img: Image.Image) -> QPixmap:
    data = img.convert("RGBA").tobytes("raw", "BGRA")
    qimg = QImage(data, img.width, img.height, img.width * 4, QImage.Format.Format_ARGB32).copy()
    return QPixmap.fromImage(qimg)


def blurred_pixmap(img: Image.Image, radius: int) -> QPixmap:
    if radius <= 0:
        return pil_to_pixmap(img)
    w, h = img.size
    small = img.resize((max(1, w // 2), max(1, h // 2)), Image.Resampling.BILINEAR)
    return pil_to_pixmap(small.filter(ImageFilter.GaussianBlur(radius / 2)))


def build_qss(p: Palette) -> str:
    a, ah, on = p.accent, p.accent_hover, p.on_accent
    ac = QColor(a)
    acc = (ac.red(), ac.green(), ac.blue())
    t = p.tint
    t_hover = tuple(_clamp(v + 14) for v in t)
    return f"""
    QWidget {{
        color: #F2F2F7;
        font-family: "Segoe UI", sans-serif;
        font-size: 13px;
    }}
    QLabel {{ background: transparent; }}
    QFrame#Sidebar {{
        background-color: rgba(0, 0, 0, 78);
        border: none;
        border-right: 1px solid rgba(255, 255, 255, 18);
        border-top-left-radius: 14px;
        border-bottom-left-radius: 14px;
    }}
    QLabel[role="AppName"] {{ font-size: 15px; font-weight: 700; }}
    QLabel[role="Muted"] {{ color: rgba(235, 235, 245, 155); font-size: 12px; }}
    QLabel[role="PageTitle"] {{ font-size: 20px; font-weight: 700; }}
    QLabel[role="Section"] {{
        color: rgba(235, 235, 245, 145); font-size: 11px; font-weight: 700;
        letter-spacing: 0.5px; padding-left: 2px;
    }}
    QLabel[role="RowTitle"] {{ font-size: 13px; font-weight: 500; }}
    QLabel[role="RowIcon"] {{ background-color: rgba(255, 255, 255, 16); border-radius: 8px; }}
    QLabel[role="Chip"] {{
        background-color: rgba(0, 0, 0, 75); border: 1px solid rgba(255, 255, 255, 30);
        border-radius: 6px; padding: 3px 9px; font-size: 11px; font-weight: 600;
        font-family: "Consolas", monospace;
        color: rgba(255, 255, 255, 225);
    }}
    QLabel[role="TileIcon"] {{ background-color: {a}; border-radius: 10px; }}
    QLabel[role="TileTitle"] {{ font-size: 15px; font-weight: 700; color: #FFFFFF; }}

    QFrame[role="Card"] {{
        background-color: {rgba(t, 165)};
        border: 1px solid rgba(255, 255, 255, 22);
        border-radius: 12px;
    }}
    QFrame[role="ActionTile"] {{
        background-color: {rgba(t, 165)};
        border: 1px solid rgba(255, 255, 255, 24);
        border-radius: 13px;
    }}
    QFrame[role="ActionTile"]:hover {{
        background-color: {rgba(t_hover, 190)};
        border: 1px solid {rgba(acc, 185)};
    }}
    QFrame[role="Divider"] {{ background-color: rgba(255, 255, 255, 15); border: none; }}

    QPushButton {{
        background-color: rgba(255, 255, 255, 16);
        border: 1px solid rgba(255, 255, 255, 26);
        border-radius: 8px;
        padding: 6px 14px;
        font-size: 12px;
        font-weight: 600;
        color: #F2F2F7;
    }}
    QPushButton:hover {{
        background-color: rgba(255, 255, 255, 26);
        border-color: rgba(255, 255, 255, 45);
    }}
    QPushButton:pressed {{ background-color: rgba(255, 255, 255, 12); }}
    QPushButton[role="Primary"] {{
        background-color: {a};
        border: 1px solid {a};
        color: {on};
        font-weight: 600;
        padding: 6px 16px;
    }}
    QPushButton[role="Primary"]:hover {{
        background-color: {ah};
        border-color: {ah};
    }}

    QPushButton[role="Nav"] {{
        text-align: left;
        background: transparent;
        border: none;
        border-radius: 9px;
        padding: 9px 12px;
        font-size: 13px;
        font-weight: 500;
        color: rgba(255, 255, 255, 200);
    }}
    QPushButton[role="Nav"]:hover {{ background-color: rgba(255, 255, 255, 14); }}
    QPushButton[role="Nav"]:checked {{
        background-color: {rgba(acc, 75)};
        color: #FFFFFF;
        font-weight: 600;
    }}

    QPushButton[role="WinBtn"] {{
        background: transparent;
        border: none;
        border-radius: 8px;
        min-height: 30px; max-height: 30px;
        min-width: 30px; max-width: 30px;
        padding: 0px;
    }}
    QPushButton[role="WinBtn"]:hover {{ background-color: rgba(255, 255, 255, 22); }}
    QPushButton#WinClose:hover {{ background-color: #E5484D; }}

    QPushButton[role="HotkeyField"] {{
        min-width: 165px;
        font-family: "Consolas", monospace;
        font-size: 12px;
        font-weight: 600;
        padding: 6px 12px;
        background-color: rgba(0, 0, 0, 65);
    }}
    QPushButton[role="HotkeyField"][recording="true"] {{
        background-color: {rgba(acc, 55)};
        border: 1px solid {a};
        color: #FFFFFF;
    }}

    QPushButton[role="ToolChip"] {{
        text-align: left;
        padding: 8px 12px;
        font-size: 12px;
        font-weight: 500;
    }}
    QPushButton[role="ToolChip"]:checked {{
        background-color: {rgba(acc, 65)};
        border: 1px solid {rgba(acc, 195)};
        color: #FFFFFF;
        font-weight: 600;
    }}
    QPushButton[role="ToolChip"]:disabled {{ color: rgba(255, 255, 255, 130); }}

    QFrame[role="Segmented"] {{
        background-color: rgba(0, 0, 0, 65);
        border: 1px solid rgba(255, 255, 255, 22);
        border-radius: 9px;
    }}
    QPushButton[role="Segment"] {{
        background: transparent;
        border: none;
        border-radius: 7px;
        padding: 5px 14px;
        font-size: 12px;
        color: rgba(255, 255, 255, 190);
    }}
    QPushButton[role="Segment"]:hover {{ background-color: rgba(255, 255, 255, 14); }}
    QPushButton[role="Segment"]:checked {{
        background-color: {a};
        color: {on};
        font-weight: 600;
    }}

    QSlider::groove:horizontal {{
        height: 4px;
        background: rgba(255, 255, 255, 32);
        border-radius: 2px;
    }}
    QSlider::sub-page:horizontal {{
        background: {a};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: #FFFFFF;
        width: 16px;
        height: 16px;
        margin: -6px 0;
        border-radius: 8px;
    }}

    QToolTip {{
        background-color: #1C1D21;
        color: #F2F2F7;
        border: 1px solid rgba(255, 255, 255, 30);
        padding: 4px 8px;
        border-radius: 6px;
    }}
    """
