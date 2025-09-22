import os
import textwrap

from utils.common.model.task_info import DownloadTaskInfo
from utils.common.enums import TemplateType

class Utils:
    @staticmethod
    def indent(text: str, prefix: str):
        return textwrap.indent(textwrap.dedent(text), prefix)
    
    def get_root_path(task_info: DownloadTaskInfo, root: bool = False):
        if task_info.template_type == TemplateType.Bangumi_strict.value or root:
            root_dir = task_info.download_path.removeprefix(task_info.download_base_path).split(os.sep)[1]

            return os.path.join(task_info.download_base_path, root_dir)
        else:
            return task_info.download_path