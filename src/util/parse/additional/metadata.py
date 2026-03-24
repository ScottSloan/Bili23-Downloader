from util.parse.additional.base import AdditionalParserBase
from util.download.task.info import TaskInfo
from util.common.config import config


class MetadataParser(AdditionalParserBase):
    def __init__(self, task_info: TaskInfo):
        super().__init__(task_info)

    def parse(self):
        metadata = self._get_metadata()

        self._write_string(metadata, suffix = "txt", qualifier = ["元数据"])

    def _get_metadata(self):
        metadata_dict = {
            "标题": self.task_info.title,
            "文件名": self.task_info.file_name,
            "封面链接": self.task_info.cover_url,
            "分P标签": self.task_info.episode_tag,
            "总文件大小（字节）": self.task_info.total_file_size,
            "输出格式": self.task_info.output_type,
        }

        metadata_lines = [f"{key}: {value}" for key, value in metadata_dict.items()]

        return "\n".join(metadata_lines)