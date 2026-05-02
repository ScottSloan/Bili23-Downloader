#!/usr/bin/env python3
"""
yt-dlp 升级功能测试脚本（独立版本）
不依赖 PySide6，直接测试核心模块
"""

import sys
import os
import time
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_task_status():
    """测试任务状态机"""
    print("=== 测试任务状态机 ===")
    
    try:
        # 直接导入，绕过 __init__.py
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "task_manager", 
            "src/util/download/task_manager.py"
        )
        task_manager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(task_manager)
        
        TaskStatus = task_manager.TaskStatus
        TaskPriority = task_manager.TaskPriority
        
        # 测试状态枚举
        assert TaskStatus.WAITING.value == "waiting"
        assert TaskStatus.DOWNLOADING.value == "downloading"
        assert TaskStatus.FINISHED.value == "finished"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.PAUSED.value == "paused"
        assert TaskStatus.CANCELLED.value == "cancelled"
        assert TaskStatus.RETRYING.value == "retrying"
        
        print("✓ 状态枚举测试通过")
        
        # 测试优先级枚举
        assert TaskPriority.LOW.value == 0
        assert TaskPriority.NORMAL.value == 1
        assert TaskPriority.HIGH.value == 2
        assert TaskPriority.URGENT.value == 3
        
        print("✓ 优先级枚举测试通过")
        
        return True
        
    except Exception as e:
        print(f"✗ 任务状态机测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_download_task():
    """测试下载任务数据类"""
    print("\n=== 测试下载任务 ===")
    
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "task_manager", 
            "src/util/download/task_manager.py"
        )
        task_manager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(task_manager)
        
        DownloadTask = task_manager.DownloadTask
        TaskStatus = task_manager.TaskStatus
        TaskPriority = task_manager.TaskPriority
        
        # 创建任务
        task = DownloadTask(
            url="https://www.bilibili.com/video/BV1GJ411x7h7",
            output_dir="./test_downloads",
            title="测试视频",
            priority=TaskPriority.HIGH
        )
        
        # 测试属性
        assert task.url == "https://www.bilibili.com/video/BV1GJ411x7h7"
        assert task.output_dir == "./test_downloads"
        assert task.title == "测试视频"
        assert task.status == TaskStatus.WAITING
        assert task.priority == TaskPriority.HIGH
        assert task.progress == 0.0
        assert task.retry_count == 0
        assert task.max_retries == 3
        
        print("✓ 任务创建测试通过")
        
        # 测试重试功能
        assert task.can_retry() == True
        task.increment_retry()
        assert task.retry_count == 1
        assert task.can_retry() == True
        
        print("✓ 重试功能测试通过")
        
        # 测试字典转换
        task_dict = task.to_dict()
        assert "task_id" in task_dict
        assert "url" in task_dict
        assert "status" in task_dict
        
        print("✓ 字典转换测试通过")
        
        return True
        
    except Exception as e:
        print(f"✗ 下载任务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_controlled_downloader():
    """测试受控下载器"""
    print("\n=== 测试受控下载器 ===")
    
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "task_manager", 
            "src/util/download/task_manager.py"
        )
        task_manager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(task_manager)
        
        ControlledDownloader = task_manager.ControlledDownloader
        DownloadTask = task_manager.DownloadTask
        
        # 创建任务
        task = DownloadTask(
            url="https://www.bilibili.com/video/BV1GJ411x7h7",
            output_dir="./test_downloads"
        )
        
        # 创建下载器
        downloader = ControlledDownloader(task)
        
        # 测试属性
        assert downloader.task == task
        assert downloader.is_running == False
        
        print("✓ 下载器创建测试通过")
        
        # 测试停止功能
        assert downloader.stop() == False  # 未运行时应该返回 False
        
        print("✓ 下载器控制测试通过")
        
        return True
        
    except Exception as e:
        print(f"✗ 受控下载器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_task_manager():
    """测试任务管理器"""
    print("\n=== 测试任务管理器 ===")
    
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "task_manager", 
            "src/util/download/task_manager.py"
        )
        task_manager_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(task_manager_module)
        
        TaskManager = task_manager_module.TaskManager
        DownloadTask = task_manager_module.DownloadTask
        TaskStatus = task_manager_module.TaskStatus
        
        # 创建任务管理器
        manager = TaskManager(max_concurrent=1)
        
        # 测试初始状态
        assert len(manager.queue) == 0
        assert manager.current is None
        assert len(manager.finished_tasks) == 0
        assert len(manager.failed_tasks) == 0
        
        print("✓ 任务管理器初始化测试通过")
        
        # 添加任务
        task1 = DownloadTask(
            url="https://www.bilibili.com/video/BV1GJ411x7h7",
            output_dir="./test_downloads",
            title="测试视频1"
        )
        
        task2 = DownloadTask(
            url="https://www.bilibili.com/video/BV1GJ411x7h8",
            output_dir="./test_downloads",
            title="测试视频2"
        )
        
        task_id1 = manager.add_task(task1)
        task_id2 = manager.add_task(task2)
        
        assert len(manager.queue) == 2
        assert task_id1 == task1.task_id
        assert task_id2 == task2.task_id
        
        print("✓ 添加任务测试通过")
        
        # 测试队列状态
        status = manager.get_queue_status()
        assert status["queue_length"] == 2
        assert status["current_task"] is None
        assert status["finished_count"] == 0
        assert status["failed_count"] == 0
        
        print("✓ 队列状态测试通过")
        
        # 测试查找任务
        found_task = manager.get_task(task_id1)
        assert found_task == task1
        
        print("✓ 查找任务测试通过")
        
        # 测试取消任务
        assert manager.cancel_task(task_id2) == True
        assert len(manager.queue) == 1
        assert task2.status == TaskStatus.CANCELLED
        
        print("✓ 取消任务测试通过")
        
        # 测试清除功能
        manager.clear_finished()
        manager.clear_failed()
        
        print("✓ 清除功能测试通过")
        
        return True
        
    except Exception as e:
        print(f"✗ 任务管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_architecture():
    """测试架构正确性"""
    print("\n=== 测试架构正确性 ===")
    
    try:
        import importlib.util
        
        # 加载 task_manager 模块
        spec = importlib.util.spec_from_file_location(
            "task_manager", 
            "src/util/download/task_manager.py"
        )
        task_manager_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(task_manager_module)
        
        TaskManager = task_manager_module.TaskManager
        ControlledDownloader = task_manager_module.ControlledDownloader
        
        # 验证 TaskManager 管理下载器
        manager = TaskManager()
        assert hasattr(manager, 'current_downloader')
        
        print("✓ TaskManager 管理下载器测试通过")
        
        # 验证架构层次
        assert hasattr(manager, 'queue')
        assert hasattr(manager, 'current')
        assert hasattr(manager, 'finished_tasks')
        assert hasattr(manager, 'failed_tasks')
        
        print("✓ 架构层次测试通过")
        
        # 验证 ControlledDownloader 有 start/stop/retry
        assert hasattr(ControlledDownloader, 'start')
        assert hasattr(ControlledDownloader, 'stop')
        assert hasattr(ControlledDownloader, 'retry')
        
        print("✓ ControlledDownloader 接口测试通过")
        
        return True
        
    except Exception as e:
        print(f"✗ 架构测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_creation():
    """测试文件创建"""
    print("\n=== 测试文件创建 ===")
    
    files_to_check = [
        'src/util/download/task_manager.py',
        'src/util/download/yt_dlp_ui_delegate.py',
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


def main():
    """运行所有测试"""
    print("开始 yt-dlp 升级功能测试...")
    print("=" * 50)
    
    tests = [
        ("文件创建", test_file_creation),
        ("任务状态机", test_task_status),
        ("下载任务", test_download_task),
        ("受控下载器", test_controlled_downloader),
        ("任务管理器", test_task_manager),
        ("架构正确性", test_architecture),
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
        print("🎉 所有升级功能测试通过!")
        print("\n架构说明:")
        print("  UI → TaskManager → ControlledDownloader")
        print("\n核心组件:")
        print("  - TaskStatus: 任务状态机")
        print("  - DownloadTask: 下载任务数据类")
        print("  - ControlledDownloader: 受控下载器 (start/stop/retry)")
        print("  - TaskManager: 任务管理器 (队列管理)")
        print("  - YTDLPUIDelegate: UI 代理 (解耦层)")
        return True
    else:
        print("⚠️ 部分测试失败，请检查错误信息。")
        return False


if __name__ == "__main__":
    # 切换到项目根目录
    os.chdir(Path(__file__).parent)
    
    success = main()
    sys.exit(0 if success else 1)