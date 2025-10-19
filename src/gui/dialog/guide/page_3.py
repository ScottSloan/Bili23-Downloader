import wx
import gettext

from utils.common.data.guide import guide_3_msg

from gui.dialog.guide.agree_page import AgreePage

_ = gettext.gettext

class Page3Panel(AgreePage):
    def __init__(self, parent: wx.Window):
        AgreePage.__init__(self, parent, guide_3_msg)

    def onChangePage(self):
        self.startCountdown()

        return {
            "title": _("免责声明"),
            "next_btn_label": _("下一步"),
            "next_btn_enable": False
        }