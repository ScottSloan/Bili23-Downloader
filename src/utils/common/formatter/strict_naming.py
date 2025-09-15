import re

from utils.common.map import cn_num_map
from utils.common.regex import Regex

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
    
    @staticmethod
    def convert_cn_num_to_arabic(cn_num: str):
        num = 0

        for c in cn_num:
            num += cn_num_map.get(c, 0)
        
        return num if num else cn_num