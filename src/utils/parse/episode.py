from utils.common.enums import ParseType, EpisodeDisplayType, VideoType

class EpisodeInfo:
    data: dict = {}
    cid_dict: dict = {}

    @classmethod
    def clear_episode_data(cls, title: str = "视频"):
        cls.data = {
            "title": title,
            "entries": []
        }
        
        cls.cid_dict.clear()

    @classmethod
    def add_item(cls, data: list | dict, parent: str, entry_data: dict):
        if isinstance(data, dict):
            if data["title"] == parent:
                if "entries" in data:
                    data["entries"].append(entry_data)
            else:
                if "entries" in data:
                    cls.add_item(data["entries"], parent, entry_data)

        elif isinstance(data, list):
            for entry in data:
                cls.add_item(entry, parent, entry_data)

class EpisodeUtils:
    @staticmethod
    def live_episode_parser(title: str, status: str):
        EpisodeInfo.add_item(EpisodeInfo.data, "直播", {
            "title": title,
            "badge": status,
            "duration": "--:--",
            "cid": 0
        })

    @staticmethod
    def get_episode_url(cid: int, parse_type: ParseType):
        episode_info = EpisodeInfo.cid_dict.get(cid)

        match parse_type:
            case ParseType.Video:
                def video():
                    from utils.parse.video import VideoInfo

                    match VideoInfo.type:
                        case VideoType.Single:
                            return VideoInfo.url

                        case VideoType.Part:
                            return f"{VideoInfo.url}?p={episode_info['page']}"

                        case VideoType.Collection:
                            return f"https://www.bilibili.com/video/{episode_info['bvid']}"

                return video()
            
            case ParseType.Bangumi:
                return f"https://www.bilibili.com/bangumi/play/ep{episode_info['ep_id']}"
        
            case ParseType.Live:
                from utils.parse.live import LiveInfo

                return f"https://live.bilibili.com/{LiveInfo.room_id}"
            
            case ParseType.Cheese:
                return f"https://www.bilibili.com/cheese/play/ep{episode_info['id']}"
