import wx

from utils.config import Config

class Dialog(wx.Dialog):
    def __init__(self, parent, title):
        wx.Dialog.__init__(self, parent, -1, title)

    def get_scaled_size(self, size: tuple):
        match Config.Sys.platform:
            case "windows":
                return self.FromDIP(size)
            
            case "linux" | "darwin":
                return wx.DefaultSize
