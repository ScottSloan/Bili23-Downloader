import ctypes
import platform

platform = platform.platform()

if platform.startswith("Windows-10") or platform.startswith("Windows-11"):
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
