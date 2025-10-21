import os
import re
import subprocess

from utils.common.model.data_type import Command, Process
from utils.common.model.task_info import DownloadTaskInfo
from utils.common.model.callback import Callback, ConsoleCallback
from utils.common.enums import StatusCode
from utils.common.exception import GlobalException
from utils.common.formatter.file_name_v2 import FileNameFormatter
from utils.common.regex import Regex
from utils.common.formatter.formatter import FormatUtils

from utils.config import Config

class FFmpeg:
    class Command:
        @staticmethod
        def get_convert_video_and_audio_command(info: dict):
            command = Command()

            vcodec = info.get("vcodec")
            crf = info.get("crf")
            vbitrate = info.get("vbitrate")

            acodec = info.get("acodec")
            asamplerate = info.get("asamplerate")
            achannel = info.get("achannel")
            abitrate = info.get("abitrate")

            input_path = info.get("input_path")
            output_path = info.get("output_path")

            raw = f'"{Config.Merge.ffmpeg_path}" -i "{input_path}" -c:v {vcodec} -c:a {acodec}'

            if vcodec != "copy":
                crf_arg = f"-crf {crf}" if crf else ""
                raw += f" {crf_arg} -b:v: {vbitrate}k"

            if acodec != "copy":
                raw += f" -ac {achannel} -ar {asamplerate} -b:a {abitrate}k"

            command.add(raw + f' "{output_path}"')

            return command.format()

        @staticmethod
        def get_cut_command(info: dict):
            command = Command()

            start_time = info.get("start_time")
            end_time = info.get("end_time")

            input_path = info.get("input_path")
            output_path = info.get("output_path")

            command.add(f'"{Config.Merge.ffmpeg_path}" -ss {start_time} -to {end_time} -i "{input_path}" -acodec copy -vcodec copy "{output_path}"')

            return command.format()
        
        @staticmethod
        def get_info_command(file_path: str):
            command = Command()

            command.add(f'"{Config.Merge.ffmpeg_path}" -i "{file_path}"')

            return command.format()

        @staticmethod
        def get_extract_audio_command(info: dict):
            command = Command()

            input_path = info.get("input_path")
            output_path = info.get("output_path")

            command.add(f'{Config.Merge.ffmpeg_path} -i "{input_path}" -vn -acodec copy "{output_path}"')

            return command.format()

        @staticmethod
        def run(command: str, callback: Callback, cwd: str = None, check = True):
            def run_process():
                p = subprocess.run(command, shell = True, cwd = cwd, stdout = subprocess.PIPE, stderr = subprocess.STDOUT, stdin = subprocess.PIPE, text = True, encoding = "utf-8")

                process = Process()
                process.return_code = p.returncode
                process.output = p.stdout

                return process
            
            def get_output():
                return f"{process.output}\n\nCommand:\n{command}"
            
            process = run_process()
                
            if not process.return_code or not check:
                callback.onSuccess(process)
            else:
                raise GlobalException(code = StatusCode.CallError.value, stack_trace = get_output(), callback = callback.onError, args = (process,))

        @staticmethod
        def run_realtime(command: str, callback: ConsoleCallback, cwd: str = None):
            def run_process():
                p = subprocess.Popen(command, shell = True, cwd = cwd, stdout = subprocess.PIPE, stdin = subprocess.PIPE, stderr = subprocess.STDOUT, text = True, universal_newlines = True, bufsize = 1, encoding = "utf-8")
                
                temp_output = []

                while True:
                    if p.poll() is None:
                        output = p.stdout.readline()

                        temp_output.append(output)

                        callback.onReadOutput(output)
                    
                    else:
                        break

                process = Process()
                process.return_code = p.returncode
                process.output = "".join(temp_output)

                p.stdout.close()

                return process

            def get_output():
                return f"{process.output}\n\nCommand:\n{command}"

            process = run_process()

            if not process.return_code:
                callback.onSuccess(process)
            else:
                raise GlobalException(code = StatusCode.CallError.value, stack_trace = get_output(), callback = callback.onError, args = (process, ))
            
    class Utils:
        temp_duration = 0

        @staticmethod
        def cut(info: dict, callback: Callback):
            command = FFmpeg.Command.get_cut_command(info)

            FFmpeg.Command.run(command, callback)

        @staticmethod
        def convert(info: dict, callback: ConsoleCallback):
            command = FFmpeg.Command.get_convert_video_and_audio_command(info)

            FFmpeg.Command.run_realtime(command, callback)

        @classmethod
        def info(cls, file_path: str, callback: Callback):
            command = FFmpeg.Command.get_info_command(file_path)

            FFmpeg.Command.run(command, callback, check = False)

        @staticmethod
        def extract_audio(info: dict, callback: Callback):
            command = FFmpeg.Command.get_extract_audio_command(info)

            FFmpeg.Command.run(command, callback)

        @staticmethod
        def parse_media_info(output: str):
            duration_info = Regex.re_findall_in_group(r"Duration: (([\d:.]+))", output, 1)

            start_info = Regex.re_findall_in_group(r"start: (([\d.]+))", output, 1)

            bitrate_info = Regex.re_findall_in_group(r"bitrate: ((\d* kb\/s))", output, 1)
        
            video_stream_info = Regex.re_match_in_group(r"Video: (.*)", output, 4)

            fps_info = Regex.re_findall_in_group(r"((\d+(?:.\d+)? fps))", output, 1)

            audio_stream_info = Regex.re_match_in_group(r"Audio: (.*)", output, 5)

            return {
                "duration": duration_info[0],
                "start": start_info[0],
                "bitrate": bitrate_info[0],
                "vcodec": video_stream_info[0],
                "vformat": video_stream_info[1],
                "resolution": video_stream_info[2],
                "vbitrate": video_stream_info[3],
                "fps": fps_info[0],
                "acodec": audio_stream_info[0],
                "samplerate": audio_stream_info[1],
                "channel": audio_stream_info[2],
                "sampleformat": audio_stream_info[3],
                "abitrate": audio_stream_info[4]
            }

        @classmethod
        def parse_progress_info(cls, output: str):
            def get_time(pattern: str):
                match = re.search(pattern, output)

                if match:
                    hours, minutes, seconds = map(int, match.groups())
                    return hours * 3600 + minutes * 60 + seconds
            
            def get_frame(pattern: str):
                result = re.findall(pattern, output)

                if result:
                    return [result[0]]
                else:
                    return ["--"]

            def get_size(pattern: str):
                result = re.findall(pattern, output)

                if result:
                    size = int(result[0][0])
                    return [FormatUtils.format_size(int(size * 1024))]
                else:
                    return ["--"]

            duration = get_time(r"Duration: (\d{2}):(\d{2}):(\d{2})")

            if duration:
                cls.temp_duration = duration

            current_time = get_time(r"time=(\d{2}):(\d{2}):(\d{2})")
            frame_info = get_frame(r"frame=\s*(\d+)")
            size_info = get_size(r"size=\s*(\d+)(KiB|kB)")

            speed_info = Regex.re_findall_in_group(r"speed=\s*((\d+\.\d+x))", output, 1)

            return {
                "progress": int(current_time / cls.temp_duration * 100) if cls.temp_duration and current_time else 0,
                "frame": frame_info[0],
                "size": size_info[0],
                "speed": speed_info[0]
            }

    class Prop:
        @staticmethod
        def full_file_name(task_info: DownloadTaskInfo):
            return FileNameFormatter.check_file_name_length(f"{task_info.file_name}.{task_info.output_type}")