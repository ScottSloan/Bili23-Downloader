import wx

from gui.dialog.guide.page_1 import Page1Panel
from gui.dialog.guide.page_2 import Page2Panel
from gui.dialog.guide.page_3 import Page3Panel

from gui.component.window.dialog import Dialog

class GuideDialog(Dialog):
    def __init__(self, parent: wx.Window):
        Dialog.__init__(self, parent, "", style = wx.DEFAULT_DIALOG_STYLE & (~wx.CLOSE_BOX), name = "guide")

        self.SetSize(self.FromDIP((450, 300)))

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

        wx.Bell()

    def init_UI(self):
        self.set_dark_mode()

        font = self.GetFont()
        font.SetFractionalPointSize(font.GetFractionalPointSize() + 3)

        self.title_lab = wx.StaticText(self, -1, "Title")
        self.title_lab.SetFont(font)

        split_line = wx.StaticLine(self, -1)

        self.notebook = wx.Simplebook(self, -1)

        self.notebook.AddPage(Page1Panel(self.notebook), "Page 1")
        self.notebook.AddPage(Page2Panel(self.notebook), "Page 2")
        self.notebook.AddPage(Page3Panel(self.notebook), "Page 3")

        self.indicator_lab = wx.StaticText(self, -1, "1/3")
        self.indicator_lab.SetFont(font)

        self.next_btn = wx.Button(self, -1, "下一步", size = self.get_scaled_size((80, 25)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.Add(self.indicator_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.next_btn, 0, wx.ALL, self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.title_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(10))
        vbox.Add(split_line, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, self.FromDIP(10))
        vbox.Add(self.notebook, 1, wx.EXPAND)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizer(vbox)

    def Bind_EVT(self):
        self.next_btn.Bind(wx.EVT_BUTTON, self.onNextPageEVT)

        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.onChangePageEVT)

    def init_utils(self):
        self.onChangePageEVT(0)

        if not self.DWMExtendFrameIntoClientArea():
            self.SetTitle("使用向导")

    def onNextPageEVT(self, event: wx.CommandEvent):
        self.notebook.SetSelection(self.notebook.GetSelection() + 1)

    def onChangePageEVT(self, event: wx.CommandEvent):
        page: Page1Panel = self.notebook.GetCurrentPage()
        data = page.onChangePage()

        self.title_lab.SetLabel(data.get("title", ""))
        self.indicator_lab.SetLabel("%d/%d" % (self.notebook.GetSelection() + 1, self.notebook.GetPageCount()))

        self.next_btn.SetLabel(data.get("next_btn_label", "下一步"))
        self.next_btn.Enable(data.get("next_btn_enable", True))

    def EnableNextButton(self, enable: bool):
        self.next_btn.Enable(enable)