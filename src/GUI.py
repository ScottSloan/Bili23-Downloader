import wx

from utils.config import Config
from utils.tool_v2 import UniversalTool

from gui.main import MainWindow

class APP(wx.App):
    def __init__(self):
        wx.App.__init__(self)
        
        # 设置语言环境为中文
        self.locale = wx.Locale(wx.LANGUAGE_CHINESE_SIMPLIFIED)
        self.SetAppName(Config.APP.name)

if __name__ == "__main__":
    UniversalTool.msw_set_utf8_encode()
    UniversalTool.set_dpi_awareness()

    app = APP()

    main_window = MainWindow(None)
    main_window.Show()

    app.MainLoop()
