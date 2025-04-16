from functools import reduce

from utils.common.enums import ParseType, VideoQualityID, AudioQualityID, StreamType, VideoCodecID
from utils.tool_v2 import RequestTool

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

        def get_url_list():
            match StreamType(self.stream_type):
                case StreamType.Dash:
                    for entry in self.download_json["dash"]["video"]:
                        if entry["id"] == video_quality_id and entry["codecid"] == video_codec_id:
                            frame_rate = entry["frame_rate"]
                            bandwidth = entry["bandwidth"]

                            return self.get_stream_download_url_list(entry), frame_rate, bandwidth
                        
                case StreamType.Flv:
                    return None, None, None
                
        def get_file_size():
            match StreamType(self.stream_type):
                case StreamType.Dash:
                    return self.get_file_size(url_list)
                
                case StreamType.Flv:
                    return reduce(lambda total, entry: total + entry["size"], self.download_json["durl"], 0)

        video_quality_id = self.get_video_quality_id(video_quality_id, self.stream_type, get_stream_json())
        video_codec_id = self.get_video_codec_id(video_quality_id, video_codec_id, self.stream_type, get_stream_json())

        key = f"{video_quality_id} - {video_codec_id}"

        if key not in self.video_size_cache:
            (url_list, frame_rate, bandwidth) = get_url_list()

            self.video_size_cache[key] = {
                "video_quality_id": video_quality_id,
                "video_codec_id": video_codec_id,
                "frame_rate": frame_rate,
                "bandwidth": bandwidth,
                "size": get_file_size()
            }

        return self.video_size_cache.get(key)

    def get_audio_stream_size(self, audio_quality_id: int):
        def get_url_list(data: dict):
            match AudioQualityID(audio_quality_id):
                case AudioQualityID._Dolby_Atoms:
                    data_node = data["dolby"]["audio"]
                    bandwidth = data_node["bandwidth"]

                case AudioQualityID._Hi_Res:
                    data_node = data["flac"]["audio"]
                    bandwidth = data_node["bandwidth"]
                
                case _:
                    for entry in data["audio"]:
                        if entry["id"] == audio_quality_id:
                            data_node = entry

                            bandwidth = entry["bandwidth"]
                            break

            return self.get_stream_download_url_list(data_node), bandwidth

        if self.stream_type == StreamType.Flv.value:
            return
        
        if not AudioInfo.Availability.audio:
            return

        audio_quality_id = self.get_audio_quality_id(audio_quality_id, self.download_json["dash"])
        
        if audio_quality_id not in self.audio_size_cache:
            (url_list, bandwidth) = get_url_list(self.download_json["dash"])

            self.audio_size_cache[audio_quality_id] = {
                "audio_quality_id": audio_quality_id,
                "bandwidth": bandwidth,
                "size": self.get_file_size(url_list)
            }     

        return self.audio_size_cache.get(audio_quality_id)
    
    def get_video_stream_codec(self, video_quality_id: int, video_codec_id: int):
        for entry in self.download_json["dash"]["video"]:
            if entry["id"] == video_quality_id and entry["codecid"] == video_codec_id:
                return video_codec_id

    @staticmethod
    def get_video_quality_id(video_quality_id: int, stream_type: int, data: list | dict):
        def get_highest_video_quality_id(data: list):
            match StreamType(stream_type):
                case StreamType.Dash:
                    highest_video_quality_id = VideoQualityID._360P.value

                    for entry in data:
                        if entry["id"] > highest_video_quality_id:
                            highest_video_quality_id = entry["id"]

                    return highest_video_quality_id
                
                case StreamType.Flv:
                    return data["accept_quality"][0]

        highest_video_quality_id = get_highest_video_quality_id(data)

        if video_quality_id == VideoQualityID._Auto.value:
            video_quality_id = highest_video_quality_id

        elif highest_video_quality_id < video_quality_id:
            video_quality_id = highest_video_quality_id

        return video_quality_id

    @staticmethod
    def get_audio_quality_id(audio_quality_id: int, data: dict):
        def get_highest_audio_quality_id(data: dict):
            highest_audio_quality = AudioQualityID._64K.value

            for entry in data["audio"]:
                if entry["id"] > highest_audio_quality:
                    highest_audio_quality = entry["id"]

            if "dolby" in data and data["dolby"]:
                if data["dolby"]["audio"]:
                    highest_audio_quality = AudioQualityID._Dolby_Atoms.value

            if "flac" in data and data["flac"]:
                if data["flac"]["audio"]:
                    highest_audio_quality = AudioQualityID._Hi_Res.value

            return highest_audio_quality
        
        highest_audio_quality = get_highest_audio_quality_id(data)

        match AudioQualityID(audio_quality_id):
            case AudioQualityID._Auto:
                audio_quality_id = highest_audio_quality

            case AudioQualityID._Dolby_Atoms | AudioQualityID._Hi_Res:
                if highest_audio_quality != audio_quality_id:
                    audio_quality_id = highest_audio_quality

            case AudioQualityID._192K | AudioQualityID._132K | AudioQualityID._64K:
                if AudioQualityID(highest_audio_quality) not in [AudioQualityID._Dolby_Atoms, AudioQualityID._Hi_Res] and highest_audio_quality < audio_quality_id:
                    audio_quality_id = highest_audio_quality

        return audio_quality_id

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

    def get_file_size(self, url_list: list):
        def request_head(url: str, cdn: str):
            return RequestTool.request_head(CDN.replace_cdn(url, cdn), headers = RequestTool.get_headers("https://www.bilibili.com"))

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