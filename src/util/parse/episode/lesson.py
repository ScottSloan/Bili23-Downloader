from ...common.translator import Translator

from .tree import TreeItem, EpisodeData, Attribute
from .base import EpisodeParserBase

import logging

logger = logging.getLogger(__name__)

class LessonEpisodeParser(EpisodeParserBase):
    def __init__(self, info_data: dict, category_name: str, kwargs: dict = {}):
        super().__init__(**kwargs)

        self.info_data = info_data["data"]
        self.category_name = category_name

    def parse(self, update_episode_list = True):
        self.episode_data_parser()

        node = self.sections_parser()

        if update_episode_list:
            current_episode_data = ("section_id", self.get_section_id())

            self.update_episode_list(node, current_episode_data)

        return node

    def sections_parser(self):
        course_title = self.get_course_title()

        root_node = TreeItem({
            "number": Translator.EPISODE_TYPE("COURSE"),
            "title": course_title
        })
        root_node.set_attribute(Attribute.TREE_NODE_BIT)

        for chapter in self.info_data.get("chapterList") or []:
            if not chapter.get("sectionList"):
                continue

            chapter_title = (chapter.get("chapterName") or "").strip()

            if chapter_title:
                parent_node = TreeItem({
                    "number": "章节",
                    "title": chapter_title
                })
                parent_node.set_attribute(Attribute.TREE_NODE_BIT)
            else:
                # chapterMode 为 0 的课程只有一个 chapterName 为空串的章节，
                # 此时再插一层节点就会在解析列表里显示成一个没有名字的空节点，
                # 因此直接把小节挂到课程节点下
                parent_node = root_node

            for section in chapter["sectionList"]:
                if item := self.section_parser(section, course_title, chapter_title):
                    parent_node.add_child(item)

            if parent_node is not root_node and parent_node.count():
                root_node.add_child(parent_node)

        return root_node

    def section_parser(self, section: dict, course_title: str, chapter_title: str):
        section_id = section.get("sectionId")

        if not section_id:
            return None

        if not section.get("videoTime"):
            # 课程尚未更新的小节，网页端同样不可播放，取播放地址只会失败，不放进列表
            logger.info("跳过尚未更新的小节：%s", section.get("sectionName", ""))

            return None

        self.episode_count += 1

        item = TreeItem({
            "badge": self.get_section_badge(section),
            "course_id": self.info_data.get("courseId", 0),
            "lesson_id": section.get("lessonId") or self.info_data.get("lessonId", 0),
            "item_id": self.info_data.get("itemId", 0),
            "section_id": section_id,
            # 列表接口的 videoTime 单位是毫秒（取播放地址的接口才是秒），此处需要换算。
            # 取整而非四舍五入，与接口自带的 videoTimeDesc 保持一致
            "duration": section["videoTime"] // 1000,
            "episode_id": self.episode_id,
            "episode_plot": chapter_title,
            "number": self.get_display_number(section.get("sectionIndex", self.episode_count)),
            "episode_number": section.get("sectionIndex", self.episode_count),
            "title": section.get("sectionName", ""),
            "related_titles": {
                "series_title": course_title,
                "season_title": course_title,
                "section_title": chapter_title or course_title
            },
            "url": self.get_section_url()
        })

        item.set_attribute(Attribute.LESSON_BIT)

        if self.target_attribute:
            item.set_attribute(self.target_attribute)

        return item

    def episode_data_parser(self):
        episode_data = self._init_episode_data()

        if self.target_episode_data_id:
            data = EpisodeData.get_episode_data(self.target_episode_data_id)

            episode_data.update(data)

        episode_data["styles"] = ["Bilibili 课堂"]
        episode_data["season_id"] = self.info_data.get("lessonId", 0)

        # 商城课程的两个接口都不返回封面、简介与作者信息，
        # mid 字段是当前登录用户自己的 uid，不能拿来当 UP 主，因此这些字段一律留空

    def get_course_title(self):
        # lessonName 是课程名，itemsName 是商品名（往往带「【25年新增…】」一类的营销后缀），
        # 课程名更适合作为目录名与刮削标题，缺失时才退回商品名
        return self.info_data.get("lessonName") or self.info_data.get("itemsName") or ""

    def get_section_url(self):
        return "https://mall.bilibili.com/lesson/play?courseId={course_id}&lessonId={lesson_id}&itemId={item_id}".format(
            course_id = self.info_data.get("courseId", 0),
            lesson_id = self.info_data.get("lessonId", 0),
            item_id = self.info_data.get("itemId", 0)
        )

    def get_section_badge(self, section: dict):
        if section.get("hasWatchRight"):
            return ""

        return "试看" if section.get("couldPreview") else "付费"

    def get_section_id(self):
        # 链接本身不指向具体小节，优先定位到上次观看的位置，其次是第一个可播放的小节
        if section_id := (self.info_data.get("locationInfo") or {}).get("sectionId"):
            return section_id

        for chapter in self.info_data.get("chapterList") or []:
            for section in chapter.get("sectionList") or []:
                if section.get("videoTime"):
                    return section.get("sectionId", "")

        return ""
