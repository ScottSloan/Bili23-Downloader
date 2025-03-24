import wx

from gui.component.frame import Frame

class DebugWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, "Debug")

        self.init_UI()

        self.CenterOnParent()

    def init_UI(self):
        panel = wx.Panel(self, -1)

        parse_info = wx.StaticText(panel, -1, "查看当前 ParseInfo")

        self.info_list = wx.ListCtrl(panel, -1, style = wx.LC_REPORT)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(parse_info, 0, wx.ALL, 10)
        vbox.Add(self.info_list, 0, wx.ALL & (~wx.TOP), 10)

        panel.SetSizerAndFit()
    
    def init_utils(self):
        pass