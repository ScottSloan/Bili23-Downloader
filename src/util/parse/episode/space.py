from .tree import TreeItem, Attribute
from .list_base import ListEpisodeParserBase

class SpaceEpisodeParser(ListEpisodeParserBase):
    NODE_TYPE_KEY = "PROFILE"

    def get_episode_list(self):
        # 按关键词搜索时可能没有任何结果
        return self.info_data["list"].get("vlist")

    def get_node_title(self):
        return self.with_search_keyword(self.info_data["info"]["name"])

    def episode_data_parser(self):
        if self.episode_id:
            return

        episode_data = self._init_episode_data()

        episode_data["space_owner"] = self.info_data["info"]["name"]
        episode_data["space_owner_id"] = self.info_data["info"]["mid"]

    def build_item_data(self, episode_data: dict):
        return {
            "aid": episode_data["aid"],
            "badge": self.get_episode_badge(episode_data),
            "bvid": episode_data["bvid"],
            "cover" : episode_data["pic"],
            "duration": self.get_episode_duration(episode_data),
            "ep_id": episode_data.get("season_id", 0),
            "episode_id": self.episode_id,
            "number": self.episode_count,
            "pubtime": episode_data["created"],
            "title": episode_data["title"],
            "url": self.build_video_url(episode_data["bvid"])
        }

    def get_episode_badge(self, episode_data: dict):
        if episode_data["is_charging_arc"]:
            return "充电专属"

        elif episode_data["is_lesson_video"]:
            return "课程"

        elif episode_data["is_union_video"]:
            return "合作"

        return ""

    def set_episode_attribute(self, episode_data: dict, item: TreeItem):
        if episode_data["is_lesson_video"]:
            item.set_attribute(Attribute.CHEESE_BIT)

        else:
            item.set_attribute(Attribute.VIDEO_BIT)

        item.set_attribute(Attribute.SPACE_BIT | Attribute.NEED_PARSE_BIT)
