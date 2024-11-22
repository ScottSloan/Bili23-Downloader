import wx
import io
import os

from utils.tool_v2 import RequestTool

class CoverViewerDialog(wx.Dialog):
    def __init__(self, parent, cover_url: str):
        self.cover_url = cover_url

        wx.Dialog.__init__(self, parent, -1, "封面")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

    def init_UI(self):
        cover = wx.StaticBitmap(self, -1, bitmap = self.get_cover_bmp())

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

    def get_cover_bmp(self):
        self.cover_raw_contents = RequestTool.request(self.cover_url)

        _temp_image = wx.Image(io.BytesIO(self.cover_raw_contents))

        _width, _height = _temp_image.GetSize()

        # 按图片原纵横比缩放
        new_height = int(self.FromDIP(640) / (_width / _height))

        return _temp_image.Scale(self.FromDIP(640), new_height, wx.IMAGE_QUALITY_HIGH).ConvertToBitmap()

    def onSave(self, event):
        dlg = wx.FileDialog(self, "保存封面", os.getcwd(), wildcard = "图片文件|*.jpg", style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)

        if dlg.ShowModal() == wx.ID_OK:
            save_path = dlg.GetPath()

            with open(save_path, "wb") as f:
                f.write(self.cover_raw_contents)
