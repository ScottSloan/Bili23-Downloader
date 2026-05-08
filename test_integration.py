#!/usr/bin/env python3
"""
测试修改后的 YTDLPDownloader 集成
"""

import os
import sys
import time
from pathlib import Path

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from util.download.downloader.yt_dlp_downloader import YTDLPDownloader, get_node_exe, FFMPEG_DIR

# 测试配置
TEST_URL = "https://www.youtube.com/shorts/kl8SjvE0g3w?feature=share"
OUTPUT_DIR = str(Path(__file__).parent / "test_downloads")
COOKIE_FILE = r"d:\Users\8567\Documents\Bili23\Bili23-Downloader\cookies.txt"

# 设置环境变量，使用外部的 Node.js 进行测试
os.environ['PATH'] = r"d:\Users\8567\Documents\yt-dlp\bin" + os.pathsep + os.environ.get('PATH', '')

def main():
    print("=" * 60)
    print("YTDLPDownloader 集成测试")
    print("=" * 60)
    
    # 检查配置
    node_exe = get_node_exe()
    print(f"Node.js 路径: {node_exe}")
    print(f"FFmpeg 目录: {FFMPEG_DIR}")
    print(f"Node.js 存在: {os.path.exists(node_exe)}")
    print(f"FFmpeg 目录存在: {os.path.isdir(FFMPEG_DIR) if FFMPEG_DIR else False}")
    print()
    
    # 创建下载器
    downloader = YTDLPDownloader()
    
    def progress_callback(data):
        if data['status'] == 'downloading':
            downloaded = data.get('downloaded_bytes', 0)
            total = data.get('total_bytes', 0)
            if total > 0:
                percent = (downloaded / total) * 100
                print(f"\r下载进度: {percent:.1f}%", end='')
    
    def finish_callback(url):
        print("\n✅ 下载完成!")
        print(f"下载的 URL: {url}")
    
    def error_callback(error_msg):
        print(f"\n❌ 下载失败: {error_msg}")
    
    downloader.set_callbacks(progress=progress_callback, finish=finish_callback, error=error_callback)
    
    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print(f"测试 URL: {TEST_URL}")
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"Cookies 文件: {COOKIE_FILE}")
    print()
    print("开始下载...")
    
    # 启动下载
    downloader.download(TEST_URL, OUTPUT_DIR, COOKIE_FILE)
    
    # 等待下载完成
    while downloader._is_downloading:
        time.sleep(1)
    
    print("\n测试完成!")

if __name__ == "__main__":
    main()
