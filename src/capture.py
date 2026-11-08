from datetime import datetime
from pathlib import Path
import ctypes
from ctypes import wintypes
from PIL import Image, ImageFilter
from PyQt6.QtGui import QImage, QPixmap, QGuiApplication
from PyQt6.QtCore import QRect, QByteArray, QBuffer, QIODevice

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
SRCCOPY = 0x00CC0020
CAPTUREBLT = 0x40000000
BI_RGB = 0


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wintypes.DWORD * 3),
    ]


user32.GetDesktopWindow.restype = wintypes.HWND
user32.GetWindowDC.argtypes = [wintypes.HWND]
user32.GetWindowDC.restype = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.ReleaseDC.restype = ctypes.c_int
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int

gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.BitBlt.argtypes = [
    wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD,
]
gdi32.BitBlt.restype = wintypes.BOOL
gdi32.GetDIBits.argtypes = [
    wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
    ctypes.c_void_p, ctypes.POINTER(BITMAPINFO), wintypes.UINT,
]
gdi32.GetDIBits.restype = wintypes.c_int if hasattr(wintypes, "c_int") else ctypes.c_int
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = wintypes.BOOL


def grab_virtual_screen():
    x = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    y = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    w = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    h = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)

    if w <= 0 or h <= 0:
        screen = QGuiApplication.primaryScreen()
        pix = screen.grabWindow(0)
        return pix, screen.geometry()

    hwnd = user32.GetDesktopWindow()
    hdc_screen = user32.GetWindowDC(hwnd)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
    hbmp = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
    old_obj = gdi32.SelectObject(hdc_mem, hbmp)

    try:
        gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, x, y, SRCCOPY | CAPTUREBLT)

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = w
        bmi.bmiHeader.biHeight = -h
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB

        buf_len = w * h * 4
        raw_buf = ctypes.create_string_buffer(buf_len)
        gdi32.GetDIBits(hdc_mem, hbmp, 0, h, raw_buf, ctypes.byref(bmi), 0)

        qimg = QImage(raw_buf, w, h, w * 4, QImage.Format.Format_RGB32).copy()
        pixmap = QPixmap.fromImage(qimg)
    finally:
        gdi32.SelectObject(hdc_mem, old_obj)
        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(hwnd, hdc_screen)

    geom = QRect(x, y, w, h)
    return pixmap, geom


def apply_blur_region(base_pixmap: QPixmap, rect: QRect, intensity: int = 15, pixelate: bool = False) -> QPixmap:
    x = max(0, rect.x())
    y = max(0, rect.y())
    w = max(1, min(rect.width(), base_pixmap.width() - x))
    h = max(1, min(rect.height(), base_pixmap.height() - y))

    cropped_qimg = base_pixmap.copy(x, y, w, h).toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    ptr = cropped_qimg.bits()
    ptr.setsize(h * w * 4)
    pil_patch = Image.frombytes("RGBA", (w, h), bytes(ptr), "raw", "RGBA")

    if pixelate:
        block = max(4, intensity)
        sw = max(1, w // block)
        sh = max(1, h // block)
        processed = pil_patch.resize((sw, sh), Image.Resampling.NEAREST).resize((w, h), Image.Resampling.NEAREST)
    else:
        processed = pil_patch.filter(ImageFilter.GaussianBlur(radius=max(2, intensity // 2)))

    raw_bgra = processed.tobytes("raw", "BGRA")
    out_qimg = QImage(raw_bgra, w, h, w * 4, QImage.Format.Format_ARGB32).copy()
    return QPixmap.fromImage(out_qimg)


def estimate_png_kb(pixmap: QPixmap) -> int:
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(buf, "PNG")
    return max(1, len(ba) // 1024)


def save_and_copy_pixmap(pixmap: QPixmap, config, is_fullscreen: bool = False) -> dict:
    result = {"copied": False, "saved_path": None, "size_kb": 0}

    if config.get("capture", "copy_to_clipboard", True):
        clipboard = QGuiApplication.clipboard()
        clipboard.setPixmap(pixmap)
        result["copied"] = True

    should_save = (
        config.get("capture", "auto_save_fullscreen", True)
        if is_fullscreen
        else config.get("capture", "auto_save_region", False)
    )

    if should_save:
        saved_path = save_pixmap_to_disk(pixmap, config)
        result["saved_path"] = saved_path
        try:
            result["size_kb"] = max(1, Path(saved_path).stat().st_size // 1024)
        except Exception:
            result["size_kb"] = estimate_png_kb(pixmap)
    else:
        result["size_kb"] = max(1, (pixmap.width() * pixmap.height()) // 3200)

    return result


def save_pixmap_to_disk(pixmap: QPixmap, config, custom_path: str = None) -> str:
    if custom_path:
        target = Path(custom_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        pixmap.save(str(target))
        return str(target)

    save_dir = Path(config.get("capture", "save_directory", str(Path.home() / "Pictures" / "SnapLite")))
    save_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    template = config.get("capture", "filename_template", "Snap_{date}_{time}")
    filename = (
        template.replace("{date}", now.strftime("%Y-%m-%d"))
        .replace("{time}", now.strftime("%H-%M-%S-%f")[:-3])
    )
    ext = config.get("capture", "image_format", "png").lower()
    full_path = save_dir / f"{filename}.{ext}"
    pixmap.save(str(full_path), ext.upper())
    return str(full_path)
