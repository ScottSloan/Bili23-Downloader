from PySide6.QtCore import QObject

from util.common import signal_bus, config, Translator, safe_remove, safe_rename, get_timestamp
from util.common.enum import DownloadStatus, DownloadType
from util.download.task.manager import task_manager
from util.ffmpeg import FFmpegCommand, FFmpegRunner
from util.download.task.info import TaskInfo

from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class Merger(QObject):
    def __init__(self, task_info: TaskInfo, parent=None):
        super().__init__(parent)
        self.task_info = task_info
        self._has_error = False
        self._ffmpeg_runner = None

    def start(self):
        if self.task_info.Download.merge_video_audio:
            # 现代 dash 视频合并
            self.merge_video_audio()

        elif self.task_info.Download.video_parts_count > 0:
            # 旧版 flv 分片下载合并
            self.merge_video_parts()

        elif config.get(config.m4a_to_mp3) and self.task_info.File.audio_file_ext == "m4a":
            self.m4a_to_mp3()

        else:
            self.rename_output_file()

    def merge_video_audio(self):
        cwd = self.get_cwd()
        v_exists = Path(cwd, self.temp_video_file_name).exists()
        a_exists = Path(cwd, self.temp_audio_file_name).exists()
        o_exists = Path(cwd, self.temp_output_file_name).exists()

        if v_exists and a_exists:
            merge_cmd = FFmpegCommand.merge_video_audio(
                video_path = self.temp_video_file_name,
                audio_path = self.temp_audio_file_name,
                output_path = self.temp_output_file_name,
                cover_path = self.check_attach_cover()
            )

            self._run_merge_command(merge_cmd, cwd)

        elif o_exists and not v_exists and not a_exists:
            self.on_merge_completed(0, "", "")

        else:
            self.set_error_message(
                Translator.ERROR_MESSAGES("DOWNLOAD_FAILED"),
                Translator.ERROR_MESSAGES("FILE_NOT_FOUND_DETAIL")
            )

    def merge_video_parts(self):
        cwd = self.get_cwd()

        lists_path = self.create_lists_file(self.task_info.Download.video_parts_count)

        self.add_file(lists_path)

        merge_cmd = FFmpegCommand.merge_video_parts(
            lists_path = lists_path,
            output_path = self.temp_output_file_name,
            cover_path = self.check_attach_cover()
        )

        self._run_merge_command(merge_cmd, cwd)

    def _run_merge_command(self, command: FFmpegCommand, cwd: Path):
        self._ffmpeg_runner = FFmpegRunner.from_command(command, parent = self)
        self._ffmpeg_runner.set_cwd(cwd)
        self._ffmpeg_runner.finished_sig.connect(self.on_merge_completed)
        self._ffmpeg_runner.error_sig.connect(self.on_merge_error)
        self._ffmpeg_runner.start()

    def rename_output_file(self):
        if self._has_error:
            return

        has_video = self.task_info.Download.type & DownloadType.VIDEO != 0
        has_audio = self.task_info.Download.type & DownloadType.AUDIO != 0
        cwd = self.get_cwd()

        try:
            if has_video and has_audio:
                self.keep_original_files()
                if self._has_error: return
                self.add_file(self.final_video_file_name, self.final_audio_file_name, clear = True)

            elif has_video and not has_audio:
                safe_rename(cwd, self.temp_video_file_name, self.final_mp4_video_file_name)
                self.add_file(self.final_mp4_video_file_name, clear = True)

            elif has_audio and not has_video:
                safe_rename(cwd, self.temp_audio_file_name, self.final_audio_file_name)
                self.add_file(self.final_audio_file_name, clear = True)

            self.mark_as_completed()

        except Exception as e:
            self.set_error_message(Translator.ERROR_MESSAGES("RENAME_FAILED"), str(e))

    def on_merge_completed(self, return_code: int, stdout: str, stderr: str):
        if getattr(self, "_has_error", False):
            return

        try:
            cwd = self.get_cwd()
            
            safe_rename(cwd, self.temp_output_file_name, self.final_output_file_name)

            if not self.task_info.Download.keep_original_files:
                safe_remove(cwd, *self.task_info.File.relative_files)
            else:
                self.keep_original_files()
                if self._has_error: return

            self.add_file(self.final_output_file_name, clear = True)
            self.mark_as_completed()

        except Exception as e:
            self.set_error_message(Translator.ERROR_MESSAGES("RENAME_FAILED"), str(e))

    def on_convert_completed(self, return_code: int, stdout: str, stderr: str):
        if getattr(self, "_has_error", False):
            return

        try:
            safe_remove(self.get_cwd(), getattr(self, "_temp_m4a_audio_name", self.temp_audio_file_name))
            self.rename_output_file()
        except Exception as e:
            self.set_error_message(Translator.ERROR_MESSAGES("RENAME_FAILED"), str(e))

    def mark_as_completed(self):
        if getattr(self, "_has_error", False):
            return

        self.task_info.Download.status = DownloadStatus.COMPLETED
        self.task_info.Basic.completed_time = get_timestamp()

        task_manager.mark_as_completed(self.task_info)

        signal_bus.download.start_next_task.emit()
        signal_bus.download.add_to_completed_list.emit([self.task_info])
        signal_bus.download.remove_from_downloading_list.emit(self.task_info)

    def keep_original_files(self):
        try:
            cwd = self.get_cwd()
            safe_rename(cwd, self.temp_video_file_name, self.final_video_file_name)
            safe_rename(cwd, self.temp_audio_file_name, self.final_audio_file_name)
        except Exception as e:
            self.set_error_message(Translator.ERROR_MESSAGES("RENAME_FAILED"), str(e))

    def on_merge_error(self, error: Exception, stdout: str, stderr: str):
        error_map = {
            "No space left on device": "INSUFFICIENT_SPACE",
            "Permission denied": "PERMISSION_DENIED",
            "Invalid data found when processing input": "CORRUPTED_FILE",
            "No such file or directory": "FILE_NOT_FOUND",
            "Could not open file": "COULD_NOT_OPEN",
            "Device or resource busy": "FILE_IS_BUSY",
            "Could not create output file": "CANNOT_CREATE"
        }

        error_message = None
        for key, message in error_map.items():
            if key in str(stderr):
                error_message = Translator.ERROR_MESSAGES(message)
                break

        if error_message is None:
            error_message = str(error)

        self.set_error_message(Translator.ERROR_MESSAGES("DOWNLOAD_FAILED"), f"{error_message}\n\n{stderr}")

    def set_error_message(self, short_message: str, description: str):
        self._has_error = True
        self.task_info.Download.status = DownloadStatus.FFMPEG_FAILED

        signal_bus.download.update_downloading_item.emit(self.task_info)
        signal_bus.toast.show_long_message.emit(short_message, description)

        logger.error(str(short_message) + ": \n" + description)

    def get_cwd(self):
        return Path(self.task_info.File.download_path, self.task_info.File.folder)

    def add_file(self, *args: str, clear=False):
        if clear:
            self.task_info.File.relative_files.clear()

        for file_name in args:
            if file_name not in self.task_info.File.relative_files:
                self.task_info.File.relative_files.append(file_name)

        task_manager.update(self.task_info)

    def m4a_to_mp3(self):
        cwd = self.get_cwd()

        if Path(cwd, self.temp_audio_file_name).exists():
            self.task_info.Download.status = DownloadStatus.CONVERTING
            signal_bus.download.update_downloading_item.emit(self.task_info)

            self._temp_m4a_audio_name = self.temp_audio_file_name
            self.task_info.File.audio_file_ext = "mp3"

            convert_cmd = FFmpegCommand.convert_m4a_to_mp3(
                input_path=self._temp_m4a_audio_name,
                output_path=self.temp_audio_file_name
            )

            self._ffmpeg_runner = FFmpegRunner.from_command(convert_cmd, parent=self)
            self._ffmpeg_runner.set_cwd(cwd)
            self._ffmpeg_runner.finished_sig.connect(self.on_convert_completed)
            self._ffmpeg_runner.error_sig.connect(self.on_merge_error)
            self._ffmpeg_runner.start()
        else:
            self.set_error_message(
                Translator.ERROR_MESSAGES("DOWNLOAD_FAILED"),
                Translator.ERROR_MESSAGES("M4A_NOT_FOUND")
            )

    def check_attach_cover(self):
        if config.get(config.attach_cover):
            cover_path = Path(self.get_cwd(), self.cover_file_name)
            if cover_path.exists():
                return self.cover_file_name
            else:
                logger.warning(f"封面文件 {cover_path} 不存在，无法嵌入封面")
        return None

    def create_lists_file(self, video_parts_count: int):
        cwd = self.get_cwd()
        lists_path = Path(cwd, f"lists_{self.task_info.Basic.task_id}.txt")

        with lists_path.open("w", encoding = "utf-8") as f:
            for i in range(video_parts_count):
                part_file_name = "video_{task_id}_{index}.{ext}".format(
                    task_id = self.task_info.Basic.task_id,
                    index = i,
                    ext = self.task_info.File.video_file_ext
                )

                f.write(f"file '{part_file_name}'\n")

        return lists_path.name

    @property
    def temp_video_file_name(self):
        return "video_{task_id}.{file_ext}".format(
            task_id = self.task_info.Basic.task_id,
            file_ext = self.task_info.File.video_file_ext
        )
    
    @property
    def temp_audio_file_name(self):
        return "audio_{task_id}.{file_ext}".format(
            task_id = self.task_info.Basic.task_id,
            file_ext = self.task_info.File.audio_file_ext
        )
    
    @property
    def temp_output_file_name(self):
        return "output_{task_id}.{file_ext}".format(
            task_id = self.task_info.Basic.task_id,
            file_ext = self.task_info.File.merge_file_ext
        )
    
    @property
    def final_output_file_name(self):
        return f"{self.task_info.File.name}.{self.task_info.File.merge_file_ext}"
    
    @property
    def final_video_file_name(self):
        return f"{self.task_info.File.name}.{self.task_info.File.video_file_ext}"

    @property
    def final_mp4_video_file_name(self):
        return f"{self.task_info.File.name}.mp4"

    @property
    def final_audio_file_name(self):
        return f"{self.task_info.File.name}.{self.task_info.File.audio_file_ext}"

    @property
    def cover_file_name(self):
        return f"{self.task_info.File.name}.{config.get(config.cover_type).value}"