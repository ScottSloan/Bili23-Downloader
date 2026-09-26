from .tree import TreeItem, Attribute
from .list_base import ListEpisodeParserBase

class WatchLaterEpisodeParser(ListEpisodeParserBase):
    NODE_TYPE_KEY = "WATCH_LATER"

    def get_episode_list(self):
        return self.info_data.get("list")

    def get_node_title(self):
        # 无关键词时返回空标题，由 update_episode_list 回退为分类名称
        return self.with_search_keyword("")

    def episode_data_parser(self):
        if self.episode_id:
            return

        episode_data = self._init_episode_data()

        # 入口固定标签。分P与合集条目二次解析后，related_titles 会给出真正的稿件标题
        # 并写进 parent_title —— 两个含义各归各的变量，不再互相覆盖
        episode_data["source_title"] = self.get_node_type_name()

    def build_item_data(self, episode_data: dict):
        return {
            "aid": episode_data["aid"],
            "badge": self.get_episode_badge(episode_data),
            "bvid": episode_data["bvid"],
            "cid": episode_data["cid"],
            "cover" : episode_data["pic"],
            "duration": self.get_episode_duration(episode_data),
            "ep_id": self.get_ep_id(episode_data),
            "episode_id": self.episode_id,
            "number": self.episode_count,
            "pubtime": episode_data["pubdate"],
            "favtime": episode_data["add_at"],
            "title": episode_data["title"],
            "url": self.build_video_url(episode_data["bvid"])
        }

    def get_episode_badge(self, episode_data: dict):
        if episode_data.get("bangumi"):
            return episode_data["pgc_label"]

        return ""

    def get_ep_id(self, episode_data: dict):
        if episode_data.get("bangumi"):
            return episode_data["bangumi"]["ep_id"]

        return ""

    def set_episode_attribute(self, episode_data: dict, item: TreeItem):
        if episode_data.get("bangumi"):
            item.set_attribute(Attribute.BANGUMI_BIT)
        else:
            item.set_attribute(Attribute.VIDEO_BIT)

        item.set_attribute(Attribute.WATCH_LATER_BIT | Attribute.NEED_PARSE_BIT)
