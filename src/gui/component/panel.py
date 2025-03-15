import wx

from utils.config import Config

class Panel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

    def get_scaled_size(self, size: tuple):
        match Config.Sys.platform:
            case "windows":
                return self.FromDIP(size)
            
            case "linux" | "darwin":
                return wx.DefaultSize
    
    def set_dark_mode(self):
        if not Config.Sys.dark_mode:
            self.SetBackgroundColour("white")