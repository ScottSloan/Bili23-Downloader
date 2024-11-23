import wx
import io
import os

from gui.templates import Frame

class CoverViewerDialog(Frame):
    def __init__(self, parent, _cover_raw_contents: bytes):
        self._cover_raw_contents = _cover_raw_contents

        Frame.__init__(self, parent, "封面")

        self.init_utils()

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

        self.onSize(None)

    def init_UI(self):
        self.cover_bmp = wx.StaticBitmap(self.panel, -1, bitmap = self.show_cover(self.FromDIP(640)))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.cover_bmp, 1, wx.EXPAND)

        self.panel.SetSizerAndFit(vbox)

        self.Fit()
        
        self.init_menubar()

    def init_menubar(self):
        menu_bar = wx.MenuBar()

        self.file_menu = wx.Menu()
        self.window_menu = wx.Menu()

        menu_bar.Append(self.file_menu, "文件(&F)")
        menu_bar.Append(self.window_menu, "窗口(&W)")

        self.file_menu.Append(self.ID_SAVE, "保存(&S)")
        self.file_menu.AppendSeparator()
        self.file_menu.Append(self.ID_CLOSE, "关闭(&X)")

        self.window_menu.Append(self.ID_FIT_SIZE, "适应图片尺寸(&A)")

        self.SetMenuBar(menu_bar)

    def Bind_EVT(self):
        self.Bind(wx.EVT_MENU, self.onSave, id = self.ID_SAVE)
        self.Bind(wx.EVT_MENU, self.onClose, id = self.ID_CLOSE)
        self.Bind(wx.EVT_MENU, self.onFitSize, id = self.ID_FIT_SIZE)

        self.panel.Bind(wx.EVT_SIZE, self.onSize)

    def init_utils(self):
        self.ID_SAVE = wx.NewIdRef()
        self.ID_CLOSE = wx.NewIdRef()
        self.ID_FIT_SIZE = wx.NewIdRef()

    def onSave(self, event):
        dlg = wx.FileDialog(self, "保存封面", os.getcwd(), wildcard = "图片文件|*.jpg", style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)

        if dlg.ShowModal() == wx.ID_OK:
            save_path = dlg.GetPath()

            with open(save_path, "wb") as f:
                f.write(self.cover_raw_contents)

    def onClose(self, event):
        self.Destroy()

    def onSize(self, event):
        temp_bmp = self.show_cover(self.GetSize()[0])

        self.cover_bmp.SetBitmap(temp_bmp)

    def onFitSize(self, event):
        self.SetSize(self.cover_bmp.GetSize()[0], self.cover_bmp.GetSize()[1] + (self.GetSize()[1] - self.GetClientSize()[1]))

    def show_cover(self, width: int):
        _temp_image = wx.Image(io.BytesIO(self._cover_raw_contents))

        _width, _height = _temp_image.GetSize()

        # 按图片原纵横比缩放
        self._x = width
        self._h = int(width / (_width / _height))

        return _temp_image.Rescale(self._x, self._h, wx.IMAGE_QUALITY_HIGH).ConvertToBitmap()
