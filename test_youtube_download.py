#!/usr/bin/env python3
"""
YouTube 视频下载自动化测试脚本
测试 URL: https://www.youtube.com/shorts/kl8SjvE0g3w?feature=share
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent / "src"
sys.path.insert(0, str(project_root))

import logging
import threading
import time
from yt_dlp import YoutubeDL

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] - %(name)s - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 测试配置
TEST_URL = "https://www.youtube.com/shorts/kl8SjvE0g3w?feature=share"
OUTPUT_DIR = str(Path(__file__).parent / "test_downloads")
COOKIE_FILE = r"d:\Users\8567\Documents\cookies.txt"  # cookies 文件路径
PROXY = "http://127.0.0.1:65532"  # 代理地址
NODE_EXE = r"d:\Users\8567\Documents\yt-dlp\bin\node.exe"  # Node.js 路径
FFMPEG_EXE = r"d:\Users\8567\Documents\yt-dlp\bin\ffmpeg.exe"  # ffmpeg 路径

def find_cookie_file():
    """尝试查找 cookies 文件"""
    # 常见位置
    possible_paths = [
        Path.home() / "cookies.txt",
        Path(__file__).parent / "cookies.txt",
        Path(__file__).parent / "src" / "cookies.txt",
    ]
    
    for path in possible_paths:
        if path.exists():
            logger.info(f"找到 cookies 文件: {path}")
            return str(path)
    
    logger.warning("未找到 cookies 文件，将尝试从浏览器获取")
    return None

def main():
    """主测试函数"""
    print("=" * 60)
    print("YouTube 视频下载自动化测试")
    print("=" * 60)
    print(f"测试 URL: {TEST_URL}")
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"Cookies 文件: {COOKIE_FILE}")
    print(f"代理地址: {PROXY}")
    print()
    
    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 验证 cookies 文件
    if not os.path.exists(COOKIE_FILE):
        print(f"❌ Cookies 文件不存在: {COOKIE_FILE}")
        return False
    
    # 进度跟踪变量
    download_finished = threading.Event()
    download_error = [None]
    
    def progress_hook(d):
        """进度回调"""
        status = d.get("status", "")
        if status == "downloading":
            percent = d.get("_percent_str", "N/A").strip()
            speed = d.get("_speed_str", "N/A").strip()
            eta = d.get("_eta_str", "N/A").strip()
            print(f"\r下载中: {percent} | 速度: {speed} | 剩余时间: {eta}", end="", flush=True)
        elif status == "finished":
            print(f"\n片段下载完成: {d.get('filename', 'N/A')}")
    
    def on_finish():
        """完成回调"""
        print("\n\n✅ 下载完成!")
        download_finished.set()
    
    def on_error(error_msg):
        """错误回调"""
        print(f"\n\n❌ 下载失败: {error_msg}")
        download_error[0] = error_msg
        download_finished.set()
    
    # 配置 yt-dlp 选项
    ydl_opts = {
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "outtmpl": f"{OUTPUT_DIR}/%(title)s [%(id)s].%(ext)s",
        "progress_hooks": [progress_hook],
        "retries": 3,
        "fragment_retries": 3,
        "concurrent_fragment_downloads": 4,
        "quiet": False,
        "no_warnings": False,
        "verbose": True,
        "cookiefile": COOKIE_FILE,
        "proxy": PROXY if PROXY else None,
        "ffmpeg_location": str(Path(FFMPEG_EXE).parent),
        "extractor_args": {
            "youtube": {
                "player_client": ["android_vr", "tv"],
                "player_skip": ["web", "mweb", "android", "ios"],
            }
        },
        "forceipv4": True,
        "nocheckcertificate": True,
        "js_runtimes": {"node": {"path": NODE_EXE}},
    }
    
    # 开始下载
    print("开始下载...")
    
    def download():
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([TEST_URL])
            on_finish()
        except Exception as e:
            on_error(str(e))
    
    download_thread = threading.Thread(target=download, daemon=True)
    download_thread.start()
    
    # 等待下载完成（最多等待 5 分钟）
    print("等待下载完成...")
    result = download_finished.wait(timeout=300)
    
    if result:
        if download_error[0]:
            print(f"\n测试失败: {download_error[0]}")
            return False
        else:
            print("\n测试成功!")
            # 列出下载的文件
            print("\n下载的文件:")
            for f in Path(OUTPUT_DIR).iterdir():
                if f.is_file():
                    size_mb = f.stat().st_size / (1024 * 1024)
                    print(f"  📄 {f.name} ({size_mb:.2f} MB)")
            return True
    else:
        print("\n测试超时（5 分钟）")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
