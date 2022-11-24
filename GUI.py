import wx
import locale

from gui.main import MainWindow

if __name__ == '__main__':
    app = wx.App()

    locale.setlocale(locale.LC_ALL, '')

    app.locale = wx.Locale("Chinese Simplified", "zh_cn", "zh_cn")

    main_window = MainWindow(None)
    main_window.Show()

    app.MainLoop()