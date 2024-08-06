import wx
import os

class CoverViewerDialog(wx.Dialog):
    def __init__(self, parent, cover_image: wx.Image, cover_image_raw):
        self.cover_image, self.cover_image_raw = cover_image, cover_image_raw

        wx.Dialog.__init__(self, parent, -1, "封面")

        self.init_UI()

        self.Bind_EVT()

        self.SetSize(self.FromDIP((480, 270)))

        self.CenterOnParent()

    def init_UI(self):
        scale_size = self.GetSize()

        cover = wx.StaticBitmap(self, -1, bitmap = self.cover_image.Scale(scale_size[0], scale_size[1], wx.IMAGE_QUALITY_HIGH).ConvertToBitmap())

        self.save_btn = wx.Button(self, -1, "保存", size = self.FromDIP((80, 28)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.save_btn, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        bottom_hbox.AddStretchSpacer()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(cover, 1, wx.ALL & (~wx.BOTTOM) | wx.EXPAND, 10)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.save_btn.Bind(wx.EVT_BUTTON, self.onSave)

    def onSave(self, event):
        dlg = wx.FileDialog(self, "保存封面", os.getcwd(), wildcard = "图片文件|*.jpg", style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)

        if dlg.ShowModal() == wx.ID_OK:
            save_path = dlg.GetPath()

            with open(save_path, "wb") as f:
                f.write(self.cover_image_raw)
