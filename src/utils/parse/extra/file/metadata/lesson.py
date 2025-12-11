import math
import textwrap

from utils.common.model.task_info import DownloadTaskInfo
from utils.common.datetime_util import DateTime

from utils.parse.extra.file.metadata.utils import Utils

class TVShowMetaDataParser:
    def __init__(self, task_info: DownloadTaskInfo):
        self.data = {
            "series_title": task_info.series_title,
            "description": task_info.description,
            "year": task_info.bangumi_pubdate[:4],
            "pubdate": task_info.bangumi_pubdate,
            "up_name": task_info.up_name,
            "poster_url": task_info.poster_url,
            "season_id": task_info.season_id,
            "dateadded": Utils.get_dateadded(task_info.pubtimestamp)
        }

    def get_nfo_contents(self):
        return textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <tvshow>
                <title>{series_title}</title>
                <plot>{description}</plot>
                <year>{year}</year>
                <premiered>{pubdate}</premiered>
                <studio>Bilibili</studio>
                <actor>
                    <name>{up_name}</name>
                    <role>发布者</role>
                </actor>
                <season>1</season>
                <thumb aspect="poster">{poster_url}</thumb>
                <namedseason number="1">{series_title}</namedseason>
                <uniqueid type="season">{season_id}</uniqueid>
                {dateadded}
            </tvshow>""".format(**self.data)).replace("\n\n", "\n")
    
class EpisodeMetaDataParser:
    def __init__(self, task_info: DownloadTaskInfo):
        self.data = {
            "title": task_info.title,
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
                <showtitle>{title}</showtitle>
                <runtime>{runtime}</runtime>
                <premiered>{aired}</premiered>
                <aired>{aired}</aired>
                <thumb>{thumb}</thumb>
                <uniqueid type="cid">{cid}</uniqueid>
                <uniqueid type="ep_id">{ep_id}</uniqueid>
                {dateadded}
            </episodedetails>""".format(**self.data)).replace("\n\n", "\n")
        