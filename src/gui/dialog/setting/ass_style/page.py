import wx

from gui.component.panel.panel import Panel
from gui.component.panel.scrolled_panel import ScrolledPanel

class Page(Panel):
    def __init__(self, parent: wx.Window):
        Panel.__init__(self, parent)

        self.scrolled_panel = ScrolledPanel(self)
        self.panel = Panel(self.scrolled_panel)

    def init_UI(self):
        self.scrolled_panel.sizer.Add(self.panel, 0, wx.EXPAND)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.scrolled_panel, 1, wx.EXPAND)

        self.SetSizer(vbox)

        self.scrolled_panel.Layout()