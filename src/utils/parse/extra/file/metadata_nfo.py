import math
import textwrap

from utils.config import Config

from utils.common.model.task_info import DownloadTaskInfo
from utils.common.datetime_util import DateTime
from utils.common.enums import ParseType

from utils.module.pic.cover import Cover

class MetadataNFOFile:
    class Video:
        def __init__(self, task_info: DownloadTaskInfo):
            self.data = {
                "title": task_info.title,
                "description": task_info.description.replace("\n", "&#10;"),
                "runtime": math.floor(task_info.duration / 60),
                "pubtime": DateTime.from_timestamp(task_info.pubtimestamp),
                "year": DateTime.from_timestamp(task_info.pubtimestamp),
                "up_name": task_info.up_name,
                "up_uid": task_info.up_uid,
                "up_face": task_info.up_face_url,
                "cover": task_info.cover_url,
                "cid": task_info.cid,
                "zone": task_info.zone,
                "subzone": task_info.subzone,
                "tags": self.get_tags(task_info.video_tags)
            }

        def get_contents(self):
            return textwrap.dedent("""\
                <?xml version="1.0" encoding="UTF-8"?>
                <movie>
                    <title>{title}</title>
                    <plot>{description}</plot>
                    <runtime>{runtime}</runtime>
                    <year>{year:%Y}</year>
                    <studio>Bilibili</studio>
                    <actor>
                        <name>{up_name}</name>
                        <role>UP主</role>
                        <profile>https://space.bilibili.com/{up_uid}</profile>
                        <thumb>{up_face}</thumb>
                    </actor>
                    <premiered>{pubtime:%Y-%m-%d}</premiered>
                    <thumb>{cover}</thumb>
                    <uniqueid type="cid">{cid}</uniqueid>
                    <genre>{zone}</genre>
                    <genre>{subzone}</genre>
                    {tags}
                </movie>""".format(**self.data))

        def get_tags(self, tags: list[str]):
            tags_elements = []

            for tag in tags:
                tag_element = """\
                    <tag>{tag}</tag>"""
                
                tags_elements.append(tag_element.format(tag = tag))

            return "\n".join(tags_elements).removeprefix("                    ")

    class BangumiTVShow:
        def __init__(self, task_info: DownloadTaskInfo):
            self.data = {
                "series_title_original": task_info.series_title_original,
                "description": task_info.description.replace("\n", "&#10;"),
                "year": task_info.bangumi_pubdate[:4],
                "pubdate": task_info.bangumi_pubdate,
                "genres": self.get_genres(task_info.bangumi_tags),
                "actors": self.get_actors(task_info.actors),
                "season_id": task_info.season_id,
                "season_num": task_info.season_num,
                "area": task_info.area,
                "poster_url": f"poster{MetadataNFOFile.get_cover_type()}"
            }

        def get_contents(self):
            return textwrap.dedent("""\
                <?xml version="1.0" encoding="UTF-8"?>
                <tvshow>
                    <title>{series_title_original}</title>
                    <plot>{description}</plot>
                    <year>{year}</year>
                    <premiered>{pubdate}</premiered>
                    {genres}
                    <studio>Bilibili</studio>
                    {actors}
                    <season>{season_num}</season>
                    <country>{area}</country>
                    <poster>{poster_url}</poster>
                    <uniqueid type="season">{season_id}</uniqueid>
                </tvshow>""".format(**self.data))
        
        def get_genres(self, tags: list[str]):
            genres = []

            for tag in tags:
                genre_element = """\
                    <genre>{tag}</genre>"""
                
                genres.append(genre_element.format(tag = tag))

            return "\n".join(genres).removeprefix("                    ")
        
        def get_actors(self, actors_list: str):
           actors = []

           for index, entry in enumerate(actors_list.split("\\n")):
                role_name = entry.split("：")

                actor_element = """\
                    <actor>
                        <name>{name}</name>
                        <role>{role}</role>
                        <order>{index}</order>
                    </actor>""".format(name = role_name[1], role = role_name[0], index = index + 1)

                actors.append(actor_element)

           return "\n".join(actors).removeprefix("                    ")

    class BangumiSeason:
        def __init__(self, task_info: DownloadTaskInfo):
            self.data = {
                "title": task_info.series_title_original,
                "description": task_info.description.replace("\n", "&#10;"),
                "year": task_info.bangumi_pubdate[:4],
                "pubdate": task_info.bangumi_pubdate,
                "poster_url": task_info.poster_url
            }

        def get_contents(self):
            return textwrap.dedent("""\
                <?xml version="1.0" encoding="UTF-8"?>
                <season>
                    <title>{title}</title>
                    <showtitle>{title}</showtitle>
                    <plot>{description}</plot>
                    <year>{year}</year>
                    <thumb aspect="poster">{poster_url}</thumb>
                    <premiered>{pubdate}</premiered>
                </season>""".format(**self.data))

    class EpisodeDetails:
        def __init__(self, task_info: DownloadTaskInfo):
            self.data = {
                "title": task_info.title,
                "season_num": task_info.season_num,
                "episode_num": task_info.episode_num,
                "aired": DateTime.time_str_from_timestamp(task_info.pubtimestamp, "%Y-%m-%d"),
                "thumb": self.get_thumb(task_info),
                "cid": task_info.cid,
                "ep_id": task_info.ep_id
            }

        def get_contents(self):
            return textwrap.dedent("""\
                <?xml version="1.0" encoding="UTF-8"?>
                <episodedetails>
                    <title>{title}</title>
                    <season>{season_num}</season>
                    <episode>{episode_num}</episode>
                    <runtime>0</runtime>
                    <aired>{aired}</aired>
                    <art>
                        <thumb>{thumb}</thumb>
                    </art>
                    <uniqueid type="cid">{cid}</uniqueid>
                    <uniqueid type="ep_id">{ep_id}</uniqueid>
                </episodedetails>""".format(**self.data))
        
        def get_thumb(self, task_info: DownloadTaskInfo):
            if task_info.extra_option.get("download_cover_file"):
                if task_info.episode_tag:
                    return f"{task_info.episode_tag}{MetadataNFOFile.get_cover_type()}"
                else:
                    return f"{task_info.file_name}{MetadataNFOFile.get_cover_type()}"
            else:
                return task_info.cover_url

    def __init__(self, task_info: DownloadTaskInfo):
        self.task_info = task_info

    def get_contents(self):
        match ParseType(self.task_info.parse_type):
            case ParseType.Video:
                file = self.Video(self.task_info)

            case ParseType.Bangumi:
                file = self.EpisodeDetails(self.task_info)
                
        return file.get_contents()
    
    def get_bangumi_season_contents(self):
        file = self.BangumiTVShow(self.task_info)

        return file.get_contents()
    
    @staticmethod
    def get_cover_type():
        return Cover.get_cover_type(Config.Basic.cover_file_type)