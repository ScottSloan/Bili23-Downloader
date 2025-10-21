import wx

from gui.component.panel.scrolled_panel import ScrolledPanel

class Choice(wx.Choice):
    def __init__(self, parent: wx.Window):
        wx.Choice.__init__(self, parent, -1)

        self.Bind_EVT()

        self.data: dict = {}

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

    def SetChoices(self, data: dict):
        self.data = data.copy()

        keys = list(data.keys())

        self.Set(keys)

        for index, value in enumerate(keys):
            self.SetClientData(index, data.get(value))

        self.SetSelection(0)

    def GetCurrentClientData(self):
        return self.GetClientData(self.GetSelection())
    
    def SetCurrentSelection(self, client_data: int):
        value_list = list(self.data.values())

        self.SetSelection(value_list.index(client_data))