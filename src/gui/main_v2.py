import wx

from utils.config import Config


from gui.component.frame import Frame

class MainWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, Config.APP.name)

        self.init_UI()

        self.CenterOnParent()

    def init_UI(self):
        panel = wx.Panel(self, -1)

        