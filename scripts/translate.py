"""
此脚本用于提取项目中的翻译字符串并生成 .ts 文件，供翻译人员使用 Qt Linguist 进行翻译。
使用前请确保已安装 PySide6，并且 pyside6-lupdate 命令可用（如果使用虚拟环境，需激活后再运行此脚本）。
运行后会在 src/res/i18n/ 目录下更新 target_languages 中每种语言的 .ts 文件，其中包含项目中所有需要翻译的字符串。
翻译完成后，使用 lrelease 命令将 .ts 文件编译成 .qm 文件，供应用程序加载使用。

This script is used to extract translation strings from the project and generate .ts files for translators to use with Qt Linguist.
Before using, make sure PySide6 is installed and the pyside6-lupdate command is available (if using a virtual environment, activate it before running this script).
After running, it will update the .ts file for each language in target_languages under src/res/i18n/, which contains all the strings that need to be translated in the project.
After translation is complete, use the lrelease command to compile the .ts file into a .qm file for the application to load and use.

注意 / Note：
    改动 .ts 之后还必须重新生成 .qm 与 resources_rc.py，否则改动不会进入程序
    （这两个生成物都提交在仓库里）。脚本末尾会打印出后续命令。
"""

import subprocess
import os
import sys

# 子进程（lupdate）直接往 fd 写，父进程的 print 若被缓冲就会排到它们后面，
# 看起来像是"两个语言都跑完了才开始打第一行"
sys.stdout.reconfigure(line_buffering = True)

# ------- 配置 (Configuration) ---------


# 目标语言，一次全部更新
# lupdate 的 -ts 一次只收一个文件，脚本内部逐个调用
target_languages = [
    "zh_CN",
    "zh_TW",
]


# 项目根目录：由脚本自身位置推导（scripts/ 的上一级）
# 原先硬编码成开发机的绝对路径，换机器或换目录后就会静默写到不存在的位置
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
    "src/gui/component/log_list/list_view.py",
    "src/gui/component/parse_list/model.py",
    "src/gui/component/parse_list/tree_view.py",
    "src/gui/component/rule_builder.py",
    "src/gui/component/setting/card.py",
    "src/gui/component/setting/group.py",
    "src/gui/component/setting/widget.py",
    "src/gui/component/widget/flyout.py",
    "src/gui/component/widget/pager.py",
    "src/gui/component/widget/progress_tip.py",
    "src/gui/component/widget/search.py",
    "src/gui/component/widget/segment.py",
    "src/gui/component/dialog.py",
    "src/gui/component/profile.py",
    "src/gui/component/sys_tray.py",
    "src/gui/dialog/download_options/card.py",
    "src/gui/dialog/download_options/dialog.py",
    "src/gui/dialog/download_options/download.py",
    "src/gui/dialog/download_options/media.py",
    "src/gui/dialog/download_options/preview.py",
    "src/gui/dialog/main_window/about.py",
    "src/gui/dialog/main_window/exit.py",
    "src/gui/dialog/main_window/terms.py",
    "src/gui/dialog/misc/auto_parse.py",
    "src/gui/dialog/misc/batch_parse.py",
    "src/gui/dialog/misc/batch_select.py",
    "src/gui/dialog/misc/duplicate_download.py",
    "src/gui/dialog/misc/interactive_video.py",
    "src/gui/dialog/misc/jump_to_page.py",
    "src/gui/dialog/misc/multi_part_lists.py",
    "src/gui/dialog/misc/parse_history.py",
    "src/gui/dialog/misc/search.py",
    "src/gui/dialog/misc/view_cover.py",
    "src/gui/dialog/setting/auto_select.py",
    "src/gui/dialog/setting/cdn_server.py",
    "src/gui/dialog/setting/danmaku_style.py",
    "src/gui/dialog/setting/edit_host.py",
    "src/gui/dialog/setting/edit_rule.py",
    "src/gui/dialog/setting/monitor_clipboard.py",
    "src/gui/dialog/setting/parse_list.py",
    "src/gui/dialog/setting/priority.py",
    "src/gui/dialog/setting/proxy.py",
    "src/gui/dialog/setting/rule_list.py",
    "src/gui/dialog/setting/select_area.py",
    "src/gui/dialog/setting/speed_limit.py",
    "src/gui/dialog/setting/starting_number.py",
    "src/gui/dialog/setting/subtitles_language.py",
    "src/gui/dialog/setting/subtitles_style.py",
    "src/gui/dialog/setting/user_agent.py",
    "src/gui/dialog/log.py",
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

# 源文件绝对路径。传列表给 lupdate 而不是拼成一整条命令字符串再交给 shell，
# 路径里带空格时不必操心引号
source_paths = [os.path.join(project_root, source).replace("\\", "/") for source in sources]

missing = [path for path in source_paths if not os.path.exists(path)]

if missing:
    print("以下源文件不存在，请检查 sources 列表：")
    for path in missing:
        print("   ", path)
    raise SystemExit(1)

failed = []

for target_language in target_languages:
    ts_path = os.path.join(project_root, f"src/res/i18n/bili23.{target_language}.ts").replace("\\", "/")

    cmd = [lupdate_cmd, *source_paths, "-ts", ts_path]

    # 不打印完整命令：六十多个绝对路径会把真正要看的信息（哪个语言、成功与否）淹掉
    print(f"\n=== 更新 {target_language}（{len(source_paths)} 个源文件）===")

    result = subprocess.run(cmd)

    print(f"{target_language} 返回码：{result.returncode}")

    if result.returncode != 0:
        failed.append(target_language)

if failed:
    print(f"\n以下语言更新失败：{'、'.join(failed)}")
    raise SystemExit(1)

# .ts 只是中间产物，程序读的是 .qm。漏掉这一步不会有任何报错，界面只会静默回退英文原文
print("\n.ts 已更新，后续还需要：")
for target_language in target_languages:
    print(f"    pyside6-lrelease src/res/i18n/bili23.{target_language}.ts")
print("    pyside6-rcc src/res/resources.qrc -o src/res/resources_rc.py")
