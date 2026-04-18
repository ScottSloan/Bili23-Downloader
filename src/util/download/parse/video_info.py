from util.download.parse.query_worker import QueryWorker
from util.common.enum import MediaType, DownloadType
from util.common import config

from ...download.task.info import TaskInfo

from collections import defaultdict

class VideoInfoParser:
    def __init__(self, info_data: dict, task_info: TaskInfo):
        self.info_data = info_data
        self.task_info = task_info

        self.video_info_map = defaultdict(lambda: defaultdict(dict))

    def _get_dash_available_quality_list(self):
        available_quality_list = []

        for entry in self.info_data["dash"]["video"].copy():
            quality_id = entry["id"]
            codec_id = entry["codecid"]

            self.video_info_map[quality_id][codec_id] = entry.copy()
            available_quality_list.append(quality_id)

        return available_quality_list
    
    def _get_mp4_available_quality_list(self):
        accept_quality_list = self.info_data["accept_quality"].copy()
        
        for quality_id in accept_quality_list.copy():
            if quality_id not in self.video_info_map.keys():
                self.video_info_map[quality_id][7] = {
                    "id": quality_id,
                    "url_entry_list": self.info_data["durl"],
                    "codecid": 7,
                    "frame_rate": 0,
                    "bandwidth": 0
                }

        return accept_quality_list

    def get_available_quality_list(self):
        match self.task_info.Download.media_type:
            case MediaType.DASH:
                return self._get_dash_available_quality_list()
            
            case MediaType.MP4 | MediaType.FLV:
                return self._get_mp4_available_quality_list()
            
            case MediaType.UNKNOWN:
                return []

    def get_available_codec_list(self, video_quality_id: int):
        return list(self.video_info_map[video_quality_id].keys())

    def parse_info(self):
        video_info = self.get_video_info(self.task_info.Download.video_quality_id, self.task_info.Download.video_codec_id)

        if video_info:
            self.task_info.Download.video_quality_id = video_info["id"]
            self.task_info.Download.video_codec_id = video_info["codecid"]
            self.task_info.File.video_file_ext = self.get_video_file_ext()

            match self.task_info.Download.media_type:
                case MediaType.DASH:
                    _parse_info = self.make_dash_video_info(video_info, self.task_info.File.video_file_ext)

                case MediaType.MP4 | MediaType.FLV:
                    _parse_info = self.make_mp4_video_info(video_info, self.task_info.File.video_file_ext)

                    self.task_info.Download.video_parts_count = len(_parse_info)

            return _parse_info

        self.task_info.Download.type &= ~DownloadType.VIDEO
        return []

    def get_video_info(self, video_quality_id: int, video_codec_id: int):
        available_quality_list = self.get_available_quality_list()

        if video_quality_id == 200:
            video_quality_id = self.get_video_quality_id_by_priority()

        elif video_quality_id not in available_quality_list:
            video_quality_id = available_quality_list[0]
        
        available_codec_list = self.get_available_codec_list(video_quality_id)

        if video_codec_id == 20:
            video_codec_id = self.get_video_codec_id_by_priority(video_quality_id)

        elif video_codec_id not in available_codec_list:
            video_codec_id = available_codec_list[0]

        return self.video_info_map[video_quality_id][video_codec_id]

    def get_video_quality_id_by_priority(self):
        for quality_id in config.get(config.video_quality_priority):
            if quality_id in self.video_info_map.keys():
                return quality_id
            
    def get_video_codec_id_by_priority(self, video_quality_id: int):
        for codec_id in config.get(config.video_codec_priority):
            if codec_id in self.video_info_map[video_quality_id].keys():
                return codec_id

    def check_is_full_video(self, media_info: dict):
        match self.task_info.Download.media_type:
            case MediaType.DASH:
                # dash 格式视频一定是完整的
                return True

            case MediaType.MP4:
                # 只需要检查 mp4 格式
                return self.info_data["timelength"] == media_info["timelength"]

    def get_video_file_ext(self):
        match self.task_info.Download.media_type:
            case MediaType.DASH:
                return "m4s"
            
            case MediaType.MP4:
                return "mp4"
            
            case MediaType.FLV:
                return "flv"

    def make_dash_video_info(self, video_info: dict, ext: str):
        temp_video_file_name = "video_{task_id}.{file_ext}".format(task_id = self.task_info.Basic.task_id, file_ext = ext)

        if temp_video_file_name not in self.task_info.File.relative_files:
            self.task_info.File.relative_files.append(temp_video_file_name)

        worker = QueryWorker(video_info)
        
        return [
            {
                **worker.query_dash_url(),
                "type": "video",
                "file_name": temp_video_file_name,
                "file_key": "video"
            }
        ]
    
    def make_mp4_video_info(self, video_info: dict, ext: str):
        worker = QueryWorker(video_info)

        info_list = []

        for entry in worker.query_mp4_url():
            temp_video_file_name = "video_{task_id}_{index}.{file_ext}".format(task_id = self.task_info.Basic.task_id, index = entry["index"], file_ext = ext)

            if temp_video_file_name not in self.task_info.File.relative_files:
                self.task_info.File.relative_files.append(temp_video_file_name)

            info_list.append({
                **entry,
                "file_name": temp_video_file_name,
                "file_key": "video_part_{index}".format(index = entry["index"])
            })

        return info_list

