#!/usr/bin/env python3
"""
自动下载并安装 FFmpeg
"""

import os
import sys
import zipfile
import tempfile
from pathlib import Path
from urllib.request import urlopen, urlretrieve
import json

# FFmpeg 版本配置
# 使用 gyan.dev 提供的 Windows 构建版本
FFMPEG_VERSION = "2024-12-09-git-88f864e2e3"
FFMPEG_FILENAME = f"ffmpeg-{FFMPEG_VERSION}-essentials_build.zip"
FFMPEG_URL = f"https://www.gyan.dev/ffmpeg/builds/packages/{FFMPEG_FILENAME}"

# 目标目录
TARGET_DIR = Path(__file__).parent / "bin"

def download_with_progress(url, filepath):
    """下载文件并显示进度"""
    print(f"正在下载: {url}")
    
    def progress_hook(count, block_size, total_size):
        percent = int(count * block_size * 100 / total_size)
        downloaded_mb = count * block_size / (1024 * 1024)
        total_mb = total_size / (1024 * 1024)
        print(f"\r下载进度: {percent}% ({downloaded_mb:.1f}MB / {total_mb:.1f}MB)", end="")
    
    urlretrieve(url, filepath, reporthook=progress_hook)
    print()  # 换行

def extract_zip(zip_path, extract_dir):
    """解压 ZIP 文件"""
    print(f"\n正在解压到: {extract_dir}")
    
    import shutil
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # 获取 ZIP 内的根目录名
        all_names = zip_ref.namelist()
        root_dir = all_names[0].split('/')[0] if all_names else None
        
        if root_dir:
            # 解压到父目录
            zip_ref.extractall(extract_dir.parent)
            
            # 获取 bin 目录
            extracted_dir = extract_dir.parent / root_dir
            bin_dir = extracted_dir / "bin"
            
            if bin_dir.exists():
                # 复制 ffmpeg.exe 和 ffprobe.exe 到目标目录
                TARGET_DIR.mkdir(parents=True, exist_ok=True)
                
                for exe_name in ["ffmpeg.exe", "ffprobe.exe"]:
                    src = bin_dir / exe_name
                    dst = TARGET_DIR / exe_name
                    if src.exists():
                        shutil.copy2(str(src), str(dst))
                        print(f"已复制: {exe_name}")
                
                # 清理临时解压目录
                shutil.rmtree(extracted_dir)
                print(f"已清理临时目录: {extracted_dir}")
    
    print("安装完成!")

def main():
    print("=" * 60)
    print("FFmpeg 自动安装程序")
    print("=" * 60)
    
    # 检查是否已安装
    ffmpeg_exe = TARGET_DIR / "ffmpeg.exe"
    if ffmpeg_exe.exists():
        print(f"\n✅ FFmpeg 已安装在: {TARGET_DIR}")
        return
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        zip_path = temp_path / FFMPEG_FILENAME
        
        # 下载 FFmpeg
        try:
            download_with_progress(FFMPEG_URL, zip_path)
        except Exception as e:
            print(f"\n❌ 下载失败: {e}")
            print("\n请手动下载:")
            print(f"  URL: {FFMPEG_URL}")
            print(f"  然后解压 bin 目录下的 ffmpeg.exe 到: {TARGET_DIR}")
            return
        
        # 解压
        try:
            extract_zip(zip_path, TARGET_DIR)
        except Exception as e:
            print(f"\n 解压失败: {e}")
            return
    
    # 验证安装
    if ffmpeg_exe.exists():
        print(f"\n✅ FFmpeg 安装成功!")
        print(f"   路径: {ffmpeg_exe}")
        
        # 测试运行
        import subprocess
        result = subprocess.run(
            [str(ffmpeg_exe), "-version"],
            capture_output=True,
            text=True
        )
        first_line = result.stdout.strip().split('\n')[0]
        print(f"   {first_line}")
    else:
        print(f"\n 安装失败，ffmpeg.exe 不存在")

if __name__ == "__main__":
    main()
