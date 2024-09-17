import wx

from utils.config import Config
from gui.main import MainWindow

if __name__ == "__main__":
    if Config.Sys.platform == "windows":
        # Windows 环境下，启用高 DPI 适配
        import ctypes
        
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    
    app = wx.App()
    app.SetAppName("Bili23 Downloader")

    main_window = MainWindow(None)
    main_window.Show()

    app.MainLoop()