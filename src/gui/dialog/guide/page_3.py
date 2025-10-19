import wx

from utils.common.data.guide import guide_3_msg

from gui.dialog.guide.agree_page import AgreePage

class Page3Panel(AgreePage):
    def __init__(self, parent: wx.Window):
        AgreePage.__init__(self, parent, guide_3_msg)

    def onChangePage(self):
        self.startCountdown()

        return {
            "title": "免责声明",
            "next_btn_label": "下一步",
            "next_btn_enable": False
        }