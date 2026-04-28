from util.common.enum import FFmpegSource
from util.common import config, Directory

from pathlib import Path
import logging
import shutil
import sys
import os

logger = logging.getLogger(__name__)

# 确定不同平台 FFmpeg 可执行文件名
if sys.platform == "win32":
    ffmpeg_executable = "ffmpeg.exe"

else:
    ffmpeg_executable = "ffmpeg"

def set_ffmpeg_environment(path: str):
    os.environ["PATH"] = str(Path(path).parent) + os.pathsep + os.environ["PATH"]

    logger.info(f"已将 FFmpeg 路径 {path} 添加到环境变量")

    config.no_ffmpeg_available = False

def try_system_ffmpeg():
    ffmpeg_path = shutil.which(ffmpeg_executable)

    if ffmpeg_path:
        logger.info(f"环境变量中找到 FFmpeg 可执行文件：{ffmpeg_path}")
        set_ffmpeg_environment(ffmpeg_path)
        return True
    
    logger.warning("环境变量中未找到 FFmpeg 可执行文件")
    return False

def try_bundled_ffmpeg():
    if config.bundle_ffmpeg_exist:
        logger.info(f"找到附带的 FFmpeg 可执行文件：{bundle_ffmpeg_path}")
        set_ffmpeg_environment(bundle_ffmpeg_path)
        return True
        
    logger.warning("没有找到附带的 FFmpeg 可执行文件")
    return False

def on_ffmpeg_not_found():
    logger.error("没有可用的 FFmpeg 可执行文件")
    config.no_ffmpeg_available = True
    return False

cwd = Directory.get_cwd()

config.ffmpeg_executable = ffmpeg_executable
bundle_ffmpeg_path = cwd / "bundle" / ffmpeg_executable
config.bundle_ffmpeg_exist = bundle_ffmpeg_path.exists()

match config.get(config.ffmpeg_source):
    case FFmpegSource.BUNDLED:
        if not try_bundled_ffmpeg():
            logger.warning("附带的 FFmpeg 不存在，将尝试使用环境变量中的 FFmpeg")
            
            if try_system_ffmpeg():
                config.set(config.ffmpeg_source, FFmpegSource.SYSTEM)
            else:
                on_ffmpeg_not_found()
                
    case FFmpegSource.SYSTEM:
        if not try_system_ffmpeg():
            logger.warning("环境变量中无 FFmpeg，将尝试使用附带的 FFmpeg")
            
            if try_bundled_ffmpeg():
                config.set(config.ffmpeg_source, FFmpegSource.BUNDLED)
            else:
                on_ffmpeg_not_found()
            
    case FFmpegSource.CUSTOM:
        custom_ffmpeg_path = Path(config.get(config.custom_ffmpeg_path), ffmpeg_executable)

        if custom_ffmpeg_path.exists():
            set_ffmpeg_environment(custom_ffmpeg_path)
        else:
            logger.warning(f"自定义 FFmpeg 路径无效：{custom_ffmpeg_path}，将尝试 fallback")

            if try_bundled_ffmpeg():
                config.set(config.ffmpeg_source, FFmpegSource.BUNDLED)

            elif try_system_ffmpeg():
                config.set(config.ffmpeg_source, FFmpegSource.SYSTEM)
                
            else:
                on_ffmpeg_not_found()

from .command import FFmpegCommand
from .runner import FFmpegRunner
