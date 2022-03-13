import wx
import os
import sys
import ctypes
import platform
import subprocess

def set_env():
    machine_platform = platform.platform()
    if machine_platform.startswith("Windows"):
        os.environ["Path"] = os.getenv("Path") + ";" + os.path.join(os.getcwd())
        os.environ["PYTHON_VLC_MODULE_PATH"] = os.path.join(os.getcwd(), "vlc")

    if machine_platform.startswith("Windows-10") or machine_platform.startswith("Windows-11"):
        ctypes.windll.shcore.SetProcessDpiAwareness(2)

def show_error_msg():
    err_app = wx.App()
    wx.MessageDialog(None, "未安装 ffmpeg\n\n本程序需要安装 ffmpeg 才能运行。", "警告", wx.ICON_WARNING).ShowModal()

def check_path():
    down_path = os.path.join(os.getcwd(), "download")

    if not os.path.exists(down_path):
        os.mkdir(down_path)

try:
    set_env()
    subprocess.check_call("ffmpeg -version", shell = True, stdout = subprocess.PIPE)
    check_path()

except:
    show_error_msg()
    sys.exit(0)