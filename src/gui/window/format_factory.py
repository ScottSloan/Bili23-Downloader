import wx

from utils.config import Config
from utils.common.icon_v3 import Icon, IconID, IconSize

from gui.component.frame import Frame
from gui.component.panel import Panel
from gui.component.large_bitmap_button import LargeBitmapButton

class FileDropTarget(wx.FileDropTarget):
    def __init__(self, parent):
        self.parent = parent

        wx.FileDropTarget.__init__(self)

    def OnDropFiles(self, x, y, filenames):
        self.parent.set_input_path(filenames[0])

        return True
    
class DropFilePage(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.Bind_EVT()

    def Bind_EVT(self):
        self.Bind(wx.EVT_PAINT, self.onPaintEVT)
        self.Bind(wx.EVT_LEFT_DOWN, self.onBrowseFileEVT)

    def onPaintEVT(self, event):
        dc = wx.PaintDC(self)

        self.draw_dashed_border(dc)
        self.draw_centered_text(dc)

    def onBrowseFileEVT(self, event):
        dlg = wx.FileDialog(self, "选择文件", defaultDir = Config.Download.path, style = wx.FD_OPEN)

        if dlg.ShowModal() == wx.ID_OK:
            self.GetParent().GetParent().GetParent().set_input_path(dlg.GetPath())

        dlg.Destroy()

    def draw_dashed_border(self, dc: wx.PaintDC):
        pen = wx.Pen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT), 2, wx.PENSTYLE_LONG_DASH)

        dc.SetPen(pen)

        client_size = self.GetClientSize()

        rect = wx.Rect(self.FromDIP(6), self.FromDIP(6), client_size.width - self.FromDIP(12), client_size.height - self.FromDIP(12))

        dc.DrawRectangle(rect)
    
    def draw_centered_text(self, dc: wx.PaintDC):
        dc.SetFont(self.GetFont())

        text = ["将文件拖拽至此处", "或点击此处手动选择文件"]

        client_height = self.GetClientSize().height
        total_text_height = sum(dc.GetTextExtent(line).height for line in text) + self.FromDIP(4) * (len(text) - 1)
        y_start = (client_height - total_text_height) // 2

        for line in text:
            text_width, text_height = dc.GetTextExtent(line)
            x = (self.GetClientSize().width - text_width) // 2
            dc.DrawText(line, x, y_start)
            y_start += text_height + self.FromDIP(4)

class SelectPage(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        font = self.GetFont()
        font.SetFractionalPointSize(font.GetFractionalPointSize() + 2)

        tip_lab = wx.StaticText(self, -1, "要如何处理此文件？")
        tip_lab.SetFont(font)

        self.detail_info_btn = LargeBitmapButton(self, Icon.get_icon_bitmap(IconID.INFO_ICON, size = IconSize.MEDIUM), "详细信息")

        self.convertion_btn = LargeBitmapButton(self, Icon.get_icon_bitmap(IconID.CONVERT_ICON, size = IconSize.MEDIUM), "格式转换")

        self.cutclip_btn = LargeBitmapButton(self, Icon.get_icon_bitmap(IconID.CUT_ICON, size = IconSize.MEDIUM), "截取片段")

        self.extraction_btn = LargeBitmapButton(self, Icon.get_icon_bitmap(IconID.AUDIO_ICON, size = IconSize.MEDIUM), "音频提取")

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddStretchSpacer()
        hbox.Add(self.detail_info_btn, 0, wx.ALL, self.FromDIP(6))
        hbox.Add(self.convertion_btn, 0, wx.ALL, self.FromDIP(6))
        hbox.Add(self.cutclip_btn, 0, wx.ALL, self.FromDIP(6))
        hbox.Add(self.extraction_btn, 0, wx.ALL, self.FromDIP(6))
        hbox.AddStretchSpacer()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(tip_lab, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        vbox.AddStretchSpacer()
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.AddStretchSpacer()

        self.SetSizer(vbox)

class CutClipPage(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        pass

class FormatFactoryWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, "视频工具箱")

        self.SetSize(self.FromDIP((450, 280)))

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CentreOnParent()

    def init_UI(self):
        file_drop_target = FileDropTarget(self)

        self.SetDropTarget(file_drop_target)

        self.panel = Panel(self)

        self.notebook = wx.Simplebook(self.panel, -1)

        self.notebook.AddPage(DropFilePage(self.notebook), "drop files")
        self.notebook.AddPage(SelectPage(self.notebook), "select action")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.notebook, 1, wx.EXPAND)

        self.panel.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        pass

    def init_utils(self):
        pass
    
    def set_input_path(self, path: str):
        self.input_path = path

        self.select_action()

    def select_action(self):
        self.notebook.SetSelection(1)