from utils.config import Config
from utils.common.enums import ParseType, EpisodeDisplayType, TemplateType
from utils.common.data.badge import badge_dict

from utils.parse.episode.episode_v2 import EpisodeInfo, Filter, Episode

class Video:
    target_cid: int = 0

    @classmethod
    def parse_episodes(cls, info_json: dict):
        cls.target_cid = info_json.get("cid")
        EpisodeInfo.parser = cls

        EpisodeInfo.clear_episode_data()

        match EpisodeDisplayType(Config.Misc.episode_display_mode):
            case EpisodeDisplayType.Single:
                cls.pages_parser(info_json)

            case EpisodeDisplayType.In_Section | EpisodeDisplayType.All:
                if "ugc_season" in info_json:
                    cls.ugc_season_parser(info_json)

                elif "node_list" in info_json:
                    cls.interact_parser(info_json)

                else:
                    cls.pages_parser(info_json)

        Filter.episode_display_mode(reset = EpisodeDisplayType(Config.Misc.episode_display_mode) == EpisodeDisplayType.In_Section)

    @classmethod
    def pages_parser(cls, info_json: dict, parent_title: str = ""):
        episode_info_list = []
        pages_cnt = len(info_json["pages"])

        part_title = info_json.get("title")

        if not parent_title:
            if pages_cnt > 1:
                page_pid = EpisodeInfo.add_item(EpisodeInfo.root_pid, EpisodeInfo.get_node_info(part_title, label = "分P"))
            else:
                page_pid = EpisodeInfo.root_pid

        for page in info_json["pages"]:
            page["cover_url"] = info_json["pic"]
            page["aid"] = info_json["aid"]
            page["bvid"] = info_json["bvid"]
            page["pubtime"] = info_json["pubdate"]
            page["title"] = page["part"] if pages_cnt > 1 else info_json["title"]
            page["part_title"] = part_title if pages_cnt > 1 else ""
            page["template_type"] = TemplateType.Video_Part.value if pages_cnt > 1 else TemplateType.Video_Normal.value
            page["parent_title"] = parent_title

            entry_info = cls.get_entry_info(page.copy(), info_json)

            if parent_title:
                episode_info_list.append(EpisodeInfo.get_entry_info(entry_info))
            else:
                EpisodeInfo.add_item(page_pid, entry_info)

        return episode_info_list

    @classmethod
    def ugc_season_parser(cls, info_json: dict, parent_title: str = ""):
        episode_info_list = []
        collection_title = info_json["ugc_season"]["title"]

        if not parent_title:
            collection_pid = EpisodeInfo.add_item(EpisodeInfo.root_pid, EpisodeInfo.get_node_info(collection_title, label = "合集"))

        for section in info_json["ugc_season"]["sections"]:
            section_title = section["title"]

            if not parent_title:
                section_pid = EpisodeInfo.add_item(collection_pid, EpisodeInfo.get_node_info(section_title, label = "章节"))

            for episode in section["episodes"]:
                cover_url = episode["arc"]["pic"]
                aid = episode["aid"]
                bvid = episode["bvid"]
                pubtime = episode["arc"]["pubdate"]
                badge =  Episode.Utils.get_badge(episode.get("attribute", 0))

                if len(episode["pages"]) == 1:
                    episode["page"] = episode["page"]["page"] if isinstance(episode["page"], dict) else episode["page"]
                    episode["cover_url"] = cover_url
                    episode["aid"] = aid
                    episode["bvid"] = bvid
                    episode["pubtime"] = pubtime
                    episode["badge"] = badge
                    episode["section_title"] = section_title
                    episode["collection_title"] = collection_title
                    episode["template_type"] = TemplateType.Video_Collection.value

                    entry_info = cls.get_entry_info(episode.copy(), info_json)

                    if parent_title:
                        episode_info_list.append(EpisodeInfo.get_entry_info(entry_info))
                    else:
                        EpisodeInfo.add_item(section_pid, entry_info)

                else:
                    part_title = episode["title"]

                    part_pid = EpisodeInfo.add_item(section_pid, EpisodeInfo.get_node_info(part_title, episode["arc"]["duration"], label = "分节"))

                    for page in episode["pages"]:
                        page["cover_url"] = cover_url
                        page["aid"] = aid
                        page["bvid"] = bvid
                        page["pubtime"] = pubtime
                        page["badge"] = badge
                        page["section_title"] = section_title
                        page["part_title"] = part_title
                        page["collection_title"] = collection_title
                        page["template_type"] = TemplateType.Video_Collection.value

                        entry_info = cls.get_entry_info(page.copy(), info_json)

                        if parent_title:
                            episode_info_list.append(EpisodeInfo.get_entry_info(entry_info))
                        else:
                            EpisodeInfo.add_item(part_pid, entry_info)

                cls.update_target_section_title(episode, section_title)

        return episode_info_list

    @classmethod
    def ugc_season_pages_parser(cls, info_json: dict, target_bvid: str, parent_title: str):
        episode_info_list = []

        for section in info_json["ugc_season"]["sections"]:
            for episode in section.get("episodes"):
                if (bvid := episode.get("bvid")) == target_bvid:
                    cover_url = episode["arc"]["pic"]
                    aid = episode["aid"]
                    bvid = episode["bvid"]
                    pubtime = episode["arc"]["pubdate"]
                    badge = Episode.Utils.get_badge(episode.get("attribute", 0))

                    if len(episode.get("pages")) == 1:
                        episode["cover_url"] = cover_url
                        episode["aid"] = aid
                        episode["bvid"] = bvid
                        episode["pubtime"] = pubtime
                        episode["badge"] = badge
                        episode["parent_title"] = parent_title

                        episode_info_list.append(EpisodeInfo.get_entry_info(cls.get_ugc_pages_entry_info(episode.copy(), info_json, multiple = False)))

                    else:
                        part_title = episode["arc"]["title"]

                        for page in episode.get("pages"):
                            page["cover_url"] = cover_url
                            page["bvid"] = bvid
                            page["aid"] = aid
                            page["collection_title"] = part_title
                            page["badge"] = badge
                            page["parent_title"] = parent_title

                            episode_info_list.append(EpisodeInfo.get_entry_info(cls.get_ugc_pages_entry_info(page.copy(), info_json, multiple = True)))

        return episode_info_list

    @classmethod
    def interact_parser(cls, info_json: dict):
        interact_title = info_json.get("title")

        interact_pid = EpisodeInfo.add_item(EpisodeInfo.root_pid, EpisodeInfo.get_node_info(interact_title, label = "互动"))

        for node in info_json.get("node_list"):
            page = {
                "cover_url": info_json["pic"],
                "aid": info_json["aid"],
                "bvid": info_json["bvid"],
                "pubtime": info_json["pubdate"],
                "title": node.title,
                "cid": node.cid,
                "interact_title": interact_title,
                "template_type": TemplateType.Video_Interact.value
            }

            EpisodeInfo.add_item(interact_pid, cls.get_entry_info(page.copy(), info_json))

    @classmethod
    def get_entry_info(cls, episode: dict, info_json: dict):
        episode["title"] = episode.get("title", episode.get("part", ""))
        episode["badge"] = Episode.Utils.get_badge(episode.get("attribute", 0))
        episode["duration"] = cls.get_duration(episode.copy())
        episode["link"] = cls.get_link(episode.copy())
        episode["type"] = ParseType.Video.value
        episode["zone"] = info_json.get("tname", "")
        episode["subzone"] = info_json.get("tname_v2", "")
        episode["up_name"] = info_json.get("owner", {"name": ""}).get("name", "")
        episode["up_mid"] = info_json.get("owner", {"mid": 0}).get("mid", 0)
        episode["interact_title"] = episode.get("interact_title", "")

        return EpisodeInfo.get_entry_info(episode)
    
    @classmethod
    def get_ugc_pages_entry_info(cls, episode: dict, info_json: dict, multiple: bool):
        episode["title"] = episode.get("title", episode.get("part", ""))
        episode["duration"] = cls.get_duration(episode.copy())
        episode["link"] = f"https://www.bilibili.com/video/{episode.get('bvid')}"
        episode["type"] = ParseType.Video.value
        episode["zone"] = info_json.get("tname", "")
        episode["subzone"] = info_json.get("tname_v2", "")
        episode["up_name"] = info_json.get("owner", {"name": ""}).get("name", "")
        episode["up_mid"] = info_json.get("owner", {"mid": 0}).get("mid", 0)
        episode["template_type"] = TemplateType.Video_Collection.value if multiple else TemplateType.Video_Normal.value

        return EpisodeInfo.get_entry_info(episode)

    @classmethod
    def update_target_section_title(cls, episode: dict, section_title: str):
        if episode.get("cid") == cls.target_cid:
            cls.target_section_title = section_title

    @classmethod
    def condition_single(cls, episode: dict):
        return episode.get("item_type") == "item" and episode.get("cid") == cls.target_cid
    
    @classmethod
    def condition_in_section(cls, episode: dict):
        return episode.get("item_type") == "node" and episode.get("title") == cls.target_section_title
    
    @staticmethod
    def get_duration(episode: dict):
        if "duration" in episode:
            return episode["duration"]
        
        elif "arc" in episode:
            return episode["arc"]["duration"]
        
        else:
            return 0
        
    @staticmethod
    def get_link(episode: dict):
        page = episode.get("page", 0)

        if page > 1:
            return f"https://www.bilibili.com/video/{episode.get('bvid')}?p={episode.get('page')}"
        else:
            return f"https://www.bilibili.com/video/{episode.get('bvid')}"