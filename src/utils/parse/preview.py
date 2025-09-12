from utils.config import Config
from utils.auth.wbi import WbiUtils

from utils.common.enums import ParseType, VideoQualityID, StreamType, VideoCodecID, AudioQualityID
from utils.common.request import RequestUtils
from utils.common.model.data_type import DownloadTaskInfo
from utils.common.map import audio_quality_sort_map, audio_quality_map

from utils.parse.live import LiveParser
from utils.parse.parser import Parser

from utils.module.web.cdn import CDN

class PreviewInfo:
    download_json: dict = {}

class VideoPreview(Parser):
    def __init__(self, parse_type: ParseType):
        super().__init__()

        self.parse_type = parse_type

        self.download_json = PreviewInfo.download_json.copy()

        self.video_size_cache = {}
        self.audio_size_cache = {}
            
    def refresh_download_json(self, episode_params: dict):
        bvid = episode_params.get("bvid")
        cid = episode_params.get("cid")
        aid = episode_params.get("aid")
        ep_id = episode_params.get("ep_id")
        qn = episode_params.get("qn")

        self.download_json = self.get_download_json(self.parse_type, bvid, cid, aid, ep_id, qn)

    @classmethod
    def get_download_json(cls, parse_type: ParseType, bvid: str = None, cid: int = None, aid: int = None, ep_id: int = None, qn: int = 0):
        referer_url = "https://www.bilibili.com/"

        def get_video_json():
            params = {
                "bvid": bvid,
                "cid": cid,
                "qn": qn,
                "fnver": 0,
                "fnval": 4048,
                "fourk": 1
            }

            url = f"https://api.bilibili.com/x/player/wbi/playurl?{WbiUtils.encWbi(params)}"

            data = cls.request_get(url, headers = RequestUtils.get_headers(referer_url = referer_url, sessdata = Config.User.SESSDATA))

            return cls.json_get(data, "data")
        
        def get_bangumi_json():
            params = {
                "bvid": bvid,
                "cid": cid,
                "qn": qn,
                "fnver": 0,
                "fnval": 12240,
                "fourk": 1
            }

            url = f"https://api.bilibili.com/pgc/player/web/playurl?{cls.url_encode(params)}"

            data = cls.request_get(url, headers = RequestUtils.get_headers(referer_url = referer_url, sessdata = Config.User.SESSDATA))

            return cls.json_get(data, "result")
        
        def get_cheese_json():
            params = {
                "avid": aid,
                "ep_id": ep_id,
                "cid": cid,
                "qn": qn,
                "fnver": 0,
                "fnval": 4048,
                "fourk": 1
            }

            url = f"https://api.bilibili.com/pugv/player/web/playurl?{cls.url_encode(params)}"

            data = cls.request_get(url, headers = RequestUtils.get_headers(referer_url = referer_url, sessdata = Config.User.SESSDATA))

            return cls.json_get(data, "data")

        match ParseType(parse_type):
            case ParseType.Video:
                return get_video_json()
            
            case ParseType.Bangumi:
                return get_bangumi_json()
            
            case ParseType.Cheese:
                return get_cheese_json()

    @staticmethod
    def get_stream_type(data: dict):
        return data.get("type", "DASH" if "dash" in data else "FLV")
    
    def get_video_stream_info(self, episode_params: dict, requery: bool = False):
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

        qn = episode_params.get("qn")
        codec = episode_params.get("codec")

        if requery:
            self.refresh_download_json(episode_params)

        video_quality_id = self.get_video_quality_id(qn, self.download_json)
        video_codec_id = self.get_video_codec_id(video_quality_id, codec, self.stream_type, self.download_json)

        key = f"{video_quality_id} - {video_codec_id}"

        if key not in self.video_size_cache:
            self.video_size_cache[key] = get_info(self.download_json)
        
        return self.video_size_cache.get(key)

    def get_audio_stream_info(self, audio_quality_id: int):
        def get_info(data: dict):
            all_url_list = self.get_audio_all_url_list(data)

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
    def get_video_quality_id(cls, video_quality_id: int, data: dict, priority_setting: list = None):
        if not priority_setting:
            priority_setting = Config.Temp.video_quality_priority.copy()

        video_quality_id_list = cls.get_video_available_quality_id_list(data)

        if video_quality_id == VideoQualityID._Auto.value:
            for value in priority_setting:
                if value in video_quality_id_list:
                    return value
                
        elif video_quality_id in video_quality_id_list:
            return video_quality_id
        
        else:
            return max(video_quality_id_list)
        
    @classmethod
    def get_audio_quality_id(cls, audio_quality_id: int, data: dict, priority_setting: list = None):
        if not priority_setting:
            priority_setting = Config.Temp.audio_quality_priority.copy()

        audio_quality_id_list = cls.get_audio_available_quality_id_list(data)

        if audio_quality_id == AudioQualityID._Auto.value:
            for value in priority_setting:
                if value in audio_quality_id_list:
                    return value
        
        elif audio_quality_id in audio_quality_id_list:
            return audio_quality_id
        
        else:
            return max(audio_quality_id_list)
        
    @classmethod
    def get_video_codec_id(cls, video_quality_id: int, video_codec_id: int, stream_type: int, data: dict, priority_setting: list = None):
        if not priority_setting:
            priority_setting = Config.Temp.video_codec_priority.copy()
                
        video_codec_id_list = cls.get_video_available_codec_id_list(video_quality_id, stream_type, data)

        if video_codec_id == VideoCodecID.Auto.value:
            for value in priority_setting:
                if value in video_codec_id_list:
                    return value

        elif video_codec_id in video_codec_id_list:
            return video_codec_id

        else:
            return video_codec_id_list[0]

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
        video_quality_data_dict = {
            "按优先级自动选择": VideoQualityID._Auto.value
        }

        video_quality_data_dict.update(dict(zip(data["accept_description"], data["accept_quality"])))

        return video_quality_data_dict

    @classmethod
    def get_audio_quality_data_dict(cls, data: dict):
        audio_quality_data_dict = {
            "按优先级自动选择": AudioQualityID._Auto.value
        }

        audio_quality_id_list = cls.get_audio_available_quality_id_list(data.get("dash", {}))

        for id in audio_quality_id_list:
            if desc := audio_quality_map.get(id):
                audio_quality_data_dict[desc] = id

        return audio_quality_data_dict

    @staticmethod
    def get_video_codec_data_dict():
        return  {
            "按优先级自动选择": 20,
            "AVC/H.264": 7,
            "HEVC/H.265": 12,
            "AV1": 13
        }

    @staticmethod
    def get_video_available_quality_id_list(data: dict):
        available_list = []

        if "dash" in data:
            for entry in data["dash"]["video"]:
                id = entry.get("id")

                available_list.append(id)

            return list(set(available_list))
        else:
            if data.get("durls"):
                for entry in data["durls"]:
                    id = entry.get("quality")

                    available_list.append(id)

                return list(set(available_list))

            else:
                return data["accept_quality"]

    @classmethod
    def get_audio_available_quality_id_list(cls, data: dict):
        available_list = []

        for entry in cls.get_audio_all_url_list(data):
            available_list.append(entry["id"])

        return available_list

    @classmethod
    def get_video_available_codec_id_list(cls, video_quality_id: int, stream_type: StreamType, data: dict):
        match StreamType(stream_type):
            case StreamType.Dash:
                return [entry["codecid"] for entry in data["dash"]["video"] if entry["id"] == video_quality_id]
                
            case StreamType.Flv | StreamType.Mp4:
                return [VideoCodecID.AVC.value]
            
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
    def get_audio_all_url_list(data: dict):
        all_url_list = []
        
        audio_node = data.get("audio")
        dolby_node = data.get("dolby", {"audio": None})
        flac_node = data.get("flac", {"audio": None})

        dolby_node = dolby_node["audio"] if dolby_node else None
        flac_node = flac_node["audio"] if flac_node else None

        if audio_node:
            if isinstance(audio_node, list):
                all_url_list.extend(audio_node)

        if dolby_node:
            if isinstance(dolby_node, list):
                all_url_list.extend(dolby_node)
            else:
                all_url_list.append(dolby_node)

        if flac_node:
            if isinstance(flac_node, list):
                all_url_list.extend(flac_node)
            else:
                all_url_list.append(flac_node)

        all_url_list.sort(key = lambda x: audio_quality_sort_map.get(x["id"]))

        return all_url_list

    @staticmethod
    def get_cache(key: int, cache: dict, data: dict):
        if key not in cache:
            data[key] = data

        data.get(key)

    @property
    def stream_type(self):
        return self.get_stream_type(self.download_json)

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
                qn = entry["qn"]

                data[desc] = qn

        return data
    
    def get_codec_data_dict(self):
        return {
            "AVC/H.264": "avc",
            "HEVC/H.265": "hevc"
        }
