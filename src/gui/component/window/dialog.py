import wx

from utils.config import Config
from utils.common.enums import Platform

class Dialog(wx.Dialog):
    def __init__(self, parent, title, style = wx.DEFAULT_DIALOG_STYLE, name = wx.DialogNameStr):
        wx.Dialog.__init__(self, parent, -1, title, style = style, name = name)

        self.Bind(wx.EVT_BUTTON, self.onCloseEVT, id = wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.onCloseEVT, id = wx.ID_CANCEL)

    def get_scaled_size(self, size: tuple):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                return self.FromDIP(size)
            
            case Platform.Linux | Platform.macOS:
                return wx.DefaultSize
    
    def set_dark_mode(self):
        if not Config.Sys.dark_mode:
            self.SetBackgroundColour("white")

    def raise_top(self):
        self.SetWindowStyle(wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)
        self.SetWindowStyle(wx.DEFAULT_DIALOG_STYLE)

    def onCloseEVT(self, event):
        match event.GetId():
            case wx.ID_OK:
                rtn =  self.onOKEVT()

            case wx.ID_CANCEL:
                rtn = self.onCancelEVT()

            case _:
                rtn = False

        if not rtn:
            if Platform(Config.Sys.platform) == Platform.Windows:
                self.Destroy()

            return event.Skip()
    
    def onOKEVT(self):
        pass

    def onCancelEVT(self):
        pass

    def DWMExtendFrameIntoClientArea(self):
        if Platform(Config.Sys.platform) == Platform.Windows:
            import ctypes
            import ctypes.wintypes

            hwnd = self.GetHandle()

            class MARGINS(ctypes.Structure):
                _fields_ = [
                    ("cxLeftWidth", ctypes.c_int),
                    ("cxRightWidth", ctypes.c_int),
                    ("cyTopHeight", ctypes.c_int),
                    ("cyBottomHeight", ctypes.c_int)
                ]

            margins = MARGINS(1, 1, 1, 1)
            colorref = ctypes.wintypes.RGB(255, 255, 255)

            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(ctypes.c_int(colorref)), ctypes.sizeof(ctypes.c_int(colorref)))
            ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))

            return True

