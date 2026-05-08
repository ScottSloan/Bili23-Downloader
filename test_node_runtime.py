#!/usr/bin/env python3
"""
测试 NodeRuntime 集成
"""

import sys
from pathlib import Path

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from util.runtime.node_runtime import NodeRuntime

def main():
    print("=" * 60)
    print("NodeRuntime 集成测试")
    print("=" * 60)
    
    # 创建 NodeRuntime 实例
    node = NodeRuntime()
    
    # 检查 Node.js 是否存在
    print(f"Node.js 路径: {node.node_path}")
    print(f"Node.js 存在: {node.exists()}")
    
    if not node.exists():
        print("\n❌ Node.js 不存在！")
        print("请将 Portable Node.js 解压到:")
        print(f"  {node.node_dir}")
        return
    
    # 获取版本
    version = node.get_version()
    print(f"Node.js 版本: {version}")
    
    # 添加到 PATH
    node.add_to_path()
    print(f"已添加到 PATH: {node.node_dir}")
    
    # 测试执行 JS 代码
    print("\n--- 测试执行 JS 代码 ---")
    result = node.run_code('console.log("Hello from Node.js " + process.version)')
    print(result)
    
    # 测试执行 JS 文件
    print("\n--- 测试执行 JS 文件 ---")
    test_js = Path(__file__).parent / "scripts" / "test.js"
    if test_js.exists():
        result = node.run_js(str(test_js))
        print(f"stdout: {result['stdout']}")
        print(f"stderr: {result['stderr']}")
        print(f"returncode: {result['returncode']}")
    else:
        print(f"测试文件不存在: {test_js}")
    
    print("\n✅ NodeRuntime 测试完成!")

if __name__ == "__main__":
    main()
