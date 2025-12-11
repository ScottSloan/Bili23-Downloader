import math
import textwrap

from utils.common.model.download_info import DownloadTaskInfo
from utils.common.datetime_util import DateTime

from utils.parse.extra.file.metadata.utils import Utils

class VideoMetadataFile:
    def __init__(self, task_info: DownloadTaskInfo):
        self.data = {
            "title": task_info.title,
            "description": task_info.description,
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
            "tags": self.get_tags(task_info.video_tags),
            "dateadded": Utils.get_dateadded(task_info.pubtimestamp)
        }

    def get_nfo_contents(self):
        return textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
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
                {dateadded}>
            </movie>""".format(**self.data)).replace("\n\n", "\n")
    
    def get_tags(self, tags: list[str]):
        tags_elements = []

        for tag in tags:
            tag_element = """\
                <tag>{tag}</tag>""".format(tag = tag)

            tags_elements.append(Utils.indent(tag_element, "                "))

        return "\n".join(tags_elements).removeprefix("                ")
    