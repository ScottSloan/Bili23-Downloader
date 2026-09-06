"""
需要弹窗的目录操作

`util/common/io/directory.py` 里其余的方法都是纯粹的文件系统操作，只有选目录要弹
QFileDialog —— 为了它一个方法，整个 Directory 类（下载链路与 FFmpeg 都在用）
会被 QtWidgets 传染，WebUI 进程里连 import 都做不到。所以把它单独挪到界面侧。
"""

from PySide6.QtWidgets import QFileDialog, QWidget

from util.common.io.directory import Directory

def browse_directory(parent: QWidget, title: str, default_path: str = ""):
    """
    弹出选择目录对话框

    返回值有三种含义，沿用原实现，调用方按此分支：
    选了可用目录 → 该路径；选了不可写的目录 → None；取消 → default_path
    """
    dir_path = QFileDialog.getExistingDirectory(
        parent, title, default_path,
        QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
    )

    if dir_path:
        if Directory.ensure_directory_accessible(dir_path):
            return dir_path

        return None

    else:
        return default_path
