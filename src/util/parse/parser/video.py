from ...network.request import SyncNetWorkRequest
from ...common.signal_bus import signal_bus
from ...common.translator import Translator
from ...common.enum import ParserType

from ..episode.dynamic import DynamicEpisodeParser
from ..episode.video import VideoEpisodeParser
from .base import ParserBase

from typing import List, Optional, Callable
from collections import deque
from threading import Event

class Node:
    def __init__(self, cid: int, title: str):
        self.cid: int = cid
        self.title: str = title
        self.options: List[Option] = []

    def to_dict(self):
        return {
            "cid": self.cid,
            "title": self.title,
            "options": [option.to_dict() for option in self.options]
        }
    
class Option:
    def __init__(self, edge_id: int, name: str):
        self.edge_id: int = edge_id
        self.name: str = name
        self.target_node_cid: Optional[int] = None
        self.show: bool = True
        self.accessed: bool = False

    def to_dict(self):
        return {
            "edge_id": self.edge_id,
            "name": self.name,
            "accessed": self.accessed,
            "target_node_cid": self.target_node_cid
        }

class InteractiveVideoParser(ParserBase):
    def __init__(self, data: dict, update_progress_callback: Callable, stop_event: Event):
        super().__init__()

        self.info_data: dict = data["data"]

        self.bvid = self.info_data["bvid"]
        self.aid = self.info_data["aid"]
        self.cid = self.info_data["cid"]

        self.graph_version = None
        self.node_list: List[Node] = []
        self.node_map: dict[int, Node] = {}
        self.visited_states: set[tuple[int, int]] = set()

        self.stop_event = stop_event
        self.update_progress = update_progress_callback

    def parse(self):
        self.get_graph_version()

        self.episode_parser = DynamicEpisodeParser(self.info_data, self.get_category_name())
        self.episode_parser.video_episode_data_parser()

        self.parse_interactive_video_episodes()

    def get_graph_version(self):
        # 获取 graph_version
        params = {
            "aid": self.aid,
            "cid": self.cid,
            "isGaiaAvoided": False,
            "web_location": 1315873,
            "dm_img_list": "[]",
            "dm_img_str": "V2ViR0wgMS4wIChPcGVuR0wgRVMgMi4wIENocm9taXVtKQ",
            "dm_cover_img_str": "QU5HTEUgKE5WSURJQSwgTlZJRElBIEdlRm9yY2UgUlRYIDQwNjAgTGFwdG9wIEdQVSAoMHgwMDAwMjhFMCkgRGlyZWN0M0QxMSB2c181XzAgcHNfNV8wLCBEM0QxMSlHb29nbGUgSW5jLiAoTlZJRElBKQ",
            "dm_img_inter": '{"ds":[],"wh":[5073,6031,29],"of":[206,412,206]}',
        }

        url = f"https://api.bilibili.com/x/player/wbi/v2?{self.enc_wbi(params)}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        self.check_response(response)

        if "interaction" in response["data"]:
            self.graph_version = response["data"]["interaction"]["graph_version"]
        
        else:
            raise ValueError("无法获取 graph_version，可能不是互动视频")

    def _reset_graph(self):
        self.node_list.clear()
        self.node_map.clear()
        self.visited_states.clear()

    def _get_node_title(self, data: dict) -> str:
        if title := data.get("title"):
            return title

        story_list = data.get("story_list") or []
        if story_list:
            return story_list[0].get("title", "")

        return ""

    def _get_or_create_node(self, cid: int, title: str):
        node = self.node_map.get(cid)

        if node is None:
            node = Node(cid, title)
            self.node_map[cid] = node
            self.node_list.append(node)

            self._update_ui_progress(title, cid)

        elif title and node.title != title:
            node.title = title

        return node

    def _build_options(self, edges: dict):
        options: List[Option] = []

        for question in edges.get("questions", []):
            for choice in question.get("choices", []):
                option = Option(choice["id"], choice.get("option", ""))
                option.target_node_cid = choice.get("cid")
                option.show = bool(question.get("type", 1))
                options.append(option)

        return options

    def _merge_options(self, node: Node, options: List[Option]):
        existing_edge_ids = {option.edge_id for option in node.options}

        for option in options:
            if option.edge_id not in existing_edge_ids:
                node.options.append(option)
                existing_edge_ids.add(option.edge_id)

    def get_edge_info(self, cid: int, edge_id: int = 0):
        # 获取节点信息，包括当前节点标题和下一跳选项
        params = {
            "bvid": self.bvid,
            "graph_version": self.graph_version,
            "edge_id": edge_id
        }

        url = f"https://api.bilibili.com/x/stein/edgeinfo_v2?{self.enc_wbi(params)}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        self.check_response(response)

        data = response["data"]
        node = self._get_or_create_node(cid, self._get_node_title(data))
        self._merge_options(node, self._build_options(data.get("edges", {})))

        return node

    def parse_interactive_video_episodes(self):
        self._reset_graph()

        pending_nodes = deque([(self.cid, 0)])

        while pending_nodes and not self.stop_event.is_set():
            cid, edge_id = pending_nodes.popleft()
            state = (cid, edge_id)

            if state in self.visited_states:
                continue

            node = self.get_edge_info(cid, edge_id)
            self.visited_states.add(state)

            for option in node.options:
                target_cid = option.target_node_cid

                if target_cid is not None and (target_cid, option.edge_id) not in self.visited_states:
                    pending_nodes.append((target_cid, option.edge_id))

        return self.node_list

    def get_category_name(self):
        # 互动视频
        return "INTERACTIVE"
    
    def _update_ui_progress(self, title: str, cid: int):
        self.update_progress(Translator.TIP_MESSAGES("PARSING_INTERACTIVE_VIDEO_NODE").format(title = title))

        self.episode_parser.update(title, cid)

        signal_bus.parse.update_parse_list_count.emit(self.get_category_name())

class VideoParser(ParserBase):
    def __init__(self):
        super().__init__()
        
    def get_aid(self):
        aid = self.find_str(r"av([0-9]+)", self.url)

        return self.aid_to_bvid(int(aid))

    def get_bvid(self):
        bvid = self.find_str(r"BV\w+", self.url)

        return bvid

    def aid_to_bvid(self, aid: int):
        XOR_CODE = 23442827791579
        MAX_AID = 1 << 51
        ALPHABET = "FcwAPNKTMug3GV5Lj7EJnHpWsx4tb8haYeviqBz6rkCy12mUSDQX9RdoZf"
        ENCODE_MAP = 8, 7, 0, 5, 1, 3, 2, 4, 6

        bvid = [""] * 9
        tmp = (MAX_AID | aid) ^ XOR_CODE

        for i in range(len(ENCODE_MAP)):
            bvid[ENCODE_MAP[i]] = ALPHABET[tmp % len(ALPHABET)]
            tmp //= len(ALPHABET)

        return "BV1" + "".join(bvid)

    def parse(self, url: str, pn: int):
        self.url = url

        match self.find_str(r"av|BV", url):
            case "av":
                self.bvid = self.get_aid()

            case "BV":
                self.bvid = self.get_bvid()

        self.get_video_info()

        if "redirect_url" in self.info_data["data"]:
            # 存在重定向链接，停止当前解析，开启新的解析线程
            signal_bus.parse.parse_url.emit(self.info_data["data"]["redirect_url"])

        elif self.is_interactive_video:
            # 互动视频，询问用户是否探查所有节点
            self.info_data["parser_type"] = ParserType.INTERACTIVE_VIDEO
            signal_bus.parse.show_interactive_video_dialog.emit(self.info_data.copy())

        else:
            episode_parser = VideoEpisodeParser(self.info_data.copy(), self.get_category_name())
            episode_parser.parse()

    def get_video_info(self):
        params = {
            "bvid": self.bvid
        }

        url = f"https://api.bilibili.com/x/web-interface/wbi/view?{self.enc_wbi(params)}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        self.check_response(response)

        self.info_data = response

    def get_category_name(self):
        # 投稿视频
        return "USER_UPLOADS"
    
    def get_interactive_video_data(self):
        return {
            "bvid": self.info_data["data"]["bvid"],
            "aid": self.info_data["data"]["aid"],
            "cid": self.info_data["data"]["cid"]
        }

    @property
    def is_interactive_video(self):
        return self.info_data["data"]["rights"]["is_stein_gate"] == 1
