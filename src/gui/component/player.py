import wx
import webbrowser
from datetime import datetime

from utils.common.icon_v4 import Icon, IconID
from utils.common.formatter import FormatUtils

from gui.component.panel.panel import Panel
from gui.component.button.bitmap_button import BitmapButton

vlc_available = False

try:
    from utils.module.vlc_player import VLCPlayer, VLCState, VLCEvent

    vlc_available = True

except:
    vlc_available = False

class Player(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        if vlc_available:
            self.init_player_UI()

            self.Bind_EVT()
        else:
            self.init_unavailable_UI()

    def init_player_UI(self):
        self.player_frame = Panel(self)
        self.player_frame.SetBackgroundColour("black")

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

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.player_frame, 1, wx.ALL | wx.EXPAND, self.FromDIP(6))
        vbox.Add(ctrl_hbox, 0, wx.EXPAND)

        self.SetSizer(vbox)

        self.timer = wx.Timer(self, -1)

    def init_unavailable_UI(self):
        def onHelpEVT(self, event):
            webbrowser.open("https://bili23.scott-sloan.cn/doc/install/vlc.html")

        tip_lab = wx.StaticText(self, -1, "VLC Media Player 不可用，无法显示预览")
        self.help_btn = wx.Button(self, -1, "帮助", size = self.get_scaled_size((100, 28)))
        self.help_btn.Bind(wx.EVT_BUTTON, onHelpEVT)

        tip_vbox = wx.BoxSizer(wx.HORIZONTAL)
        tip_vbox.AddStretchSpacer()
        tip_vbox.Add(tip_lab, 0, wx.ALL, self.FromDIP(6))
        tip_vbox.AddStretchSpacer()

        btn_vbox = wx.BoxSizer(wx.HORIZONTAL)
        btn_vbox.AddStretchSpacer()
        btn_vbox.Add(self.help_btn, 0, wx.ALL, self.FromDIP(6))
        btn_vbox.AddStretchSpacer()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddStretchSpacer()
        vbox.Add(tip_vbox, 0, wx.EXPAND)
        vbox.Add(btn_vbox, 0, wx.EXPAND)
        vbox.AddStretchSpacer()

        self.SetSizer(vbox)

    def Bind_EVT(self):
        self.play_btn.Bind(wx.EVT_BUTTON, self.onPlayEVT)
        self.stop_btn.Bind(wx.EVT_BUTTON, self.onStopEVT)

        self.progress_bar.Bind(wx.EVT_SCROLL_THUMBTRACK, self.onSliderEVT)
        self.progress_bar.Bind(wx.EVT_SCROLL_THUMBRELEASE, self.onSeekEVT)

        self.Bind(wx.EVT_TIMER, self.onTimerEVT)

    def init_player(self, input_path: str):
        if not vlc_available:
            return

        self.player = VLCPlayer()

        self.player.set_window(self.player_frame.GetHandle())
        self.player.set_mrl(input_path)
        self.player.register_callback(VLCEvent.LengthChanged.value, self.onLengthChangeEVT)

        self.player_frame.SetInitialSize()
        self.GetSizer().Layout()

        self.onSlider = False

    def close_player(self):
        if vlc_available:
            self.reset()

    def onPlayEVT(self, event):
        match self.player.get_state():
            case VLCState.Stopped:
                self.player.play()

                if not self.timer.IsRunning():
                    self.timer.Start(1000)

                self.set_play_btn_icon(VLCState.Paused)

            case VLCState.Playing:
                self.player.pause()

                self.set_play_btn_icon(VLCState.Playing)

            case VLCState.Paused:
                self.player.resume()

                self.set_play_btn_icon(VLCState.Paused)

    def onSliderEVT(self, event):
        self.onSlider = True

        self.update_time(self.progress_bar.GetValue())

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

            self.update_time(offset)

    def onStopEVT(self, event):
        self.reset()

    def onLengthChangeEVT(self, event):
        length = self.player.get_length()

        self.progress_bar.SetRange(0, length)
        self.length_lab.SetLabel(FormatUtils.format_duration(int(length / 1000)))

    def get_time(self):
        offset = self.player.get_progress()
        date_str = FormatUtils.format_duration(int(offset / 1000), show_hour = True)

        return wx.DateTime(datetime.strptime(date_str, "%H:%M:%S"))

    def update_time(self, offset: int):
        def worker():
            self.time_lab.SetLabel(FormatUtils.format_duration(int(offset / 1000)))

        wx.CallAfter(worker)

    def set_play_btn_icon(self, state: str):
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
        self.progress_bar.SetRange(0, 0)
        self.time_lab.SetLabel("00:00")

        self.set_play_btn_icon(VLCState.Stopped)