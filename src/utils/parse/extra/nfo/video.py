from utils.common.model.download_info import DownloadTaskInfo

from utils.parse.video import VideoParser
from utils.parse.extra.parser import Parser
from utils.parse.extra.file.metadata.video import VideoMetadataFile

class VideoNFOParser(Parser):
    def __init__(self, task_info: DownloadTaskInfo):
        Parser.__init__(self)

        self.task_info = task_info

    def download_video_nfo(self):
        self.get_video_extra_info()

        file = VideoMetadataFile(self.task_info)
        contents = file.get_nfo_contents()

        self.save_file(f"{self.task_info.file_name}.nfo", contents, "w")

    def get_video_extra_info(self):
        info = VideoParser.get_video_extra_info(self.task_info.bvid)

        self.task_info.up_face_url = info.get("up_face")
        self.task_info.description = info.get("description")
        self.task_info.video_tags = VideoParser.get_video_tags(self.task_info.bvid)
