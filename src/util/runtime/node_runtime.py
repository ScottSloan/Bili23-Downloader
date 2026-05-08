import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class NodeRuntime:
    """
    Portable Node.js Runtime Manager
    """

    def __init__(self):
        root = Path(__file__).resolve().parent.parent.parent.parent
        self.node_dir = root / "bin" / "node"
        self.node_path = self.node_dir / "node.exe"
        self.npm_path = self.node_dir / "npm.cmd"

    def exists(self):
        """检查 Node.js 是否存在"""
        return self.node_path.exists()

    def get_version(self):
        """获取 Node.js 版本"""
        if not self.exists():
            return None
        try:
            result = subprocess.run(
                [str(self.node_path), "-v"],
                capture_output=True,
                text=True,
                encoding="utf-8"
            )
            return result.stdout.strip()
        except Exception as e:
            logger.error(f"获取 Node.js 版本失败: {e}")
            return None

    def run_js(self, script_path, args=None):
        """
        执行 JS 文件
        
        Args:
            script_path: JS 文件路径
            args: 传递给脚本的参数列表
            
        Returns:
            dict: 包含 returncode, stdout, stderr
        """
        if not self.exists():
            raise FileNotFoundError("node.exe 不存在")

        cmd = [str(self.node_path), str(script_path)]

        if args:
            cmd.extend(args)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )

        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }

    def run_code(self, js_code):
        """
        直接执行 JS 字符串
        
        Args:
            js_code: JavaScript 代码字符串
            
        Returns:
            str: 标准输出
        """
        result = subprocess.run(
            [str(self.node_path), "-e", js_code],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )

        return result.stdout

    def npm_install(self, package_name):
        """
        安装 npm 包
        
        Args:
            package_name: 包名
            
        Returns:
            str: 安装输出
        """
        result = subprocess.run(
            [str(self.npm_path), "install", package_name],
            cwd=str(self.node_dir),
            capture_output=True,
            text=True,
            encoding="utf-8"
        )

        return result.stdout

    def add_to_path(self):
        """将 Node.js 目录添加到 PATH 环境变量"""
        import os
        node_dir = str(self.node_dir)
        if node_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] += ";" + node_dir
            logger.info(f"已将 Node.js 目录添加到 PATH: {node_dir}")
