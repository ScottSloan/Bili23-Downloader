from PySide6.QtCore import QObject

from util.common.enum import DownloadStatus, DownloadType, CoverType
from util.download.task.manager import task_manager
from util.common.timestamp import get_timestamp
from util.common.signal_bus import signal_bus
from util.ffmpeg.command import FFmpegCommand
from util.common.translator import Translator
from util.download.task.info import TaskInfo
from util.ffmpeg.runner import FFmpegRunner
from util.common.io import Remover, Renamer
from util.common.config import config

from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class Merger(QObject):
    def __init__(self, task_info: TaskInfo, parent = None):
        super().__init__(parent)

        self.task_info = task_info

    def start(self):
        if self.task_info.Download.merge_video_audio:
            self.merge_video_audio()

        elif config.get(config.m4a_to_mp3) and self.task_info.File.audio_file_ext == "m4a":
            self.m4a_to_mp3()

        else:
            self.rename_output_file()

    def merge_video_audio(self):
        cwd = self.get_cwd()

        if Path(cwd, self.temp_video_file_name).exists() and Path(cwd, self.temp_audio_file_name).exists():
            # 只有临时视频和音频文件都存在时，才进行合并

            merge_cmd = FFmpegCommand.merge_video_audio(
                video_path = self.temp_video_file_name,
                audio_path = self.temp_audio_file_name,
                output_path = self.temp_output_file_name,
                cover_path = self.check_attach_cover()
            )

            (
                FFmpegRunner.from_command(merge_cmd)
                .set_cwd(cwd)
                .on_completed(self.on_merge_completed)
                .on_error(self.on_merge_error)
                .start()
            )

            self.add_file(
                self.temp_output_file_name
            )

        elif Path(cwd, self.temp_output_file_name).exists():
            # 如果是合并后的视频文件已经存在了，说明之前的合并过程已经完成了，直接跳过合并过程
            self.on_merge_completed(0, "", "")

        else:
            # 下载文件不存在，视为合并失败
            self.set_error_message(Translator.ERROR_MESSAGES("DOWNLOAD_FAILED"), Translator.ERROR_MESSAGES("FILE_NOT_FOUND"))

    def rename_output_file(self):
        has_video = self.task_info.Download.type & DownloadType.VIDEO != 0
        has_audio = self.task_info.Download.type & DownloadType.AUDIO != 0

        cwd = self.get_cwd()

        if has_video and has_audio:
            self.keep_original_files()

            self.add_file(
                self.final_video_file_name,
                self.final_audio_file_name,
                clear = True
            )

        elif has_video and not has_audio:
            (
                Renamer()
                .set_cwd(cwd)
                .set_on_error(self.on_rename_error)
                .add_file(self.temp_video_file_name, self.final_video_file_name)
                .execute()
            )

            self.add_file(
                self.final_video_file_name,
                clear = True
            )

        elif has_audio and not has_video:
            (
                Renamer()
                .set_cwd(cwd)
                .set_on_error(self.on_rename_error)
                .add_file(self.temp_audio_file_name, self.final_audio_file_name)
                .execute()
            )

            self.add_file(
                self.final_audio_file_name,
                clear = True
            )

        self.mark_as_completed()

    def on_merge_completed(self, return_code: int, stdout: str, stderr: str):
        def _post():
            cwd = self.get_cwd()
            
            if not self.task_info.Download.keep_original_files:
                (
                    Remover()
                    .set_cwd(cwd)
                    .add_file(self.temp_video_file_name)
                    .add_file(self.temp_audio_file_name)
                    .execute()
                )
            else:
                self.keep_original_files()

            # 不直接在 ffmpeg 输出阶段重命名文件，避免文件名带 '-' 导致 ffmpeg 解析为参数
            # 直接用系统底层提供的重命名方式，能有效避免上述问题
            (
                Renamer()
                .set_cwd(cwd)
                .set_on_error(self.on_rename_error)
                .add_file(self.temp_output_file_name, self.final_output_file_name)
                .execute()
            )

            self.add_file(
                self.final_output_file_name,
                clear = True
            )

        try:
            _post()

            self.mark_as_completed()

        except Exception as e:
            self.set_error_message(e, str(e))

    def on_convert_completed(self, return_code: int, stdout: str, stderr: str):
        (
            Remover()
            .set_cwd(self.get_cwd())
            .add_file(Path(self.temp_audio_file_name).with_suffix(".m4a"))
            .execute()
        )
        
        self.rename_output_file()

    def mark_as_completed(self):
        self.task_info.Download.status = DownloadStatus.COMPLETED
        self.task_info.Basic.completed_time = get_timestamp()

        task_manager.mark_as_completed(self.task_info)

        signal_bus.download.start_next_task.emit()
        signal_bus.download.add_to_completed_list.emit([self.task_info])
        signal_bus.download.remove_from_downloading_list.emit(self.task_info)

    def keep_original_files(self):
        (
            Renamer()
            .set_cwd(self.get_cwd())
            .set_on_error(self.on_rename_error)
            .add_file(self.temp_video_file_name, self.final_video_file_name)
            .add_file(self.temp_audio_file_name, self.final_audio_file_name)
            .execute()
        )

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

        self.set_error_message(Translator.ERROR_MESSAGES("DOWNLOAD_FAILED"), "{}\n\n{}".format(error_message, stderr))

    def on_rename_error(self, error: str, *args: str):
        self.set_error_message(Translator.ERROR_MESSAGES("RENAME_FAILED"), error)

    def set_error_message(self, short_message: str, description: str):
        self.task_info.Download.status = DownloadStatus.FFMPEG_FAILED

        signal_bus.download.update_downloading_item.emit(self.task_info)
        signal_bus.toast.show_long_message.emit(short_message, description)

        logger.error(str(short_message) + ": \n" + description)

    def get_cwd(self):
        return Path(self.task_info.File.download_path, self.task_info.File.folder)

    def add_file(self, *args: str, clear = False):
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

            convert_cmd = FFmpegCommand.convert_m4a_to_mp3(
                input_path = self.temp_audio_file_name,
                output_path = Path(self.temp_audio_file_name).with_suffix(".mp3")
            )

            self.task_info.File.audio_file_ext = "mp3"

            (
                FFmpegRunner.from_command(convert_cmd)
                .set_cwd(cwd)
                .on_completed(self.on_convert_completed)
                .on_error(self.on_merge_error)
                .start()
            )

    def check_attach_cover(self):
        if config.get(config.attach_cover):
            cover_path = Path(self.get_cwd(), self.cover_file_name)

            # 只有封面确实存在时，才返回封面路径，否则视为不需要嵌入封面
            if cover_path.exists():
                return self.cover_file_name
            else:
                logger.warning(f"封面文件 {cover_path} 不存在，无法嵌入封面")
            
        return None

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
        # 只有在合并视频和音频的情况下，才使用这个属性
        return f"{self.task_info.File.name}.{self.task_info.File.merge_file_ext}"
    
    @property
    def final_video_file_name(self):
        return f"{self.task_info.File.name}.{self.task_info.File.video_file_ext}"
    
    @property
    def final_audio_file_name(self):
        return f"{self.task_info.File.name}.{self.task_info.File.audio_file_ext}"

    @property
    def cover_file_name(self):
        return f"{self.task_info.File.name}.{config.get(config.cover_type).value}"