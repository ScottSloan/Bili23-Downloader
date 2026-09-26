from PySide6.QtCore import QObject

from ...common.enum import DownloadStatus, DownloadType, OriginalFileType, ToastNotificationCategory
from ...common.io.file import safe_remove, safe_rename
from ...common.timestamp import get_timestamp
from ...common.signal_bus import signal_bus
from ...common.translator import Translator
from ..task.options import resolve

from ...parse.additional.chapter import ChapterParser

from ...ffmpeg.command import FFmpegCommand
from ...ffmpeg.runner import FFmpegRunner

from ..task.manager import task_manager
from ..task.info import TaskInfo

from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# 存在独立 DASH 音频流时 audio_file_ext 的取值（见 parse/audio_info.py 的 get_audio_file_ext）。
# 这些流下发的都是 fMP4 分片容器（.m4s 的内容配 .m4a/.flac/.ec3 的扩展名），交付前必须
# 重封装成与扩展名一致的标准容器，否则严格解析器打不开。
# 用它当判据而不是逐个判断扩展名，是为了让三种格式始终走同一条命令
DASH_AUDIO_STREAM_EXTS = ("m4a", "flac", "ec3")

# stop() 超时后从 parent 链上摘下来的 Merger 暂存于此，保活到 FFmpeg 线程真正结束。
# 不保活的话，Python 侧最后一个引用消失就会析构，而 C++ 端的 QThread 还在跑
_detached_mergers: set = set()

class Merger(QObject):
    def __init__(self, task_info: TaskInfo, parent = None):
        super().__init__(parent)

        self.task_info = task_info
        self._has_error = False
        self._stopped = False
        self._ffmpeg_runner = None

        self._output_audio_file = None
        # 转换成功后才写回 File.audio_file_ext 的目标扩展名，None 表示本次不改扩展名
        self._converted_audio_file_ext = None
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

    def detach(self):
        """
        stop() 超时后调用：脱离 parent 链并自行保活，直到 FFmpeg 线程结束

        留在链上的话，销毁 Downloader 会连带析构仍在运行的 FFmpegRunner，
        Qt 随即 qFatal 中止进程。摘下来之后本对象与 Downloader 再无关系，
        线程自己跑完即可安全回收
        """
        try:
            self.setParent(None)

            runner = self._ffmpeg_runner

            if runner is None or not runner.isRunning():
                self.deleteLater()
                return

            _detached_mergers.add(self)

            runner.finished.connect(self._on_detached_finished)

            # 连接之前线程可能刚好结束，finished 已经发过且不会再发，这里补一次检查
            if not runner.isRunning():
                self._on_detached_finished()

        except RuntimeError:
            # C++ 侧已经析构，无需再处理
            _detached_mergers.discard(self)

    def _on_detached_finished(self):
        _detached_mergers.discard(self)

        try:
            self.deleteLater()

        except RuntimeError:
            # 同上
            pass

    def start(self):
        """
        启动合并流程，并兜住其中的全部异常

        调用方在此之前已经把状态置为 MERGING。这条路径上有大量文件系统操作
        （探测文件是否存在、写 concat 清单、拉起 FFmpeg 线程），任意一处抛出，
        任务就会永远停在 MERGING：状态已经置位，却没有任何 FFmpeg 在跑，
        也就再没有人把它推向终态。而合并额度全局只有一个，这一个僵住会让
        整条队列都排不下去，所以这里必须保证异常一定收敛到失败态
        """
        try:
            self._start()

        except Exception as e:
            logger.exception("启动 FFmpeg 合并流程时发生异常")

            self.set_error_message(Translator.ERROR_MESSAGES("DOWNLOAD_FAILED"), str(e))

    def _start(self):
        if self.task_info.Download.merge_video_audio:
            if self.should_remux_kept_audio():
                # 保留原始文件时音频要当成品交付，而它同时是合并命令的输入，两者只能串行：
                # 先重封装，完成后由回调接回合并流程
                self.remux_audio(on_finished = self.on_remux_before_merge_completed)
                return

            # 现代 dash 视频合并
            self.merge_video_audio()

        elif self.task_info.Download.video_parts_count > 0:
            # 旧版 flv 分片下载合并
            self.merge_video_parts()

        elif self.task_info.File.audio_file_ext in DASH_AUDIO_STREAM_EXTS:
            if self.task_info.File.audio_file_ext == "m4a" and resolve(self.task_info, "m4a_to_mp3"):
                # 转 mp3 是重编码，容器随之重写，不必再重封装一次
                self.m4a_to_mp3()
                return

            self.remux_audio(on_finished = self.on_convert_completed)

        else:
            # 纯视频下载（未勾选独立音频流）走这里：audio_file_ext 为空串，
            # 没有任何音频文件需要交付，直接改名即可
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
        self._start_ffmpeg(command, cwd, self.on_merge_completed)

    def _start_ffmpeg(self, command: FFmpegCommand, cwd: Path, on_finished):
        # 上一次的 runner 必须先收干净再覆盖引用。保留原始文件的合并任务会在同一个 Merger 上
        # 顺序跑两次 FFmpeg（重封装 → 合并），而 stop()/detach() 只认得 _ffmpeg_runner 一个引用，
        # 上一个 runner 若还活着就变成无人认领的 child，只能等本对象析构时被连带销毁 ——
        # 销毁一个仍在运行的 QThread 会让 Qt 直接 qFatal
        if not self.retire_runner():
            self.set_error_message(
                Translator.ERROR_MESSAGES("DOWNLOAD_FAILED"),
                Translator.ERROR_MESSAGES("FFMPEG_STILL_RUNNING")
            )
            return

        # 下载阶段结束时进度停在 100，这里必须归零，否则进度条会从满格开始重走
        self.task_info.Download.progress = 0

        self._ffmpeg_runner = FFmpegRunner.from_command(command, parent = self)
        self._ffmpeg_runner.set_cwd(cwd)
        # FFmpeg 自己报的时长更准，这里给的只是它打印出 Duration 之前的兜底
        self._ffmpeg_runner.set_duration(self.task_info.Episode.duration)
        self._ffmpeg_runner.progress_signal.connect(self.on_progress_updated)
        self._ffmpeg_runner.finished_signal.connect(on_finished)
        self._ffmpeg_runner.error_signal.connect(self.on_merge_error)
        self._ffmpeg_runner.start()

    def retire_runner(self, timeout: int = 3000):
        """
        回收上一次的 FFmpegRunner，返回是否可以安全启动下一个

        能走到这里，说明上一个 runner 的 finished_signal 已经送达（第二次启动只发生在它的
        回调里），它的 run() 只剩 Qt 收尾的几条指令，wait 几乎立刻返回。

        顺序不能反：先确认线程退出再清引用。清早了它就变成无人认领的 child，而销毁一个仍在
        运行的 QThread 会让 Qt 直接 qFatal。仍在运行时宁可让本次流程失败收场，由用户重试，
        也不覆盖引用
        """
        runner = self._ffmpeg_runner

        if runner is None:
            return True

        try:
            if not runner.wait(timeout):
                logger.error(f"上一个 FFmpeg 线程在 {timeout} ms 内仍未退出，本次不再启动新的 FFmpeg")
                return False

        except RuntimeError:
            # C++ 侧已经析构，无需再处理
            pass

        self._ffmpeg_runner = None

        try:
            runner.setParent(None)
            runner.deleteLater()

        except RuntimeError:
            # 同上
            pass

        return True

    def on_progress_updated(self, progress: int):
        if self._has_error or self._stopped:
            return

        # 合并进度只用于界面反馈，不落库：它变化频繁，而任务重启后本就要从头合并
        self.task_info.Download.progress = progress

        signal_bus.download.update_downloading_item.emit(self.task_info)

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
                final_audio_file_name = safe_rename(cwd, self.output_audio_file_name, self.final_audio_file_name).name
                self.add_file(final_audio_file_name, clear = True)

            self.mark_as_completed()

        except Exception as e:
            self.set_error_message(Translator.ERROR_MESSAGES("RENAME_FAILED"), str(e))

    def on_merge_completed(self, return_code: int, stdout: str, stderr: str):
        if getattr(self, "_has_error", False):
            return

        if self._stopped:
            # 本 Merger 已被接管或随任务一同销毁，状态交由接管方推进，这里不能再改
            logger.debug("合并完成回调在 Merger 停止后到达，已忽略")
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
            # 必须赶在改扩展名之前删源文件，此刻 temp_audio_file_name 指的还是输入的那个原始流。
            # 重封装路径下 _converted_audio_file_ext 保持 None、扩展名不变，这一步只是顺带清理
            safe_remove(self.get_cwd(), self.temp_audio_file_name)

            if self._converted_audio_file_ext:
                self.task_info.File.audio_file_ext = self._converted_audio_file_ext

            self.rename_output_file()

        except Exception as e:
            self.set_error_message(Translator.ERROR_MESSAGES("RENAME_FAILED"), str(e))

    def mark_as_completed(self):
        if getattr(self, "_has_error", False):
            return

        self.task_info.Download.status = DownloadStatus.COMPLETED
        # 合并阶段把 progress 覆盖成了 FFmpeg 的进度（runner 侧封顶 99），完成时须收回 100：
        # 这个值会被 build_record 一并序列化进已完成记录，也会被下载列表直接画成进度条，
        # 留着 FFmpeg 的中间值就是已完成任务的进度条停在半途，且重启后依旧
        self.task_info.Download.progress = 100
        self.task_info.Basic.completed_time = get_timestamp()

        # 必须等这条写入落盘再往下走。下面的 remove_from_downloading_list 会一路同步
        # 走到 Downloader.on_delete()，那是整个下载流程中最容易出现原生崩溃的一段
        # （线程池与定时器的销毁）。进程若在那里没了，异步排队的这条记录就永远丢了：
        # 磁盘上是合并好的成品，库里却停在「下载中」
        task_manager.mark_as_completed(self.task_info, wait = True)

        signal_bus.download.auto_manage_concurrent_downloads.emit()
        signal_bus.download.add_to_completed_list.emit([self.task_info])
        signal_bus.download.remove_from_downloading_list.emit(self.task_info)

    def get_keep_original_file_type(self):
        try:
            return OriginalFileType(resolve(self.task_info, "keep_original_files_type"))
        except ValueError:
            # 降级用的枚举成员被改名或删除时按「都保留」处理，与旧行为的默认值一致
            return OriginalFileType.BOTH

    def should_remux_kept_audio(self):
        """
        本次是否需要先把音频重封装再交付

        除「保留原始文件且保留范围含音频」外，还要确认磁盘上真有独立音频流：扩展名不在
        DASH_AUDIO_STREAM_EXTS 里就说明上游没拿到音频流（audio_info.py 会清掉 AUDIO 位），
        或走的是音频内嵌在分片里的 flv 老格式，此时重封装必然找不到输入文件
        """
        if not self.task_info.Download.keep_original_files:
            return False

        if self.task_info.File.audio_file_ext not in DASH_AUDIO_STREAM_EXTS:
            return False

        return self.get_keep_original_file_type() in (OriginalFileType.BOTH, OriginalFileType.AUDIO)

    def keep_original_files(self):
        try:
            cwd = self.get_cwd()

            kept_original_files = []

            match self.get_keep_original_file_type():
                case OriginalFileType.BOTH:
                    final_video_file_name = safe_rename(cwd, self.temp_video_file_name, self.final_video_file_name).name
                    final_audio_file_name = safe_rename(cwd, self.output_audio_file_name, self.final_audio_file_name).name

                    kept_original_files.extend([final_video_file_name, final_audio_file_name])

                case OriginalFileType.VIDEO:
                    final_video_file_name = safe_rename(cwd, self.temp_video_file_name, self.final_video_file_name).name
                    kept_original_files.append(final_video_file_name)

                case OriginalFileType.AUDIO:
                    final_audio_file_name = safe_rename(cwd, self.output_audio_file_name, self.final_audio_file_name).name
                    kept_original_files.append(final_audio_file_name)

            return kept_original_files
        except Exception as e:
            self.set_error_message(Translator.ERROR_MESSAGES("RENAME_FAILED"), str(e))

            return []

    def on_merge_error(self, error: Exception, stdout: str, stderr: str):
        # 主动终止 FFmpeg 必然带回一个非零返回码，这不是真正的合并失败，
        # 不能据此把任务标记为失败
        if self._stopped:
            logger.debug("合并错误回调在 Merger 停止后到达，已忽略")
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

    def set_error_message(self, short_message: str, description: str):
        self._has_error = True
        self.task_info.Download.status = DownloadStatus.FFMPEG_FAILED

        signal_bus.download.update_downloading_item.emit(self.task_info)

        # 失败同样要唤醒调度器。FFmpeg 全局只允许跑一个，而这个额度完全靠该信号释放，
        # 这里不发的话，队列里其余等待合并的任务就再没有下一次被调度的机会，会一直干等
        signal_bus.download.auto_manage_concurrent_downloads.emit()

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

            # 转换期间不能就地把 audio_file_ext 改成 mp3：一旦中途失败或程序退出，
            # 重试时 start() 里的 m4a 判断就不再成立，会跑去重命名一个根本不存在的 mp3。
            # 因此先输出到独立的临时名，等转换真正完成再改扩展名
            temp_output_audio_file_name = "output_{task_id}.mp3".format(task_id = self.task_info.Basic.task_id)

            self._output_audio_file = temp_output_audio_file_name
            self._converted_audio_file_ext = "mp3"

            convert_cmd = FFmpegCommand.convert_m4a_to_mp3(
                input_path = self.temp_audio_file_name,
                output_path = temp_output_audio_file_name
            )

            self._start_ffmpeg(convert_cmd, cwd, self.on_convert_completed)
        else:
            self.set_error_message(
                Translator.ERROR_MESSAGES("DOWNLOAD_FAILED"),
                Translator.ERROR_MESSAGES("M4A_NOT_FOUND")
            )

    def remux_audio(self, on_finished):
        """
        把独立音频流重封装成标准容器，完成后回调 on_finished

        与 m4a_to_mp3 同构：先写独立的临时名，成功了再由回调改名交付。就地把
        temp_audio_file_name 覆盖掉的话，中途失败或程序退出会让任务停在「文件已经不是
        原始流、记录却仍指向原始流」的状态，重试时无从判断

        两种调用方：仅音频下载直接交付（回调 on_convert_completed），以及保留原始文件时
        为合并准备交付用的音频（回调 on_remux_before_merge_completed）
        """
        cwd = self.get_cwd()

        if not Path(cwd, self.temp_audio_file_name).exists():
            self.set_error_message(
                Translator.ERROR_MESSAGES("DOWNLOAD_FAILED"),
                Translator.ERROR_MESSAGES("FILE_NOT_FOUND_DETAIL")
            )
            return

        self.task_info.Download.status = DownloadStatus.CONVERTING
        signal_bus.download.update_downloading_item.emit(self.task_info)

        self._output_audio_file = self.temp_remux_audio_file_name

        remux_cmd = FFmpegCommand.remux_audio(
            input_path = self.temp_audio_file_name,
            output_path = self.temp_remux_audio_file_name
        )

        self._start_ffmpeg(remux_cmd, cwd, on_finished)

    def on_remux_before_merge_completed(self, return_code: int, stdout: str, stderr: str):
        """
        保留原始文件的合并任务：音频已重封装完，接着跑合并
        """
        if self._has_error or self._stopped:
            return

        # 任务整体仍然是「合并中」，重封装只是为交付保留的原始文件做准备
        self.task_info.Download.status = DownloadStatus.MERGING
        signal_bus.download.update_downloading_item.emit(self.task_info)

        if self.task_info.Download.merge_video_audio:
            self.merge_video_audio()
        else:
            self.merge_video_parts()

    def check_attach_cover(self):
        if resolve(self.task_info, "attach_cover"):
            cover_path = Path(self.get_cwd(), self.cover_file_name)
            if cover_path.exists():
                self._embedded_cover_file_name = self.cover_file_name
                self._delete_cover_after_embedding = resolve(self.task_info, "delete_cover_after_attach")
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

        delete_danmaku = resolve(self.task_info, "delete_danmaku_after_embed")
        delete_subtitle = resolve(self.task_info, "delete_subtitle_after_embed")

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
    def temp_remux_audio_file_name(self):
        # 刻意不复用 output_ 前缀：temp_output_file_name 是 output_{task_id}.{merge_file_ext}，
        # 与 m4a/flac/ec3 虽然天然不撞，但那依赖 VideoContainer 只有两个成员这个隐含前提，
        # 不如另起前缀让「不撞」变成一眼可见的事实
        return "remux_{task_id}.{file_ext}".format(
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
            file_ext = resolve(self.task_info, "cover_type").value
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
    def output_audio_file_name(self):
        """
        当前应当交付的音频文件：重封装/转换跑过就是它的产物，否则是下载到的原始流

        这个属性是 self._output_audio_file 的唯一解析处，改名交付的每一条路径都从这里取源
        """
        return self._output_audio_file or self.temp_audio_file_name

    @property
    def final_audio_file_name(self):
        return f"{self.task_info.File.name}.{self.task_info.File.audio_file_ext}"

    @property
    def cover_file_name(self):
        return f"{self.task_info.File.name}.{resolve(self.task_info, 'cover_type').value}"
