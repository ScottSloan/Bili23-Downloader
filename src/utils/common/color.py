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
    
    @staticmethod
    def convert_to_ass_color(hex_color: str):
        hex_new = hex_color.lstrip("#").upper()

        r, g, b = hex_new[0:2], hex_new[2:4], hex_new[4:6]

        return f"&H{b}{g}{r}&"
    
    @staticmethod
    def convert_to_ass_style_color(hex_color: str):
        hex_new = hex_color.lstrip("#").upper()

        r, g, b, a = hex_new[0:2], hex_new[2:4], hex_new[4:6], hex_new[6:8]

        return f"&H{a}{b}{g}{r}"
    
    @staticmethod
    def convert_to_hex_color(ass_color: str):
        ass_new = ass_color.lstrip("&H").rstrip("&").upper()

        b, g, r = ass_new[0:2], ass_new[2:4], ass_new[4:6]

        return f"{r}{g}{b}"
    
    @staticmethod
    def convert_to_abgr_color(ass_color: str):
        ass_new = ass_color.lstrip("&H").rstrip("&").upper()

        a, b, g, r = ass_new[0:2], ass_new[2:4], ass_new[4:6], ass_new[6:8]

        return int(f"{a}{b}{g}{r}", 16)