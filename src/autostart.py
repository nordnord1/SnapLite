import os
import sys
import subprocess
from pathlib import Path


def get_startup_folder() -> Path:
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def get_shortcut_path() -> Path:
    return get_startup_folder() / "SnapLite.lnk"


def is_autostart_enabled() -> bool:
    return get_shortcut_path().exists()


def set_autostart_enabled(enable: bool) -> bool:
    lnk_path = get_shortcut_path()
    if enable:
        if getattr(sys, "frozen", False):
            target_path = sys.executable
            arguments = ""
            work_dir = str(Path(sys.executable).parent)
        else:
            py_dir = Path(sys.executable).parent
            pythonw = py_dir / "pythonw.exe"
            target_path = str(pythonw if pythonw.exists() else Path(sys.executable))
            main_script = Path(__file__).resolve().parent.parent / "main.py"
            arguments = f'"{main_script}"'
            work_dir = str(main_script.parent)

        ps_cmd = (
            "$ws = New-Object -ComObject WScript.Shell; "
            f"$s = $ws.CreateShortcut('{lnk_path}'); "
            f"$s.TargetPath = '{target_path}'; "
            f"$s.Arguments = '{arguments}'; "
            f"$s.WorkingDirectory = '{work_dir}'; "
            "$s.Save()"
        )
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return True
        except Exception:
            return False
    else:
        if lnk_path.exists():
            archived = lnk_path.with_suffix(".disabled")
            try:
                lnk_path.replace(archived)
            except Exception:
                pass
        return True
