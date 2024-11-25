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

        self.onResizeEVT(None)
        self.onFitSizeEVT(None)

    def init_UI(self):
        self.cover_bmp = wx.StaticBitmap(self.panel, -1, bitmap = self.show_cover(self.FromDIP(640)))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.cover_bmp, 1, wx.EXPAND)

        self.panel.SetSizerAndFit(vbox)

        self.Fit()
        
        self.init_menubar()
        self.init_statusbar()

    def init_menubar(self):
        menu_bar = wx.MenuBar()

        self.file_menu = wx.Menu()
        self.options_menu = wx.Menu()

        menu_bar.Append(self.file_menu, "文件(&F)")
        menu_bar.Append(self.options_menu, "选项(&O)")

        self.file_menu.Append(self.ID_SAVE, "保存原图(&S)\tCtrl+S")
        self.file_menu.AppendSeparator()
        self.file_menu.Append(self.ID_CLOSE, "关闭(&X)\tAlt+F4")

        self.options_menu.Append(self.ID_ORIGINAL_SIZE, "显示原图(&R)")
        self.options_menu.AppendSeparator()
        self.options_menu.Append(self.ID_FIT_SIZE, "窗口适应图片尺寸(&A)")

        self.SetMenuBar(menu_bar)

    def init_statusbar(self):
        _size = self._temp_image.GetSize()

        self.status_bar: wx.StatusBar = self.CreateStatusBar()

        self.status_bar.SetFieldsCount(2)
        self.status_bar.SetStatusWidths([250, 250])

        self.status_bar.SetStatusText("Ready", 0)
        self.status_bar.SetStatusText(f"原图：{_size[0]}x{_size[1]}", 1)

    def Bind_EVT(self):
        self.Bind(wx.EVT_MENU, self.onSaveEVT, id = self.ID_SAVE)
        self.Bind(wx.EVT_MENU, self.onExitEVT, id = self.ID_CLOSE)
        self.Bind(wx.EVT_MENU, self.onFitSizeEVT, id = self.ID_FIT_SIZE)
        self.Bind(wx.EVT_MENU, self.onOriginalSizeEVT, id = self.ID_ORIGINAL_SIZE)

        self.panel.Bind(wx.EVT_SIZE, self.onResizeEVT)

    def init_utils(self):
        self.ID_SAVE = wx.NewIdRef()
        self.ID_CLOSE = wx.NewIdRef()
        self.ID_ORIGINAL_SIZE = wx.NewIdRef()
        self.ID_FIT_SIZE = wx.NewIdRef()

    def onSaveEVT(self, event):
        dlg = wx.FileDialog(self, "保存封面", os.getcwd(), wildcard = "图片文件|*.jpg", style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)

        if dlg.ShowModal() == wx.ID_OK:
            save_path = dlg.GetPath()

            with open(save_path, "wb") as f:
                f.write(self.cover_raw_contents)

    def onExitEVT(self, event):
        self.Destroy()

    def onResizeEVT(self, event):
        temp_bmp: wx.Bitmap = self.show_cover(self.GetSize()[0])
        _size = temp_bmp.GetSize()

        self.cover_bmp.SetBitmap(temp_bmp)

        self.status_bar.SetStatusText(f"尺寸：{_size[0]}x{_size[1]}", 0)

    def onFitSizeEVT(self, event):
        self.SetSize(self.cover_bmp.GetSize()[0], self.cover_bmp.GetSize()[1] + (self.GetSize()[1] - self.GetClientSize()[1]))

    def onOriginalSizeEVT(self, event):
        self.cover_bmp.SetBitmap(self._temp_image)

        self.onFitSizeEVT(event)

        self.CenterOnScreen()

    def show_cover(self, width: int):
        self._temp_image = wx.Image(io.BytesIO(self._cover_raw_contents))

        _width, _height = self._temp_image.GetSize()

        # 按图片原纵横比缩放
        self._x = width
        self._h = int(width / (_width / _height))

        return self._temp_image.Copy().Rescale(self._x, self._h, wx.IMAGE_QUALITY_HIGH).ConvertToBitmap()
