from ....download.task.info import TaskInfo
from ....format.time import Time

from ...episode.tree import Attribute

from pathlib import Path
from typing import List
import textwrap
import math

video_base = """<?xml version="1.0" encoding="UTF-8"?>
<movie>
    <title>{title}</title>
    <plot>{plot}</plot>
    <runtime>{runtime}</runtime>
    <premiered>{premiered:%Y-%m-%d}</premiered>
    <year>{year}</year>
    <actor>
        <name>{uploader}</name>
        <role>UP主</role>
        <profile>https://space.bilibili.com/{uploader_uid}</profile>
        <thumb>{uploader_face}</thumb>
    </actor>
    {tag}
    <thumb>{thumb}</thumb>
    <uniqueid type="bvid">{bvid}</uniqueid>
</movie>
"""

tvshow_base = """<?xml version="1.0" encoding="UTF-8"?>
<tvshow>
    <title>{title}</title>
    <plot>{plot}</plot>
    <premiered>{premiered:%Y-%m-%d}</premiered>
    <year>{year}</year>
    <studio>Bilibili</studio>
    <director>{director}</director>
    {genre}
    {country}
    {rating}
    {status}
    <thumb aspect="poster">{thumb}</thumb>
    <uniqueid type="season_id">{season_id}</uniqueid>
</tvshow>
"""

episode_base = """<?xml version="1.0" encoding="UTF-8"?>
<episodedetails>
    <title>{title}</title>
    <plot>{plot}</plot>
    <runtime>{runtime}</runtime>
    <premiered>{premiered:%Y-%m-%d}</premiered>
    <year>{year}</year>
    <studio>Bilibili</studio>
    <episode>{episode}</episode>
    <director>{director}</director>
    {genre}
    {country}
    <thumb>{thumb}</thumb>
    <uniqueid type="ep_id">{ep_id}</uniqueid>
</episodedetails>
"""

class MetadataNFO:
    def __init__(self, task_info: TaskInfo):
        self.task_info = task_info

    def generate(self):
        contents_list = []

        attr = self.task_info.Episode.attribute

        if attr & Attribute.VIDEO_BIT != 0:
            contents_list.append({
                "contents": self._generate_video(),
                "name": self.task_info.File.name,
                "qualifier": ["元数据"]
            })

        if attr & Attribute.BANGUMI_BIT != 0 or attr & Attribute.CHEESE_BIT != 0:
            # 确保 tvshow.nfo 不重复生成
            if not self._is_tvshow_exists():
                contents_list.append({
                    "contents": self._generate_tvshow(self.task_info.Episode.styles),
                    "name": "tvshow",
                    "qualifier": []
                })

            contents_list.append({
                "contents": self._generate_episode(self.task_info.Episode.styles),
                "name": self.task_info.File.name,
                "qualifier": []
            })

        return contents_list

    def _generate_video(self):
        pubtime = Time.from_timestamp(self.task_info.Episode.pubtime)

        return video_base.format(
            title = self.task_info.Basic.show_title,
            plot = self.task_info.Episode.description,
            runtime = math.ceil(self.task_info.Episode.duration / 60),
            premiered = pubtime,
            year = pubtime.year,
            uploader = self.task_info.Episode.uploader,
            uploader_uid = self.task_info.Episode.uploader_uid,
            uploader_face = self.task_info.Episode.uploader_face,
            tag = "\n    ".join([f"<tag>{tag}</tag>" for tag in self.task_info.Episode.tags]),
            thumb = self.task_info.Episode.cover,
            bvid = self.task_info.Episode.bvid
        )
    
    def _generate_tvshow(self, genres: List[str]):
        premiered = Time.from_timestamp(self.task_info.Episode.premiered)

        return tvshow_base.format(
            title = self.task_info.Episode.season_title,
            plot = self.task_info.Episode.description,
            premiered = premiered,
            year = premiered.year,
            director = self.task_info.Episode.uploader,
            genre = "\n    ".join([f"<genre>{genre}</genre>" for genre in genres]),
            country = "\n    ".join([f"<country>{area}</country>" for area in self.task_info.Episode.areas]),
            rating = self._get_rating(),
            status = self._get_status(),
            thumb = self.task_info.Episode.poster,
            season_id = self.task_info.Episode.season_id
        )
    
    def _generate_episode(self, genres: List[str]):
        premiered = Time.from_timestamp(self.task_info.Episode.pubtime)

        return episode_base.format(
            title = self.task_info.Episode.episode_title,
            plot = self.task_info.Episode.episode_plot,
            runtime = math.ceil(self.task_info.Episode.duration / 60),
            premiered = premiered,
            year = premiered.year,
            episode = self.task_info.Episode.episode_number,
            director = self.task_info.Episode.uploader,
            genre = "\n    ".join([f"<genre>{genre}</genre>" for genre in genres]),
            country = "\n    ".join([f"<country>{area}</country>" for area in self.task_info.Episode.areas]),
            thumb = self.task_info.Episode.cover,
            ep_id = self.task_info.Episode.ep_id
        )
    
    def _is_tvshow_exists(self):
        path = Path(self.task_info.File.download_path, self.task_info.File.folder, "tvshow.nfo")

        return path.exists()
    
    def _get_rating(self):
        # 获取评分信息
        if self.task_info.Episode.rating:
            rating = """\
                <ratings>
                    <rating default="true" max="10" name="Bilibili">
                        <value>{rating}</value>
                        <votes>{votes}</votes>
                    </rating>
                </ratings>
                <rating>{rating}</rating>
                """.format(rating = self.task_info.Episode.rating, votes = self.task_info.Episode.rating_votes)
            
            return self._dedent(rating)
        
        return ""
    
    def _get_status(self):
        # 获取完结状态
        if self.task_info.Episode.new_ep_status:
            return "<status>Ongoing</status>"
        else:
            return "<status>Ended</status>"
    
    def _dedent(self, text: str):
        lines = textwrap.dedent(text).splitlines()

        for index, line in enumerate(lines):
            if index != 0:
                lines[index] = "    " + line

        return "\n".join(lines)
        
