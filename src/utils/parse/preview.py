from functools import reduce

from utils.common.enums import ParseType, VideoQualityID, AudioQualityID, StreamType, VideoCodecID
from utils.common.request import RequestUtils
from utils.common.data_type import DownloadTaskInfo
from utils.common.map import video_quality_map, get_mapping_key_by_value

from utils.parse.video import VideoInfo
from utils.parse.bangumi import BangumiInfo
from utils.parse.cheese import CheeseInfo
from utils.parse.audio import AudioInfo

from utils.module.cdn import CDN

class Preview:
    def __init__(self, parse_type: ParseType, stream_type: int):
        self.stream_type = stream_type
        self.download_json = self.get_download_json(parse_type)

        self.video_size_cache = {}
        self.audio_size_cache = {}

    def get_download_json(self, parse_type: ParseType):
        match parse_type:
            case ParseType.Video:
                return VideoInfo.download_json

            case ParseType.Bangumi:
                return BangumiInfo.download_json

            case ParseType.Cheese:
                return CheeseInfo.download_json

    def get_video_stream_info(self, video_quality_id: int, video_codec_id: int):
        def get_stream_json():
            match StreamType(self.stream_type):
                case StreamType.Dash:
                    return self.download_json["dash"]["video"]

                case StreamType.Flv:
                    return self.download_json

        def get_info(data: dict):
            for entry in data:
                if entry["id"] == video_quality_id and entry["codecid"] == video_codec_id:
                    return {
                        "id": video_quality_id,
                        "codec": 0,
                        "framerate": entry["frame_rate"],
                        "bandwidth": entry["bandwidth"],
                        "size": self.get_file_size(self.get_stream_download_url_list(entry))
                    }

        video_quality_id = self.get_video_quality_id(video_quality_id, self.stream_type, get_stream_json())
        video_codec_id = self.get_video_codec_id(video_quality_id, video_codec_id, self.stream_type, get_stream_json())

        key = f"{video_quality_id} - {video_codec_id}"

        if key not in self.video_size_cache:
            self.video_size_cache[key] = get_info(get_stream_json())
        
        return self.video_size_cache.get(key)

    def get_audio_stream_info(self, audio_quality_id: int):
        def get_info(data: dict):
            all_url_list = AudioInfo.get_all_audio_url_list(data)

            for entry in all_url_list:
                if entry["id"] == audio_quality_id:
                    return {
                        "id": audio_quality_id,
                        "codec": entry["codecs"],
                        "bandwidth": entry["bandwidth"],
                        "size": self.get_file_size(self.get_stream_download_url_list(entry))
                    }

        audio_quality_id = self.get_audio_quality_id(audio_quality_id, self.download_json["dash"])
        
        if audio_quality_id not in self.audio_size_cache:
            self.audio_size_cache[audio_quality_id] = get_info(self.download_json["dash"])

        return self.audio_size_cache.get(audio_quality_id)
    
    def get_video_stream_codec(self, video_quality_id: int, video_codec_id: int):
        for entry in self.download_json["dash"]["video"]:
            if entry["id"] == video_quality_id and entry["codecid"] == video_codec_id:
                return video_codec_id

    @classmethod
    def get_video_quality_id(cls, video_quality_id: int, stream_type: int, data: list | dict):
        video_quality_id_list, video_quality_desc_list = cls.get_video_quality_id_desc_list(data)

        video_quality_id_list.remove(VideoQualityID._Auto.value)

        if video_quality_id in video_quality_id_list:
            return video_quality_id
        else:
            return video_quality_id_list[0]

    @staticmethod
    def get_audio_quality_id(audio_quality_id: int, data: dict):
        audio_quality_id_list, audio_quality_desc_list = AudioInfo.get_audio_quality_id_desc_list(data)

        audio_quality_id_list.remove(AudioQualityID._Auto.value)

        if audio_quality_id in audio_quality_id_list:
            return audio_quality_id
        else:
            return audio_quality_id_list[0]
        
    @staticmethod
    def get_video_codec_id(video_quality_id: int, video_codec_id: int, stream_type: int, data: list):
        def check_codec_id():
            match StreamType(stream_type):
                case StreamType.Dash:
                    codec_id_list = []

                    for entry in data:
                        if entry["id"] == video_quality_id:
                            codec_id_list.append(entry["codecid"])

                    return codec_id_list
                
                case StreamType.Flv:
                    return [VideoCodecID.AVC.value]

        codec_id_list = check_codec_id()

        if video_codec_id not in codec_id_list:
            video_codec_id = codec_id_list[0]
        
        return video_codec_id

    @classmethod
    def get_video_resolution(cls, task_info: DownloadTaskInfo, data: list):
        video_quality_id = cls.get_video_quality_id(task_info.video_quality_id, task_info.stream_type, data)

        for entry in data:
            if entry["id"] == video_quality_id:
                return entry["width"], entry["height"]

    @classmethod
    def get_video_quality_id_desc_list(cls, data: dict):
        video_quality_id_list, video_quality_desc_list = [], []

        video_quality_id_list.append(VideoQualityID._Auto.value)
        video_quality_desc_list.append("自动")

        for entry in data:
            id = entry["id"]
            desc = get_mapping_key_by_value(video_quality_map, id)

            if desc:
                video_quality_id_list.append(id)
                video_quality_desc_list.append(desc)

        return video_quality_id_list, video_quality_desc_list

    def get_file_size(self, url_list: list):
        def request_head(url: str, cdn: str):
            return RequestUtils.request_head(CDN.replace_cdn(url, cdn), headers = RequestUtils.get_headers(referer_url = "https://www.bilibili.com"))

        cdn_list = CDN.get_cdn_list()

        for url in url_list:
            for cdn in cdn_list:
                req = request_head(url, cdn)

                if "Content-Length" in req.headers:
                    file_size = int(req.headers.get("Content-Length"))

                    if file_size:
                        return file_size

    @staticmethod
    def get_stream_download_url_list(data: dict):
        def generator(x: list):
            for v in x:
                if isinstance(v, list):
                    for y in v:
                        yield y
                else:
                    yield v

        return [i for i in generator([data[n] for n in ["backupUrl", "backup_url", "baseUrl", "base_url", "url"] if n in data])]
    
    @staticmethod
    def get_cache(key: int, cache: dict, data: dict):
        if key not in cache:
            data[key] = data

        data.get(key)