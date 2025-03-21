import wx

from gui.component.dialog import Dialog

class ProcessingWindow(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "处理中")

        self.SetSize(self.FromDIP((200, 80)))

        self.EnableCloseButton(False)
        
        self.init_UI()
        
        self.CenterOnParent()
        
    def init_UI(self):
        self.processing_label = wx.StaticText(self, -1, "正在处理中，请稍候")

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.processing_label, 0, wx.ALL | wx.CENTER, 10)

        self.SetSizerAndFit(hbox)
        