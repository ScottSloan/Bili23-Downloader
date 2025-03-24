import os
import subprocess

from utils.common.enums import DownloadOption, StreamType, StatusCode, OverrideOption, Platform
from utils.common.data_type import DownloadTaskInfo, Command, MergeCallback, CutInfo, CutCallback
from utils.common.exception import GlobalException
from utils.common.thread import Thread
from utils.config import Config

class FFmpeg:
    def __init__(self):
        pass

    def set_task_info(self, task_info: DownloadTaskInfo):
        self.task_info = task_info

    def set_cut_info(self, cut_info: CutInfo):
        self.cut_info = cut_info

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

    def merge_video(self, callback: MergeCallback):
        def check_file_exist():
            index = 0
            path = os.path.join(Config.Download.path, callback.onGetFullFileName())

            while os.path.exists(path):
                match OverrideOption(Config.Merge.override_option):
                    case OverrideOption.Rename:
                        index += 1

                        self.task_info.suffix = f"_{index}"
                        path = os.path.join(Config.Download.path, callback.onGetFullFileName())

                    case OverrideOption.Override:
                        self.delete_specific_file(path)
            
            callback.onSaveSuffix()

        check_file_exist()
    
        self.full_file_name = callback.onGetFullFileName()

        match StreamType(self.task_info.stream_type):
            case StreamType.Dash:
                command = self.get_dash_command()

            case StreamType.Flv:
                command = self.get_flv_command()
        
        resp = self.run_command(command, cwd = Config.Download.path, output = True, return_code = True)

        if not resp[0]:
            callback.onSuccess()
        else:
            raise GlobalException(code = StatusCode.FFmpegCall.value, stack_trace = resp[1], callback = callback.onError)
    
    def cut_clip(self, callback: CutCallback):
        command = self.get_cut_command()

        resp = self.run_command(command, output = True, return_code = True)

        if not resp[0]:
            callback.onSuccess()
        else:
            raise GlobalException(code = StatusCode.FFmpegCall.value, stack_trace = resp[1], callback = callback.onError)

    def get_dash_command(self):
        def get_merge_command():
            return f'"{Config.FFmpeg.path}" -y -i "{self.dash_video_temp_file_name}" -i "{self.dash_audio_temp_file_name}" -acodec copy -vcodec copy -strict experimental {self.output_temp_file_name}'

        def get_convent_command():
            if self.task_info.output_type == "m4a" and Config.Merge.m4a_to_mp3:
                self.task_info.output_type = "mp3"
                return f'"{Config.FFmpeg.path}" -y -i "{self.dash_audio_temp_file_name}" -c:a libmp3lame -q:a 0 "{self.output_temp_file_name}"'
            
            elif self.task_info.output_type == "flac":
                return f'"{Config.FFmpeg.path}" -y -i "{self.dash_audio_temp_file_name}" -c:a flac -q:a 0 "{self.output_temp_file_name}"'
            
            else:
                return self.get_rename_command(self.dash_audio_temp_file_name, self.output_temp_file_name)

        command = Command()

        match DownloadOption(self.task_info.download_option):
            case DownloadOption.VideoAndAudio:
                command.add(get_merge_command())
                command.add(self.get_rename_command(self.output_temp_file_name, self.full_file_name))

            case DownloadOption.OnlyVideo:
                command.add(self.get_rename_command(self.dash_video_temp_file_name, self.full_file_name))
            
            case DownloadOption.OnlyAudio:
                command.add(get_convent_command())
                command.add(self.get_rename_command(self.output_temp_file_name, self.full_file_name))
        
        return command.format()
    
    def get_flv_command(self):
        def create_list_file():
            with open(os.path.join(Config.Download.path, self.flv_list_file_name), "w", encoding = "utf-8") as f:
                f.write("\n".join([f"file flv_{self.task_info.id}_part{i + 1}.flv" for i in range(self.task_info.flv_video_count)]))

        def get_merge_command():
            return f'"{Config.FFmpeg.path}" -y -f concat -safe 0 -i "{self.flv_list_file_name}" -c copy "{self.output_temp_file_name}"'

        command = Command()

        if self.task_info.flv_video_count > 1:
            create_list_file()

            command.add(get_merge_command())
            command.add(self.get_rename_command(self.output_temp_file_name, self.full_file_name))
        else:
            command.add(self.get_rename_command(self.flv_temp_file_name, self.full_file_name))

        return command.format()

    def get_cut_command(self):
        command = Command()

        command.add(f'"{Config.FFmpeg.path}" -ss {self.cut_info.start_time} -to {self.cut_info.end_time} -i "{self.cut_info.input_path}" -acodec copy -vcodec copy "{self.cut_info.output_path}"')

        return command.format()

    def get_rename_command(self, src: str, dst: str):
        def get_sys_rename_command():
            match Platform(Config.Sys.platform):
                case Platform.Linux:
                    return "rename"

                case Platform.Linux | Platform.macOS:
                    return "mv"

        def get_escape_character():
            match Platform(Config.Sys.platform):
                case Platform.Windows | Platform.macOS:
                    return ""
                
                case Platform.Linux:
                    return "-- "

        return f'{get_sys_rename_command()} "{src}" {get_escape_character()}"{dst}"'
    
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

    def clear_temp_files(self):
        def get_dash_temp_file_list():
            match DownloadOption(self.task_info.download_option):
                case DownloadOption.VideoAndAudio:
                    temp_file_list.append(self.dash_video_temp_file_name)
                    temp_file_list.append(self.dash_audio_temp_file_name)

                case DownloadOption.OnlyVideo:
                    temp_file_list.append(self.dash_video_temp_file_name)

                case DownloadOption.OnlyAudio:
                    temp_file_list.append(self.dash_audio_temp_file_name)
            
            temp_file_list.append(self.output_temp_file_name)

        def get_flv_temp_file_list():
            if self.task_info.flv_video_count > 1:
                temp_file_list.append(self.flv_list_file_name)
                temp_file_list.extend([f"flv_{self.task_info.id}_part{i + 1}" for i in range(self.task_info.flv_video_count)])
            else:
                temp_file_list.append(self.flv_temp_file_name)

        def delete_file(file_list: list):
            for file in file_list:
                path = os.path.join(Config.Download.path, file)

                self.delete_specific_file(path)
        
        def worker():
            match StreamType(self.task_info.stream_type):
                case StreamType.Dash:
                    get_dash_temp_file_list()

                case StreamType.Flv:
                    get_flv_temp_file_list()

            delete_file(temp_file_list)
        
        temp_file_list = []
        
        Thread(target = worker).start()

    def delete_specific_file(self, path: str):
        while os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

    @property
    def ffmpeg_file_name(self):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                return "ffmpeg.exe"
            
            case Platform.Linux | Platform.macOS:
                return "ffmpeg"

    @property
    def dash_video_temp_file_name(self):
        return f"video_{self.task_info.id}.{self.task_info.video_type}"
    
    @property
    def dash_audio_temp_file_name(self):
        return f"audio_{self.task_info.id}.{self.task_info.audio_type}"

    @property
    def output_temp_file_name(self):
        return f"out_{self.task_info.id}.{self.task_info.output_type}"

    @property
    def flv_temp_file_name(self):
        return f"flv_{self.task_info.id}.flv"
    
    @property
    def flv_list_file_name(self):
        return f"flv_list_{self.task_info.id}.txt"