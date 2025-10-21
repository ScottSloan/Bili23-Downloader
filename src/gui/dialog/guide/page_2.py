import wx
import gettext

from utils.common.data.guide import guide_2_msg

from gui.dialog.guide.agree_page import AgreePage

_ = gettext.gettext

class Page2Panel(AgreePage):
    def __init__(self, parent: wx.Window):
        AgreePage.__init__(self, parent, guide_2_msg)

    def onChangePage(self):
        self.startCountdown()
        
        return {
            "title": _("使用须知"),
            "next_btn_label": _("下一步"),
            "next_btn_enable": False
        }