import ctypes
from ctypes import wintypes
from PyQt6.QtCore import QThread, pyqtSignal

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WH_KEYBOARD_LL = 13
HC_ACTION = 0
WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP = 0x0100, 0x0101, 0x0104, 0x0105
WM_QUIT = 0x0012
PM_REMOVE = 0x0001
QS_ALLINPUT = 0x04FF
WAIT_OBJECT_0 = 0x00000000

VK_SHIFT, VK_CONTROL, VK_MENU = 0x10, 0x11, 0x12
VK_LWIN, VK_RWIN, VK_ESCAPE = 0x5B, 0x5C, 0x1B
MODIFIER_VKS = {0x10, 0x11, 0x12, 0x5B, 0x5C, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5}

MOD_CTRL, MOD_ALT, MOD_SHIFT, MOD_WIN = 1, 2, 4, 8

LRESULT = ctypes.c_ssize_t
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = LRESULT
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT]
user32.PeekMessageW.restype = wintypes.BOOL
user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.MsgWaitForMultipleObjects.argtypes = [
    wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE), wintypes.BOOL, wintypes.DWORD, wintypes.DWORD
]
user32.MsgWaitForMultipleObjects.restype = wintypes.DWORD
user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostThreadMessageW.restype = wintypes.BOOL

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetCurrentThreadId.argtypes = []
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
kernel32.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateEventW.restype = wintypes.HANDLE
kernel32.SetEvent.argtypes = [wintypes.HANDLE]
kernel32.SetEvent.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

_NAMED_VK = {
    0x2C: "PrintScreen", 0x2D: "Insert", 0x2E: "Delete", 0x24: "Home", 0x23: "End",
    0x21: "PageUp", 0x22: "PageDown", 0x20: "Space", 0x09: "Tab", 0x0D: "Enter",
    0x08: "Backspace", 0x13: "Pause", 0x91: "ScrollLock", 0x25: "Left", 0x26: "Up",
    0x27: "Right", 0x28: "Down", 0x1B: "Esc",
}
for _i in range(24):
    _NAMED_VK[0x70 + _i] = f"F{_i + 1}"
for _i in range(10):
    _NAMED_VK[0x60 + _i] = f"Num{_i}"

_NAME_TO_VK = {name.upper(): vk for vk, name in _NAMED_VK.items()}
_NAME_TO_VK.update({"PRTSC": 0x2C, "PRINT": 0x2C, "SNAPSHOT": 0x2C, "ESCAPE": 0x1B, "RETURN": 0x0D})


def vk_to_name(vk: int) -> str:
    if vk in _NAMED_VK:
        return _NAMED_VK[vk]
    if 0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A:
        return chr(vk)
    return f"VK{vk}"


def format_hotkey(mods: int, vk: int) -> str:
    parts = []
    if mods & MOD_CTRL:
        parts.append("Ctrl")
    if mods & MOD_ALT:
        parts.append("Alt")
    if mods & MOD_SHIFT:
        parts.append("Shift")
    if mods & MOD_WIN:
        parts.append("Win")
    parts.append(vk_to_name(vk))
    return "+".join(parts)


def parse_hotkey(text: str) -> tuple[int, int]:
    mods, vk = 0, 0
    for part in (p.strip().upper() for p in (text or "").split("+") if p.strip()):
        if part in ("CTRL", "CONTROL"):
            mods |= MOD_CTRL
        elif part == "ALT":
            mods |= MOD_ALT
        elif part == "SHIFT":
            mods |= MOD_SHIFT
        elif part in ("WIN", "META", "SUPER"):
            mods |= MOD_WIN
        elif part in _NAME_TO_VK:
            vk = _NAME_TO_VK[part]
        elif len(part) == 1 and part.isalnum():
            vk = ord(part)
        elif part.startswith("VK") and part[2:].isdigit():
            vk = int(part[2:])
    return mods, vk


def _pressed(vk: int) -> bool:
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def current_modifiers() -> int:
    mods = 0
    if _pressed(VK_CONTROL):
        mods |= MOD_CTRL
    if _pressed(VK_MENU):
        mods |= MOD_ALT
    if _pressed(VK_SHIFT):
        mods |= MOD_SHIFT
    if _pressed(VK_LWIN) or _pressed(VK_RWIN):
        mods |= MOD_WIN
    return mods


class GlobalHotkeyManager(QThread):
    region_triggered = pyqtSignal()
    fullscreen_triggered = pyqtSignal()
    hotkey_captured = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._bindings: dict[str, tuple[int, int]] = {}
        self._swallowed: set[int] = set()
        self._capturing: bool = False
        self._capture_cb = None
        self._pending_actions: list[tuple[str, str]] = []
        self._hook = None
        self._thread_id = 0
        self._wake_event = kernel32.CreateEventW(None, False, False, None)
        self._proc = HOOKPROC(self._hook_proc)
        self.hotkey_captured.connect(self._deliver_captured)
        self.start()

    def run(self):
        self._thread_id = kernel32.GetCurrentThreadId()
        hmod = kernel32.GetModuleHandleW(None)
        self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, hmod, 0)

        handles = (wintypes.HANDLE * 1)(self._wake_event)
        msg = wintypes.MSG()
        running = True

        while running:
            res = user32.MsgWaitForMultipleObjects(1, handles, False, 0xFFFFFFFF, QS_ALLINPUT)
            if res == WAIT_OBJECT_0:
                while self._pending_actions:
                    kind, payload = self._pending_actions.pop(0)
                    if kind == "region":
                        self.region_triggered.emit()
                    elif kind == "fullscreen":
                        self.fullscreen_triggered.emit()
                    elif kind == "capture":
                        self.hotkey_captured.emit(payload)

            while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
                if msg.message == WM_QUIT:
                    running = False
                    break
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None
        if self._wake_event:
            kernel32.CloseHandle(self._wake_event)
            self._wake_event = None

    def register_all(self, region_hk: str, fullscreen_hk: str) -> dict:
        new_bindings = {}
        status = {}
        for name, text in (("region", region_hk), ("fullscreen", fullscreen_hk)):
            mods, vk = parse_hotkey(text)
            if vk:
                new_bindings[name] = (mods, vk)
            status[name] = bool(vk)
        self._bindings = new_bindings
        return status

    def begin_capture(self, callback):
        self._capture_cb = callback
        self._capturing = True

    def cancel_capture(self):
        self._capturing = False
        self._capture_cb = None

    def _deliver_captured(self, combo: str):
        cb = self._capture_cb
        self._capture_cb = None
        if cb is not None:
            cb(combo if combo else None)

    def unregister_all(self):
        self._bindings.clear()
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
            if self._wake_event:
                kernel32.SetEvent(self._wake_event)
            self.wait(1000)

    def _match(self, vk: int):
        mods = current_modifiers()
        for name, (m, v) in self._bindings.items():
            if v == vk and m == mods:
                return name
        return None

    def _enqueue(self, kind: str, payload: str = ""):
        self._pending_actions.append((kind, payload))
        if self._wake_event:
            kernel32.SetEvent(self._wake_event)

    def _hook_proc(self, n_code, w_param, l_param):
        try:
            if n_code == HC_ACTION and l_param:
                vk = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents.vkCode
                if vk not in MODIFIER_VKS:
                    if w_param in (WM_KEYDOWN, WM_SYSKEYDOWN):
                        if self._capturing:
                            self._capturing = False
                            combo = "" if vk == VK_ESCAPE else format_hotkey(current_modifiers(), vk)
                            self._swallowed.add(vk)
                            self._enqueue("capture", combo)
                            return 1
                        name = self._match(vk)
                        if name is not None:
                            if vk not in self._swallowed:
                                self._swallowed.add(vk)
                                self._enqueue(name)
                            return 1
                    elif w_param in (WM_KEYUP, WM_SYSKEYUP):
                        if vk in self._swallowed:
                            self._swallowed.discard(vk)
                            return 1
                        if self._capturing:
                            self._capturing = False
                            combo = "" if vk == VK_ESCAPE else format_hotkey(current_modifiers(), vk)
                            self._enqueue("capture", combo)
                            return 1
                        name = self._match(vk)
                        if name is not None:
                            self._enqueue(name)
                            return 1
        except Exception:
            pass
        return user32.CallNextHookEx(self._hook, n_code, w_param, l_param)
