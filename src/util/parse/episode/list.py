from .tree import TreeItem, Attribute
from .list_base import ListEpisodeParserBase

class ListEpisodeParser(ListEpisodeParserBase):
    NODE_TYPE_KEY = "COLLECTION_LIST"

    def get_episode_list(self):
        return self.info_data["archives"]

    def get_node_title(self):
        if "title" in self.info_data["meta"]:
            return self.info_data["meta"]["title"]

        else:
            return self.info_data["meta"]["name"]

    def episode_data_parser(self):
        # 创建 episode_id
        if self.episode_id:
            return

        episode_data = self._init_episode_data()

        episode_data["collection_title"] = self.get_node_title()

    def get_current_episode_data(self):
        # 播放页链接（www.bilibili.com/list/{mid}?oid=…&bvid=…）指向合集里的
        # 某一个视频，由解析器写进接口数据里，见 ListParser.parse_play_page
        bvid = self.info_data.get("_current_bvid")

        return ("bvid", bvid) if bvid else None

    def build_item_data(self, episode_data: dict):
        return {
            "aid": episode_data["aid"],
            "bvid": episode_data["bvid"],
            "cover" : episode_data["pic"],
            "duration": self.get_episode_duration(episode_data),
            "number": self.episode_count,
            "pubtime": episode_data["pubdate"],
            "episode_id": self.episode_id,
            "title": episode_data["title"],
            "url": self.build_video_url(episode_data["bvid"])
        }

    def set_episode_attribute(self, episode_data: dict, item: TreeItem):
        item.set_attribute(
            Attribute.COLLECTION_LIST_BIT | Attribute.COLLECTION_BIT
            | Attribute.VIDEO_BIT | Attribute.NEED_PARSE_BIT
        )
