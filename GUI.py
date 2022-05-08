import wx
import os
import subprocess

from gui.main import MainWindow

from utils.config import Config

class Main(MainWindow):
    def __init__(self, parent):
        MainWindow.__init__(self, parent)

def onExit():
    from gui.download import downloader

    downloader.force_shutdown()

    if os.path.exists(Config.res_info):
        os.remove(Config.res_info)

if __name__ == "__main__":
    process = subprocess.Popen(Config.ARIA2C_PATH, shell = True)

    app = wx.App()
    app.SetAppName("Bili23 Downloader")

    main_window = Main(None)
    main_window.Show()
    
    main_window.list_lc.SetFocus()

    app.MainLoop()

    onExit()