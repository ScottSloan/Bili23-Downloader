from util.common.enum import FFmpegSource
from util.common.config import config

from pathlib import Path
import logging
import sys
import os

logger = logging.getLogger(__name__)

# 确定不同平台 FFmpeg 可执行文件名
if sys.platform == "win32":
    ffmpeg_executable = "ffmpeg.exe"

else:
    ffmpeg_executable = "ffmpeg"

config.ffmpeg_executable = ffmpeg_executable

match config.get(config.ffmpeg_source):
    case FFmpegSource.BUNDLED:
        # 检查 Bundle 目录中是否存在附带的 FFmpeg
        bundle_ffmpeg_exist = Path(Path.cwd(), "bundle", ffmpeg_executable).exists()

        if not bundle_ffmpeg_exist:
            # 不存在则 fallback
            config.set(config.ffmpeg_source, FFmpegSource.SYSTEM)

            logger.warning("附带的 FFmpeg 不存在，将尝试使用环境变量中的 FFmpeg")

        else:
            # 将附带的 FFmpeg 路径添加到环境变量
            os.environ["PATH"] = os.environ["PATH"] + os.pathsep + str(Path.cwd() / "bundle")

            logger.info("已添加附带的 FFmpeg 路径到环境变量")

        # 临时标记 bundle_ffmpeg_exist
        config.bundle_ffmpeg_exist = bundle_ffmpeg_exist

    case FFmpegSource.CUSTOM:
        # 将自定义的 FFmpeg 路径添加到环境变量
        os.environ["PATH"] = os.environ["PATH"] + os.pathsep + str(Path(config.get(config.custom_ffmpeg_path)).parent)

        logger.info("已添加自定义 FFmpeg 路径到环境变量")
