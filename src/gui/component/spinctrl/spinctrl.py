import wx

class SpinCtrl(wx.SpinCtrl):
    def __init__(self, parent: wx.Window, value: str = "", min: int = 0, max: int = 100, size: wx.Size = wx.DefaultSize):
        wx.SpinCtrl.__init__(self, parent, -1, value = value, min = min, max = max, size = size)

        self.Bind_EVT()

    def Bind_EVT(self):
        self.Bind(wx.EVT_MOUSEWHEEL, self.onMouseWheelEVT)
    
    def onMouseWheelEVT(self, event: wx.MouseEvent):
        parent = self.GetParent()

        while parent is not None:
            if isinstance(parent, wx.ScrolledWindow):
                evt = wx.MouseEvent(event)
                wx.PostEvent(parent.GetEventHandler(), evt)

                event.StopPropagation()
            
            parent = parent.GetParent()