from utils.parse.episode.episode_v2 import EpisodeInfo, Filter
from utils.parse.episode.video import Video
from utils.parse.episode.cheese import Cheese

class Space:
    parent_title: str = ""
    video_info_dict: dict = {}
    cheese_info_dict: dict = {}

    @classmethod
    def parse_episodes(cls, info_json: dict, bvid: str, video_info_dict: dict, cheese_info_dict: dict, parent_title: str):
        cls.parent_title = parent_title
        Video.parent_title = parent_title

        EpisodeInfo.clear_episode_data()

        cls.video_info_dict = video_info_dict.copy()
        cls.cheese_info_dict = cheese_info_dict.copy()

        for episode in info_json.get("episodes"):
            bvid = episode.get("bvid")

            if (season_id := episode.get("season_id")):
                if episode.get("is_lesson_video"):
                    season_info = cls.cheese_info_dict.get(season_id)

                    Cheese.parse_episodes(season_info, parent_title = parent_title)
                else:
                    season_info = cls.video_info_dict.get(season_id)

                    if episode.get("is_avoided"):
                        Video.ugc_season_parser(season_info.copy())
                    else:
                        Video.ugc_season_pages_parser(episode.copy(), season_info.copy(), bvid)
            else:
                Video.pages_parser(cls.video_info_dict.get(bvid).copy())

        Filter.episode_display_mode(reset = True)