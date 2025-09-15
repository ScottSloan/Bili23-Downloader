class TreeListItemInfo:
    def __init__(self):
        self.number: int = 0
        self.page: int = 0
        self.season_num: int = 0
        self.episode_num: int = 0

        self.title: str = ""

        self.cid: int = 0
        self.aid: int = 0
        self.bvid: str = ""
        self.ep_id: int = 0
        self.season_id: int = 0
        self.media_id: int = 0

        self.pubtime: int = 0
        self.badge: str = ""
        self.duration: str = ""
        self.cover_url: str = ""
        self.link: str = ""

        self.pid: str = ""

        self.section_title: str = ""
        self.part_title: str = ""
        self.collection_title: str = ""
        self.series_title: str = ""
        self.interact_title: str = ""
        self.parent_title: str = ""

        self.area: str = ""
        self.zone: str = ""
        self.subzone: str = ""
        self.up_name: str = ""
        self.up_mid: int = 0

        self.item_type: str = "node"
        self.type: int = 0
        self.bangumi_type: str = ""
        self.template_type: int = 0

    def to_dict(self):
        return {
            "number": self.number,
            "page": self.page,
            "season_num": self.season_num,
            "episode_num": self.episode_num,

            "title": self.title,

            "cid": self.cid,
            "aid": self.aid,
            "bvid": self.bvid,
            "ep_id": self.ep_id,
            "season_id": self.season_id,
            "media_id": self.media_id,

            "pubtime": self.pubtime,
            "badge": self.badge,
            "duration": self.duration,
            "cover_url": self.cover_url,
            "link": self.link,

            "pid": self.pid,

            "section_title": self.section_title,
            "part_title": self.part_title,
            "collection_title": self.collection_title,
            "series_title": self.series_title,
            "interact_title": self.interact_title,
            "parent_title": self.parent_title,

            "area": self.area,
            "zone": self.zone,
            "subzone": self.subzone,
            "up_name": self.up_name,
            "up_mid": self.up_mid,

            "item_type": self.item_type,
            "type": self.type,
            "bangumi_type": self.bangumi_type,
            "template_type": self.template_type
        }

    def load_from_dict(self, data: dict):
        self.number = data.get("number", self.number)
        self.page = data.get("page", self.page)
        self.season_num = data.get("season_num", self.season_num)
        self.episode_num = data.get("episode_num", self.episode_num)

        self.title = data.get("title", self.title)

        self.cid = data.get("cid", self.cid)
        self.aid = data.get("aid", self.aid)
        self.bvid = data.get("bvid", self.bvid)
        self.ep_id = data.get("ep_id", self.ep_id)
        self.season_id = data.get("season_id", self.season_id)
        self.media_id = data.get("media_id", self.media_id)

        self.pubtime = data.get("pubtime", self.pubtime)
        self.badge = data.get("badge", self.badge)
        self.duration = data.get("duration", self.duration)
        self.cover_url = data.get("cover_url", self.cover_url)
        self.link = data.get("link", self.link)

        self.pid = data.get("pid", self.pid)

        self.section_title = data.get("section_title", self.section_title)
        self.part_title = data.get("part_title", self.part_title)
        self.collection_title = data.get("collection_title", self.collection_title)
        self.series_title = data.get("series_title", self.series_title)
        self.interact_title = data.get("interact_title", self.interact_title)
        self.parent_title = data.get("parent_title", self.parent_title)

        self.area = data.get("area", self.area)
        self.zone = data.get("zone", self.zone)
        self.subzone = data.get("subzone", self.subzone)
        self.up_name = data.get("up_name", self.up_name)
        self.up_mid = data.get("up_mid", self.up_mid)

        self.item_type = data.get("item_type", self.item_type)
        self.type = data.get("type", self.type)
        self.bangumi_type = data.get("bangumi_type", self.bangumi_type)
        self.template_type = data.get("template_type", self.template_type)