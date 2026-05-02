"""
此脚本用于提取项目中的翻译字符串并生成 .ts 文件，供翻译人员使用 Qt Linguist 进行翻译。
使用前请确保已安装 PySide6，并且 pyside6-lupdate 命令可用（如果使用虚拟环境，需激活后再运行此脚本）。
运行后会在 src/res/i18n/ 目录下生成或更新目标语言文件，其中包含项目中所有需要翻译的字符串。
翻译完成后，使用 lrelease 命令将 .ts 文件编译成 .qm 文件，供应用程序加载使用。

This script is used to extract translation strings from the project and generate .ts files for translators to use with Qt Linguist.
Before using, make sure you have PySide6 installed and the pyside6-lupdate command is available (if using a virtual environment, activate it before running this script).
After running, it will generate or update the target language file in the src/res/i18n/ directory, which contains all the strings that need to be translated in the project.
After translation is complete, use the lrelease command to compile the .ts file into a .qm file for the application to load and use.
"""

import subprocess
import os

# ------- 配置 (Configuration) ---------


# 目标语言
# Target language (e.g., "zh_CN" for Simplified Chinese, "en_US" for English)
target_language = "zh_TW"


# 项目根目录（请根据实际情况修改）
# Project root directory (please modify according to your actual situation)
project_root = r"D:\Projects\Python\Bili23_Downloader_Fluent"


# ---------- 代码实现 (Code Implementation) ---------

# lupdate 可执行文件（如果已激活虚拟环境，直接用命令即可）
lupdate_cmd = "pyside6-lupdate"

# 需要翻译的源文件列表（用正斜杠）
sources = [
    "src/gui/component/download_list/item_delegate.py",
    "src/gui/component/download_list/list_view.py",
    "src/gui/component/download_list/top_widget.py",
    "src/gui/component/entry_list/entry_item_delegate.py",
    "src/gui/component/entry_list/list_view.py",
    "src/gui/component/parse_list/model.py",
    "src/gui/component/parse_list/tree_view.py",
    "src/gui/component/setting/card.py",
    "src/gui/component/setting/group.py",
    "src/gui/component/setting/widget.py",
    "src/gui/component/widget/flyout.py",
    "src/gui/component/widget/search.py",
    "src/gui/component/widget/segment.py",
    "src/gui/component/dialog.py",
    "src/gui/component/profile.py",
    "src/gui/component/sys_tray.py",
    "src/gui/dialog/download_options/card.py",
    "src/gui/dialog/download_options/dialog.py",
    "src/gui/dialog/download_options/download.py",
    "src/gui/dialog/download_options/media.py",
    "src/gui/dialog/misc/about.py",
    "src/gui/dialog/misc/batch_select.py",
    "src/gui/dialog/misc/exit.py",
    "src/gui/dialog/misc/parse_history.py",
    "src/gui/dialog/misc/search.py",
    "src/gui/dialog/misc/terms.py",
    "src/gui/dialog/setting/cdn_server.py",
    "src/gui/dialog/setting/danmaku_style.py",
    "src/gui/dialog/setting/edit_host.py",
    "src/gui/dialog/setting/edit_rule.py",
    "src/gui/dialog/setting/parse_list.py",
    "src/gui/dialog/setting/priority.py",
    "src/gui/dialog/setting/proxy.py",
    "src/gui/dialog/setting/rule_list.py",
    "src/gui/dialog/setting/speed_limit.py",
    "src/gui/dialog/setting/starting_number.py",
    "src/gui/dialog/setting/subtitles_language.py",
    "src/gui/dialog/setting/subtitles_style.py",
    "src/gui/dialog/setting/user_agent.py",
    "src/gui/dialog/login.py",
    "src/gui/dialog/update.py",
    "src/gui/interface/download.py",
    "src/gui/interface/main_window.py",
    "src/gui/interface/parse.py",
    "src/gui/interface/setting.py",
    "src/util/common/translator.py",
    "src/util/download/downloader/downloader.py",
    "src/util/parse/worker.py"
]

# ts 文件路径
ts_file = f"src/res/i18n/bili23.{target_language}.ts"

# 拼接命令
source_args = " ".join([os.path.join(project_root, s).replace("\\", "/") for s in sources])
ts_path = os.path.join(project_root, ts_file).replace("\\", "/")
cmd = f"{lupdate_cmd} {source_args} -ts {ts_path}"

print("执行命令：", cmd)
# 执行命令
result = subprocess.run(cmd, shell=True)
print("返回码：", result.returncode)