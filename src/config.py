import json
import sys
from pathlib import Path

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
    def __init__(self, config_path="config.json"):
        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).resolve().parent.parent
        self.config_path = base_dir / config_path
        self.data = self._load()

    def _load(self) -> dict:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                return self._merge_defaults(DEFAULT_CONFIG, loaded)
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

    def save(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def get(self, section: str, key: str = None, default=None):
        if key is None:
            return self.data.get(section, default)
        val = self.data.get(section, {}).get(key, default)
        if section == "capture" and key == "save_directory" and not val:
            return str(Path.home() / "Pictures" / "SnapLite")
        return val

    def set(self, section: str, key: str, value=None, save: bool = True):
        if value is None and not isinstance(self.data.get(section), dict):
            self.data[section] = key
        else:
            self.data.setdefault(section, {})[key] = value
        if save:
            self.save()
