import os
import time
from io import BytesIO
from threading import Event, Lock

from utils.config import Config

from utils.common.request import RequestUtils
from utils.common.model.data_type import LiveRoomInfo
from utils.common.model.callback import LiveRecordingCallback
from utils.common.formatter.formatter import FormatUtils
from utils.common.formatter.file_name_v2 import FileNameFormatter
from utils.common.thread import Thread
from utils.common.io.directory import Directory
from utils.common.enums import LiveFileSplit
from utils.common.datetime_util import DateTime
from utils.common.const import Const

class Utils:
    def __init__(self, parent):
        self.parent: Recorder = parent

    def get_file_buffer(self):
        ms = DateTime.now().microsecond // 1000
        title = FileNameFormatter.get_legal_file_name(self.parent.room_info.title)

        file_name = f"直播录制_{DateTime.time_str('%Y%m%d_%H%M%S_')}_{ms:03d}_{title}.flv"

        path = os.path.join(self.parent.room_info.working_directory, file_name)

        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(b"\0")

        self.parent.file_buffer = open(path, "r+b")

    def check_working_directory(self):
        if not self.parent.room_info.working_directory:
            up_name  = FileNameFormatter.get_legal_file_name(self.parent.room_info.up_name)

            self.parent.room_info.working_directory = os.path.join(self.parent.room_info.base_directory, f"{up_name}_{self.parent.room_info.room_id}")

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
        if self.parent.current_recording_time >= self.parent.target_time_duration:
            with self.parent.lock:
                self.parent.current_recording_time = 0

                self.get_file_buffer()

    def check_file_size(self):
        if self.parent.current_downloaded_size >= self.parent.target_split_size:
            with self.parent.lock:
                self.parent.current_downloaded_size = 0

                self.get_file_buffer()

    def update_recording_progress(self, chunk_size: int):
        self.parent.current_downloaded_size += chunk_size
        self.parent.total_downloaded_size += chunk_size

    def update_recording_speed_time(self, speed: str):
        self.parent.room_info.total_size = self.parent.total_downloaded_size

        self.parent.current_recording_time += 1
        self.parent.total_recording_time += 1

        self.parent.callback.onRecording(speed)

    def reset_flag(self):
        self.parent.stop_event.clear()
        
        self.parent.current_downloaded_size = 0
        self.parent.current_recording_time = 0

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
        self.total_downloaded_size = 0

        self.current_recording_time = 0
        self.total_recording_time = 0

        self.target_split_size = self.room_info.split_unit * Const.Size_1MB
        self.target_time_duration = self.room_info.split_unit * 60

    def set_recorder_info(self, recorder_info: dict):
        self.recorder_info = recorder_info

    def start_recording(self):
        self.utils.reset_flag()

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

            self.utils.update_recording_speed_time(FormatUtils.format_speed(speed))

            self.utils.check_file_split()
            