import wx

from utils.common.data_type import LiveRoomInfo
from utils.common.thread import Thread
from utils.common.icon_v4 import Icon, IconID
from utils.common.enums import LiveRecordingStatus, LiveStatus

from utils.module.pic.cover import Cover

from gui.dialog.live_recording_option import LiveRecordingOptionDialog

from gui.component.label.info_label import InfoLabel
from gui.component.button.bitmap_button import BitmapButton

from gui.component.panel.panel import Panel

class LiveRoomItemPanel(Panel):
    def __init__(self, parent, info: LiveRoomInfo, live_recording_window):
        self.info, self.live_recording_window = info, live_recording_window

        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

    def init_UI(self):
        self.set_dark_mode()

        font = self.GetFont()
        font.SetFractionalPointSize(font.GetFractionalPointSize() + 2)

        self.cover_bmp = wx.StaticBitmap(self, -1, size = self.FromDIP((112, 63)))
        self.cover_bmp.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.cover_bmp.SetToolTip("查看封面")

        self.up_name_lab = wx.StaticText(self, -1, "主播")
        self.up_name_lab.SetFont(font)

        self.title_lab = wx.StaticText(self, -1, "直播间标题")

        self.room_id_lab = InfoLabel(self, "ID 123456", size = self.FromDIP((90, 16)))
        self.area_lab = InfoLabel(self, "分区", size = self.FromDIP((150, 16)))
        self.live_status_lab = InfoLabel(self, "直播中", size = self.FromDIP((50, 16)))
        self.rec_bmp = wx.StaticBitmap(self, -1, bitmap = Icon.get_icon_bitmap(IconID.Rec))
        self.rec_bmp.Hide()
        self.recording_lab = wx.StaticText(self, -1, "录制中")
        self.recording_lab.SetForegroundColour(wx.Colour(235, 54, 67))
        self.recording_lab.Hide()

        info_hbox = wx.BoxSizer(wx.HORIZONTAL)
        info_hbox.Add(self.room_id_lab, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.ALIGN_CENTER | wx.ALIGN_LEFT, self.FromDIP(6))
        info_hbox.Add(self.area_lab, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.ALIGN_CENTER | wx.ALIGN_LEFT, self.FromDIP(6))
        info_hbox.Add(self.live_status_lab, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.ALIGN_CENTER | wx.ALIGN_LEFT, self.FromDIP(6))
        info_hbox.Add(self.rec_bmp, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) & (~wx.RIGHT) | wx.ALIGN_CENTER | wx.ALIGN_LEFT, self.FromDIP(6))
        info_hbox.Add(self.recording_lab, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        room_info_vbox = wx.BoxSizer(wx.VERTICAL)
        room_info_vbox.Add(self.up_name_lab, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.EXPAND, self.FromDIP(6))
        room_info_vbox.Add(self.title_lab, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        room_info_vbox.Add(info_hbox, 0, wx.EXPAND)

        self.pause_btn = BitmapButton(self, Icon.get_icon_bitmap(IconID.Start_Recording))
        self.pause_btn.SetToolTip("开始录制")
        self.stop_btn = BitmapButton(self, Icon.get_icon_bitmap(IconID.Close))
        self.stop_btn.SetToolTip("删除房间")

        panel_hbox = wx.BoxSizer(wx.HORIZONTAL)
        panel_hbox.Add(self.cover_bmp, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        panel_hbox.Add(room_info_vbox, 0, wx.ALIGN_CENTER)
        panel_hbox.AddStretchSpacer()
        panel_hbox.Add(self.pause_btn, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        panel_hbox.Add(self.stop_btn, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        panel_hbox.AddSpacer(self.FromDIP(6))

        bottom_border = wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL)

        panel_vbox = wx.BoxSizer(wx.VERTICAL)
        panel_vbox.Add(panel_hbox, 1, wx.EXPAND)
        panel_vbox.Add(bottom_border, 0, wx.EXPAND)

        self.SetSizer(panel_vbox)

    def Bind_EVT(self):
        self.cover_bmp.Bind(wx.EVT_LEFT_DOWN, self.onViewCoverEVT)
        self.pause_btn.Bind(wx.EVT_BUTTON, self.onPauseEVT)
        self.stop_btn.Bind(wx.EVT_BUTTON, self.onStopEVT)

    def init_utils(self):
        self.show_live_room_info()

        Thread(target = self.show_cover).start()

    def show_live_room_info(self):
        self.up_name_lab.SetLabel(self.info.up_name)
        self.title_lab.SetLabel(self.info.title)

        self.room_id_lab.SetLabel(f"ID {self.info.room_id}")
        self.area_lab.SetLabel(f"{self.info.parent_area} · {self.info.area}")

    def show_cover(self):
        def setBitmap():
            self.cover_bmp.SetBitmap(bitmap)

        if not self.cover_bmp.GetBitmap():
            size = wx.Size(self.FromDIP(112), self.FromDIP(63))

            image = Cover.crop_cover(Cover.get_cover_raw_contents(self.info.cover_url))

            bitmap = Cover.get_scaled_bitmap_from_image(image, size)

            wx.CallAfter(setBitmap)

    def start_recording(self):
        def start():
            self.set_recording_status(LiveRecordingStatus.Recording.value)

        if LiveStatus(self.info.live_status) == LiveStatus.Not_Started:
            wx.MessageDialog(self, "录制失败\n\n直播间未开播，无法进行录制", "警告", wx.ICON_WARNING).ShowModal()
            return
        
        if not self.info.option_setuped:
            dlg = LiveRecordingOptionDialog(self.live_recording_window, self.info.room_id)

            if dlg.ShowModal() == wx.ID_OK:
                self.info.option_setuped = True
                start()
        else:
            start()

    def stop_recording(self):
        self.set_recording_status(LiveRecordingStatus.Free.value)

    def onPauseEVT(self, event):
        match LiveRecordingStatus(self.info.recording_status):
            case LiveRecordingStatus.Free:
                self.start_recording()

            case LiveRecordingStatus.Recording:
                self.stop_recording()

    def onViewCoverEVT(self, event):
        Cover.view_cover(self.live_recording_window, self.info.cover_url)

    def onStopEVT(self, event):
        self.Destroy()

        self.live_recording_window.remove_live_room()

    def set_recording_status(self, status: int):
        self.info.recording_status = status

        match LiveRecordingStatus(status):
            case LiveRecordingStatus.Recording:
                self.pause_btn.SetBitmap(Icon.get_icon_bitmap(IconID.Stop_Recording))

                self.pause_btn.SetToolTip("停止录制")
                self.rec_bmp.Show()
                self.recording_lab.Show()

            case LiveRecordingStatus.Free:
                self.pause_btn.SetBitmap(Icon.get_icon_bitmap(IconID.Start_Recording))

                self.pause_btn.SetToolTip("开始录制")
                self.rec_bmp.Hide()
                self.recording_lab.Hide()

        self.GetSizer().Layout()