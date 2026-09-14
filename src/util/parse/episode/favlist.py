from .tree import TreeItem, Attribute
from .list_base import ListEpisodeParserBase

class FavlistEpisodeParser(ListEpisodeParserBase):
    NODE_TYPE_KEY = "FAVORITES"

    def get_episode_list(self):
        return self.info_data.get("medias")

    def get_node_title(self):
        return self.with_search_keyword(self.info_data["info"]["title"])

    def episode_data_parser(self):
        if self.episode_id:
            return

        episode_data = self._init_episode_data()

        episode_data["favorites_name"] = self.info_data["info"]["title"]
        episode_data["favorites_id"] = self.info_data["info"]["id"]
        episode_data["favorites_owner"] = self.info_data["info"]["upper"]["name"]
        episode_data["favorites_owner_id"] = self.info_data["info"]["upper"]["mid"]

    def build_item_data(self, episode_data: dict):
        return {
            "badge": self.get_episode_badge(episode_data),
            "bvid": episode_data["bvid"],
            "cover" : episode_data["cover"],
            "duration": self.get_episode_duration(episode_data),
            "ep_id": episode_data["id"],
            "episode_id": self.episode_id,
            "number": self.episode_count,
            "pubtime": episode_data["pubtime"],
            "favtime": episode_data["fav_time"],
            "title": self.get_episode_title(episode_data),
            "url": self.build_video_url(episode_data["bvid"])
        }

    def get_episode_badge(self, episode_data: dict):
        if episode_data.get("ogv"):
            return episode_data["ogv"]["type_name"]

        # 分P视频 page 数 > 1
        if episode_data.get("page", 0) > 1:
            return "分P"

        return ""

    def get_episode_title(self, episode_data: dict):
        if episode_data.get("ogv"):
            return "{title} - {intro}".format(
                title = episode_data["title"],
                intro = episode_data["intro"]
            )

        return episode_data["title"]

    def set_episode_attribute(self, episode_data: dict, item: TreeItem):
        if episode_data.get("ogv"):
            item.set_attribute(Attribute.BANGUMI_BIT)
        else:
            item.set_attribute(Attribute.VIDEO_BIT)

        if episode_data.get("page", 0) > 1:
            item.set_attribute(Attribute.FAVORITE_WITH_MULTI_PART_VIDEO_BIT)

        item.set_attribute(Attribute.FAVLIST_BIT | Attribute.NEED_PARSE_BIT)
