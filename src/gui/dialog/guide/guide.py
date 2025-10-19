import wx

from gui.dialog.guide.page_1 import Page1Panel
from gui.dialog.guide.page_2 import Page2Panel
from gui.dialog.guide.page_3 import Page3Panel
from gui.dialog.guide.page_4 import Page4Panel

from gui.component.window.dialog import Dialog

class GuideDialog(Dialog):
    def __init__(self, parent: wx.Window):
        self.can_close = False

        Dialog.__init__(self, parent, "", style = wx.DEFAULT_DIALOG_STYLE & (~wx.CLOSE_BOX) & (~wx.SYSTEM_MENU), name = "guide")

        self.SetSize(self.FromDIP((475, 310)))

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

        self.notebook = wx.Simplebook(self, -1)

        self.notebook.AddPage(Page1Panel(self.notebook), "Page 1")
        self.notebook.AddPage(Page2Panel(self.notebook), "Page 2")
        self.notebook.AddPage(Page3Panel(self.notebook), "Page 3")
        self.notebook.AddPage(Page4Panel(self.notebook), "Page 4")

        self.indicator_lab = wx.StaticText(self, -1, "1/4")
        self.indicator_lab.SetFont(font)

        self.next_btn = wx.Button(self, -1, "下一步", size = self.get_scaled_size((80, 25)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.Add(self.indicator_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(10))
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.next_btn, 0, wx.ALL, self.FromDIP(10))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.title_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(10))
        vbox.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, self.FromDIP(10))
        vbox.Add(self.notebook, 1, wx.EXPAND)
        vbox.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, self.FromDIP(10))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizer(vbox)

    def Bind_EVT(self):
        self.Bind(wx.EVT_CLOSE, self.onCloseEVT)

        self.next_btn.Bind(wx.EVT_BUTTON, self.onNextPageEVT)

        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.onChangePageEVT)

    def init_utils(self):
        self.onChangePageEVT(0)

        if not self.DWMExtendFrameIntoClientArea():
            self.SetTitle("使用向导")

    def onCloseEVT(self, event: wx.CloseEvent):
        if self.can_close:
            return super().onCloseEVT(event)

    def onNextPageEVT(self, event: wx.CommandEvent):
        if self.notebook.GetSelection() + 1 >= self.notebook.GetPageCount():
            self.notebook.GetCurrentPage().save()

            self.can_close = True
            self.Close()

        else:
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