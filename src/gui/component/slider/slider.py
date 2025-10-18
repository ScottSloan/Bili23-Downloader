import wx

from gui.component.panel.scrolled_panel import ScrolledPanel

class Slider(wx.Slider):
    def __init__(self, parent: wx.Window, value: int = 0, min_value: int = 0, max_value: int = 100):
        wx.Slider.__init__(self, parent, -1, value = value, minValue = min_value, maxValue = max_value)

        self.Bind_EVT()

    def Bind_EVT(self):
        self.Bind(wx.EVT_MOUSEWHEEL, self.onMouseWheelEVT)

    def onMouseWheelEVT(self, event: wx.MouseEvent):
        parent = self.GetParent()

        while parent is not None:
            if isinstance(parent, ScrolledPanel):
                evt = wx.MouseEvent(event)
                wx.PostEvent(parent.GetEventHandler(), evt)

                event.StopPropagation()
            
            parent = parent.GetParent()