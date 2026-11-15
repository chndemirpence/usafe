"""Opt-in Windows launcher for the USAFE website's desktop app link."""
import ctypes
from ctypes import wintypes
import hashlib
from pathlib import Path
import winreg

SCHEME = r"Software\Classes\usafe-connect"
COMMAND = SCHEME + r"\shell\open\command"


def launcher_command(executable: Path) -> str:
    # The browser's URI is intentionally omitted. Its only action is to show the app.
    return f'"{executable.resolve()}" --from-website'


def is_enabled(executable: Path) -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, SCHEME) as scheme:
            winreg.QueryValueEx(scheme, "URL Protocol")
        return winreg.QueryValue(winreg.HKEY_CURRENT_USER, COMMAND) == launcher_command(executable)
    except OSError:
        return False


def register_launcher(executable: Path):
    executable = executable.resolve(strict=True)
    if executable.name.casefold() != "usafe connect.exe":
        raise OSError("Open the packaged USAFE Connect app to enable website launch.")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, COMMAND) as command:
        winreg.SetValueEx(command, "", 0, winreg.REG_SZ, launcher_command(executable))
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, SCHEME) as scheme:
        winreg.SetValueEx(scheme, "", 0, winreg.REG_SZ, "URL:USAFE Connect")
        winreg.SetValueEx(scheme, "URL Protocol", 0, winreg.REG_SZ, "")


def _window_property(executable: Path) -> str:
    identifier = hashlib.sha256(str(executable.resolve()).casefold().encode()).hexdigest()[:24]
    return "USAFE.Connect." + identifier


def mark_window(tk_window_id: int, executable: Path):
    user32 = ctypes.windll.user32
    user32.GetAncestor.argtypes = (wintypes.HWND, wintypes.UINT)
    user32.GetAncestor.restype = wintypes.HWND
    user32.SetPropW.argtypes = (wintypes.HWND, wintypes.LPCWSTR, wintypes.HANDLE)
    # Tk's inner window is a child of the native top-level window.
    hwnd = user32.GetAncestor(tk_window_id, 2)
    if hwnd:
        user32.SetPropW(hwnd, _window_property(executable), 1)


def show_existing_window(executable: Path) -> bool:
    user32 = ctypes.windll.user32
    user32.GetPropW.argtypes = (wintypes.HWND, wintypes.LPCWSTR)
    user32.GetPropW.restype = wintypes.HANDLE
    user32.ShowWindow.argtypes = (wintypes.HWND, ctypes.c_int)
    user32.IsIconic.argtypes = (wintypes.HWND,)
    user32.SetForegroundWindow.argtypes = (wintypes.HWND,)
    window_property = _window_property(executable)
    selected = None
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback_type
    def find(hwnd, _):
        nonlocal selected
        if user32.GetPropW(hwnd, window_property):
            selected = hwnd
            return False
        return True

    user32.EnumWindows.argtypes = (callback_type, wintypes.LPARAM)
    user32.EnumWindows(find, 0)
    if not selected:
        return False
    if user32.IsIconic(selected):
        user32.ShowWindow(selected, 9)
    user32.SetForegroundWindow(selected)
    return True
