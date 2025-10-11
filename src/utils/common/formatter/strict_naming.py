from utils.common.map import cn_num_map
from utils.common.datetime_util import DateTime
from utils.common.model.task_info import DownloadTaskInfo

class StrictNaming:
    @classmethod
    def check_strict_naming(cls, task_info: DownloadTaskInfo):
        cls.get_episode_tag(task_info)

        cls.get_section_title_ex(task_info)

    @classmethod
    def get_season_num_ex(cls, info_json: dict):
        # 获取当前番剧的季编号
        for index, entry in enumerate(info_json.get("seasons")):
            if entry["season_id"] == info_json.get("season_id"):
                return index + 1
    
    @classmethod
    def get_episode_tag(cls, task_info: DownloadTaskInfo):
        season_string = "S{season_num:02}".format(season_num = task_info.season_num)
        episode_string = "E{episode_num:0>{width}}".format(episode_num = task_info.episode_num, width = len(str(task_info.total_count)) if task_info.total_count > 9 else 2)

        if task_info.episode_num != 0:
            task_info.episode_tag = "{season_string}{episode_string}".format(title = task_info.title, season_string = season_string, episode_string = episode_string)
        else:
            task_info.episode_tag = ""

    @classmethod
    def get_section_title_ex(cls, task_info: DownloadTaskInfo):
        if task_info.bangumi_type != "电影":
            section_title_ex = "Season {season_num:02}".format(season_num = task_info.season_num)
        else:
            section_title_ex = f"{task_info.series_title} ({DateTime.time_str_from_timestamp(task_info.pubtimestamp, "%Y")})"

        task_info.section_title_ex = section_title_ex
    
    @staticmethod
    def convert_cn_num_to_arabic(cn_num: str):
        num = 0

        for c in cn_num:
            num += cn_num_map.get(c, 0)
        
        return num if num else cn_num