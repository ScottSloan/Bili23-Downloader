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
    os.environ["PATH"] = os.environ["PATH"] + os.pathsep + str(Path(path).parent)

    logger.info(f"已将 FFmpeg 路径 {path} 添加到环境变量")

    config.no_ffmpeg_available = False

def check_environment_ffmpeg():
    ffmpeg_path = shutil.which(ffmpeg_executable)

    if ffmpeg_path:
        logger.info(f"环境变量中找到 FFmpeg 可执行文件：{ffmpeg_path}")

        set_ffmpeg_environment(ffmpeg_path)
    else:
        logger.warning("环境变量中未找到 FFmpeg 可执行文件")

    return ffmpeg_path

def try_fallback_to_bundled_ffmpeg():
    if config.bundle_ffmpeg_exist:
        config.set(config.ffmpeg_source, FFmpegSource.BUNDLED)

        set_ffmpeg_environment(bundle_ffmpeg_path)
    else:
        logger.error("没有可用的 FFmpeg 可执行文件")

cwd = Directory.get_cwd()

config.ffmpeg_executable = ffmpeg_executable

bundle_ffmpeg_path = cwd / "bundle" / ffmpeg_executable

config.bundle_ffmpeg_exist = bundle_ffmpeg_path.exists()

if config.bundle_ffmpeg_exist:
    logger.info("检测到附带的 FFmpeg 可执行文件：" + str(bundle_ffmpeg_path))

match config.get(config.ffmpeg_source):
    case FFmpegSource.BUNDLED:
        # 检查 Bundle 目录中是否存在附带的 FFmpeg
        
        if not config.bundle_ffmpeg_exist:
            # 不存在则 fallback
            config.set(config.ffmpeg_source, FFmpegSource.SYSTEM)

            check_environment_ffmpeg()

            logger.warning("附带的 FFmpeg 不存在，将尝试使用环境变量中的 FFmpeg")
        else:
            # 将附带的 FFmpeg 路径添加到环境变量
            set_ffmpeg_environment(bundle_ffmpeg_path)
            
    case FFmpegSource.SYSTEM:
        path_ffmpeg_executable = check_environment_ffmpeg()

        if not path_ffmpeg_executable:
            # 尝试 fallback 到附带的 FFmpeg
            try_fallback_to_bundled_ffmpeg()
            
    case FFmpegSource.CUSTOM:
        # 将自定义的 FFmpeg 路径添加到环境变量
        custom_ffmpeg_path = Path(config.get(config.custom_ffmpeg_path), ffmpeg_executable)

        # 检查自定义路径是否存在 FFmpeg 可执行文件
        if custom_ffmpeg_path.exists():
            set_ffmpeg_environment(custom_ffmpeg_path)
        else:
            logger.warning(f"自定义 FFmpeg 路径无效，未找到 FFmpeg 可执行文件：{custom_ffmpeg_path}")

            # 尝试 fallback 到环境变量中的 FFmpeg
            try_fallback_to_bundled_ffmpeg()

from util.ffmpeg.command import FFmpegCommand
from util.ffmpeg.runner import FFmpegRunner
