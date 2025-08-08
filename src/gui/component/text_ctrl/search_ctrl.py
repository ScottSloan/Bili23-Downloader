import wx

class SearchCtrl(wx.SearchCtrl):
    def __init__(self, parent, placeholder: str, size = wx.DefaultSize, search_btn: bool = False, clear_btn: bool = False):
        wx.SearchCtrl.__init__(self, parent, size = size)

        self.ShowSearchButton(search_btn)
        self.ShowCancelButton(clear_btn)
        self.SetDescriptiveText(placeholder)