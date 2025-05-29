import wx

from gui.component.frame import Frame
from gui.component.panel import Panel

class FileDropTarget(wx.FileDropTarget):
    def __init__(self):
        wx.FileDropTarget.__init__(self)

    def OnDropFiles(self, x, y, filenames):
        print(filenames[0])

        return True
    
class DropFilePage(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.Bind_EVT()

    def Bind_EVT(self):
        self.Bind(wx.EVT_PAINT, self.onPaint)

    def onPaint(self, event):
        dc = wx.PaintDC(self)

        self.draw_dashed_border(dc)
        self.draw_centered_text(dc)

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
        total_text_height = sum(dc.GetTextExtent(line).height for line in text) + 5 * (len(text) - 1)
        y_start = (client_height - total_text_height) // 2

        for line in text:
            text_width, text_height = dc.GetTextExtent(line)
            x = (self.GetClientSize().width - text_width) // 2  # 水平居中
            dc.DrawText(line, x, y_start)
            y_start += text_height + 5  # 行间距5像素

class FormatFactoryWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, "视频工具箱")

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CentreOnParent()

    def init_UI(self):
        file_drop_target = FileDropTarget()

        self.SetDropTarget(file_drop_target)

        self.panel = Panel(self)

        self.notebook = wx.Simplebook(self.panel, -1)

        self.notebook.AddPage(DropFilePage(self.notebook), "drop files")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.notebook, 1, wx.EXPAND)

        self.panel.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        pass

    def init_utils(self):
        pass
    