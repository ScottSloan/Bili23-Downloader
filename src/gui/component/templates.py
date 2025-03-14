import wx
import time
import wx.dataview
from wx.lib.scrolledpanel import ScrolledPanel as _ScrolledPanel

from utils.config import Config
from utils.common.icon_v2 import IconManager, IconType

class Frame(wx.Frame):
    def __init__(self, parent, title, style = wx.DEFAULT_FRAME_STYLE):
        wx.Frame.__init__(self, parent, -1, title, style = style)

        icon_manager = IconManager(self)

        self.SetIcon(wx.Icon(icon_manager.get_icon_bitmap(IconType.APP_ICON_SMALL)))

class ScrolledPanel(_ScrolledPanel):
    def __init__(self, parent, size = wx.DefaultSize):
        _ScrolledPanel.__init__(self, parent, -1, size = size)

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.SetSizer(self.sizer)

class InfoBar(wx.InfoBar):
    def __init__(self, parent):
        wx.InfoBar.__init__(self, parent, -1)

    def ShowMessage(self, msg, flags=...):
        super().Dismiss()
        return super().ShowMessage(msg, flags)

class TextCtrl(wx.TextCtrl):
    def __init__(self, *args, **kwargs):

        self.double_click_lock = 0 # 双击锁，防止双击抬起误触发全选

        self.last_click_time = 0 # 上一次双击的时间

        wx.TextCtrl.__init__(self, *args, **kwargs)

        self.Bind_EVT()

    def Bind_EVT(self):
        self.Bind(wx.EVT_LEFT_UP, self.onClickEVT)
        
        self.Bind(wx.EVT_LEFT_DCLICK, self.onDClickEVT)

    def onClickEVT(self, event):
        event.Skip() # 保留原有事件

        if int(time.time() * 1000) - self.last_click_time < 500: # 双击和单击的点击间隔小于 500ms，视为三击
            if self.double_click_lock==0:
                if self.GetSelection()!=(0,-1): # 检查是否已经全选
                    self.SelectAll()
        self.double_click_lock = 0
    
    def onDClickEVT(self, event):
        event.Skip() # 保留原有事件

        self.last_click_time = int(time.time() * 1000)
        self.double_click_lock = 1

class ActionButton(wx.Panel):
    def __init__(self, parent, title):
        self._title = title

        wx.Panel.__init__(self, parent, -1)

        self.init_UI()

        self.Bind_EVT()

        self._active = False
        self._lab_hover = False

    def init_UI(self):
        self.icon = wx.StaticBitmap(self, -1, size = self.FromDIP((16, 16)))

        self.lab = wx.StaticText(self, -1, self._title)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddSpacer(50)
        hbox.Add(self.icon, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        hbox.Add(self.lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)
        hbox.AddSpacer(50)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddSpacer(5)
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.AddSpacer(5)

        self.SetSizerAndFit(vbox)
    
    def Bind_EVT(self):
        self.Bind(wx.EVT_ENTER_WINDOW, self.onHoverEVT)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.onLeaveEVT)
        self.Bind(wx.EVT_LEFT_DOWN, self.onClickEVT)

        self.lab.Bind(wx.EVT_ENTER_WINDOW, self.onLabHoverEVT)
        self.lab.Bind(wx.EVT_LEAVE_WINDOW, self.onLabLeaveEVT)
        self.lab.Bind(wx.EVT_LEFT_DOWN, self.onClickEVT)

    def onHoverEVT(self, event):
        self.SetBackgroundColour(wx.Colour(220, 220, 220))

        self.Refresh()

        event.Skip()

    def onLabHoverEVT(self, event):
        self._lab_hover = True

        event.Skip()
    
    def onLeaveEVT(self, event):
        if not self._active and not self._lab_hover:
            self.SetBackgroundColour("white")

            self.Refresh()

        event.Skip()

    def onLabLeaveEVT(self, event):
        self._lab_hover = False

        event.Skip()
    
    def onClickEVT(self, event):
        self.SetBackgroundColour(wx.Colour(210, 210, 210))

        self.Refresh()

        self._active = True

        self.onClickCustomEVT()

        event.Skip()
    
    def setActiveState(self):
        self._active = True
        self.SetBackgroundColour(wx.Colour(210, 210, 210))

        self.Refresh()

    def setUnactiveState(self):
        self._active = False
        self.SetBackgroundColour("white")

        self.Refresh()

    def setBitmap(self, bitmap):
        self.icon.SetBitmap(bitmap)

    def setTitle(self, title):
        self.lab.SetLabel(title)

    def onClickCustomEVT(self):
        pass

class InfoLabel(wx.StaticText):
    def __init__(self, parent, label: str = wx.EmptyString, size = wx.DefaultSize):
        wx.StaticText.__init__(self, parent, -1, label, size = size)

        if not Config.Sys.dark_mode:
            self.SetForegroundColour(wx.Colour(108, 108, 108))