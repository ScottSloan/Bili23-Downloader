import wx

from utils.config import Config

class InfoLabel(wx.StaticText):
    def __init__(self, parent, label: str = wx.EmptyString, size = wx.DefaultSize, color: wx.Colour = None):
        self.color = color

        wx.StaticText.__init__(self, parent, -1, label, size = size)

        self.reset_color()

    def reset_color(self):
        if not Config.Sys.dark_mode:
            if self.color:
                self.SetForegroundColour(self.color)
            else:
                self.SetForegroundColour(wx.Colour(108, 108, 108))