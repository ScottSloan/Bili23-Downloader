import textwrap

from utils.common.model.task_info import DownloadTaskInfo

class MetadataNFOFile:
    class Video:
        def __init__(self, task_info: DownloadTaskInfo):
            self.data = {
                "title": task_info.title,
                "description": "暂时空缺",
                "duration": task_info.duration,
                "pubtime": "暂时空缺",
                "up_name": task_info.up_name,
                "zone": task_info.zone,
                "subzone": task_info.subzone,
            }

        def get_contents(self):
            return textwrap.dedent("""\
                <?xml version="1.0" encoding="UTF-8"?>
                <movie>
                    <title>{title}</title>
                    <plot>{description}</plot>
                    <runtime>{duration}</runtime>
                    <year>2023</year>
                    <studio>Bilibili</studio>
                    <actor>
                        <name>{up_name}</name>
                        <role>Creator</role>
                    </actor>
                    <premiered>{pubtime}</premiered>
                    <genre>{zone}</genre>
                    <genre>{subzone}</genre>
                </movie>\
                """.format(**self.data))

    def __init__(self, task_info: DownloadTaskInfo):
        self.task_info = task_info

    def get_contents(self):
        return self.Video(self.task_info).get_contents()
    