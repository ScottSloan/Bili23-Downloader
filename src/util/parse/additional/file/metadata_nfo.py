from util.parse.episode.tree import Attribute
from util.format.time import Time

from ....download.task.info import TaskInfo

from pathlib import Path
from typing import List
import math

video_base = """<?xml version="1.0" encoding="UTF-8"?>
<movie>
    <title>{title}</title>
    <plot>{plot}</plot>
    <runtime>{runtime}</runtime>
    <premiered>{premiered:%Y-%m-%d}</premiered>
    <year>{year}</year>
    <director>{director}</director>
    {tag}
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
            director = self.task_info.Episode.uploader,
            tag = "\n    ".join([f"<tag>{tag}</tag>" for tag in self.task_info.Episode.tags])
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
            country = "\n    ".join([f"<country>{area}</country>" for area in self.task_info.Episode.areas])
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
            country = "\n    ".join([f"<country>{area}</country>" for area in self.task_info.Episode.areas])
        )
    
    def _is_tvshow_exists(self):
        path = Path(self.task_info.File.download_path, self.task_info.File.folder, "tvshow.nfo")

        return path.exists()
    