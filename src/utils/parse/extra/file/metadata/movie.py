import math
import textwrap

from utils.common.model.task_info import DownloadTaskInfo

from utils.parse.extra.file.metadata.utils import Utils

class MovieMetaDataParser:
    def __init__(self, task_info: DownloadTaskInfo):
        self.data = {
            "title": task_info.series_title,
            "year": task_info.bangumi_pubdate[:4],
            "ratings": self.get_ratings(task_info.rating, task_info.rating_count),
            "genres": self.get_genres(task_info.bangumi_tags),
            "description": task_info.description,
            "runtime": math.floor(task_info.duration / 60),
            "pubdate": task_info.bangumi_pubdate,
            "poster_url": task_info.poster_url,
            "countrys": self.get_countries(task_info.areas),
            "actors": self.get_actors(task_info.actors),
            "dateadded": Utils.get_dateadded(task_info.pubtimestamp)
        }

    def get_nfo_contents(self):
        return textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <movie>
                <title>{title}</title>
                <year>{year}</year>
                {ratings}
                {genres}
                <plot>{description}</plot>
                <outline>{description}</outline>
                <runtime>{runtime}</runtime>
                <premiered>{pubdate}</premiered>
                <thumb aspect="poster">{poster_url}</thumb>
                {countrys}
                {actors}
                {dateadded}
            </movie>""".format(**self.data)).replace("\n\n", "\n")
    
    def get_genres(self, tags: list[str]):
        genres = []

        for tag in tags:
            genre_element = """\
                <genre>{tag}</genre>""".format(tag = tag)

            genres.append(Utils.indent(genre_element, "                "))

        return "\n".join(genres).removeprefix("                ")
    
    def get_ratings(self, rating: float, votes: int):
        ratings_element = """\
            <ratings>
                <rating default="true" max="10" name="Bilibili">
                    <value>{rating}</value>
                    <votes>{votes}</votes>
                </rating>
            </ratings>""".format(rating = rating, votes = votes)

        return Utils.indent(ratings_element, "                ").removeprefix("                ")
    
    def get_actors(self, actors_list: str):
        actors = []

        if not actors_list:
            return ""
        else:
            split_chars = ["、", " / ", " "]

            for char in split_chars:
                if char in actors_list:
                    actors_list = actors_list.replace(char, "\n")
                    break

        for entry in actors_list.split("\n"):
            actor_element = """\
                <actor>
                    <name>{name}</name>
                </actor>""".format(name = entry)

            actors.append(Utils.indent(actor_element, "                "))

        return "\n".join(actors).removeprefix("                ")

    def get_countries(self, areas_list: list[str]):
        countrys = []

        for area in areas_list:
            country_element = """\
                <country>{area}</country>""".format(area = area["name"])

            countrys.append(Utils.indent(country_element, "                "))

        return "\n".join(countrys).removeprefix("                ")
