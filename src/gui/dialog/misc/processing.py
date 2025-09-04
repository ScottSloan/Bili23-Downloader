import wx

from utils.common.enums import ProcessingType

from gui.component.window.dialog import Dialog

class ProcessingWindow(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "解析中", style = wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        self.EnableCloseButton(False)
        
        self.init_UI()

        self.Bind_EVT()
        
        self.CenterOnParent()
        
    def init_UI(self):
        self.processing_label = wx.StaticText(self, -1, "正在解析中，请稍候")
        self.name_lab = wx.StaticText(self, -1, "")
        self.node_title_label = wx.StaticText(self, -1, "节点：--")

        self.cancel_btn = wx.Button(self, -1, "取消", size = self.get_scaled_size((60, 24)))

        btn_hbox = wx.BoxSizer(wx.HORIZONTAL)
        btn_hbox.AddStretchSpacer()
        btn_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        btn_hbox.AddStretchSpacer()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.processing_label, 0, wx.ALL, self.FromDIP(6))
        vbox.Add(self.name_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        vbox.Add(self.node_title_label, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        vbox.Add(btn_hbox, 0, wx.EXPAND)

        self.SetSizer(vbox)

    def Bind_EVT(self):
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.onCancelEVT)

    def onCancelEVT(self, event):
        pass
    
    def UpdateName(self, name: str):
        def worker():
            self.name_lab.SetLabel(name)

            self.Layout()
        
        wx.CallAfter(worker)

    def UpdateTitle(self, title: str):
        def worker():
            self.node_title_label.SetLabel(title)

            self.Layout()
        
        wx.CallAfter(worker)

    def ShowModal(self, type: ProcessingType):
        self.SetType(type)

        self.reset()

        return super().ShowModal()
    
    def SetType(self, type: ProcessingType):
        def worker():
            self.SetTitle(title)
            self.processing_label.SetLabel(tip)

            self.name_lab.Show(title_show)
            self.node_title_label.Show(title_show)

            self.Layout()
            
        match type:
            case ProcessingType.Process:
                title = "处理中"
                tip = "正在处理中，请稍候"
                title_show = False

            case ProcessingType.Parse:
                title = "解析中"
                tip = "正在解析中，请稍候"
                title_show = False

            case ProcessingType.Interact:
                title = "互动视频"
                tip = "正在探查所有节点，请稍候"
                title_show = True

            case ProcessingType.Page:
                title = "解析中"
                tip = "正在获取所有分页数据，请稍候"
                title_show = True

        wx.CallAfter(worker)

    def Layout(self):
        super().Layout()

        self.Fit()

        self.CenterOnParent()

    def reset(self):
        self.name_lab.SetLabel("")
        self.node_title_label.SetLabel("节点：--")