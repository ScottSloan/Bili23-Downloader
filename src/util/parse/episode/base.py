from ...common.signal_bus import signal_bus
from ...common.translator import Translator
from ...common.enum import AutoSelectMode
from ...common.config import config
from ...format.units import Units

from .tree import TreeItem, EpisodeData, Attribute

class EpisodeParserBase:
    def __init__(self, **kwargs):
        self.episode_id = ""
        self.category_name = ""
        self.info_data: dict = {}

        self.target_episode_info: str | int = kwargs.get("target_episode_info")
        self.target_episode_data_id: str = kwargs.get("target_episode_data_id")
        self.target_attribute: int = kwargs.get("target_attribute")
        self.target_number: int | str = kwargs.get("target_number")

        self.episode_count = 0

    def get_search_keyword(self):
        return self.info_data.get("_search_keyword", "")

    def with_search_keyword(self, title: str):
        # 搜索状态下在节点标题中标注关键词，使解析列表与解析历史能区分出不同的搜索结果
        keyword = self.get_search_keyword()

        if not keyword:
            return title

        label = Translator.TIP_MESSAGES("SEARCH_KEYWORD").format(keyword = keyword)

        # 历史记录、稍后再看本身没有标题，只保留关键词，分类名由列表另行显示
        return "{title} - {label}".format(title = title, label = label) if title else label

    def get_display_number(self, default_number: int):
        if self.target_number is not None and self.target_number != "":
            return self.target_number

        return default_number

    def update_episode_list(self, node: TreeItem, current_episode_data: tuple = None):
        # 由于顶层 root_node 不可见，需要在外面再包一层，避免顶层节点信息丢失

        root_node = TreeItem({})
        root_node.add_child(node)

        title = node.title

        # 动态解析会先用一棵空树建立根节点，此时没有子节点可供取标题
        if not title and node.count():
            child = node.child(0)

            if child.has_attribute(Attribute.VIDEO_BIT) or child.has_attribute(Attribute.AUDIO_BIT):
                title = node.child(0).title

            if child.has_attribute(Attribute.HISTORY_BIT) or child.has_attribute(Attribute.WATCH_LATER_BIT):
                title = node.number

        if config.get(config.auto_select_mode) == AutoSelectMode.MANUAL:
            current_episode_data = None

        signal_bus.parse.update_parse_list.emit(title, self.category_name, root_node, current_episode_data)

    def get_episode_duration(self, episode_data: dict):
        if "duration" in episode_data:
            return episode_data["duration"]
        
        elif "arc" in episode_data:
            return episode_data["arc"]["duration"]
        
        elif "length" in episode_data:
            return Units.unformat_episode_duration(episode_data["length"])

        else:
            return 0
        
    def _init_episode_data(self):
        if not self.episode_id:
            self.episode_id = EpisodeData.add_episode()

        return EpisodeData.get_episode_data(self.episode_id)
    
    def _video_episode_data_parser(self):
        episode_data = self._init_episode_data()

        if self.target_episode_data_id:
            data = EpisodeData.get_episode_data(self.target_episode_data_id)

            episode_data.update(data)

        # 简介
        episode_data["description"] = self.info_data.get("desc", "")
        # 分区信息
        episode_data["tid"] = self.info_data.get("tid", 0)
        episode_data["tid_v2"] = self.info_data.get("tid_v2", 0)
        # UP 主信息
        episode_data["uploader"] = self.info_data["owner"]["name"]
        episode_data["uploader_uid"] = self.info_data["owner"]["mid"]
        episode_data["uploader_face"] = self.info_data["owner"]["face"]        
