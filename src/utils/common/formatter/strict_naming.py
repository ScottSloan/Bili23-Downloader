import re

from utils.common.map import cn_num_map
from utils.common.regex import Regex
from utils.common.model.task_info import DownloadTaskInfo

class StrictNaming:
    @classmethod
    def get_season_num(cls, season_title: str):
        pattern = r'(?:第\s*([一二三四五六七八九十百零\d]+)\s*季|([一二三四五六七八九十百零\d]+)\s*季|Season\s*(\d+)|S(\d+)|[^\d](\d+)$)'
        match = re.search(pattern, season_title)

        if match:
            # 先匹配中文数字
            season = match.group(1) or match.group(2)
            # 再匹配英文数字
            season = season or match.group(3) or match.group(4) or match.group(5)

            # 中文数字转阿拉伯数字
            if season and not season.isdigit():
                return cls.convert_cn_num_to_arabic(season)
            
            return int(season)
        
        # 未匹配到季编号，则默认返回 1 代表第一季
        return 1
    
    @classmethod
    def add_episode_badge(cls, task_info: DownloadTaskInfo):
        season_string = "S{season_num:02}".format(season_num = task_info.season_num)
        episode_string = "E{episode_num:0>{width}}".format(episode_num = task_info.episode_num, width = len(str(task_info.total_count)) if task_info.total_count > 9 else 2)

        task_info.title = "{title} - {season_string}{episode_string}".format(title = task_info.title, season_string = season_string, episode_string = episode_string)

    @classmethod
    def add_season_section_badge(cls, task_info: DownloadTaskInfo):
        if task_info.bangumi_type != "电影":
            if task_info.section_title == "正片":
                section_title = "Season {season_num:02}".format(season_num = task_info.season_num)
            else:
                section_title = "Extra/" + task_info.section_title

            task_info.section_title = section_title
    
    @staticmethod
    def convert_cn_num_to_arabic(cn_num: str):
        num = 0

        for c in cn_num:
            num += cn_num_map.get(c, 0)
        
        return num if num else cn_num