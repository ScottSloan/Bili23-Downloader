from PySide6.QtCore import Qt

from enum import IntFlag
from typing import List
import uuid

class EpisodeData:
    table: dict[str, dict] = {}

    @classmethod
    def add_episode(cls):
        episode_id = str(uuid.uuid4())
        cls.table[episode_id] = {}
        return episode_id

    @classmethod
    def get_episode_data(cls, episode_id: str):
        return cls.table.get(episode_id, {})

    @classmethod
    def clear_cache(cls):
        cls.table.clear()

class Attribute(IntFlag):
    VIDEO_BIT = 1 << 0
    BANGUMI_BIT = 1 << 1
    CHEESE_BIT = 1 << 2
    NORMAL_BIT = 1 << 8
    PART_BIT = 1 << 9
    COLLECTION_BIT = 1 << 10
    COLLECTION_LIST_BIT = 1 << 11
    FAVLIST_BIT = 1 << 12
    SPACE_BIT = 1 << 13
    POPULAR_BIT = 1 << 14
    WATCH_LATER_BIT = 1 << 15
    INTERACTIVE_BIT = 1 << 16
    DOWNLOAD_AS_SINGLE_VIDEO_BIT = 1 << 17
    TREE_NODE_BIT = 1 << 20
    NEED_PARSE_BIT = 1 << 25

class TreeItemBase:
    def __init__(self):
        self.parent = None
        self.checked = Qt.CheckState.Unchecked
        self.children: List["TreeItem"] = []

    def add_child(self, child: "TreeItem"):
        child.parent = self
        self.children.append(child)

    def child(self, row: int):
        return self.children[row]

    def count(self):
        return len(self.children)

    def row(self):
        if self.parent:
            return self.parent.children.index(self)
        return 0

    def set_checked_state(self, state: Qt.CheckState):
        if isinstance(state, int):
            state = Qt.CheckState(state)
        if self.checked == state:
            return
        self.checked = state
        if state in (Qt.CheckState.Checked, Qt.CheckState.Unchecked):
            self._propagate_down(state)
        if self.parent:
            self.parent._propagate_up()

    def _propagate_down(self, state: Qt.CheckState):
        self.checked = state
        for child in self.children:
            child._propagate_down(state)

    def _propagate_up(self):
        states = [child.checked for child in self.children]
        if all(s == Qt.CheckState.Checked for s in states):
            new_state = Qt.CheckState.Checked
        elif all(s == Qt.CheckState.Unchecked for s in states):
            new_state = Qt.CheckState.Unchecked
        else:
            new_state = Qt.CheckState.PartiallyChecked
        if self.checked != new_state:
            self.checked = new_state
            if self.parent:
                self.parent._propagate_up()

    def get_all_checked_children(self, to_dict=False, mark_as_downloaded=False):
        checked_items: List["TreeItem"] = []
        for child in self.children:
            if child.children:
                checked_items.extend(child.get_all_checked_children(to_dict=to_dict, mark_as_downloaded=mark_as_downloaded))
            else:
                if child.checked == Qt.CheckState.Checked and child.attribute & Attribute.TREE_NODE_BIT == 0:
                    if mark_as_downloaded:
                        child.downloaded = True
                    if to_dict:
                        checked_items.append(child.to_dict())
                    else:
                        checked_items.append(child)
        return checked_items

    def get_all_children(self, to_dict=False):
        all_items: List["TreeItem"] = []
        for child in self.children:
            if child.children:
                all_items.extend(child.get_all_children(to_dict=to_dict))
            else:
                if child.attribute & Attribute.TREE_NODE_BIT == 0:
                    if to_dict:
                        all_items.append(child.to_dict())
                    else:
                        all_items.append(child)
        return all_items

class TreeItem(TreeItemBase):
    def __init__(self, item_data: dict):
        super().__init__()
        self.attribute = 0
        self.pubtime = item_data.get("pubtime", 0)
        self.favtime = item_data.get("favtime", 0)
        self.viewtime = item_data.get("viewtime", 0)
        self.expired = item_data.get("expired", False)
        self.aid = item_data.get("aid", 0)
        self.cid = item_data.get("cid", 0)
        self.url = item_data.get("url", "")
        self.bvid = item_data.get("bvid", "")
        self.ep_id = item_data.get("ep_id", 0)
        self.badge = item_data.get("badge", "")
        self.cover = item_data.get("cover", "")
        self.title = item_data.get("title", "")
        self.number = item_data.get("number", "")
        self.duration = item_data.get("duration", 0)
        self.episode_id = item_data.get("episode_id", "")
        self.episode_plot = item_data.get("episode_plot", "")
        self.part_number = item_data.get("part_number", 0)
        self.episode_number = item_data.get("episode_number", 0)
        self.related_titles = item_data.get("related_titles", {})
        self.uploader = item_data.get("uploader", "")
        self.uploader_uid = item_data.get("uploader_uid", 0)
        self.downloaded = False

    def set_attribute(self, flag: int):
        self.attribute |= flag

    def to_dict(self):
        data = {
            "attribute": self.attribute,
            "episode_id": self.episode_id,
            "episode_number": self.episode_number,
            "aid": self.aid,
            "badge": self.badge,
            "bvid": self.bvid,
            "cid": self.cid,
            "cover": self.cover,
            "duration": self.duration,
            "ep_id": self.ep_id,
            "number": self.number,
            "pubtime": self.pubtime,
            "favtime": self.favtime,
            "part_number": self.part_number,
            "related_titles": self.related_titles,
            "title": self.title,
            "url": self.url,
            "episode_plot": self.episode_plot,
        }
        if self.uploader:
            data["uploader_info"] = {
                "uploader": self.uploader,
                "uploader_uid": self.uploader_uid
            }
        return data

    def search_items(self, keyword: str):
        matches = []
        if keyword.lower() in self.title.lower():
            matches.append(self)
        for child in self.children:
            matches.extend(child.search_items(keyword))
        return matches

    @property
    def dyn_time(self):
        return self.pubtime
