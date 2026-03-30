from PySide6.QtCore import QStandardPaths, QFile, QTextStream

from functools import wraps
from pathlib import Path
import webbrowser

def ensure_file_exists(func):
    # 检查文件是否已经释放到临时目录
    @wraps(func)
    def wrapper(cls, file_name: str, *args, **kwargs):
        temp_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.TempLocation)

        file_path = Path(temp_dir, file_name)

        if not file_path.exists():
            # 从资源文件中读取内容并写入临时目录
            file = QFile(f":/bili23/html/{file_name}")

            if file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text):
                stream = QTextStream(file)
                content = stream.readAll()

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

        return func(cls, file_name, str(file_path), *args, **kwargs)
    
    return wrapper

class WebPage:
    """
    调用系统默认浏览器打开本地 HTML 文件的工具类
    """

    @classmethod
    @ensure_file_exists
    def open(cls, file_name: str, file_path: str = None):
        """
        调用系统默认浏览器打开对应的 HTML 文件
        """
        webbrowser.open(file_path)
