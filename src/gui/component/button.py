import wx

from utils.config import Config
from utils.common.enums import Platform

class Button(wx.Button):
    def __init__(self, parent, label: str, size: tuple, set_variant: bool = False):
        wx.Button.__init__(self, parent, -1, label, size = size)

        if Config.Sys.platform == Platform.macOS.value and set_variant:
            self.SetWindowVariant(wx.WINDOW_VARIANT_LARGE)
