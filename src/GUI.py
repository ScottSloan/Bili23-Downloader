import wx
import ctypes

from utils.config import Config
from gui.main import MainWindow

class APP(wx.App):
    def __init__(self):
        wx.App.__init__(self)
        
        # 设置语言环境为中文
        self.locale = wx.Locale(wx.LANGUAGE_CHINESE_SIMPLIFIED)
        self.SetAppName(Config.APP.name)

if __name__ == "__main__":
    if Config.Sys.platform == "windows":
        # Windows 环境下，启用高 DPI 适配
        ctypes.windll.shcore.SetProcessDpiAwareness(2)

    app = APP()

    main_window = MainWindow(None)
    main_window.Show()

    app.MainLoop()
