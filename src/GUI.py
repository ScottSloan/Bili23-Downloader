import wx

from utils.config import Config
from gui.main import MainWindow

if __name__ == "__main__":
    

    app = wx.App()
    app.SetAppName(Config.APP.name)

    main_window = MainWindow(None)
    main_window.Show()

    app.MainLoop()