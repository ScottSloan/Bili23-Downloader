import wx
import gettext

from gui.component.panel.scrolled_panel import ScrolledPanel
from gui.component.panel.panel import Panel

_ = gettext.gettext

class Page(Panel):
    def __init__(self, parent: wx.Window, name: str, index: int):
        from gui.window.main.main_v3 import MainWindow

        self.parent: MainWindow = parent.GetParent().GetParent()
        self.index = index

        Panel.__init__(self, parent, name = name)

        self.scrolled_panel = ScrolledPanel(self)
        self.panel = Panel(self.scrolled_panel)

    def init_UI(self):
        self.scrolled_panel.sizer.Add(self.panel, 0, wx.EXPAND)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.scrolled_panel, 1, wx.EXPAND)

        self.SetSizer(vbox)

        self.scrolled_panel.Layout()

    def onValidate(self):
        pass

    def warn(self, message: str):
        wx.MessageDialog(self.GetParent(), _("保存设置失败\n\n所在页面：%s\n错误原因：%s" % (self.GetName(), message)), _("警告"), wx.ICON_WARNING).ShowModal()

        self.change_to_current_page()

        return True
    
    def change_to_current_page(self):
        parent: wx.Notebook = self.GetParent()

        parent.SetSelection(self.index)
