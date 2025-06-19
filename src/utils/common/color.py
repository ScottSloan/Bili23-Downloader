import wx

from utils.config import Config

from utils.common.enums import Platform

class Color:
    @staticmethod
    def get_panel_background_color():
        match Platform(Config.Sys.platform):
            case Platform.Windows | Platform.Linux:
                return wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENUBAR)
            
            case Platform.macOS:
                if Config.Sys.dark_mode:
                    return wx.Colour(40, 40, 40)
                else:
                    return wx.Colour(246, 246, 246)
                
    @staticmethod
    def get_text_color():
        return wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENUTEXT)