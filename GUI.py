import wx

from gui.main import MainWindow

if __name__ == '__main__':
    app = wx.App()

    # app.locale = wx.Locale(wx.LANGUAGE_CHINESE_SIMPLIFIED)

    main_window = MainWindow(None)
    main_window.Show()

    app.MainLoop()