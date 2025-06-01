import wx
from datetime import datetime
import wx.lib.masked as masked

from utils.config import Config
from utils.tool_v2 import FormatTool
from utils.common.icon_v4 import Icon, IconID, IconSize
from utils.common.enums import Platform

from utils.module.vlc_player import VLCPlayer, VLCState, VLCEvent

from gui.component.frame import Frame
from gui.component.panel import Panel
from gui.component.large_bitmap_button import LargeBitmapButton
from gui.component.bitmap_button import BitmapButton

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
        pen = wx.Pen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENUTEXT), 2, wx.PENSTYLE_LONG_DASH)
        brush = wx.Brush(wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENUBAR))

        dc.SetPen(pen)
        dc.SetBrush(brush)

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

        self.Bind_EVT()

    def init_UI(self):
        self.detail_info_btn = LargeBitmapButton(self, Icon.get_icon_bitmap(IconID.Info, icon_size = IconSize.MEDIUM), "详细信息")

        self.convertion_btn = LargeBitmapButton(self, Icon.get_icon_bitmap(IconID.Convert, icon_size = IconSize.MEDIUM), "格式转换")

        self.cutclip_btn = LargeBitmapButton(self, Icon.get_icon_bitmap(IconID.Cut, icon_size = IconSize.MEDIUM), "截取片段")

        self.extraction_btn = LargeBitmapButton(self, Icon.get_icon_bitmap(IconID.Audio, icon_size = IconSize.MEDIUM), "音频提取")

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddStretchSpacer()
        hbox.Add(self.detail_info_btn, 0, wx.ALL, self.FromDIP(6))
        hbox.Add(self.convertion_btn, 0, wx.ALL, self.FromDIP(6))
        hbox.Add(self.cutclip_btn, 0, wx.ALL, self.FromDIP(6))
        hbox.Add(self.extraction_btn, 0, wx.ALL, self.FromDIP(6))
        hbox.AddStretchSpacer()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddStretchSpacer()
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.AddStretchSpacer()

        self.SetSizer(vbox)

    def Bind_EVT(self):
        self.detail_info_btn.onClickCustomEVT = self.onDetailInfoEVT
        self.convertion_btn.onClickCustomEVT = self.onConvertionEVT
        self.cutclip_btn.onClickCustomEVT = self.onCutClipEVT
        self.extraction_btn.onClickCustomEVT = self.onExtractionEVT

    def onDetailInfoEVT(self):
        self.get_input_file(0, "详细信息")

    def onConvertionEVT(self):
        self.get_input_file(1, "格式转换")

    def onCutClipEVT(self):
        self.get_input_file(2, "截取片段")

    def onExtractionEVT(self):
        self.get_input_file(3, "音频分离")

    def get_input_file(self, page: int, title: str):
        parent = self.GetParent().GetParent().GetParent()

        parent.select_action(1)
        parent.set_target_page(page, title)

class SubPage(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

    def init_UI(self):
        font = self.GetFont()
        font.SetFractionalPointSize(font.GetFractionalPointSize() + 3)

        self.back_icon = wx.StaticBitmap(self, -1, Icon.get_icon_bitmap(IconID.Back, icon_size = IconSize.SMALL))

        self.title_lab = wx.StaticText(self, -1, "Title")
        self.title_lab.SetFont(font)

        top_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_hbox.Add(self.back_icon, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.AddSpacer(self.FromDIP(4))
        top_hbox.Add(self.title_lab, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        top_border = wx.StaticLine(self, -1)

        self.notebook = wx.Simplebook(self, -1)

        self.notebook.AddPage(DetailInfoPage(self.notebook), "detail_info")
        self.notebook.AddPage(ConvertionPage(self.notebook), "convertion")
        self.notebook.AddPage(CutClipPage(self.notebook), "cut clip")
        self.notebook.AddPage(ExtractionPage(self.notebook), "extraction")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(top_hbox, 0, wx.EXPAND)
        vbox.Add(top_border, 0, wx.EXPAND)
        vbox.Add(self.notebook, 1, wx.EXPAND)

        self.SetSizer(vbox)

    def Bind_EVT(self):
        self.back_icon.Bind(wx.EVT_LEFT_DOWN, self.onBackEVT)

    def init_utils(self):
        self.input_path = None

    def onBackEVT(self, event):
        parent = self.GetParent().GetParent().GetParent()

        self.notebook.GetCurrentPage().onCloseEVT()

        parent.select_action(0)

class DetailInfoPage(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        pass

    def Bind_EVT(self):
        pass

    def init_utils(self):
        pass

    def onCloseEVT(self):
        pass

class ConvertionPage(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        pass

    def Bind_EVT(self):
        pass

    def init_utils(self):
        pass

    def onCloseEVT(self):
        pass

class CutClipPage(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        self.player_panel = Panel(self)
        self.player_panel.SetBackgroundColour("black")

        self.play_btn = BitmapButton(self, Icon.get_icon_bitmap(IconID.Play))
        self.stop_btn = BitmapButton(self, Icon.get_icon_bitmap(IconID.Stop))
        self.time_lab = wx.StaticText(self, -1, "00:00")
        self.length_lab = wx.StaticText(self, -1, "00:00")
        self.progress_bar = wx.Slider(self, -1)

        ctrl_hbox = wx.BoxSizer(wx.HORIZONTAL)
        ctrl_hbox.Add(self.play_btn, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        ctrl_hbox.Add(self.stop_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        ctrl_hbox.Add(self.time_lab, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        ctrl_hbox.Add(self.progress_bar, 1, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        ctrl_hbox.Add(self.length_lab, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        bottom_line = wx.StaticLine(self, -1)

        start_time_lab = wx.StaticText(self, -1, "开始时间")
        self.start_time_box = masked.TimeCtrl(self, -1, "00:00:00")
        self.start_time_paste_btn = wx.Button(self, -1, "填入", size = self.get_scaled_size((50, 24)))
        self.start_time_paste_btn.SetToolTip("填入当前进度作为开始截取的时间")
        self.start_time_box.SetOwnFont(self.GetFont())

        start_time_hbox = wx.BoxSizer(wx.HORIZONTAL)
        start_time_hbox.Add(start_time_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        start_time_hbox.Add(self.start_time_box, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        start_time_hbox.Add(self.start_time_paste_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        end_time_lab = wx.StaticText(self, -1, "结束时间")
        self.end_time_box = masked.TimeCtrl(self, -1, "00:00:10")
        self.end_time_paste_btn = wx.Button(self, -1, "填入", size = self.get_scaled_size((50, 24)))
        self.end_time_paste_btn.SetToolTip("填入当前进度作为结束截取的时间")
        self.end_time_box.SetOwnFont(self.GetFont())

        end_hbox = wx.BoxSizer(wx.HORIZONTAL)
        end_hbox.Add(end_time_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        end_hbox.Add(self.end_time_box, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        end_hbox.Add(self.end_time_paste_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.cut_btn = wx.Button(self, -1, "开始截取", size = self.get_scaled_size((100, 28)))

        time_hbox = wx.BoxSizer(wx.HORIZONTAL)
        time_hbox.Add(start_time_hbox, 0, wx.EXPAND)
        time_hbox.Add(end_hbox, 0, wx.EXPAND)
        time_hbox.AddStretchSpacer()
        time_hbox.Add(self.cut_btn, 0, wx.ALL, self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.player_panel, 1, wx.ALL | wx.EXPAND, self.FromDIP(6))
        vbox.Add(ctrl_hbox, 0, wx.EXPAND)
        vbox.Add(bottom_line, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.EXPAND)
        vbox.Add(time_hbox, 0, wx.EXPAND)

        self.SetSizer(vbox)

        self.timer = wx.Timer(self, -1)

    def Bind_EVT(self):
        self.play_btn.Bind(wx.EVT_BUTTON, self.onPlayEVT)
        self.stop_btn.Bind(wx.EVT_BUTTON, self.onStopEVT)

        self.progress_bar.Bind(wx.EVT_SCROLL_THUMBTRACK, self.onSliderEVT)
        self.progress_bar.Bind(wx.EVT_SCROLL_THUMBRELEASE, self.onSeekEVT)

        self.start_time_paste_btn.Bind(wx.EVT_BUTTON, self.onPasteStartTimeEVT)
        self.end_time_paste_btn.Bind(wx.EVT_BUTTON, self.onPasteEndTimeEVT)
        self.cut_btn.Bind(wx.EVT_BUTTON, self.onCutEVT)

        self.Bind(wx.EVT_TIMER, self.onTimerEVT)

    def init_utils(self):
        self.player = VLCPlayer()

        self.player.set_window(self.player_panel.GetHandle())
        self.player.set_mrl(self.GetParent().GetParent().input_path)
        self.player.register_callback(VLCEvent.LengthChanged.value, self.onLengthChangeEVT)

        self.player_panel.SetInitialSize()
        self.GetSizer().Layout()

        self.onSlider = False

    def onCloseEVT(self):
        self.reset()

    def onPlayEVT(self, event):
        match self.player.get_state():
            case VLCState.Stopped:
                self.player.play()

                if not self.timer.IsRunning():
                    self.timer.Start(1000)

                self.set_icon(VLCState.Paused)

            case VLCState.Playing:
                self.player.pause()

                self.set_icon(VLCState.Playing)

            case VLCState.Paused:
                self.player.resume()

                self.set_icon(VLCState.Paused)

    def onSliderEVT(self, event):
        self.onSlider = True

        self.set_time_lab(self.progress_bar.GetValue())

    def onSeekEVT(self, event):
        offset = self.progress_bar.GetValue()

        self.player.seek(offset)

        self.onSlider = False

    def onTimerEVT(self, event):
        if self.player.get_state() == VLCState.Ended:
            self.reset()

        if not self.onSlider:
            offset = self.player.get_progress()

            self.progress_bar.SetValue(offset)

            self.set_time_lab(offset)

    def onStopEVT(self, event):
        self.reset()

    def onPasteStartTimeEVT(self, event):
        self.start_time_box.SetValue(self.get_current_progress())

    def onPasteEndTimeEVT(self, event):
        self.end_time_box.SetValue(self.get_current_progress())

    def onCutEVT(self, event):
        pass
    
    def onLengthChangeEVT(self, event):
        length = self.player.get_length()

        self.progress_bar.SetRange(0, length)
        self.length_lab.SetLabel(FormatTool._format_duration(int(length / 1000)))

    def get_current_progress(self):
        offset = self.player.get_progress()
        date_str = FormatTool._format_duration(int(offset / 1000), show_hour = True)

        return wx.DateTime(datetime.strptime(date_str, "%H:%M:%S"))

    def set_time_lab(self, offset: int):
        def worker():
            self.time_lab.SetLabel(FormatTool._format_duration(int(offset / 1000)))

        wx.CallAfter(worker)

    def set_icon(self, state: str):
        match state:
            case VLCState.Playing | VLCState.Stopped:
                self.play_btn.SetBitmap(Icon.get_icon_bitmap(IconID.Play))

            case VLCState.Paused:
                self.play_btn.SetBitmap(Icon.get_icon_bitmap(IconID.Pause))

    def reset(self):
        if hasattr(self, "player"):
            self.player.stop()

        self.timer.Stop()

        self.progress_bar.SetValue(0)
        self.time_lab.SetLabel("00:00")

        self.set_icon(VLCState.Stopped)

class ExtractionPage(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        pass
    
    def Bind_EVT(self):
        pass

    def init_utils(self):
        pass

    def onCloseEVT(self):
        pass

class FormatFactoryWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, "视频工具箱")

        self.SetSize(self.FromDIP((750, 450)))

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CentreOnParent()

    def init_UI(self):
        file_drop_target = FileDropTarget(self)

        self.SetDropTarget(file_drop_target)

        self.panel = Panel(self)

        self.notebook = wx.Simplebook(self.panel, -1)

        self.select_page = SelectPage(self.notebook)
        self.drop_files_page = DropFilePage(self.notebook)
        self.sub_page = SubPage(self.notebook)

        self.notebook.AddPage(self.select_page, "select action")
        self.notebook.AddPage(self.drop_files_page, "drop files")
        self.notebook.AddPage(self.sub_page, "sub page")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.notebook, 1, wx.EXPAND)

        self.panel.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.Bind(wx.EVT_CLOSE, self.onCloseEVT)

    def init_utils(self):
        pass
    
    def onCloseEVT(self, event):
        self.sub_page.notebook.GetCurrentPage().onCloseEVT()

        event.Skip()

    def set_input_path(self, path: str):
        self.sub_page.input_path = path

        self.select_action(2)
        self.sub_page.notebook.GetCurrentPage().init_utils()

    def select_action(self, page: int):
        self.notebook.SetSelection(page)

    def set_target_page(self, page: int, title: str):
        self.sub_page.notebook.SetSelection(page)

        self.sub_page.title_lab.SetLabel(title)