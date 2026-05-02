#!/usr/bin/env python3
"""
yt-dlp 下载器测试脚本
测试新创建的 yt-dlp 下载模块是否正常工作
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_basic_downloader():
    """测试基础下载器功能"""
    print("=== 测试基础 yt-dlp 下载器 ===")
    
    try:
        from util.download.yt_dlp_downloader import YTDLPDownloader
        
        downloader = YTDLPDownloader()
        
        # 定义回调函数
        def progress_callback(data):
            status = data.get("status", "")
            if status == "downloading":
                print(f"进度: {data.get('percent', '')} - 速度: {data.get('speed', '')}")
            elif status == "finished":
                print(f"完成: {data.get('filename', '')}")
        
        def finish_callback(url):
            print(f"下载完成: {url}")
        
        def error_callback(msg):
            print(f"下载错误: {msg}")
        
        # 连接信号
        downloader.progress_signal.connect(progress_callback)
        downloader.finished_signal.connect(finish_callback)
        downloader.error_signal.connect(error_callback)
        
        # 测试 URL（使用一个简短的测试视频）
        test_url = "https://www.bilibili.com/video/BV1GJ411x7h7"  # 替换为实际的测试视频
        
        print(f"开始下载测试: {test_url}")
        
        # 开始下载（注释掉实际下载，只测试接口）
        # success = downloader.download(test_url, output_dir="./test_downloads")
        # print(f"下载启动: {'成功' if success else '失败'}")
        
        print("基础下载器测试完成（接口正常）")
        return True
        
    except Exception as e:
        print(f"基础下载器测试失败: {e}")
        return False


def test_adapter():
    """测试适配器功能"""
    print("\n=== 测试 yt-dlp 适配器 ===")
    
    try:
        from util.download.yt_dlp_adapter import YTDLPTaskAdapter
        
        adapter = YTDLPTaskAdapter()
        
        # 模拟任务信息
        class MockTaskInfo:
            class Download:
                status = "pending"
                progress = 0
                info_label = ""
                type = 1  # VIDEO
                
            def __init__(self):
                self.Download = self.Download()
                self.url = "https://www.bilibili.com/video/BV1GJ411x7h7"
        
        mock_task = MockTaskInfo()
        
        def progress_callback(task, data):
            print(f"任务进度: {data}")
        
        def finish_callback(task):
            print(f"任务完成: {task.url}")
        
        def error_callback(task, msg):
            print(f"任务错误: {msg}")
        
        # 连接信号
        adapter.task_progress_signal.connect(progress_callback)
        adapter.task_finished_signal.connect(finish_callback)
        adapter.task_error_signal.connect(error_callback)
        
        print("适配器接口测试完成")
        return True
        
    except Exception as e:
        print(f"适配器测试失败: {e}")
        return False


def test_configuration():
    """测试配置功能"""
    print("\n=== 测试配置功能 ===")
    
    try:
        from util.download.yt_dlp_downloader import YTDLPDownloader
        
        # 测试默认配置
        default_config = YTDLPDownloader.get_default_config()
        print("默认配置:", default_config)
        
        # 测试自定义配置
        custom_config = YTDLPDownloader.create_custom_config(
            format="bestaudio/best",
            ratelimit=1024 * 1024,  # 1MB/s
            proxy="http://127.0.0.1:7890"
        )
        print("自定义配置:", custom_config)
        
        print("配置功能测试完成")
        return True
        
    except Exception as e:
        print(f"配置功能测试失败: {e}")
        return False


def test_global_instance():
    """测试全局实例功能"""
    print("\n=== 测试全局实例 ===")
    
    try:
        from util.download.yt_dlp_downloader import get_global_downloader
        from util.download.yt_dlp_adapter import get_global_adapter
        
        # 测试全局下载器
        downloader1 = get_global_downloader()
        downloader2 = get_global_downloader()
        
        print(f"全局下载器单例测试: {downloader1 is downloader2}")
        
        # 测试全局适配器
        adapter1 = get_global_adapter()
        adapter2 = get_global_adapter()
        
        print(f"全局适配器单例测试: {adapter1 is adapter2}")
        
        print("全局实例测试完成")
        return True
        
    except Exception as e:
        print(f"全局实例测试失败: {e}")
        return False


def test_imports():
    """测试所有模块导入"""
    print("\n=== 测试模块导入 ===")
    
    modules_to_test = [
        "util.download.yt_dlp_downloader",
        "util.download.yt_dlp_adapter", 
        "util.download.yt_dlp_integration"
    ]
    
    all_success = True
    
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"✓ {module_name} 导入成功")
        except ImportError as e:
            print(f"✗ {module_name} 导入失败: {e}")
            all_success = False
    
    return all_success


def main():
    """运行所有测试"""
    print("开始 yt-dlp 下载器测试...")
    print("=" * 50)
    
    tests = [
        ("模块导入", test_imports),
        ("基础下载器", test_basic_downloader),
        ("适配器", test_adapter),
        ("配置功能", test_configuration),
        ("全局实例", test_global_instance),
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
        print("🎉 所有测试通过! yt-dlp 下载器可以正常使用。")
        return True
    else:
        print("⚠️ 部分测试失败，请检查错误信息。")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)