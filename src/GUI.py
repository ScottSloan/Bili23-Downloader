import wx
import os

from utils.config import Config
from utils.common.enums import Platform
from utils.auth.cookie import CookieUtils

from gui.main_v3 import MainWindow

class APP(wx.App):
    def __init__(self):
        self.init_env()

        wx.App.__init__(self)
        
        # 设置语言环境为中文
        self.locale = wx.Locale(wx.LANGUAGE_CHINESE_SIMPLIFIED)
        self.SetAppName(Config.APP.name)

    def init_env(self):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                self.init_msw_env()

            case Platform.Linux:
                self.init_linux_env()

        self.init_vlc_env()

        CookieUtils.init_cookie_params()

    def init_msw_env(self):
        import ctypes
        import subprocess

        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        subprocess.run("chcp 65001", stdout = subprocess.PIPE, shell = True)

    def init_linux_env(self):
        os.environ['GDK_BACKEND'] = "x11"

    def init_vlc_env(self):
        os.environ['PYTHON_VLC_MODULE_PATH'] = "./vlc"

if __name__ == "__main__":
    app = APP()

    main_window = MainWindow(None)
    main_window.Show()

    app.MainLoop()
