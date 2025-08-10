from utils.common.enums import ParseType, VideoQualityID, StreamType, VideoCodecID
from utils.common.request import RequestUtils
from utils.common.model.data_type import DownloadTaskInfo
from utils.common.model.dict_info import DictInfo

from utils.parse.video import VideoInfo, VideoParser
from utils.parse.bangumi import BangumiInfo, BangumiParser
from utils.parse.cheese import CheeseInfo, CheeseParser
from utils.parse.live import LiveParser
from utils.parse.audio import AudioInfo

from utils.module.web.cdn import CDN

class VideoPreview:
    def __init__(self, parse_type: ParseType, stream_type: int):
        self.parse_type, self.stream_type = parse_type, stream_type

        self.download_json = self.get_download_json(parse_type)

        self.video_size_cache = {}
        self.audio_size_cache = {}

    @staticmethod
    def get_download_json(parse_type: ParseType):
        match parse_type:
            case ParseType.Video:
                return VideoInfo.download_json

            case ParseType.Bangumi:
                return BangumiInfo.download_json

            case ParseType.Cheese:
                return CheeseInfo.download_json
            
    def refresh_download_json(self, video_quality_id: int):
        match self.parse_type:
            case ParseType.Video:
                VideoParser.get_video_available_media_info(video_quality_id)

            case ParseType.Bangumi:
                BangumiParser.get_bangumi_available_media_info(video_quality_id)

            case ParseType.Cheese:
                CheeseParser.get_cheese_available_media_info(video_quality_id)

        self.download_json = self.get_download_json(self.parse_type)

    def get_video_stream_info(self, video_quality_id: int, video_codec_id: int, requery: bool = False):
        def get_info(data: dict):
            match StreamType(self.stream_type):
                case StreamType.Dash:
                    for entry in data["dash"]["video"]:
                        if entry["id"] == video_quality_id and entry["codecid"] == video_codec_id:
                            return {
                                "id": video_quality_id,
                                "codec": entry["codecid"],
                                "framerate": entry["frame_rate"],
                                "bandwidth": entry["bandwidth"],
                                "size": self.get_file_size(self.get_stream_download_url_list(entry))
                            }
                        
                case StreamType.Flv:
                    size = 0

                    for entry in data["durl"]:
                        size += entry["size"]

                    return {
                        "id": video_quality_id,
                        "codec": video_codec_id,
                        "seg": len(data["durl"]),
                        "size": size
                    }
                
                case StreamType.Mp4:
                    if data["durls"]:
                        for entry in data["durls"]:
                            if entry["quality"] == video_quality_id:
                                node = entry["durl"][0]

                    else:
                        node = data["durl"][0]

                    return {
                        "id": video_quality_id,
                        "codec": video_codec_id,
                        "size": node["size"]
                    }

        if requery:
            self.refresh_download_json(video_quality_id)

        video_quality_id = self.get_video_quality_id(video_quality_id, self.download_json)
        video_codec_id = self.get_video_codec_id(video_quality_id, video_codec_id, self.stream_type, self.download_json)

        key = f"{video_quality_id} - {video_codec_id}"

        if key not in self.video_size_cache:
            self.video_size_cache[key] = get_info(self.download_json)
        
        return self.video_size_cache.get(key)

    def get_audio_stream_info(self, audio_quality_id: int):
        def get_info(data: dict):
            all_url_list = AudioInfo.get_all_audio_url_list(data)

            for entry in all_url_list:
                if entry["id"] == audio_quality_id:
                    return {
                        "id": audio_quality_id,
                        "codec": "m4a" if entry["codecs"].startswith("mp4a") else entry["codecs"],
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
    def get_video_quality_id(cls, video_quality_id: int, data: dict):
        video_quality_id_list = cls.get_video_available_quality_id_list(data)

        if video_quality_id in video_quality_id_list:
            return video_quality_id
        else:
            return max(video_quality_id_list)

    @staticmethod
    def get_audio_quality_id(audio_quality_id: int, data: dict):
        audio_quality_data_dict = AudioInfo.get_audio_quality_id_desc_list(data, auto = False)

        return audio_quality_data_dict.check_id(audio_quality_id)
        
    @staticmethod
    def get_video_codec_id(video_quality_id: int, video_codec_id: int, stream_type: int, data: dict):
        def check_codec_id():
            match StreamType(stream_type):
                case StreamType.Dash:
                    return [entry["codecid"] for entry in data["dash"]["video"] if entry["id"] == video_quality_id]
                    
                case StreamType.Flv | StreamType.Mp4:
                    return [VideoCodecID.AVC.value]
                
        codec_id_list = check_codec_id()

        if video_codec_id not in codec_id_list:
            video_codec_id = codec_id_list[0]
        
        return video_codec_id

    @classmethod
    def get_video_resolution(cls, task_info: DownloadTaskInfo, data: dict):
        video_quality_id = cls.get_video_quality_id(task_info.video_quality_id, data)

        stream_type = data.get("type", "DASH" if "dash" in data else "FLV")

        match StreamType(stream_type):
            case StreamType.Dash:
                for entry in data["dash"]["video"]:
                    if entry["id"] == video_quality_id:
                        return entry["width"], entry["height"]
                    
            case StreamType.Flv:
                pass

            case StreamType.Mp4:
                pass

    @classmethod
    def get_video_quality_data_dict(cls, data: dict):
        video_quality_data_dict = DictInfo()

        video_quality_data_dict["自动"] = VideoQualityID._Auto.value

        video_quality_data_dict.update(dict(zip(data["accept_description"], data["accept_quality"])))

        return video_quality_data_dict

    @staticmethod
    def get_video_available_quality_id_list(data: dict):
        available_list = []

        if "dash" in data:
            for entry in data["dash"]["video"]:
                id = entry.get("id")

                available_list.append(id)

            return available_list
        else:
            if data["durls"]:
                for entry in data["durls"]:
                    id = entry.get("quality")

                    available_list.append(id)
            
                return available_list
            
            else:
                return data["accept_quality"]

    @staticmethod
    def get_file_size(url_list: list):
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

class LivePreview:
    def __init__(self, room_id: int):
        self.room_id = room_id

        self.stream_json: dict = {}

    def get_live_stream_json(self):
        self.stream_json = LiveParser.get_live_stream_info(self.room_id)

    def get_quality_data_dict(self):
        data = {}

        for entry in self.stream_json.get("g_qn_desc"):
            if entry.get("media_base_desc"):
                desc = entry["media_base_desc"]["detail_desc"]["desc"]
                qn = entry["media_base_desc"]["qn"]

                data[desc] = qn

        return data
    
    def get_codec_data_dict(self):
        return {
            "AVC/H.264": "avc",
            "HEVC/H.265": "hevc"
        }
