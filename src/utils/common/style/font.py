import wx

from utils.config import Config

from utils.common.enums import Platform

class SysFont:
    sys_font_list: list = []

    @classmethod
    def get_monospaced_font(cls):
        font_list = cls.get_sys_monospaced_font_list()

        for font in cls.get_preferred_font_list():
            if font in font_list:
                return font
    
    @staticmethod
    def get_sys_monospaced_font_list():
        return wx.FontEnumerator().GetFacenames(fixedWidthOnly = True)
    
    @staticmethod
    def get_preferred_font_list():
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                return [
                    "Consolas",
                    "Cascadia Code"
                ]
            
            case Platform.Linux:
                return [
                    "Monospace",
                    "DejaVu Sans Mono",
                    "Ubuntu Mono",
                    "Noto Mono"
                ]
            
            case Platform.macOS:
                return [
                    "Menlo"
                ]
    
    