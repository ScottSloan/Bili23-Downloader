from ...common.enum import ParserType
from ...network.request import SyncNetWorkRequest
from ..episode.list import ListEpisodeParser
from .base import ParserBase

from urllib.parse import urlencode, urlparse
import math

class ListParser(ParserBase):
    def __init__(self):
        super().__init__()

        self.ps = 30

    def get_mid(self):
        # 只在路径部分匹配：播放页链接的查询串里带着 oid 这类长数字，
        # 拿整条链接去搜会被它们干扰
        mid = self.find_str(r"/([0-9]+)", urlparse(self.url).path)

        return mid
    
    def get_season_id(self):
        season_id = self.find_str(r"/([0-9]+)\?type=season", self.url)

        return season_id
    
    def get_series_id(self):
        series_id = self.find_str(r"/([0-9]+)\?type=series", self.url)

        return series_id

    def get_sid(self):
        # 播放页链接的 sid，既可能是合集 id 也可能是系列 id，判定见 parse_play_page
        sid = self.find_str(r"sid=([0-9]+)", self.url, check = False)

        return sid

    def get_bvid(self):
        # 只在查询串的 bvid 参数上匹配：播放页链接里 "bvid=" 本身就含 "bv"，
        # 用 (?:BV|bv)\w+ 在整条链接里搜会先命中它、取回 "bvid"
        bvid = self.find_str(r"bvid=([Bb][Vv][0-9A-Za-z]+)", self.url, check = False)

        return bvid

    def get_oid(self):
        # 播放页链接里的 oid 就是 aid
        oid = self.find_str(r"oid=([0-9]+)", self.url, check = False)

        return oid

    def parse(self, url: str, pn: int, get_info_data: bool = False):
        self.url = url
        self.pn = pn

        self.mid = self.get_mid()

        if "type=" in self.url:
            # 根据 url 中的 type 参数判断是合集还是系列
            match self.find_str(r"type=(season|series)", self.url):
                case "season":
                    self.season_id = self.get_season_id()

                    self.get_seasons_archives_list()

                case "series":
                    self.series_id = self.get_series_id()

                    self.get_series_archives_list()
                    self.get_series_meta_info()

        else:
            # 播放页链接，形如 https://www.bilibili.com/list/{mid}?sid=…&oid=…&bvid=…
            self.parse_play_page()

        if get_info_data:
            return self.info_data

        episode_parser = ListEpisodeParser(self.info_data.copy(), self.get_category_name())
        episode_parser.parse()

    def parse_play_page(self):
        """
        处理播放页链接，形如：

            https://www.bilibili.com/list/{mid}?sid={id}
            https://www.bilibili.com/list/{mid}?oid={aid}&bvid={bv}
            https://www.bilibili.com/list/{mid}?sid={id}&oid={aid}&bvid={bv}

        这类链接是合集/系列播放页的地址栏内容，用户直接复制过来时列表身份并不总是
        写在链接里：sid 指向的可能是合集也可能是系列，只给了视频时更是完全没提。
        而合集与系列的接口对"id 存在但不属于本类型"的容忍度不一样（系列接口会明确
        报错，合集接口只有 id 不存在时才报错），单靠试探有误判的余地，所以能靠视频
        判断就不试探：

        1. 链接里带视频时，先反查视频所属的合集（ugc_season）。它与链接给的 sid
           一致（或链接根本没给 sid），就按合集解析；
        2. 否则把 sid 交给 parse_by_sid 处理；
        3. 两者都没有，说明链接里没有任何列表信息，维持原有的报错。
        """
        video_data = self.get_video_data()

        sid = self.get_sid()

        season = (video_data or {}).get("ugc_season")

        if season and (not sid or str(season["id"]) == sid):
            # mid 与 season_id 一律用接口给的，不用链接路径里的数字：两者理论上
            # 一致，但视频实际属于哪个合集，接口比链接可靠
            self.mid = season["mid"]
            self.season_id = str(season["id"])

            self.get_seasons_archives_list()

        elif sid:
            self.parse_by_sid(sid)

        else:
            raise ValueError("无效的链接")

        if video_data:
            # 链接指向的是列表里的某一个视频，记下来交给解析列表定位并勾选
            self.info_data["data"]["_current_bvid"] = video_data["bvid"]

    def parse_by_sid(self, sid: str):
        # sid 是合集 id 还是系列 id，靠探针区分：系列接口对非系列的 id 会返回
        # 非 0 的 code（147002 视频列表已失效），命中即系列、不命中按合集处理。
        # 先探系列而不是合集，是因为合集接口对不存在的 id 直接报错（-404），
        # 拿它当探针得靠捕获异常；探针拿到的 meta 正好是系列所需的 meta，
        # 复用掉还能省一次请求
        meta = self.get_series_meta(sid)

        if meta:
            self.series_id = sid

            self.get_series_archives_list()
            self.get_series_meta_info(meta)

        else:
            self.season_id = sid

            self.get_seasons_archives_list()

    def get_video_data(self) -> dict:
        """
        取播放页链接里那个视频的信息，链接里没带视频时返回 None。

        链接可能只给 oid（aid）也可能只给 bvid，也可能两个都给，都指向同一个视频。
        返回空表示链接里没有视频，此时不发任何请求。
        """
        if bvid := self.get_bvid():
            params = {"bvid": bvid}

        elif aid := self.get_oid():
            params = {"aid": aid}

        else:
            return None

        url = f"https://api.bilibili.com/x/web-interface/wbi/view?{self.enc_wbi(params)}"

        request = SyncNetWorkRequest(url, raise_for_status = self.raise_for_status)
        response = request.run()

        self.check_response(response)

        return response["data"]

    def get_series_meta(self, sid: str):
        """
        探测 sid 是否为系列 id，是则返回该系列的 meta，不是则返回 None。

        探测失败是预期结果之一，因此不能走 check_response（它会直接抛异常）。
        """
        params = {
            "series_id": sid,
            "web_location": "333.1387"
        }

        url = f"https://api.bilibili.com/x/series/series?{urlencode(params)}"

        request = SyncNetWorkRequest(url, raise_for_status = self.raise_for_status)
        response = request.run()

        if response.get("code", -1) != 0:
            return None

        return response["data"]["meta"]

    def get_seasons_archives_list(self):
        # 合集，以 season_id 区分
        # 形如 https://space.bilibili.com/{mid}/lists/{season_id}?type=season
        params = {
            "mid": self.mid,
            "season_id": self.season_id,
            "sort_reverse": "false",
            "page_size": self.ps,
            "page_num": self.pn,
            "web_location": "333.1387",
        }

        url = f"https://api.bilibili.com/x/polymer/web-space/seasons_archives_list?{urlencode(params)}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        self.check_response(response)

        self.info_data = response

    def get_series_archives_list(self):
        # 系列，以 series_id 区分
        # 形如 https://space.bilibili.com/{mid}/lists/{series_id}?type=series
        params = {
            "mid": self.mid,
            "current_mid": 0,
            "series_id": self.series_id,
            "only_normal": "true",
            "sort": "desc",
            "ps": self.ps,
            "pn": self.pn,
            "web_location": "333.1387",
        }

        url = f"https://api.bilibili.com/x/series/archives?{urlencode(params)}"

        request = SyncNetWorkRequest(url, raise_for_status = self.raise_for_status)
        response = request.run()

        self.check_response(response)

        self.info_data = response

    def get_series_meta_info(self, meta: dict = None):
        # 由于系列的接口不含 meta 信息，还需要额外获取。
        # 探针（parse_by_sid）已经拿到过 meta 时直接传进来复用，不再重复请求
        if meta is None:
            params = {
                "series_id": self.series_id,
                "web_location": "333.1387"
            }

            url = f"https://api.bilibili.com/x/series/series?{urlencode(params)}"

            request = SyncNetWorkRequest(url, raise_for_status = self.raise_for_status)
            response = request.run()

            self.check_response(response)

            meta = response["data"]["meta"]

        self.info_data["data"]["meta"] = meta.copy()

    def get_parser_type(self):
        return ParserType.COLLECTION_LIST
    
    def get_extra_data(self):
        count = self.info_data["data"]["page"]["total"]

        return {
            "pagination": True,
            "pagination_data": {
                "total_pages": math.ceil(count / self.ps),
                "total_items": count,
                "current_page": self.pn
            }
        }
    