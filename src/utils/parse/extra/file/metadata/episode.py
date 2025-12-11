import math
import textwrap

from utils.common.model.download_info import DownloadTaskInfo
from utils.common.datetime_util import DateTime

from utils.parse.extra.file.metadata.utils import Utils

class TVShowMetaDataParser:
    def __init__(self, task_info: DownloadTaskInfo):
        self.data = {
            "series_title_original": task_info.series_title_original,
            "description": task_info.description,
            "year": task_info.bangumi_pubdate[:4],
            "pubdate": task_info.bangumi_pubdate,
            "ratings": self.get_ratings(task_info.rating, task_info.rating_count),
            "genres": self.get_genres(task_info.bangumi_tags),
            "actors": self.get_actors(task_info.actors),
            "season_id": task_info.season_id,
            "season_num": task_info.season_num,
            "area": self.get_countries(task_info.areas),
            "poster_url": task_info.poster_url,
            "named_seasons": self.get_named_season(task_info.seasons, task_info.series_title_original),
            "dateadded": Utils.get_dateadded(task_info.pubtimestamp)
        }

    def get_nfo_contents(self):
        return textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <tvshow>
                <title>{series_title_original}</title>
                <plot>{description}</plot>
                <year>{year}</year>
                <premiered>{pubdate}</premiered>
                {ratings}
                {genres}
                <studio>Bilibili</studio>
                {actors}
                <season>{season_num}</season>
                <country>{area}</country>
                <thumb aspect="poster">{poster_url}</thumb>
                {named_seasons}
                <uniqueid type="season">{season_id}</uniqueid>
                {dateadded}
            </tvshow>""".format(**self.data)).replace("\n\n", "\n")
    
    def get_ratings(self, rating: float, votes: int):
        ratings_element = """\
            <ratings>
                <rating default="true" max="10" name="Bilibili">
                    <value>{rating}</value>
                    <votes>{votes}</votes>
                </rating>
            </ratings>""".format(rating = rating, votes = votes)

        return Utils.indent(ratings_element, "                ").removeprefix("                ")

    def get_genres(self, tags: list[str]):
        genres = []

        for tag in tags:
            genre_element = """\
                <genre>{tag}</genre>""".format(tag = tag)

            genres.append(Utils.indent(genre_element, "                "))

        return "\n".join(genres).removeprefix("                ")
    
    def get_actors(self, actors_list: str):
        actors = []

        if not actors_list:
            return ""

        for entry in actors_list.split("\n"):
            entry = entry.strip()

            if not entry or entry.endswith("："):
                continue

            parts = entry.split("：", 1)

            if len(parts) == 1:
                actor_element = """
                    <actor>
                        <name>{}</name>
                    </actor>""".format(parts[0].strip())

            elif len(parts) == 2:
                actor_element = """
                    <actor>
                        <name>{}</name>
                        <role>{}</role>
                    </actor>""".format(parts[1].strip(), parts[0].strip())

            actors.append(Utils.indent(actor_element, "                "))

        return "".join(actors).removeprefix("                ")

    def get_named_season(self, seasons_data: list[dict], series_title_original: str):
        seasons = []

        for index, entry in enumerate(seasons_data):
            season_element = """\
                <namedseason number="{season_num}">{season_title}</namedseason>""".format(season_num = index + 1, season_title = f"{series_title_original} {entry['season_title']}")

            seasons.append(Utils.indent(season_element, "                "))

        return "\n".join(seasons).removeprefix("                ")

    def get_countries(self, areas_list: list[str]):
        countrys = []

        for area in areas_list:
            country_element = """\
                <country>{area}</country>""".format(area = area["name"])

            countrys.append(Utils.indent(country_element, "                "))

        return "\n".join(countrys).removeprefix("                ")

class SeasonMetadataParser:
    def __init__(self, task_info: DownloadTaskInfo):
        self.data = {
            "season_num": task_info.season_num,
            "series_title": task_info.series_title,
            "series_title_original": task_info.series_title_original,
            "description": task_info.description,
            "year": task_info.bangumi_pubdate[:4],
            "pubdate": task_info.bangumi_pubdate,
            "poster_url": task_info.poster_url,
            "season_id": task_info.season_id
        }

    def get_nfo_contents(self):
        return textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <season>
                <seasonnumber>{season_num}</seasonnumber>
                <title>{series_title}</title>
                <showtitle>{series_title_original}</showtitle>
                <plot>{description}</plot>
                <year>{year}</year>
                <thumb aspect="poster">{poster_url}</thumb>
                <premiered>{pubdate}</premiered>
                <uniqueid type="season_id">{season_id}</uniqueid>
            </season>""".format(**self.data)).replace("\n\n", "\n")
    
class EpisodeMetadataParser:
    def __init__(self, task_info: DownloadTaskInfo):
        self.data = {
            "title": task_info.title,
            "series_title_original": task_info.series_title_original,
            "season_num": task_info.season_num,
            "episode_num": task_info.episode_num,
            "runtime": math.floor(task_info.duration / 60),
            "aired": DateTime.time_str_from_timestamp(task_info.pubtimestamp, "%Y-%m-%d"),
            "thumb": task_info.cover_url,
            "cid": task_info.cid,
            "ep_id": task_info.ep_id,
            "dateadded": Utils.get_dateadded(task_info.pubtimestamp)
        }

    def get_nfo_contents(self):
        return textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <episodedetails>
                <title>{title}</title>
                <showtitle>{series_title_original}</showtitle>
                <season>{season_num}</season>
                <episode>{episode_num}</episode>
                <runtime>{runtime}</runtime>
                <premiered>{aired}</premiered>
                <aired>{aired}</aired>
                <thumb>{thumb}</thumb>
                <uniqueid type="cid">{cid}</uniqueid>
                <uniqueid type="ep_id">{ep_id}</uniqueid>
                {dateadded}
            </episodedetails>""".format(**self.data)).replace("\n\n", "\n")
