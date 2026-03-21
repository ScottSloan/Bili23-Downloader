from util.common.signal_bus import signal_bus
from util.parse.episode.tree import TreeItem
from util.format import Units

class EpisodeParserBase:
    def __init__(self, **kwargs):
        self.episode_id = ""
        self.info_data: dict = {}

        self.target_episode_info: str | int = kwargs.get("target_episode_info")
        self.target_episode_data_id: str = kwargs.get("target_episode_data_id")
        self.target_attribute: int = kwargs.get("target_attribute")

    def update_episode_list(self, node: TreeItem):
        # 由于顶层 root_node 不可见，需要在外面再包一层，避免顶层节点信息丢失

        root_node = TreeItem({})
        root_node.add_child(node)

        signal_bus.parse.update_parse_list.emit(root_node)

    def get_episode_duration(self, episode_data: dict):
        if "duration" in episode_data:
            return episode_data["duration"]
        
        elif "arc" in episode_data:
            return episode_data["arc"]["duration"]
        
        elif "length" in episode_data:
            return Units.unformat_episode_duration(episode_data["length"])

        else:
            return 0
