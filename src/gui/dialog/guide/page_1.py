import wx

from utils.common.data.guide import guide_1_msg

from gui.component.panel.panel import Panel

class Page1Panel(Panel):
    def __init__(self, parent: wx.Window):
        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        font = self.GetFont()
        font.SetFractionalPointSize(font.GetFractionalPointSize() + 1)

        self.desc_lab = wx.StaticText(self, -1, guide_1_msg)
        self.desc_lab.Wrap(self.FromDIP(400))
        self.desc_lab.SetFont(font)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.desc_lab, 0, wx.ALL, self.FromDIP(10))

        self.SetSizer(vbox)

    def onChangePage(self):
        return {
            "title": "欢迎使用 Bili23 Downloader",
            "next_btn_label": "下一步",
            "next_btn_enable": True
        }