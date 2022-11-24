import os
import ctypes
import platform

PLATFORM = platform.platform()

if PLATFORM.startswith("Windows-10") or PLATFORM.startswith("Windows-11"):
    ctypes.windll.shcore.SetProcessDpiAwareness(2)

default_download_path = os.path.join(os.getcwd(), "download")

if not os.path.exists(default_download_path):
    os.mkdir(default_download_path)
    