#!/usr/bin/env python3
"""
自动下载并安装 Portable Node.js
"""

import os
import sys
import zipfile
import tempfile
from pathlib import Path
from urllib.request import urlopen, urlretrieve
import json

# Node.js 版本配置
NODE_VERSION = "22.14.0"  # LTS 版本
NODE_ARCH = "win-x64"
NODE_FILENAME = f"node-v{NODE_VERSION}-{NODE_ARCH}.zip"
NODE_URL = f"https://nodejs.org/dist/v{NODE_VERSION}/{NODE_FILENAME}"

# 目标目录
TARGET_DIR = Path(__file__).parent / "bin" / "node"

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
            
            # 如果解压后的目录名不是目标目录，移动内容
            extracted_dir = extract_dir.parent / root_dir
            if extracted_dir != extract_dir:
                # 如果目标目录已存在，先删除
                if extract_dir.exists():
                    shutil.rmtree(extract_dir)
                
                # 移动所有文件到目标目录
                shutil.move(str(extracted_dir), str(extract_dir))
                print(f"已移动: {extracted_dir} -> {extract_dir}")
    
    print("解压完成!")

def main():
    print("=" * 60)
    print("Portable Node.js 自动安装程序")
    print("=" * 60)
    
    # 检查是否已安装
    node_exe = TARGET_DIR / "node.exe"
    if node_exe.exists():
        print(f"\n✅ Node.js 已安装在: {TARGET_DIR}")
        print(f"   版本: {node_exe}")
        return
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        zip_path = temp_path / NODE_FILENAME
        
        # 下载 Node.js
        try:
            download_with_progress(NODE_URL, zip_path)
        except Exception as e:
            print(f"\n❌ 下载失败: {e}")
            print("\n请手动下载:")
            print(f"  URL: {NODE_URL}")
            print(f"  然后解压到: {TARGET_DIR}")
            return
        
        # 解压
        try:
            extract_zip(zip_path, TARGET_DIR)
        except Exception as e:
            print(f"\n❌ 解压失败: {e}")
            return
    
    # 验证安装
    if node_exe.exists():
        print(f"\n✅ Node.js 安装成功!")
        print(f"   路径: {node_exe}")
        
        # 测试运行
        import subprocess
        result = subprocess.run(
            [str(node_exe), "-v"],
            capture_output=True,
            text=True
        )
        print(f"   版本: {result.stdout.strip()}")
    else:
        print(f"\n❌ 安装失败，node.exe 不存在")

if __name__ == "__main__":
    main()
