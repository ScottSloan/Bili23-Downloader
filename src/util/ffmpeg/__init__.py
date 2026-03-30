from util.common.enum import FFmpegSource
from util.common import config

from pathlib import Path
import logging
import shutil
import sys
import os

logger = logging.getLogger(__name__)

def set_ffmpeg_environment(path: str):
    os.environ["PATH"] = os.environ["PATH"] + os.pathsep + str(Path(path).parent)

    logger.info(f"已将 FFmpeg 路径 {path} 添加到环境变量")

# 确定不同平台 FFmpeg 可执行文件名
if sys.platform == "win32":
    ffmpeg_executable = "ffmpeg.exe"

else:
    ffmpeg_executable = "ffmpeg"

# 确定当前主程序是发行版还是开发版
if home := os.environ.get("PYSTAND_HOME"):
    cwd = Path(home)
else:
    cwd = Path.cwd()

config.ffmpeg_executable = ffmpeg_executable

bundle_ffmpeg_path = cwd / "bundle" / ffmpeg_executable

logger.info(f"正在检查附带的 FFmpeg 是否存在于 {bundle_ffmpeg_path}")

config.bundle_ffmpeg_exist = bundle_ffmpeg_path.exists()

match config.get(config.ffmpeg_source):
    case FFmpegSource.BUNDLED:
        # 检查 Bundle 目录中是否存在附带的 FFmpeg
        
        if not config.bundle_ffmpeg_exist:
            # 不存在则 fallback
            config.set(config.ffmpeg_source, FFmpegSource.SYSTEM)

            logger.warning("附带的 FFmpeg 不存在，将尝试使用环境变量中的 FFmpeg")

        else:
            # 将附带的 FFmpeg 路径添加到环境变量
            set_ffmpeg_environment(bundle_ffmpeg_path)
            
            logger.info("已添加附带的 FFmpeg 路径到环境变量")

    case FFmpegSource.SYSTEM:
        path_ffmpeg_executable = shutil.which(ffmpeg_executable)

        if not path_ffmpeg_executable:
            logger.error("环境变量中未找到 FFmpeg 可执行文件，正在检查附带的 FFmpeg")

            if config.bundle_ffmpeg_exist:
                # 如果环境变量中没有 FFmpeg，但附带的 FFmpeg 存在，则使用附带的 FFmpeg
                config.set(config.ffmpeg_source, FFmpegSource.BUNDLED)

                set_ffmpeg_environment(bundle_ffmpeg_path)

                logger.info("已切换到使用附带的 FFmpeg，并添加其路径到环境变量")

            else:
                logger.error("未找到 FFmpeg 可执行文件，且附带的 FFmpeg 也不存在，请检查设置中的 FFmpeg 配置")
            
        logger.info("使用环境变量中的 FFmpeg")

    case FFmpegSource.CUSTOM:
        # 将自定义的 FFmpeg 路径添加到环境变量
        set_ffmpeg_environment(config.get(config.custom_ffmpeg_path))

        logger.info("已添加自定义 FFmpeg 路径到环境变量")

from util.ffmpeg.command import FFmpegCommand
from util.ffmpeg.runner import FFmpegRunner
