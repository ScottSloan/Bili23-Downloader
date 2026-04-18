from util.common import signal_bus
from util.format import Units

from .tree import TreeItem, Attribute

class EpisodeParserBase:
    def __init__(self, **kwargs):
        self.episode_id = ""
        self.category_name = ""
        self.info_data: dict = {}

        self.target_episode_info: str | int = kwargs.get("target_episode_info")
        self.target_episode_data_id: str = kwargs.get("target_episode_data_id")
        self.target_attribute: int = kwargs.get("target_attribute")

    def update_episode_list(self, node: TreeItem, current_episode_data: tuple = None):
        # 由于顶层 root_node 不可见，需要在外面再包一层，避免顶层节点信息丢失

        root_node = TreeItem({})
        root_node.add_child(node)

        if node.count() == 1 and node.child(0).attribute & Attribute.VIDEO_BIT:
            title = node.child(0).title
        else:
            title = node.title

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
