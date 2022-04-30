import wx

from gui.main import MainWindow

class Main(MainWindow):
    def __init__(self, parent):
        MainWindow.__init__(self, parent)
        
if __name__ == "__main__":
    app = wx.App()

    main_window = Main(None)
    main_window.Show()

    app.MainLoop()