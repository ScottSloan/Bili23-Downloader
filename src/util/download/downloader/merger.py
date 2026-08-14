from PySide6.QtCore import QObject

from ...common.enum import DownloadStatus, DownloadType, OriginalFileType, ToastNotificationCategory
from ...common.io.file import safe_remove, safe_rename
from ...common.timestamp import get_timestamp
from ...common.signal_bus import signal_bus
from ...common.translator import Translator
from ...common.config import config

from ...parse.additional.chapter import ChapterParser

from ...ffmpeg.command import FFmpegCommand
from ...ffmpeg.runner import FFmpegRunner

from ..task.manager import task_manager
from ..task.info import TaskInfo

from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class Merger(QObject):
    def __init__(self, task_info: TaskInfo, parent = None):
        super().__init__(parent)

        self.task_info = task_info
        self._has_error = False
        self._stopped = False
        self._ffmpeg_runner = None

        self._output_audio_file = None
        self._embedded_cover_file_name = None
        self._delete_cover_after_embedding = False
        self._embedded_subtitle_list = []

    def stop(self, timeout: int = 3000):
        """
        终止正在进行的 FFmpeg 任务，返回其线程是否已退出

        FFmpegRunner 是 QThread，且挂在本对象的 parent 链上。若在它仍然运行时
        销毁 Downloader，整条链会被连带析构，Qt 随即 qFatal 中止进程。
        因此销毁本对象之前必须先在这里把线程收干净。
        """
        self._stopped = True

        runner = self._ffmpeg_runner

        if runner is None:
            return True

        try:
            if not runner.isRunning():
                return True

            return runner.stop(timeout)

        except RuntimeError:
            # C++ 侧已经析构，无需再处理
            return True

    def start(self):
        if self.task_info.Download.merge_video_audio:
            # 现代 dash 视频合并
            self.merge_video_audio()

        elif self.task_info.Download.video_parts_count > 0:
            # 旧版 flv 分片下载合并
            self.merge_video_parts()

        elif self.task_info.File.audio_file_ext == "m4a":
            if config.get(config.m4a_to_mp3):
                # 将 m4a 转换为 mp3
                self.m4a_to_mp3()
                return
            
            # else:
            #     # 对 m4a 文件进行修复
            #     self.fix_mp4_box()

            self.rename_output_file()

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
                cover_path = self.check_attach_cover(),
                chapter_path = self.check_attach_chapter(),
                subtitle_list = self.check_embed_subtitles()
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
            cover_path = self.check_attach_cover(),
            chapter_path = self.check_attach_chapter(),
            subtitle_list = self.check_embed_subtitles()
        )

        self._run_merge_command(merge_cmd, cwd)

    def _run_merge_command(self, command: FFmpegCommand, cwd: Path):
        self._ffmpeg_runner = FFmpegRunner.from_command(command, parent = self)
        self._ffmpeg_runner.set_cwd(cwd)
        self._ffmpeg_runner.finished_signal.connect(self.on_merge_completed)
        self._ffmpeg_runner.error_signal.connect(self.on_merge_error)
        self._ffmpeg_runner.start()

    def rename_output_file(self):
        if self._has_error:
            return

        has_video = self.task_info.Download.type & DownloadType.VIDEO != 0
        has_audio = self.task_info.Download.type & DownloadType.AUDIO != 0
        cwd = self.get_cwd()

        try:
            if has_video and has_audio:
                kept_original_files = self.keep_original_files()
                if self._has_error: return

                self.add_file(*kept_original_files, clear = True)

            elif has_video and not has_audio:
                final_video_file_name = safe_rename(cwd, self.temp_video_file_name, self.final_mp4_video_file_name).name
                self.add_file(final_video_file_name, clear = True)

            elif has_audio and not has_video:
                if self._output_audio_file is None:
                    self._output_audio_file = self.temp_audio_file_name

                final_audio_file_name = safe_rename(cwd, self._output_audio_file, self.final_audio_file_name).name
                self.add_file(final_audio_file_name, clear = True)

            self.mark_as_completed()

        except Exception as e:
            self.set_error_message(Translator.ERROR_MESSAGES("RENAME_FAILED"), str(e))

    def on_merge_completed(self, return_code: int, stdout: str, stderr: str):
        if getattr(self, "_has_error", False) or self._stopped:
            return

        try:
            cwd = self.get_cwd()
            
            final_output_file_name = safe_rename(cwd, self.temp_output_file_name, self.final_output_file_name).name

            kept_original_files = []

            if not self.task_info.Download.keep_original_files:
                safe_remove(cwd, *self.task_info.File.relative_files)
            else:
                kept_original_files = self.keep_original_files()
                if self._has_error: return

                safe_remove(cwd, *self.task_info.File.relative_files)

            self.delete_embedded_cover()
            self.delete_embedded_subtitles()
            self.delete_embedded_chapter()
            self.add_file(final_output_file_name, *kept_original_files, clear = True)
            self.mark_as_completed()

        except Exception as e:
            self.set_error_message(Translator.ERROR_MESSAGES("RENAME_FAILED"), str(e))

    def on_convert_completed(self, return_code: int, stdout: str, stderr: str):
        if getattr(self, "_has_error", False) or self._stopped:
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

        signal_bus.download.auto_manage_concurrent_downloads.emit()
        signal_bus.download.add_to_completed_list.emit([self.task_info])
        signal_bus.download.remove_from_downloading_list.emit(self.task_info)

    def keep_original_files(self):
        try:
            cwd = self.get_cwd()

            try:
                original_file_type = OriginalFileType(config.keep_original_files_type)
            except ValueError:
                original_file_type = OriginalFileType.BOTH

            kept_original_files = []

            match original_file_type:
                case OriginalFileType.BOTH:
                    final_video_file_name = safe_rename(cwd, self.temp_video_file_name, self.final_video_file_name).name
                    final_audio_file_name = safe_rename(cwd, self.temp_audio_file_name, self.final_audio_file_name).name

                    kept_original_files.extend([final_video_file_name, final_audio_file_name])

                case OriginalFileType.VIDEO:
                    final_video_file_name = safe_rename(cwd, self.temp_video_file_name, self.final_video_file_name).name
                    kept_original_files.append(final_video_file_name)

                case OriginalFileType.AUDIO:
                    final_audio_file_name = safe_rename(cwd, self.temp_audio_file_name, self.final_audio_file_name).name
                    kept_original_files.append(final_audio_file_name)

            return kept_original_files
        except Exception as e:
            self.set_error_message(Translator.ERROR_MESSAGES("RENAME_FAILED"), str(e))

            return []

    def on_merge_error(self, error: Exception, stdout: str, stderr: str):
        # 主动终止 FFmpeg 必然带回一个非零返回码，这不是真正的合并失败，
        # 不能据此把任务标记为失败
        if self._stopped:
            return

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

        long_message = f"{error_message}\n\n\n{stderr}"

        self.set_error_message(Translator.ERROR_MESSAGES("DOWNLOAD_FAILED"), long_message)

        signal_bus.download.auto_manage_concurrent_downloads.emit()

    def set_error_message(self, short_message: str, description: str):
        self._has_error = True
        self.task_info.Download.status = DownloadStatus.FFMPEG_FAILED

        signal_bus.download.update_downloading_item.emit(self.task_info)
        
        signal_bus.toast.show_long_message.emit(
            ToastNotificationCategory.ERROR,
            short_message,
            description
        )

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

            self._temp_m4a_audio_name = self.temp_audio_file_name
            self.task_info.File.audio_file_ext = "mp3"

            self._output_audio_file = self.temp_audio_file_name

            convert_cmd = FFmpegCommand.convert_m4a_to_mp3(
                input_path = self._temp_m4a_audio_name,
                output_path = self.temp_audio_file_name
            )

            self._ffmpeg_runner = FFmpegRunner.from_command(convert_cmd, parent=self)
            self._ffmpeg_runner.set_cwd(cwd)
            self._ffmpeg_runner.finished_signal.connect(self.on_convert_completed)
            self._ffmpeg_runner.error_signal.connect(self.on_merge_error)
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
                self._embedded_cover_file_name = self.cover_file_name
                self._delete_cover_after_embedding = config.get(config.delete_cover_after_attach)
                return self.cover_file_name
            else:
                logger.warning(f"封面文件 {cover_path} 不存在，无法嵌入封面")
        return None

    def delete_embedded_cover(self):
        if self._embedded_cover_file_name and self._delete_cover_after_embedding:
            safe_remove(self.get_cwd(), self._embedded_cover_file_name)

    def check_embed_subtitles(self):
        # 待嵌入的弹幕/字幕轨由附加内容解析阶段登记，只有 ASS 格式且输出 MKV 时才会有登记结果
        if self.task_info.File.merge_file_ext != "mkv":
            return None

        cwd = self.get_cwd()
        subtitle_list = []

        for entry in self.task_info.File.subtitle_track_list:
            if not Path(cwd, entry["file"]).exists():
                logger.warning(f"字幕文件 {entry['file']} 不存在，无法嵌入")
                continue

            subtitle_list.append(dict(entry))

        if not subtitle_list:
            return None

        # 字幕轨排在弹幕轨之前，并把首条字幕标记为默认轨：打开视频即显示字幕，弹幕需手动开启
        # sort 是稳定排序，同类轨道之间保持解析时的先后顺序
        subtitle_list.sort(key = lambda entry: 0 if entry["kind"] == "subtitle" else 1)

        if subtitle_list[0]["kind"] == "subtitle":
            subtitle_list[0]["default"] = True

        self._embedded_subtitle_list = subtitle_list

        return subtitle_list

    def delete_embedded_subtitles(self):
        # 与封面一致，合并成功后才删除源文件；合并失败时保留，重试可直接复用
        if not self._embedded_subtitle_list:
            return

        delete_danmaku = config.get(config.delete_danmaku_after_embed)
        delete_subtitle = config.get(config.delete_subtitle_after_embed)

        file_list = [
            entry["file"] for entry in self._embedded_subtitle_list
            if (delete_danmaku if entry["kind"] == "danmaku" else delete_subtitle)
        ]

        if file_list:
            safe_remove(self.get_cwd(), *file_list)

    def check_attach_chapter(self):
        # 章节文件由 ChapterParser 在附加内容解析阶段生成，视频没有章节时不会存在
        chapter_file_name = ChapterParser.get_file_name(self.task_info.Basic.task_id)

        if Path(self.get_cwd(), chapter_file_name).exists():
            return chapter_file_name

        return None

    def delete_embedded_chapter(self):
        # 章节文件仅为中间文件，合并成功后删除；合并失败时保留，重试可直接复用
        safe_remove(self.get_cwd(), ChapterParser.get_file_name(self.task_info.Basic.task_id))

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

    def fix_mp4_box(self):
        cwd = self.get_cwd()

        if Path(cwd, self.temp_audio_file_name).exists():
            self.task_info.Download.status = DownloadStatus.CONVERTING
            signal_bus.download.update_downloading_item.emit(self.task_info)

            temp_output_audio_file_name = "output_{task_id}.m4a".format(task_id = self.task_info.Basic.task_id)

            self._output_audio_file = temp_output_audio_file_name

            fix_command = FFmpegCommand.fix_mp4_box(
                input_path = self.temp_audio_file_name,
                output_path = temp_output_audio_file_name
            )

            self._ffmpeg_runner = FFmpegRunner.from_command(fix_command, parent = self)
            self._ffmpeg_runner.set_cwd(cwd)
            self._ffmpeg_runner.finished_signal.connect(self.on_convert_completed)
            self._ffmpeg_runner.error_signal.connect(self.on_merge_error)
            self._ffmpeg_runner.start()
        else:
            self.set_error_message(
                Translator.ERROR_MESSAGES("DOWNLOAD_FAILED"),
                Translator.ERROR_MESSAGES("M4A_NOT_FOUND")
            )

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
    def temp_cover_file_name(self):
        return "cover_{task_id}.{file_ext}".format(
            task_id = self.task_info.Basic.task_id,
            file_ext = config.get(config.cover_type).value
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
