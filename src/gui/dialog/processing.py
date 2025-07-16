import wx

from utils.common.enums import ProcessingType

from gui.component.window.dialog import Dialog

class ProcessingWindow(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "Processing")

        self.EnableCloseButton(False)
        
        self.init_UI()
        
        self.CenterOnParent()
        
    def init_UI(self):
        self.processing_label = wx.StaticText(self, -1, "label")
        self.node_title_label = wx.StaticText(self, -1, "节点：--")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.processing_label, 0, wx.ALL, self.FromDIP(6))
        vbox.Add(self.node_title_label, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

        self.SetSizerAndFit(vbox)

    def onUpdateNode(self, title: str):
        def worker():
            self.node_title_label.SetLabel(f"节点：{title}")

            self.Layout()
            self.Fit()

        wx.CallAfter(worker)

    def ShowModal(self, type: ProcessingType):
        self.SetType(type)

        return super().ShowModal()
    
    def SetType(self, type: ProcessingType):
        match type:
            case ProcessingType.Process:
                title = "处理中"
                tip = "正在处理中，请稍候"
                show = False

            case ProcessingType.Parse:
                title = "解析中"
                tip = "正在解析中，请稍候"
                show = False

            case ProcessingType.Interact:
                title = "互动视频"
                tip = "正在探查所有节点，请稍候"
                show = True

        self.SetTitle(title)
        self.processing_label.SetLabel(tip)
        self.node_title_label.Show(show)

        self.GetSizer().Layout()
        self.Fit()
        
        self.CenterOnParent()
