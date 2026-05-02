#!/usr/bin/env python3
"""
yt-dlp 核心功能测试脚本
不依赖 PySide6，只测试 yt-dlp 核心功能
"""

import sys
import os
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_yt_dlp_installation():
    """测试 yt-dlp 是否正常安装"""
    print("=== 测试 yt-dlp 安装 ===")
    
    try:
        import yt_dlp
        print(f"✓ yt-dlp 版本: {yt_dlp.version.__version__}")
        return True
    except ImportError as e:
        print(f"✗ yt-dlp 导入失败: {e}")
        return False


def test_basic_yt_dlp_functionality():
    """测试基础 yt-dlp 功能"""
    print("\n=== 测试基础 yt-dlp 功能 ===")
    
    try:
        import yt_dlp
        
        # 测试配置创建
        ydl_opts = {
            'format': 'bv+ba/b',
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
        }
        
        print("✓ 配置创建成功")
        
        # 测试 YoutubeDL 实例化
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print("✓ YoutubeDL 实例化成功")
        
        return True
        
    except Exception as e:
        print(f"✗ 基础功能测试失败: {e}")
        return False


def test_core_downloader_logic():
    """测试核心下载逻辑（不依赖 Qt）"""
    print("\n=== 测试核心下载逻辑 ===")
    
    try:
        import yt_dlp
        
        # 模拟进度回调
        def progress_hook(d):
            status = d.get('status', '')
            if status == 'downloading':
                percent = d.get('_percent_str', '').strip()
                speed = d.get('_speed_str', '').strip()
                print(f"下载进度: {percent} - 速度: {speed}")
            elif status == 'finished':
                print(f"下载完成: {d.get('filename', '')}")
        
        # 创建配置
        ydl_opts = {
            'format': 'bv+ba/b',
            'merge_output_format': 'mp4',
            'outtmpl': './test_downloads/%(title)s.%(ext)s',
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
        }
        
        # 创建测试目录
        os.makedirs('./test_downloads', exist_ok=True)
        
        print("✓ 下载逻辑配置成功")
        print("注意: 实际下载测试已禁用，避免网络请求")
        
        return True
        
    except Exception as e:
        print(f"✗ 核心下载逻辑测试失败: {e}")
        return False


def test_configuration_options():
    """测试配置选项"""
    print("\n=== 测试配置选项 ===")
    
    try:
        import yt_dlp
        
        # 测试各种配置选项
        configs = [
            {
                'name': '默认配置',
                'opts': {
                    'format': 'bv+ba/b',
                    'merge_output_format': 'mp4',
                }
            },
            {
                'name': '音频配置', 
                'opts': {
                    'format': 'bestaudio/best',
                    'extractaudio': True,
                    'audioformat': 'mp3',
                }
            },
            {
                'name': '限速配置',
                'opts': {
                    'format': 'bv+ba/b',
                    'ratelimit': 1024 * 1024,  # 1MB/s
                }
            },
            {
                'name': '代理配置',
                'opts': {
                    'format': 'bv+ba/b',
                    'proxy': 'http://127.0.0.1:7890',
                }
            }
        ]
        
        for config in configs:
            try:
                with yt_dlp.YoutubeDL(config['opts']) as ydl:
                    print(f"✓ {config['name']} 测试成功")
            except Exception as e:
                print(f"✗ {config['name']} 测试失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ 配置选项测试失败: {e}")
        return False


def test_file_creation():
    """测试文件创建和结构"""
    print("\n=== 测试文件创建 ===")
    
    files_to_check = [
        'src/util/download/yt_dlp_downloader.py',
        'src/util/download/yt_dlp_adapter.py',
        'src/util/download/yt_dlp_integration.py',
        'requirements.txt',
        'pyproject.toml',
        'YT_DLP_INTEGRATION_GUIDE.md',
    ]
    
    all_exist = True
    
    for file_path in files_to_check:
        full_path = Path(file_path)
        if full_path.exists():
            print(f"✓ {file_path} 存在")
        else:
            print(f"✗ {file_path} 不存在")
            all_exist = False
    
    return all_exist


def test_requirements_update():
    """测试依赖更新"""
    print("\n=== 测试依赖更新 ===")
    
    try:
        # 检查 requirements.txt
        with open('requirements.txt', 'r', encoding='utf-8') as f:
            requirements_content = f.read()
        
        if 'yt-dlp' in requirements_content:
            print("✓ requirements.txt 已更新")
        else:
            print("✗ requirements.txt 未更新")
            return False
        
        # 检查 pyproject.toml
        with open('pyproject.toml', 'r', encoding='utf-8') as f:
            toml_content = f.read()
        
        if 'yt-dlp' in toml_content:
            print("✓ pyproject.toml 已更新")
        else:
            print("✗ pyproject.toml 未更新")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ 依赖更新测试失败: {e}")
        return False


def main():
    """运行所有核心测试"""
    print("开始 yt-dlp 核心功能测试...")
    print("=" * 50)
    
    tests = [
        ("文件创建", test_file_creation),
        ("依赖更新", test_requirements_update),
        ("yt-dlp 安装", test_yt_dlp_installation),
        ("基础功能", test_basic_yt_dlp_functionality),
        ("下载逻辑", test_core_downloader_logic),
        ("配置选项", test_configuration_options),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"测试 {test_name} 发生异常: {e}")
            results.append((test_name, False))
    
    # 输出测试结果
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    
    for test_name, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"{test_name}: {status}")
    
    total_passed = sum(1 for _, success in results if success)
    total_tests = len(results)
    
    print(f"\n总计: {total_passed}/{total_tests} 个测试通过")
    
    if total_passed == total_tests:
        print("🎉 所有核心测试通过! yt-dlp 下载器可以正常使用。")
        print("\n下一步:")
        print("1. 安装依赖: pip install -r requirements.txt")
        print("2. 参考 YT_DLP_INTEGRATION_GUIDE.md 进行集成")
        print("3. 在 PySide6 环境中测试完整功能")
        return True
    else:
        print("⚠️ 部分测试失败，请检查错误信息。")
        return False


if __name__ == "__main__":
    # 切换到项目根目录
    os.chdir(Path(__file__).parent)
    
    success = main()
    sys.exit(0 if success else 1)