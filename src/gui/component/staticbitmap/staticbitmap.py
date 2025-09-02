import wx

from utils.common.style.color import Color

from gui.component.panel.panel import Panel

class StaticBitmap(Panel):
    def __init__(self, parent: wx.Window, bmp: wx.Bitmap = None, image: wx.Image = None, size: wx.Size = None):
        Panel.__init__(self, parent, size = size)

        self.SetBackgroundColour(parent.GetBackgroundColour())

        if bmp or image:
            self.SetBitmap(bmp = bmp, image = image)

    def get_bmp(self):
        width, height = self.GetClientSize()

        return self.image.Copy().Scale(width, height, wx.IMAGE_QUALITY_BICUBIC).ConvertToBitmap()

    def draw_bmp(self, event: wx.PaintEvent):
        self.SetBackgroundColour(self.GetParent().GetBackgroundColour())

        dc = wx.BufferedPaintDC(self)
        dc.Clear()

        bmp = self.get_bmp()

        dc.DrawBitmap(bmp, (0, 0), True)

    def draw_text(self, event: wx.PaintEvent):
        self.SetBackgroundColour(self.GetParent().GetBackgroundColour())

        dc = wx.BufferedPaintDC(self)
        dc.Clear()

        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 2))

        dc.SetFont(font)

        client_width, client_height = self.GetClientSize()

        total_text_height = sum(dc.GetTextExtent(line).height for line in self.text) + self.FromDIP(4) * (len(self.text) - 1)
        y_start = (client_height - total_text_height) // 2

        for line in self.text:
            text_width, text_height = dc.GetTextExtent(line)
            x = (self.FromDIP(150) - text_width) // 2
            dc.DrawText(line, x, y_start)
            y_start += text_height + self.FromDIP(4)

        dc.SetPen(wx.Pen(Color.get_border_color(), width = 1))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)

        dc.DrawRectangle(2, 2, client_width - 4, client_height - 4)

    def SetBitmap(self, bmp: wx.Bitmap = None, image: wx.Image = None):
        self.image = bmp.ConvertToImage() if bmp else image
        
        self.Bind(wx.EVT_PAINT, self.draw_bmp)

        self.Refresh()

    def SetTextTip(self, text: list):
        self.text = text

        self.Bind(wx.EVT_PAINT, self.draw_text)

        self.Refresh()