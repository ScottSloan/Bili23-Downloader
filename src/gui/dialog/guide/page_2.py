import wx

from utils.common.data.guide import guide_2_msg

from gui.dialog.guide.agree_page import AgreePage

class Page2Panel(AgreePage):
    def __init__(self, parent: wx.Window):
        AgreePage.__init__(self, parent, guide_2_msg)

    def onChangePage(self):
        self.startCountdown()
        
        return {
            "title": "使用须知",
            "next_btn_label": "下一步",
            "next_btn_enable": False
        }