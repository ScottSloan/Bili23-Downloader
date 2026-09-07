"""
预览里那部分与 Qt 无关的逻辑：算出有哪些画质、编码、音质

`video_info.py` 与 `audio_info.py` 继承 QObject，是为了让查询文件大小的 worker 能把
结果排队回 GUI 线程（那一段确实需要 Qt）。但**「这个视频有哪些档位可选」纯粹是在读
`PreviewerInfo.info_data`**，和线程、界面都没关系 —— WebUI 要的正是这一部分。

所以把它们抽成两个基类，Qt 那两个类改为继承。两端因此得出完全相同的可选项，
不会出现「桌面能选 4K 而网页里没有」这种对不上的情况。

状态仍然放在全局的 `PreviewerInfo` 上（没有改动它）：桌面版整个预览流程都建立在它之上，
搬走的话牵动面太大。代价是**预览必须串行**，服务端那边用一把锁保证，见 `preview/session.py`。
"""

from collections import defaultdict
import logging

from ...common.config import config
from ...common.data import audio_reorder_map, reversed_audio_quality_map, reversed_video_quality_map
from ...common.enum import MediaType

from ..quality import parse_declared_quality_map

from .info import PreviewerInfo

logger = logging.getLogger(__name__)

class VideoQualityBase:
    """画质与编码的可选项计算。不碰 Qt，也不发请求"""

    def _get_dash_available_quality_list(self):
        for entry in PreviewerInfo.info_data["dash"]["video"].copy():
            self.video_info_map[entry["id"]][entry["codecid"]] = entry.copy()

        # 画质列表以 support_formats 的声明为准，而不是响应里实际给到的流：
        # 少数稿件一次请求拿不全所有档位，据 dash.video 建列表会漏掉可选画质，原因见 quality.py。
        # 只对普通视频这么做：番剧、课程同样带 support_formats，但它们的流要走各自的接口取，
        # 缺档时按普通视频的 playurl 去补只会拿到对不上的结果
        if PreviewerInfo.info_data.get("parser_type") == "video":
            self.declared_quality_map = parse_declared_quality_map(PreviewerInfo.info_data)

        if self.declared_quality_map:
            return list(self.declared_quality_map.keys())

        return sorted(self.video_info_map.keys(), reverse = True)
    
    def _get_mp4_available_quality_list(self):
        accept_quality_list = PreviewerInfo.info_data["accept_quality"].copy()
        
        for quality_id in accept_quality_list.copy():
            self.video_info_map[quality_id][7] = {
                "id": quality_id,
                "codecid": 7,
                "frame_rate": 0,
                "bandwidth": 0,
                "timelength": 0
            }

        return accept_quality_list

    def get_available_quality_list(self):
        match PreviewerInfo.media_type:
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

    def parse_quality_info(self):
        self.video_info_map = defaultdict(lambda: defaultdict(dict))
        self.declared_quality_map = None

        initial_data = {
            "auto": 200
        }

        self.available_quality_list = self.get_available_quality_list()

        for quality_id in self.available_quality_list.copy():
            quality_str = reversed_video_quality_map.get(quality_id)

            initial_data[quality_str] = quality_id
        
        PreviewerInfo.video_quality_choice_data = initial_data.copy()

    def parse_codec_info(self):
        initial_data = {
            "auto": 20,
            "AVC/H.264": 7,
            "HEVC/H.265": 12,
            "AV1": 13
        }

        PreviewerInfo.video_codec_choice_data = initial_data.copy()

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


class AudioQualityBase:
    """音质的可选项计算。同上"""

    def _get_dash_available_quality_list(self):
        available_quality_list = []

        dash_node = PreviewerInfo.info_data["dash"]

        if audio_node := self.safe_get(dash_node.copy(), ["flac", "audio"]):
            # 30251 为 Hi-Res 无损
            quality_id = 30251
            audio_node["id"] = quality_id

            available_quality_list.append(quality_id)

            self.audio_quality_info_map[quality_id] = audio_node.copy()

        if audio_node := self.safe_get(dash_node.copy(), ["dolby", "audio"]):
            # 30250 30255 均为杜比全景声，为便于区分，统一为 30250
            if audio_node[0]["id"] == 30255:
                logger.info("检测到 audio_quality_id 为 30255 的杜比全景声音频，已统一为 30250 以便区分")

            quality_id = 30250
            audio_node[0]["id"] = quality_id

            available_quality_list.append(quality_id)

            self.audio_quality_info_map[quality_id] = audio_node[0].copy()

        if dash_node.get("audio", []):

            for entry in dash_node["audio"].copy():
                quality_id = entry["id"]

                if quality_id not in available_quality_list:
                    available_quality_list.append(quality_id)

                    self.audio_quality_info_map[quality_id] = entry.copy()

        return sorted(available_quality_list, key = lambda x: audio_reorder_map.get(x))

    def _get_m4a_available_quality_list(self):
        # m4a 只支持 192K 码率
        self.audio_quality_info_map[30280] = {
            "id": 30280,
            "codecs": "mp4a.40.2",
            "backup_url": PreviewerInfo.info_data["cdns"],
            "bandwidth": 192000
        }

        return [30280]

    def get_available_list(self):
        match PreviewerInfo.media_type:
            case MediaType.DASH:
                return self._get_dash_available_quality_list()
            
            case MediaType.M4A:
                return self._get_m4a_available_quality_list()
            
            case _:
                return []
    
    def parse_info(self):
        self.audio_quality_info_map = defaultdict(dict)

        initial_data = {
            "auto": 30300
        }

        available_audio_quality = self.get_available_list()

        for quality_id in available_audio_quality.copy():
            quality_str = reversed_audio_quality_map.get(quality_id)

            initial_data[quality_str] = quality_id

        PreviewerInfo.audio_quality_choice_data = initial_data.copy()

    def make_empty_data(self, reason: str):
        return {
            "empty": True,
            "reason": reason
        }

    def safe_get(self, data: dict, keys: list, default = None):
        for key in keys:
            if data := data.get(key):
                continue

            else:
                return default

        return data
