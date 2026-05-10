from util.parse.episode.tree import TreeItem, EpisodeData, Attribute
from util.parse.episode.base import EpisodeParserBase

import httpx
import logging
import time

logger = logging.getLogger(__name__)

_http_client = None
_ugc_cache = {}

def _get_http_client():
    global _http_client
    if _http_client is None:
        _http_client = httpx.Client(
            headers={
                "Referer": "https://www.bilibili.com/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            follow_redirects=True,
            timeout=10,
        )
    return _http_client

class BilibiliEpisodeParser(EpisodeParserBase):
    def __init__(self, info_data: dict, category_name: str, kwargs: dict = {}):
        super().__init__(**kwargs)
        self.info_data = info_data
        self.category_name = category_name

    def parse(self):
        self.episode_id = self.info_data.get("id", "")

        bvid = self.info_data.get("id", "")
        ugc_season = self._fetch_ugc_season(bvid)

        if ugc_season and ugc_season.get("sections"):
            node = self._collection_parser(ugc_season, bvid)
        else:
            node = self._single_parser()

        if self.target_episode_info:
            return node
        else:
            episode_data = ("bvid", self.info_data.get("id", ""))
            self.update_episode_list(node, episode_data)

    def _fetch_ugc_season(self, bvid: str) -> dict | None:
        if bvid in _ugc_cache:
            return _ugc_cache[bvid]

        try:
            url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
            client = _get_http_client()
            resp = client.get(url)
            data = resp.json()
            if data.get("code") == 0:
                view = data.get("data", {})
                ugc_season = view.get("ugc_season")
                if ugc_season:
                    _ugc_cache[bvid] = ugc_season
                    return ugc_season
            _ugc_cache[bvid] = None
            return None
        except Exception as e:
            logger.warning(f"获取合集信息失败: {e}")
            _ugc_cache[bvid] = None
            return None

    def _single_parser(self):
        node_data = {
            "number": self.category_name,
            "title": ""
        }

        root_node = TreeItem(node_data)
        root_node.set_attribute(Attribute.TREE_NODE_BIT)

        duration = self.info_data.get("duration") or 0
        timestamp = self.info_data.get("timestamp") or 0

        item_data = {
            "episode_id": self.episode_id,
            "aid": self.info_data.get("aid", 0),
            "badge": "",
            "bvid": self.info_data.get("id", ""),
            "cid": self.info_data.get("cid", 0),
            "cover": self.info_data.get("thumbnail", ""),
            "duration": int(duration),
            "number": 1,
            "pubtime": int(timestamp),
            "title": self.info_data.get("title", ""),
            "url": self.info_data.get("webpage_url", ""),
            "uploader": self.info_data.get("uploader", ""),
            "uploader_uid": int(self.info_data.get("uploader_id", 0) or 0)
        }

        item = TreeItem(item_data)
        self.set_attribute(item, Attribute.VIDEO_BIT | Attribute.NORMAL_BIT)

        root_node.add_child(item)

        return root_node

    def _collection_parser(self, ugc_season: dict, current_bvid: str):
        collection_title = ugc_season.get("title", "")
        collection_id = ugc_season.get("id", 0)

        root_node_data = {
            "number": "合集",
            "title": collection_title
        }

        root_node = TreeItem(root_node_data)
        root_node.set_attribute(Attribute.TREE_NODE_BIT)

        sections = ugc_season.get("sections", [])

        for section in sections:
            section_title = section.get("title", "")
            episodes = section.get("episodes", [])

            if len(sections) > 1:
                section_node_data = {
                    "number": section_title,
                    "title": section_title
                }
                section_node = TreeItem(section_node_data)
                section_node.set_attribute(Attribute.TREE_NODE_BIT)
                root_node.add_child(section_node)
            else:
                section_node = root_node

            for idx, ep in enumerate(episodes, 1):
                ep_bvid = ep.get("bvid", "")
                arc = ep.get("arc", {})
                page = ep.get("page", {})

                episode_id = EpisodeData.add_episode()
                EpisodeData.table[episode_id] = {
                    "collection_title": collection_title,
                    "series_title": collection_title,
                    "section_title": section_title,
                    "parent_title": collection_title,
                }

                item_data = {
                    "episode_id": episode_id,
                    "aid": ep.get("aid", 0),
                    "badge": "",
                    "bvid": ep_bvid,
                    "cid": ep.get("cid", 0),
                    "cover": arc.get("pic", ""),
                    "duration": int(arc.get("duration", 0)),
                    "number": idx,
                    "pubtime": int(arc.get("pubdate", 0)),
                    "title": ep.get("title", ""),
                    "url": f"https://www.bilibili.com/video/{ep_bvid}",
                    "uploader": arc.get("author", {}).get("name", ""),
                    "uploader_uid": arc.get("author", {}).get("mid", 0)
                }

                item = TreeItem(item_data)
                self.set_attribute(item, Attribute.VIDEO_BIT | Attribute.COLLECTION_LIST_BIT)

                if ep_bvid == current_bvid:
                    item.set_checked_state(2)

                section_node.add_child(item)

        return root_node