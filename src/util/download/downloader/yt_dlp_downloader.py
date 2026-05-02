from yt_dlp import YoutubeDL
import os
import threading


class YTDLPDownloader:
    """
    通用下载引擎（B站 / YouTube / 全网站）
    """

    def __init__(self):
        self.progress_callback = None
        self.finish_callback = None
        self.error_callback = None
        self._stop_event = threading.Event()
        self._ydl = None
        self._is_downloading = False
        self._task_info = None

    def set_callbacks(self, progress=None, finish=None, error=None):
        self.progress_callback = progress
        self.finish_callback = finish
        self.error_callback = error

    def set_task_info(self, task_info):
        """设置任务信息，用于获取 cookie_file 等配置"""
        self._task_info = task_info

    def start(self):
        """开始下载"""
        if not self._task_info:
            return

        cookie_file = None
        if self._task_info.cookie_file and os.path.exists(self._task_info.cookie_file):
            cookie_file = self._task_info.cookie_file

        self.download(
            url=self._task_info.Episode.url,
            output_dir=self._task_info.File.download_path,
            cookie_file=cookie_file
        )

    def pause(self):
        """暂停下载"""
        self._stop_event.set()
        self._is_downloading = False

    def resume(self):
        """继续下载"""
        self._stop_event.clear()
        self.start()

    def retry(self):
        """重试下载"""
        self._stop_event.clear()
        self.start()

    def start_merge(self):
        """开始合并"""
        pass

    def download(self, url, output_dir="downloads", cookie_file=None):
        """
        主下载入口
        """

        ydl_opts = {
            # 画质策略（通用）
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",

            # 输出路径
            "outtmpl": f"{output_dir}/%(title)s.%(ext)s",

            # 进度回调
            "progress_hooks": [self._hook],

            # 稳定性
            "retries": 3,
            "fragment_retries": 3,
            "concurrent_fragment_downloads": 4,

            # 日志控制
            "quiet": True,
            "no_warnings": True,
        }

        # cookie（B站/YouTube premium）
        if cookie_file:
            ydl_opts["cookiefile"] = cookie_file

        self._is_downloading = True
        self._stop_event.clear()

        try:
            with YoutubeDL(ydl_opts) as ydl:
                self._ydl = ydl
                ydl.download([url])

            if self.finish_callback and not self._stop_event.is_set():
                self.finish_callback(url)

        except Exception as e:
            if self._stop_event.is_set():
                pass  # 用户主动停止，不报错
            elif self.error_callback:
                self.error_callback(str(e))
            else:
                print("[ERROR]", e)
        finally:
            self._is_downloading = False
            self._ydl = None

    def _hook(self, d):
        """
        yt-dlp 进度回调
        """
        if self._stop_event.is_set():
            raise Exception("Download stopped by user")

        if d["status"] == "downloading":
            if self.progress_callback:
                self.progress_callback({
                    "status": "downloading",
                    "filename": d.get("filename"),
                    "percent": d.get("_percent_str", "").strip(),
                    "speed": d.get("_speed_str", "").strip(),
                    "eta": d.get("_eta_str", "").strip(),
                })

        elif d["status"] == "finished":
            if self.progress_callback:
                self.progress_callback({
                    "status": "finished",
                    "filename": d.get("filename"),
                })
