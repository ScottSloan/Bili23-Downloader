import ctypes
import platform

machine_platform = platform.platform()
if machine_platform.startswith("Windows-10") or machine_platform.startswith("Windows-11"):
    ctypes.windll.shcore.SetProcessDpiAwareness(2)