import wx

from utils.config import Config
from utils.tool_v2 import UniversalTool
from utils.auth.cookie import CookieUtils

from gui.main_v2 import MainWindow

class APP(wx.App):
    def __init__(self):
        wx.App.__init__(self)
        
        # 设置语言环境为中文
        self.locale = wx.Locale(wx.LANGUAGE_CHINESE_SIMPLIFIED)
        self.SetAppName(Config.APP.name)

def init():
    UniversalTool.msw_set_utf8_encode()
    UniversalTool.msw_set_dpi_awareness()

    cookie_utils = CookieUtils()
    cookie_utils.init_cookie_params()

if __name__ == "__main__":
    init()

    app = APP()

    main_window = MainWindow(None)
    main_window.Show()

    app.MainLoop()
