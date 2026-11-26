import json
import os
import sys
from pathlib import Path
from PyQt6.QtCore import QTimer

DEFAULT_HOTKEYS = {
    "region_capture": "Ctrl+PrintScreen",
    "fullscreen_capture": "PrintScreen",
}

DEFAULT_CONFIG = {
    "language": "ua",
    "hotkeys": dict(DEFAULT_HOTKEYS),
    "capture": {
        "copy_to_clipboard": True,
        "auto_save_fullscreen": True,
        "auto_save_region": False,
        "save_directory": "",
        "filename_template": "Snap_{date}_{time}",
        "image_format": "png",
        "show_magnifier": True,
        "show_crosshair": True,
        "dim_opacity": 110
    },
    "toolbar": {
        "position": "top",
        "default_color": "#FF3B30",
        "stroke_width": 3,
        "blur_intensity": 15,
        "visible_tools": [
            "select", "rect", "ellipse", "line", "arrow", "pen",
            "highlighter", "text", "callout", "step", "blur", "pixelate"
        ]
    },
    "appearance": {
        "background_image": "",
        "background_blur": 18,
        "background_dim": 45,
        "adaptive_colors": True,
        "manual_accent": "#2563EB",
        "accent_color": "#2563EB"
    }
}


class ConfigManager:
    def __init__(self, config_name="config.json"):
        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).resolve().parent.parent

        appdata = os.environ.get("APPDATA", "")
        user_dir = (Path(appdata) if appdata else Path.home() / "AppData" / "Roaming") / "SnapLite"
        self.config_path = user_dir / config_name
        self._legacy_path = base_dir / config_name
        self._dirty = False

        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(220)
        self._save_timer.timeout.connect(self.save)

        self.data = self._load()

    def _load(self) -> dict:
        for candidate in (self.config_path, self._legacy_path):
            if candidate.exists():
                try:
                    with open(candidate, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                    merged = self._merge_defaults(DEFAULT_CONFIG, loaded)
                    if candidate != self.config_path:
                        self._write_file(merged)
                    return merged
                except Exception:
                    pass
        return json.loads(json.dumps(DEFAULT_CONFIG))

    def _merge_defaults(self, default: dict, loaded: dict) -> dict:
        result = json.loads(json.dumps(default))
        for k, v in loaded.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = self._merge_defaults(result[k], v)
            else:
                result[k] = v
        return result

    def _write_file(self, payload: dict):
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            self._dirty = False
        except Exception:
            pass

    def save(self):
        if self._save_timer.isActive():
            self._save_timer.stop()
        self._write_file(self.data)

    def flush(self):
        if self._dirty or self._save_timer.isActive():
            self.save()

    def get(self, section: str, key: str = None, default=None):
        if key is None:
            return self.data.get(section, default)
        val = self.data.get(section, {}).get(key, default)
        if section == "capture" and key == "save_directory" and not val:
            return str(Path.home() / "Pictures" / "SnapLite")
        return val

    def set(self, section: str, key: str, value=None, save: bool = True, debounce: bool = False):
        if value is None and not isinstance(self.data.get(section), dict):
            if self.data.get(section) == key:
                return
            self.data[section] = key
        else:
            sec_dict = self.data.setdefault(section, {})
            if sec_dict.get(key) == value:
                return
            sec_dict[key] = value

        self._dirty = True
        if save:
            if debounce:
                self._save_timer.start()
            else:
                self.save()
