import os
import textwrap

from utils.config import Config

from utils.common.model.task_info import DownloadTaskInfo
from utils.common.enums import TemplateType
from utils.common.datetime_util import DateTime

class Utils:
    @staticmethod
    def indent(text: str, prefix: str):
        return textwrap.indent(textwrap.dedent(text), prefix)
    
    @staticmethod
    def get_root_path(task_info: DownloadTaskInfo, root: bool = False):
        if task_info.template_type == TemplateType.Bangumi_strict.value or root:
            root_dir = task_info.download_path.removeprefix(task_info.download_base_path).split(os.sep)[1]

            return os.path.join(task_info.download_base_path, root_dir)
        else:
            return task_info.download_path
        
    @staticmethod
    def get_dateadded(timestamp: int):
        option = Config.Temp.scrape_option.get("video")

        if option.get("add_date") == 0:
            if option.get("add_date_source") == 0:
                date = DateTime.time_str("%Y-%m-%d %H:%M:%S")
            else:
                date = DateTime.time_str_from_timestamp(timestamp, "%Y-%m-%d %H:%M:%S")

            return """<dateadded>{date}</dateadded>""".format(date = date)
        else:
            return ""