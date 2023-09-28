import wx
import ctypes

from gui.main import MainWindow

if __name__ == "__main__":
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
    
    app = wx.App()

    main_window = MainWindow(None)
    main_window.Show()

    app.MainLoop()