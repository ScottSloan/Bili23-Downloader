from ...common.enum import ParserType, ToastNotificationCategory
from ...common.translator import Translator
from ...common.signal_bus import signal_bus
from ...common._json import json_dumps
from ...common.config import config

from ..search_url import extract_keyword

from functools import reduce
from hashlib import md5
import urllib.parse
import logging
import time
import re

logger = logging.getLogger(__name__)

mixinKeyEncTab = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]

class ParserBase:
    def __init__(self):
        self.url = ""
        self.info_data = {}

        # 停止标记，用于跳转链接时停止当前解析流程
        self.stop_flag = False
        # 是否抛出异常
        self.raise_for_status = True

        self.error_message = ""

    def get_url_keyword(self):
        """
        从链接中提取搜索关键词，供支持服务端搜索的解析类型使用。

        关键词跟随链接传递，因此翻页与自动解析分页无需额外处理即可保持搜索状态。
        """
        return extract_keyword(self.url)

    def set_search_keyword(self, keyword: str):
        """
        把搜索关键词一并放进接口数据，供 episode 解析器在节点标题中标注。

        自动解析分页复用的也是这份数据，因此无需再单独传递。
        """
        self.info_data["data"]["_search_keyword"] = keyword

    def find_str(self, pattern: str, url: str, check: bool = True):
        result = re.findall(pattern, url)
        
        if result:
            return result[0]
        
        elif check:
            raise ValueError("无效的链接")

    def enc_wbi(self, params: dict):
        def getMixinKey(orig: str):
            return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, "")[:32]
                
        mixin_key = getMixinKey(config.get(config.img_key) + config.get(config.sub_key))
        curr_time = round(time.time())

        params["wts"] = curr_time
        params = dict(sorted(params.items()))
        params = {
            k : "".join(filter(lambda chr: chr not in "!'()*", str(v)))
            for k, v 
            in params.items()
        }
        
        query = urllib.parse.urlencode(params)
        wbi_sign = md5((query + mixin_key).encode()).hexdigest()
        params["w_rid"] = wbi_sign

        return urllib.parse.urlencode(params)

    def _build_video_info_url(self, bvid: str, cid: int, quality_id: int):
        params = {
            "bvid": bvid,
            "cid": cid,
            "qn": quality_id,
            "fnver": 0,
            "fnval": 4048,
            "fourk": 1,
        }

        return f"https://api.bilibili.com/x/player/wbi/playurl?{self.enc_wbi(params)}"

    def _supplement_video_info(self, response: dict, bvid: str, cid: int):
        # 部分稿件的高画质响应只包含最高画质，需要再请求缺失的较低画质并合并。
        try:
            if response.get("code") != 0:
                return response

            data = response.get("data") or {}
            video_list = (data.get("dash") or {}).get("video") or []

            if not video_list:
                return response

            video_keys = {
                (item.get("id"), item.get("codecid"), item.get("codecs"))
                for item in video_list
            }
            available_quality_ids = {
                quality_id
                for quality_id, _, _ in video_keys
                if isinstance(quality_id, int)
            }

            if not available_quality_ids:
                return response

            highest_quality_id = max(available_quality_ids)
            advertised_quality_ids = {
                item.get("quality")
                for item in data.get("support_formats") or []
                if isinstance(item, dict)
            }
            advertised_quality_ids.update(data.get("accept_quality") or [])
            missing_quality_id = max(
                (
                    quality_id
                    for quality_id in advertised_quality_ids - available_quality_ids
                    if isinstance(quality_id, int) and quality_id < highest_quality_id
                ),
                default = None
            )

            if missing_quality_id is None:
                return response

            from ...network.request import SyncNetWorkRequest

            supplement_url = self._build_video_info_url(bvid, cid, missing_quality_id)
            supplement_response = SyncNetWorkRequest(supplement_url).run()

            if supplement_response.get("code") != 0:
                return response

            for item in supplement_response["data"]["dash"]["video"]:
                key = (item.get("id"), item.get("codecid"), item.get("codecs"))

                if key not in video_keys:
                    video_list.append(item)
                    video_keys.add(key)

        except Exception:
            # 补充请求失败不应影响初始响应中已经可用的画质。
            logger.warning("补充获取较低画质视频流失败，将使用初始响应", exc_info = True)

        return response

    def on_error(self, message: str):
        self.error_message = message

        logger.error(message)

    def check_response(self, response: dict):
        if self.error_message:
            raise RuntimeError(self.error_message)
        
        if response.get("code", -1) != 0:
            logger.error("接口请求错误：\n{response}".format(
                response = json_dumps(response, indent = 2)
                )
            )

            raise RuntimeError(response.get("message", "未知错误"))
    
    def get_extra_data(self) -> dict:
        return {}
    
    def get_parser_type(self) -> ParserType:
        return ParserType.UNKNOWN
    
    def get_category_name(self) -> str:
        return self.get_parser_type().value
    
    def check_login(self):
        if not config.get(config.is_login) or config.is_expired:
            signal_bus.toast.show_long_message.emit(
                ToastNotificationCategory.ERROR,
                Translator.ERROR_MESSAGES("LOGIN_REQUIRED"),
                Translator.ERROR_MESSAGES("LOGIN_REQUIRED_MESSAGE")
            )

            raise RuntimeError(Translator.ERROR_MESSAGES("LOGIN_REQUIRED_MESSAGE"))
