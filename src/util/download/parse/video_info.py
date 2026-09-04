from ...common.enum import MediaType, DownloadType
from ...common.config import config

from ...parse.episode.tree import Attribute
from ...parse.quality import parse_declared_quality_map, fetch_video_streams, merge_video_streams

from ..parse.query_worker import QueryWorker
from ..task.info import TaskInfo

from collections import defaultdict

class VideoInfoParser:
    def __init__(self, info_data: dict, task_info: TaskInfo):
        self.info_data = info_data
        self.task_info = task_info

        self.video_info_map = defaultdict(lambda: defaultdict(dict))
        # support_formats 声明的「画质 -> 编码」，缺失时为 None，表示只能以 dash.video 为准
        self.declared_quality_map = None
        self.available_quality_list = []

    def _get_dash_available_quality_list(self):
        for entry in self.info_data["dash"]["video"].copy():
            self.video_info_map[entry["id"]][entry["codecid"]] = entry.copy()

        # 画质列表以 support_formats 的声明为准，而不是响应里实际给到的流：
        # 少数稿件一次请求拿不全所有档位，据 dash.video 建列表会漏掉可选画质，原因见 quality.py。
        # 只对普通视频这么做：番剧、课程同样带 support_formats，但它们的流要走各自的接口取，
        # 缺档时按普通视频的 playurl 去补只会拿到对不上的结果
        if self.task_info.Episode.attribute & Attribute.VIDEO_BIT:
            self.declared_quality_map = parse_declared_quality_map(self.info_data)

        if self.declared_quality_map:
            return list(self.declared_quality_map.keys())

        return sorted(self.video_info_map.keys(), reverse = True)
    
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
            
            case MediaType.UNKNOWN | MediaType.M4A:
                return []

    def get_available_codec_list(self, video_quality_id: int):
        codec_list = list(self.video_info_map[video_quality_id].keys())

        if codec_list:
            return codec_list

        # 该档位的流尚未取到，用 support_formats 声明的编码顶上，实测两者始终一致
        return (self.declared_quality_map or {}).get(video_quality_id, [])

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
        self.available_quality_list = self.get_available_quality_list()

        if not self.available_quality_list:
            return {}

        if video_quality_id == 200:
            video_quality_id = self.get_video_quality_id_by_priority()

        elif video_quality_id not in self.available_quality_list:
            video_quality_id = self.available_quality_list[0]

        available_codec_list = self.get_available_codec_list(video_quality_id)

        if not available_codec_list:
            return {}

        if video_codec_id == 20 or video_codec_id not in available_codec_list:
            video_codec_id = self.get_video_codec_id_by_priority(video_quality_id)

        video_info = self.video_info_map[video_quality_id][video_codec_id]

        if not video_info:
            # 选定档位的流不在首次响应里，按需补取一次
            video_info = self.supplement_video_info(video_quality_id, video_codec_id)

        return video_info

    def supplement_video_info(self, video_quality_id: int, video_codec_id: int):
        stream_list = fetch_video_streams(self.task_info.Episode.bvid, self.task_info.Episode.cid, video_quality_id)

        merge_video_streams(self.video_info_map, stream_list)

        if video_info := self.video_info_map[video_quality_id][video_codec_id]:
            return video_info

        # 补到的流里没有选定的编码，退回这一档位可用的第一个
        for entry in self.video_info_map[video_quality_id].values():
            if entry:
                return entry

        return {}

    def get_video_quality_id_by_priority(self):
        # 以声明的档位为准，缺流的档位同样参与优先级匹配，否则会错选成更高的画质
        for quality_id in config.get(config.video_quality_priority):
            if quality_id in self.available_quality_list:
                return quality_id

        return self.available_quality_list[0]

    def get_video_codec_id_by_priority(self, video_quality_id: int):
        available_codec_list = self.get_available_codec_list(video_quality_id)

        for codec_id in config.get(config.video_codec_priority):
            if codec_id in available_codec_list:
                return codec_id

        return available_codec_list[0]

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

