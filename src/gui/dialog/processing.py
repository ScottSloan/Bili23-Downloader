import wx

from utils.common.enums import ProcessingType

from gui.component.dialog import Dialog

class ProcessingWindow(Dialog):
    def __init__(self, parent, type: int):
        self.type = type

        Dialog.__init__(self, parent, self.get_title())

        self.SetSize(self.FromDIP((200, 80)))

        self.EnableCloseButton(False)
        
        self.init_UI()
        
        self.CenterOnParent()
        
    def init_UI(self):
        self.processing_label = wx.StaticText(self, -1, self.get_tip())

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.processing_label, 0, wx.ALL | wx.CENTER, self.FromDIP(6))

        self.SetSizerAndFit(hbox)

    def get_title(self):
        match ProcessingType(self.type):
            case ProcessingType.Normal:
                return "处理中"
            
            case ProcessingType.Parse:
                return "解析中"
            
            case ProcessingType.Interact:
                return "互动视频"
            
    def get_tip(self):
        match ProcessingType(self.type):
            case ProcessingType.Normal:
                return "正在处理中，请稍候"
            
            case ProcessingType.Parse:
                return "正在解析中，请稍候"
            
            case ProcessingType.Interact:
                return "正在探查所有分支，请稍候"

        