import wx

class SearchCtrl(wx.SearchCtrl):
    def __init__(self, parent, placeholder: str, size = wx.DefaultSize, search: bool = False, clear: bool = False):
        wx.SearchCtrl.__init__(self, parent, size = size)

        self.ShowSearchButton(search)
        self.ShowCancelButton(clear)
        self.SetDescriptiveText(placeholder)