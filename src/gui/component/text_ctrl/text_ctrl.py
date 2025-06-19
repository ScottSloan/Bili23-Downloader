import wx
import time

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
            if self.double_click_lock == 0:
                if self.GetSelection() != (0, -1): # 检查是否已经全选
                    self.SelectAll()

        self.double_click_lock = 0
    
    def onDClickEVT(self, event):
        event.Skip() # 保留原有事件

        self.last_click_time = int(time.time() * 1000)
        self.double_click_lock = 1
