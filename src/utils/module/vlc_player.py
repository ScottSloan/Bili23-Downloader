import os
from enum import Enum

from utils.config import Config
from utils.common.enums import Platform

os.environ['PYTHON_VLC_MODULE_PATH'] = "./VLC"

import vlc

class VLCState(Enum):
    Playing = 0
    Paused = 1
    Stopped = 2
    Ended = 3

class VLCEvent(Enum):
    LengthChanged = vlc.EventType.MediaPlayerLengthChanged

class VLCPlayer:
    def __init__(self, *args):
        if args:
            instance = vlc.Instance(args)
            self.player: vlc.MediaPlayer = instance.media_player_new()
        else:
            self.player = vlc.MediaPlayer()

    def set_mrl(self, mrl: str):
        self.player.set_mrl(mrl)

    def play(self):
        return self.player.play()
    
    def pause(self):
        return self.player.pause()
    
    def resume(self):
        return self.player.set_pause(0)
    
    def stop(self):
        return self.player.stop()
    
    def seek(self, progress: int):
        return self.player.set_time(progress)
    
    def get_length(self):
        return self.player.get_length()
    
    def get_state(self):
        match self.player.get_state():
            case vlc.State.Playing:
                return VLCState.Playing
            
            case vlc.State.Paused:
                return VLCState.Paused
            
            case vlc.State.Stopped | vlc.State.NothingSpecial:
                return VLCState.Stopped
            
            case vlc.State.Ended:
                return VLCState.Ended
            
    def release(self):
        self.player.release()
    
    def register_callback(self, event_type, callback):
        self.player.event_manager().event_attach(event_type, callback)

    def unregister_callback(self, event_type, callback):
        self.player.event_manager().event_detach(event_type, callback)

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
