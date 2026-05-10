from util.download.downloader.yt_dlp_downloader import YTDLPDownloader
import os
from pathlib import Path


class YTDLPAdapter:
    """
    兼容 Bili23 TaskManager 的适配层
    """

    def __init__(self, task_manager=None):
        self.downloader = YTDLPDownloader()
        self.task_manager = task_manager
        self.current_task = None

    def set_callbacks(self, progress, finish, error):
        self.downloader.set_callbacks(progress, finish, error)

    def start_task(self, task_info):
        """
        启动任务
        """

        self.current_task = task_info

        cookie_file = self._resolve_cookie_file(task_info)

        output_path = task_info.File.download_path
        if task_info.File.folder and task_info.File.folder != ".":
            output_path = str(Path(task_info.File.download_path) / task_info.File.folder)
            os.makedirs(output_path, exist_ok=True)

        self.downloader.download(
            url=task_info.Episode.url,
            output_dir=output_path,
            cookie_file=cookie_file
        )

    def _resolve_cookie_file(self, task_info):
        """
        解析 cookie 文件路径
        仅使用用户在解析阶段手动选择的 cookie_file
        如果用户没有选择，则不使用任何 cookies
        """
        if task_info.cookie_file and os.path.exists(task_info.cookie_file):
            return task_info.cookie_file

        return None

    def cancel(self):
        """
        yt-dlp 本身无法优雅 pause，只能终止进程级逻辑（可扩展）
        """
        pass
