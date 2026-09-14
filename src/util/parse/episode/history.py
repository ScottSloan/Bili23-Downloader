from ...common.translator import Translator

from .tree import TreeItem, Attribute
from .list_base import ListEpisodeParserBase

class HistoryEpisodeParser(ListEpisodeParserBase):
    NODE_TYPE_KEY = "HISTORY"

    def get_episode_list(self):
        return self.info_data.get("list")

    def get_node_title(self):
        # 无关键词时返回空标题，由 update_episode_list 回退为分类名称
        return self.with_search_keyword("")

    def episode_data_parser(self):
        if self.episode_id:
            return

        episode_data = self._init_episode_data()

        episode_data["parent_title"] = self.get_node_type_name()

    def build_item_data(self, episode_data: dict):
        return {
            "badge": self.get_episode_badge(episode_data),
            "bvid": episode_data["history"]["bvid"],
            "cid": episode_data["history"]["cid"],
            "cover" : episode_data["cover"],
            "duration": self.get_episode_duration(episode_data),
            "ep_id": episode_data["history"]["epid"],
            "episode_id": self.episode_id,
            "number": self.episode_count,
            "viewtime": episode_data["view_at"],
            "title": self.get_episode_title(episode_data),
            "url": self.get_episode_url(episode_data),
            "expired": episode_data["duration"] == 0
        }

    def get_episode_badge(self, episode_data: dict):
        if episode_data.get("duration") == 0:
            return Translator.TIP_MESSAGES("EXPIRED")
        else:
            return episode_data["badge"]

    def get_episode_title(self, episode_data: dict):
        if episode_data["history"]["business"] == "pgc":
            show_title = episode_data.get("show_title", "")

            if show_title:
                return "{} - {}".format(episode_data["title"], show_title)
            else:
                return episode_data["title"]
        else:
            return episode_data["title"]

    def get_episode_url(self, episode_data: dict):
        uri = episode_data["uri"]
        bvid = episode_data["history"]["bvid"]

        if uri:
            return uri

        else:
            return self.build_video_url(bvid)

    def set_episode_attribute(self, episode_data: dict, item: TreeItem):
        match episode_data["history"]["business"]:
            case "archive":
                item.set_attribute(Attribute.VIDEO_BIT)

            case "pgc":
                item.set_attribute(Attribute.BANGUMI_BIT)

            case "cheese":
                item.set_attribute(Attribute.CHEESE_BIT)

        item.set_attribute(Attribute.HISTORY_BIT | Attribute.NEED_PARSE_BIT)
