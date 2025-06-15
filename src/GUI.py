import wx

from utils.config import Config
from utils.common.enums import Platform
from utils.auth.cookie import CookieUtils

from gui.main_v2 import MainWindow

class APP(wx.App):
    def __init__(self):
        wx.App.__init__(self)
        
        # 设置语言环境为中文
        self.locale = wx.Locale(wx.LANGUAGE_CHINESE_SIMPLIFIED)
        self.SetAppName(Config.APP.name)

def init():
    def windows():
        import ctypes
        import subprocess

        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        subprocess.run("chcp 65001", stdout = subprocess.PIPE, shell = True)

    def linux():
        import os

        os.environ['GDK_BACKEND'] = "x11"

    def init_vlc_path():
        import os

        os.environ['PYTHON_VLC_MODULE_PATH'] = "./vlc"

    match Platform(Config.Sys.platform):
        case Platform.Windows:
            windows()

        case Platform.Linux:
            linux()

    init_vlc_path()

    CookieUtils.init_cookie_params()

if __name__ == "__main__":
    init()

    app = APP()

    main_window = MainWindow(None)
    main_window.Show()

    app.MainLoop()
