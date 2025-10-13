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
    def get_label_text_color():
        return wx.Colour(64, 64, 64)
    
    @staticmethod
    def get_border_color():
        if Config.Sys.dark_mode:
            return wx.Colour("white")
        else:
            return wx.Colour(227, 229, 231)
        
    @staticmethod
    def get_frame_text_color():
        if Config.Sys.dark_mode:
            return wx.Colour("white")
        else:
            return wx.Colour(90, 90, 90)
        
    @staticmethod
    def convert_to_ass_abgr_color(hex_color: str, alpha: str = None):
        hex_new = hex_color.lstrip("#").upper()

        r, g, b, a = hex_new[0:2], hex_new[2:4], hex_new[4:6], hex_new[6:8]

        if alpha:
            a = alpha
        else:
            a = "00" if not a else a

        return f"&H{a}{b}{g}{r}&"
    
    @staticmethod
    def convert_to_ass_bgr_color(hex_color: str):
        hex_new = hex_color.lstrip("#").upper()

        r, g, b = hex_new[0:2], hex_new[2:4], hex_new[4:6]

        return f"&H{b}{g}{r}&"
    
    @staticmethod
    def convert_to_ass_a_color(alpha: int):
        return f"&H{Color.dec_to_hex(alpha)}"

    @staticmethod
    def convert_to_hex_color(ass_color: str):
        ass_new = ass_color.lstrip("&H").rstrip("&").upper()

        b, g, r = ass_new[0:2], ass_new[2:4], ass_new[4:6]

        return f"{r}{g}{b}"
    
    @staticmethod
    def convert_to_abgr_color(ass_color: str):
        ass_new = ass_color.lstrip("&H").rstrip("&").upper()

        a, b, g, r = ass_new[0:2], ass_new[2:4], ass_new[4:6], ass_new[6:8]

        return int(r, 16), int(g, 16), int(b, 16), int(a, 16)

    @staticmethod
    def dec_to_hex(dec_color: int):
        return hex(dec_color)[2:].upper()