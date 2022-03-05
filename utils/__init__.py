import wx
import os
import sys
import platform
import subprocess

def set_env():
    if platform.platform().startswith("Windows"):
        Path = os.getenv("Path")
        os.environ["Path"] = Path + ";" + os.path.join(os.getcwd())

def show_error_msg():
    err_app = wx.App()
    wx.MessageDialog(None, "未安装 ffmpeg\n\n本程序需要安装 ffmpeg 才能运行。", "警告", wx.ICON_WARNING).ShowModal()

def check_path():
    down_path = os.path.join(os.getcwd(), "download")

    if not os.path.exists(down_path):
        os.mkdir(down_path)

try:
    set_env()
    subprocess.check_call("ffmpeg -version", shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    check_path()

except:
    show_error_msg()
    sys.exit(0)