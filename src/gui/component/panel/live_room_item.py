import wx

from utils.common.model.data_type import LiveRoomInfo
from utils.common.model.callback import LiveRecordingCallback
from utils.common.style.icon_v4 import Icon, IconID
from utils.common.enums import LiveRecordingStatus, LiveStatus
from utils.common.thread import Thread

from utils.module.pic.cover import Cover
from utils.module.recorder import Recorder

from gui.dialog.live_recording_option import LiveRecordingOptionDialog

from gui.component.label.info_label import InfoLabel
from gui.component.button.bitmap_button import BitmapButton

from gui.component.panel.panel import Panel

class Utils:
    class UI:
        def __init__(self, parent: wx.Window):
            self.parent: LiveRoomItemPanel = parent

        def show_cover(self, cover_url: str):
            def worker():
                self.parent.cover_bmp.SetBitmap(bitmap)

            size = self.parent.cover_bmp.GetSize()

            image = Cover.crop_cover(Cover.get_cover_raw_contents(cover_url))

            bitmap = Cover.get_scaled_bitmap_from_image(image, size)

            wx.CallAfter(worker)

        def set_up_name(self, up_name: str):
            self.parent.up_name_lab.SetLabel(up_name)

        def set_title(self, title: str):
            self.parent.title_lab.SetLabel(title)

        def set_room_id(self, room_id: int):
            self.parent.room_id_lab.SetLabel(f"ID {room_id}")

        def set_area(self, parent_area: str, area: str):
            self.parent.area_lab.SetLabel(f"{parent_area} · {area}")

        def set_speed(self, speed: str):
            self.parent.speed_lab.SetLabel(speed)

        def set_pause_btn(self, icon_id: IconID, tool_tip: str):
            self.parent.pause_btn.SetBitmap(Icon.get_icon_bitmap(icon_id))

            self.parent.pause_btn.SetToolTip(tool_tip)
        
        def show_recording_label(self, show: bool):
            self.parent.rec_bmp.Show(show)
            self.parent.recording_lab.Show(show)

        def update(self):
            self.parent.Layout()

    def __init__(self, parent: wx.Window, room_info: LiveRoomInfo):
        self.parent: LiveRoomItemPanel = parent
        self.room_info = room_info

        self.ui = Utils.UI(parent)

    def show_room_info(self):
        self.ui.set_up_name(self.room_info.up_name)
        self.ui.set_title(self.room_info.title)

        self.ui.set_room_id(self.room_info.room_id)
        self.ui.set_area(self.room_info.parent_area, self.room_info.area)

        self.ui.update()

    def show_cover(self):
        self.ui.show_cover(f"{self.room_info.cover_url}@.jpeg")

    def destroy_panel(self):
        self.parent.Destroy()

        self.parent.live_recording_window.remove_item()

    def start_recording(self):
        if self.check_live_status():
            return
        
        if self.check_option_setup():
            return
        
        self.set_recording_status(LiveRecordingStatus.Recording)

        Thread(target = self.recording_thread).start()

    def recording_thread(self):
        self.recorder = Recorder(self.room_info, self.get_recorder_callback())

        self.recorder.start_recording()

    def stop_recording(self):
        self.set_recording_status(LiveRecordingStatus.Free)

    def onRecording(self, speed: str):
        def worker():
            self.ui.set_speed(speed)

            self.ui.update()

        wx.CallAfter(worker)

    def check_live_status(self):
        if LiveStatus(self.room_info.live_status) == LiveStatus.Not_Started:
            wx.MessageDialog(self.parent, "录制失败\n\n直播间未开播，无法进行录制", "警告", wx.ICON_WARNING).ShowModal()
            return True
        
    def check_option_setup(self):
        if not self.room_info.option_setuped:
            dlg = LiveRecordingOptionDialog(self.parent.live_recording_window, self.room_info)

            if dlg.ShowModal() != wx.ID_OK:
                return True
            
            self.room_info.option_setuped = True

    def set_recording_status(self, status: LiveRecordingStatus):
        def worker():
            self.update_pause_btn(status)

        self.room_info.recording_status = status

        wx.CallAfter(worker)

    def update_pause_btn(self, status: LiveRecordingStatus):
        match LiveRecordingStatus(status):
            case LiveRecordingStatus.Free:
                self.ui.set_pause_btn(IconID.Start_Recording, "开始录制")

                self.ui.show_recording_label(False)

            case LiveRecordingStatus.Recording:
                self.ui.set_pause_btn(IconID.Stop_Recording, "停止录制")

                self.ui.show_recording_label(True)

        self.ui.update()

    def get_recorder_callback(self):
        class RecorderCallback(LiveRecordingCallback):
            def onRecording(speed: str):
                self.onRecording(speed)
        
        return RecorderCallback

class LiveRoomItemPanel(Panel):
    def __init__(self, parent, room_info: LiveRoomInfo, live_recording_window):
        from gui.window.live_recording import LiveRecordingWindow

        self.room_info = room_info
        self.live_recording_window: LiveRecordingWindow = live_recording_window

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
        self.recording_lab = wx.StaticText(self, -1, "录制中", size = self.FromDIP((50, 16)))
        self.recording_lab.SetForegroundColour(wx.Colour(235, 54, 67))
        self.recording_lab.Hide()
        self.speed_lab = InfoLabel(self, "")

        info_hbox = wx.BoxSizer(wx.HORIZONTAL)
        info_hbox.Add(self.room_id_lab, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.ALIGN_CENTER | wx.ALIGN_LEFT, self.FromDIP(6))
        info_hbox.Add(self.area_lab, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.ALIGN_CENTER | wx.ALIGN_LEFT, self.FromDIP(6))
        info_hbox.Add(self.live_status_lab, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.ALIGN_CENTER | wx.ALIGN_LEFT, self.FromDIP(6))
        info_hbox.Add(self.rec_bmp, 0, wx.RIGHT | wx.ALIGN_CENTER | wx.ALIGN_LEFT, self.FromDIP(6))
        info_hbox.Add(self.recording_lab, 0, wx.RIGHT | wx.ALIGN_CENTER | wx.ALIGN_LEFT, self.FromDIP(6))
        info_hbox.Add(self.speed_lab, 0, wx.RIGHT | wx.ALIGN_CENTER | wx.ALIGN_LEFT, self.FromDIP(6))

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
        self.Bind(wx.EVT_WINDOW_DESTROY, self.onDestroyEVT)

        self.cover_bmp.Bind(wx.EVT_LEFT_DOWN, self.onCoverEVT)

        self.pause_btn.Bind(wx.EVT_BUTTON, self.onPauseEVT)
        self.stop_btn.Bind(wx.EVT_BUTTON, self.onStopEVT)

    def init_utils(self):
        self.utils = Utils(self, self.room_info)

        self.panel_destroy = False

    def onDestroyEVT(self, event: wx.CommandEvent):
        self.panel_destory = True

        event.Skip()

    def onCoverEVT(self, event: wx.MouseEvent):
        Cover.view_cover(self.live_recording_window, self.room_info.cover_url)

    def onPauseEVT(self, event: wx.CommandEvent):
        match LiveRecordingStatus(self.room_info.recording_status):
            case LiveRecordingStatus.Free:
                self.utils.start_recording()

            case LiveRecordingStatus.Recording:
                self.utils.stop_recording()

    def onStopEVT(self, event):
        self.utils.destroy_panel()
