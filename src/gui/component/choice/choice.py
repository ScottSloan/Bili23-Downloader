import wx

class Choice(wx.Choice):
    def __init__(self, parent: wx.Window):
        wx.Choice.__init__(self, parent, -1)

        self.data: dict = {}

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