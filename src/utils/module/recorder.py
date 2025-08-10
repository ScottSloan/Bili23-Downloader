import time
from threading import Event

from utils.common.request import RequestUtils
from utils.common.model.data_type import LiveRoomInfo

class Utils:
    def __init__(self, parent):
        self.parent: Recorder = parent

    def check_file_size(self):
        if self.parent.current_downloaded_size > 100 * 1024 * 1024:
            pass

class Recorder:
    def __init__(self, room_info: LiveRoomInfo, callback):
        self.room_info = room_info

    def init_utils(self):
        self.stop_event = Event()

        self.current_downloaded_size = 0

    def start_recording(self):
        pass

    def record_thread(self):
        file = ""

        with open(file, "r+b") as f:
            with RequestUtils.request_get(self.room_info.stream_url, stream = True) as req:
                for chunk in req.iter_content(chunk_size = 1024):
                    if chunk:
                        if self.stop_event.is_set():
                            break

                        f.write(chunk)

    def stop_recording(self):
        self.stop_event.set()

    def listener(self):
        while self.stop_event.is_set():
            temp_downloaded_size = self.current_downloaded_size

            time.sleep(1)

            speed = self.current_downloaded_size - temp_downloaded_size
            