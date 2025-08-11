import os
import time
from io import BytesIO
from threading import Event, Lock

from utils.config import Config

from utils.common.request import RequestUtils
from utils.common.model.data_type import LiveRoomInfo
from utils.common.model.callback import LiveRecordingCallback
from utils.common.formatter.formatter import FormatUtils
from utils.common.thread import Thread
from utils.common.io.directory import Directory
from utils.common.enums import LiveFileSplit

class Utils:
    def __init__(self, parent):
        self.parent: Recorder = parent

    def get_file_buffer(self):
        file_name = "直播录制_20250811_165348_242544"
        
        path = os.path.join(self.parent.room_info.working_directory, "1.flv")

        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(b"\0")

        self.parent.file_buffer = open(path, "r+b")

    def check_working_directory(self):
        if not self.parent.room_info.working_directory:
            self.parent.room_info.working_directory = os.path.join(self.parent.room_info.base_directory, self.parent.room_info.title)

            Directory.create_directory(self.parent.room_info.working_directory)

            self.parent.room_info.update()

    def check_file_split(self):
        match LiveFileSplit(self.parent.room_info.file_split):
            case LiveFileSplit.Disable:
                return
            
            case LiveFileSplit.ByDuration:
                self.check_duration()

            case LiveFileSplit.BySize:
                self.check_file_size()

    def check_duration(self):
        pass

    def check_file_size(self):
        if self.parent.current_downloaded_size > 100 * 1024 * 1024:
            pass

    def update_recording_progress(self, chunk_size: int):
        self.parent.current_downloaded_size += chunk_size

    def update_recording_speed(self, speed: str):
        self.parent.room_info.total_size = self.parent.current_downloaded_size

        self.parent.callback.onRecording(speed)

class Recorder:
    def __init__(self, room_info: LiveRoomInfo, callback: LiveRecordingCallback):
        self.room_info = room_info
        self.callback = callback

        self.init_utils()

    def init_utils(self):
        self.utils = Utils(self)

        self.lock = Lock()
        self.stop_event = Event()

        self.file_buffer = BytesIO()

        self.recorder_info: dict = {}

        self.current_downloaded_size = 0

    def set_recorder_info(self, recorder_info: dict):
        self.recorder_info = recorder_info

    def start_recording(self):
        self.utils.check_working_directory()

        self.utils.get_file_buffer()

        Thread(target = self.listener).start()
        Thread(target = self.record_thread).start()

    def record_thread(self):
        with RequestUtils.request_get(self.recorder_info.get("stream_url"), headers = RequestUtils.get_headers(referer_url = self.recorder_info.get("referer_url"), sessdata = Config.User.SESSDATA), stream = True) as req:
            for chunk in req.iter_content(chunk_size = 1024):
                if chunk:
                    with self.lock:
                        if self.stop_event.is_set():
                            break

                        self.file_buffer.write(chunk)

                        self.utils.update_recording_progress(len(chunk))

    def stop_recording(self):
        self.stop_event.set()

        self.file_buffer.close()

    def listener(self):
        while not self.stop_event.is_set():
            temp_downloaded_size = self.current_downloaded_size

            time.sleep(1)

            speed = self.current_downloaded_size - temp_downloaded_size

            self.utils.update_recording_speed(FormatUtils.format_speed(speed))

            self.utils.check_file_split()
            