import wx

from utils.config import Config

from utils.common.style.color import Color

class InfoLabel(wx.StaticText):
    def __init__(self, parent, label: str = wx.EmptyString, size = wx.DefaultSize, color: wx.Colour = wx.Colour(108, 108, 108)):
        self.color = color

        wx.StaticText.__init__(self, parent, -1, label, size = size)

        self.SetForegroundColour(self.get_default_color())

    def get_default_color(self):
        if not Config.Sys.dark_mode:
            return self.color
        else:
            return Color.get_text_color()