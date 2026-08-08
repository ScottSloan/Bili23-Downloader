from ..common.io.directory import Directory
from ..common.enum import FFmpegSource
from ..common.config import config

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

bundle_ffmpeg_path = None

_initialized = False

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

def get_bundle_ffmpeg_path():
    return Directory.get_cwd() / "bundle" / ffmpeg_executable

def on_ffmpeg_not_found():
    logger.error("没有可用的 FFmpeg 可执行文件")
    config.no_ffmpeg_available = True
    return False

def init_ffmpeg():
    # 探测 FFmpeg 需要扫描 PATH 与安装目录，属于磁盘 IO。此前该逻辑写在模块顶层，
    # 任何一次 util 子模块导入都会连带执行，白白占用启动的关键路径，现改为显式调用。
    global bundle_ffmpeg_path, _initialized

    if _initialized:
        return

    _initialized = True

    config.ffmpeg_executable = ffmpeg_executable

    bundle_ffmpeg_path = get_bundle_ffmpeg_path()
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
            custom_ffmpeg_path = Path(config.get(config.custom_ffmpeg_path))

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
