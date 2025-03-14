import wx

from utils.config import Config

class InfoLabel(wx.StaticText):
    def __init__(self, parent, label: str = wx.EmptyString, size = wx.DefaultSize):
        wx.StaticText.__init__(self, parent, -1, label, size = size)

        if not Config.Sys.dark_mode:
            self.SetForegroundColour(wx.Colour(108, 108, 108))