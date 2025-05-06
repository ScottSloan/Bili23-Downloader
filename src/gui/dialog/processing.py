import wx

from utils.common.enums import ProcessingType

from gui.component.dialog import Dialog

class ProcessingWindow(Dialog):
    def __init__(self, parent, type: ProcessingType):
        self.type = type

        Dialog.__init__(self, parent, self.get_title())

        self.EnableCloseButton(False)
        
        self.init_UI()
        
        self.CenterOnParent()
        
    def init_UI(self):
        self.processing_label = wx.StaticText(self, -1, self.get_tip())
        self.node_title_label = wx.StaticText(self, -1, "节点：--")

        self.node_title_label.Show(self.type == ProcessingType.Interact)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.processing_label, 0, wx.ALL, self.FromDIP(6))
        vbox.Add(self.node_title_label, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

        self.SetSizerAndFit(vbox)

    def get_title(self):
        match self.type:
            case ProcessingType.Normal:
                return "处理中"
            
            case ProcessingType.Parse:
                return "解析中"
            
            case ProcessingType.Interact:
                return "互动视频"
            
    def get_tip(self):
        match self.type:
            case ProcessingType.Normal:
                return "正在处理中，请稍候"
            
            case ProcessingType.Parse:
                return "正在解析中，请稍候"
            
            case ProcessingType.Interact:
                return "正在探查所有分支，请稍候"
    
    def change_type(self, type: ProcessingType):
        self.type = type

        self.SetTitle(self.get_title())
        self.processing_label.SetLabel(self.get_tip())

        self.node_title_label.Show(self.type == ProcessingType.Interact)

        self.Layout()
        self.Fit()

    def onUpdateNode(self, title: str):
        def worker():
            self.node_title_label.SetLabel(f"节点：{title}")

            self.Layout()
            self.Fit()

        wx.CallAfter(worker)
