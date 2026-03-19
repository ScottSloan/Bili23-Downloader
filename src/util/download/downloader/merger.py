from util.common.enum import DownloadStatus, DownloadType
from util.download.task.manager import task_manager
from util.common.timestamp import get_timestamp
from util.common.signal_bus import signal_bus
from util.ffmpeg.command import FFmpegCommand
from util.download.task.info import TaskInfo
from util.ffmpeg.runner import FFmpegRunner
from util.common.io import Remover, Renamer

from pathlib import Path

class Merger:
    def __init__(self, task_info: TaskInfo):
        self.task_info = task_info

    def start(self):
        if self.task_info.Download.merge_video_audio:
            self.merge_video_audio()
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
            self.set_error_message("下载文件不存在", "")

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

        self.mark_as_completed()

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
            "No space left on device": "磁盘空间不足",
            "Permission denied": "没有权限写入文件",
            "Invalid data found when processing input": "文件损坏或格式不受支持",
            "No such file or directory": "文件不存在或路径错误",
            "Could not open file": "无法打开文件",
            "Device or resource busy": "文件被占用",
            "Could not create output file": "无法创建输出文件",
            "Format not supported": "文件格式不受支持",
            "Unknown encoder": "未知编码器",
            "Unknown decoder": "未知解码器",
        }

        error_message = None

        for key, message in error_map.items():
            if key in str(stderr):
                error_message = message
                break

        if error_message is None:
            error_message = str(error)

        self.set_error_message(error_message, stderr)

    def on_rename_error(self, error: str, *args: str):
        self.set_error_message("重命名文件失败", error)

    def set_error_message(self, short_message: str, description: str):
        self.task_info.Download.status = DownloadStatus.MERGE_FAILED

        self.task_info.Error.short_message = short_message
        self.task_info.Error.description = description

    def get_cwd(self):
        return Path(self.task_info.File.download_path, self.task_info.File.folder)

    def add_file(self, *args: str, clear = False):
        if clear:
            self.task_info.File.relative_files.clear()

        for file_name in args:
            if file_name not in self.task_info.File.relative_files:
                self.task_info.File.relative_files.append(file_name)

        task_manager.update(self.task_info)

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
