import ctypes
from ctypes import wintypes

MessageBoxW = ctypes.windll.user32.MessageBoxW
MessageBoxW.argtypes = (
    wintypes.HWND,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.UINT
)
MessageBoxW.restype = wintypes.INT

def show_message(title: str, message: str, buttons: int = 0x0, icon: int = 0x30) -> int:
    return MessageBoxW(0, message, title, buttons | icon)