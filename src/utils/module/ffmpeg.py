import os
import subprocess
from typing import Callable

from utils.common.enums import DownloadOption, StreamType
from utils.common.data_type import DownloadTaskInfo, Command
from utils.config import Config

class FFmpeg:
    def __init__(self):
        pass

    def detect_location(self):
        if not Config.FFmpeg.path:
            cwd_path = self.get_cwd_path()
            env_path = self.get_env_path()
    
            if cwd_path:
                Config.FFmpeg.path = cwd_path

            if env_path and not cwd_path:
                Config.FFmpeg.path = env_path

    def check_available(self):
        self.detect_location()

        cmd = f""""{Config.FFmpeg.path}" -version"""

        if "ffmpeg version" in self.run_command(cmd, output = True):
            Config.FFmpeg.available = True

    def merge_video(self, task_info: DownloadTaskInfo, full_file_name: str, callback: Callable):
        self.full_file_name = full_file_name

        match StreamType(task_info.stream_type):
            case StreamType.Dash:
                command = self.get_dash_command(task_info)

            case StreamType.Flv:
                command = self.get_flv_command(task_info)
        
        resp = self.run_command(command, cwd = Config.Download.path, output = True, return_code = True)

        if not resp[0]:
            callback()
        else:
            print(resp[1])

    def get_dash_command(self, task_info: DownloadTaskInfo):
        def get_video_temp_file_name():
            return f"video_{task_info.id}.{task_info.video_type}"

        def get_audio_temp_file_name():
            return f"audio_{task_info.id}.{task_info.audio_type}"
        
        def get_merge_command():
            return f'"{Config.FFmpeg.path}" -y -i "{get_video_temp_file_name()}" -i "{get_audio_temp_file_name()}" -acodec copy -vcodec copy -strict experimental {self.get_output_temp_file_name(task_info)}'

        def get_convent_command():
            if task_info.output_type == "m4a" and Config.Merge.m4a_to_mp3:
                task_info.output_type = "mp3"
                return f'"{Config.FFmpeg.path}" -y -i "{get_audio_temp_file_name()}" -c:a libmp3lame -q:a 0 "{self.get_output_temp_file_name(task_info)}"'
            
            elif task_info.output_type == "flac":
                return f'"{Config.FFmpeg.path}" -y -i "{get_audio_temp_file_name()}" -c:a flac -q:a 0 "{self.get_output_temp_file_name(task_info)}"'
            
            else:
                return self.get_rename_command(get_audio_temp_file_name(), self.get_output_temp_file_name(task_info))

        command = Command()

        match DownloadOption(task_info.download_option):
            case DownloadOption.VideoAndAudio:
                command.add(get_merge_command())
                command.add(self.get_rename_command(self.get_output_temp_file_name(task_info), self.full_file_name))

            case DownloadOption.OnlyVideo:
                command.add(self.get_rename_command(get_video_temp_file_name(), self.full_file_name))
            
            case DownloadOption.OnlyAudio:
                command.add(get_convent_command())
                command.add(self.get_rename_command(self.get_output_temp_file_name(task_info), self.full_file_name))
        
        return command.format()
    
    def get_flv_command(self, task_info: DownloadTaskInfo):
        def get_flv_temp_file_name():
            return f"flv_{task_info.id}.flv"
        
        def get_list_file_name():
            return f"flv_list_{task_info.id}.txt"

        def create_list_file():
            with open(os.path.join(Config.Download.path, get_list_file_name()), "w", encoding = "utf-8") as f:
                f.write("\n".join([f"file flv_{task_info.id}_part{i + 1}.flv" for i in range(task_info.flv_video_count)]))

        def get_merge_command():
            return f'"{Config.FFmpeg.path}" -y -f concat -safe 0 -i "{get_list_file_name()}" -c copy "{self.get_output_temp_file_name(task_info)}"'

        command = Command()

        if task_info.flv_video_count > 1:
            create_list_file()

            command.add(get_merge_command())
            command.add(self.get_rename_command(self.get_output_temp_file_name(task_info), self.full_file_name))
        else:
            command.add(self.get_rename_command(get_flv_temp_file_name(), self.full_file_name))

        return command.format()

    def get_rename_command(self, src: str, dst: str):
        def get_sys_rename_command():
            match Config.Sys.platform:
                case "windows":
                    return "rename"

                case "linux" | "darwin":
                    return "mv"

        def get_escape_character():
            match Config.Sys.platform:
                case "windows" | "darwin":
                    return ""
                
                case "linux":
                    return "--"

        return f'{get_sys_rename_command()} "{src}" {get_escape_character()}"{dst}"'
    
    def get_output_temp_file_name(self, task_info: DownloadTaskInfo):
            return f"out_{task_info.id}.{task_info.output_type}"

    def run_command(self, command: str, cwd: str = None, output: bool = False, return_code: bool = False):
        process = subprocess.run(command, shell = True, cwd = cwd, stdout = subprocess.PIPE, stderr = subprocess.STDOUT, stdin = subprocess.PIPE, text = True, encoding = "utf-8")

        if output and return_code:
            return (process.returncode, process.stdout)

        if output:
            return process.stdout
        
        if return_code:
            return process.returncode
    
    def get_env_path(self):
        ffmpeg_path = None
        path_env = os.environ.get("PATH", "")

        for directory in path_env.split(os.pathsep):
            possible_path = os.path.join(directory, self.ffmpeg_file_name)

            if os.path.isfile(possible_path) and os.access(possible_path, os.X_OK):
                ffmpeg_path = possible_path
                break

        return ffmpeg_path

    def get_cwd_path(self):
        ffmpeg_path = None

        possible_path = os.path.join(os.getcwd(), self.ffmpeg_file_name)
        
        if os.path.isfile(possible_path) and os.access(possible_path, os.X_OK):
            ffmpeg_path = possible_path

        return ffmpeg_path

    @property
    def ffmpeg_file_name(self):
        match Config.Sys.platform:
            case "windows":
                return "ffmpeg.exe"
            
            case "linux" | "darwin":
                return "ffmpeg"
