from urllib.parse import urlparse, parse_qs

from ...common.enum import ParserType
from ...network.request import RequestType, SyncNetWorkRequest
from ..episode.lesson import LessonEpisodeParser
from .base import ParserBase

"""
会员购商城课程（mall.bilibili.com/lesson/play）的接口基地址与课程中心（www.bilibili.com/cheese，走 api.bilibili.com/pugv）不同，没有 season_id / ep_id，也没有 aid / cid，条目只能靠 courseId + lessonId +
itemId + sectionId 四元组定位，取到的也不是 dash 流而是一条完整的 mp4 直链
"""
LESSON_API_BASE = "https://mall.bilibili.com/mall-search-items"

# 取小节播放地址的接口，预览与下载两侧都要用
LESSON_PLAY_DETAIL_URL = f"{LESSON_API_BASE}/items/course/section/play/detail"

# 接口不返回任何清晰度信息，且只有一条流可选，这里取一个标称值让界面有东西可显示
LESSON_VIDEO_QUALITY_ID = 80

def build_lesson_play_payload(course_id: int, lesson_id: int, item_id: int, section_id: int):
    return {
        "courseId": course_id,
        "lessonId": lesson_id,
        "itemId": item_id,
        "sectionId": section_id
    }

def build_lesson_media_info(data: dict):
    """
    把商城课程的单条 mp4 直链包装成 playurl 接口的 mp4（durl）格式
    """
    video_url = (data or {}).get("videoUrl")

    if not video_url:
        raise RuntimeError("接口未返回该小节的播放地址")

    return {
        "format": "mp4",
        "quality": LESSON_VIDEO_QUALITY_ID,
        "accept_quality": [LESSON_VIDEO_QUALITY_ID],
        "timelength": 0,
        "durl": [
            {
                "order": 1,
                "length": int(data.get("videoTime") or 0) * 1000,
                "size": 0,
                "url": video_url,
                "backup_url": []
            }
        ]
    }

class LessonParser(ParserBase):
    def __init__(self):
        super().__init__()

        self.course_id = 0
        self.lesson_id = 0
        self.item_id = 0

    def parse(self, url: str, pn: int):
        self.url = url

        self.check_login()

        self.get_id_from_url()

        self.get_lesson_info()

        episode_parser = LessonEpisodeParser(self.info_data, self.get_category_name())
        episode_parser.parse()

    def get_id_from_url(self):
        query = parse_qs(urlparse(self.url).query)

        def get_id(name: str):
            value = query.get(name, [""])[0].strip()

            if not value.isdigit():
                raise ValueError("无效的链接")

            return int(value)

        self.course_id = get_id("courseId")
        self.lesson_id = get_id("lessonId")
        self.item_id = get_id("itemId")

    def get_lesson_info(self):
        url = f"{LESSON_API_BASE}/items/course/h5/detail"

        request = SyncNetWorkRequest(url, RequestType.POST, json_data = self.get_id_payload(), raise_for_status = self.raise_for_status)
        response = request.run()

        self.check_response(response)

        self.info_data = response

        if not isinstance(self.info_data.get("data"), dict):
            # code 为 0 但没有数据体，多半是课程已下架或该账号无权访问
            raise RuntimeError("接口未返回课程数据，请确认该课程是否已购买")


        self.info_data["data"].update(self.get_id_payload())

    def get_id_payload(self):
        return {
            "courseId": self.course_id,
            "lessonId": self.lesson_id,
            "itemId": self.item_id
        }

    def get_parser_type(self):
        return ParserType.CHEESE
