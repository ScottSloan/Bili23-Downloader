import wx
import webbrowser
from enum import Enum

from utils.common.icon_v4 import Icon, IconID
from utils.common.formatter import FormatUtils
from utils.common.data_type import PlayerCallback
from utils.common.enums import Platform

from utils.config import Config

from gui.component.panel.panel import Panel
from gui.component.button.bitmap_button import BitmapButton

vlc_available = False

try:
    import vlc

    vlc_available = True

except:
    vlc_available = False

if vlc_available:
    class VLCState(Enum):
        Playing = 0
        Paused = 1
        Stopped = 2
        Ended = 3

    class VLCEvent(Enum):
        LengthChanged = vlc.EventType.MediaPlayerLengthChanged

class Player(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        if vlc_available:
            self.init_player_UI()

            self.Bind_EVT()

            self.onSlider = False
        else:
            self.init_unavailable_UI()

    def init_player_UI(self):
        self.player_panel = Panel(self)
        self.player_panel.SetBackgroundColour("black")

        self.play_btn = BitmapButton(self, Icon.get_icon_bitmap(IconID.Play))
        self.stop_btn = BitmapButton(self, Icon.get_icon_bitmap(IconID.Stop))
        self.time_lab = wx.StaticText(self, -1, "00:00")
        self.length_lab = wx.StaticText(self, -1, "00:00")
        self.progress_bar = wx.Slider(self, -1)

        ctrl_hbox = wx.BoxSizer(wx.HORIZONTAL)
        ctrl_hbox.Add(self.play_btn, 0, wx.ALL| wx.ALIGN_CENTER, self.FromDIP(6))
        ctrl_hbox.Add(self.stop_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        ctrl_hbox.Add(self.time_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        ctrl_hbox.Add(self.progress_bar, 1, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        ctrl_hbox.Add(self.length_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.player_panel, 1, wx.EXPAND)
        vbox.Add(ctrl_hbox, 0, wx.EXPAND)

        self.SetSizer(vbox)

        self.timer = wx.Timer(self, -1)

        self.Instance = vlc.Instance()
        self.player: vlc.MediaPlayer = self.Instance.media_player_new()

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

    def init_player(self, callback: PlayerCallback):
        self.callback = callback

    def close_player(self):
        if vlc_available:
            self.reset()

    def onPlayEVT(self, event):
        match self.get_state():
            case VLCState.Stopped:
                self.play()

                if not self.timer.IsRunning():
                    self.timer.Start(1000)

                self.set_play_btn_icon(VLCState.Paused)

            case VLCState.Playing:
                self.player.pause()

                self.set_play_btn_icon(VLCState.Playing)

            case VLCState.Paused:
                self.player.set_pause(0)

                self.set_play_btn_icon(VLCState.Paused)

    def onSliderEVT(self, event):
        self.onSlider = True

        self.update_time(self.progress_bar.GetValue())

    def onSeekEVT(self, event):
        offset = self.progress_bar.GetValue()

        self.seek(offset)

        self.onSlider = False

    def onTimerEVT(self, event):
        if self.player.get_state() == VLCState.Ended:
            self.reset()

        if not self.onSlider:
            offset = self.get_progress()

            self.progress_bar.SetValue(offset)

            self.update_time(offset)

    def onStopEVT(self, event):
        self.reset()

    def onLengthChangeEVT(self, event):
        length = self.player.get_length()

        self.progress_bar.SetRange(0, length)
        self.length_lab.SetLabel(FormatUtils.format_duration(int(length / 1000)))

        wx.CallAfter(self.callback.onLengthChange, length)

    def set_playurl(self, path: str):
        self.path = path

    def play(self):
        self.set_mrl(self.path)
        self.set_window(self.player_panel.GetHandle())
        self.register_callback(VLCEvent.LengthChanged.value, self.onLengthChangeEVT)

        self.player_panel.SetInitialSize()
        self.GetSizer().Layout()

        self.player.play()

    def set_mrl(self, mrl: str):
        media = self.Instance.media_new(mrl)

        self.player.set_media(media)

    def get_time(self):
        return self.player.get_length()
    
    def seek(self, progress: int):
        return self.player.set_time(progress)
    
    def get_state(self):
        if vlc_available:
            match self.player.get_state():
                case vlc.State.Playing:
                    return VLCState.Playing
                
                case vlc.State.Paused:
                    return VLCState.Paused
                
                case vlc.State.Stopped | vlc.State.NothingSpecial:
                    return VLCState.Stopped
                
                case vlc.State.Ended:
                    return VLCState.Ended
    
    def get_progress(self):
        return self.player.get_time()
    
    def set_window(self, handle: int):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                self.player.set_hwnd(handle)

            case Platform.Linux:
                self.player.set_xwindow(handle)

            case Platform.macOS:
                self.player.set_nsobject(int(handle))

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

        wx.CallAfter(self.callback.onReset)

    def register_callback(self, event_type, callback):
        self.player.event_manager().event_attach(event_type, callback)

    def unregister_callback(self, event_type, callback):
        self.player.event_manager().event_detach(event_type, callback)