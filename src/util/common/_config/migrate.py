"""
配置文件迁移

存量用户的 config.json 结构版本低于当前版本时，在这里补齐差异。
每段迁移都必须**幂等**：迁移完成后会写回新的 config_version，但用户可能在两个版本之间来回切换，
同一段迁移被跑第二遍不能造成破坏。

## 降级保护

旧实现只判断 `config_version < app_config_version`，版本更高时直接跳过，看起来无害 ——
但下一次 save() 会把整个文件按旧版本的字段集重写一遍，新版本独有的配置就此丢失。
GUI 与 WebUI 共用一份 config.json（D5）之后，两边版本不一致会成为常态，
这条路径会变成**双向数据丢失**。

现在有两层防护：

1. `ConfigStore` 保存时读改写，磁盘上认不出来的键一律原样保留（见 store.py）。
   这挡住了「新版本新增的字段」被抹掉。
2. 这里额外保住 `config_version` 本身不被写小。若旧版本把它改回 2150，
   新版本下次启动会误以为需要重跑迁移 —— 迁移虽然是幂等的，但不该依赖这一点来兜底。
"""

import logging

logger = logging.getLogger(__name__)

def check_need_patch(data: dict, app_config_version: int):
    """
    判断磁盘上的配置是否需要迁移

    返回 (是否需要迁移, 磁盘上的 config_version)。
    data 为已读出的原始 JSON（空字典表示文件不存在或读取失败）
    """
    if not data:
        # 文件不存在或读不出来，用的是全套默认值，没有可迁移的东西
        return False, 0

    application = data.get("Application")

    if not isinstance(application, dict) or "config_version" not in application:
        # 早期版本没有这个字段，从 0 开始跑完整套迁移
        return True, 0

    config_version = application.get("config_version", 0)

    if not isinstance(config_version, int):
        logger.warning("config_version 不是整数（%r），按需要迁移处理", config_version)

        return True, 0

    if config_version > app_config_version:
        logger.warning(
            "配置文件来自更新的版本（结构版本 %d，本程序支持 %d）。"
            "未知字段会原样保留，但本程序不认识的设置不会生效",
            config_version, app_config_version
        )

        return False, config_version

    return config_version < app_config_version, config_version

def patch_config(config, config_version: int) -> None:
    """按结构版本逐段迁移。config 为已完成加载的配置对象"""
    from ..enum import ProxyMode, ConventionType

    from .schema import DefaultValue

    if config_version < 2130:
        # 2.13.0 起代理设置由 proxy_enabled 开关改为 proxy_mode 三态选择。
        # 旧版开着代理开关的迁移为手动设置，其余保持默认的跟随系统代理
        if config.raw_data.get("Advanced", {}).get("proxy_enabled"):
            config.set(config.proxy_mode, ProxyMode.MANUAL)

            logger.info("代理设置已迁移为手动设置")

    if config_version < 2140:
        # 2.14.0 起支持 SDR 增强（qn 122）。画质优先级列表是一份完整枚举，
        # 选择画质时只遍历列表内的值，旧配置里没有 122 就永远选不中该画质；
        # 且优先级对话框是按配置列表渲染的，缺项不仅调不了，保存后还会把它彻底丢掉。
        # 因此这里补进列表，位置与默认值一致（HDR 之后、4K 之前），用户自定义过的顺序不受影响
        video_quality_priority = config.get(config.video_quality_priority).copy()

        if 122 not in video_quality_priority:
            if 120 in video_quality_priority:
                video_quality_priority.insert(video_quality_priority.index(120), 122)
            else:
                # 找不到 4K 作为锚点时兜底追加，至少保证该画质可被选中
                video_quality_priority.append(122)

            config.set(config.video_quality_priority, video_quality_priority)

            logger.info("SDR 增强画质已补入画质优先级列表")

    if config_version < 2150:
        # 2.15.0 起支持会员购商城课程，它是独立的命名类型（31）。命名规则列表是一份完整枚举，
        # 缺少该类型时 get_rule_from_config() 会返回 None，格式化文件名直接失败，
        # 任务连名字都取不到。因此为旧配置补上这条默认规则，排在课程之后
        naming_rule_list = config.get(config.naming_rule_list).copy()

        if not any(entry.get("type") == ConventionType.LESSON for entry in naming_rule_list):
            lesson_rule = next(
                entry.copy() for entry in DefaultValue.naming_rule_list
                if entry["type"] == ConventionType.LESSON
            )

            # 用户可能为课程建过多条自定义规则，插在最后一条之后，不要把这一组拆开
            cheese_index = next(
                (index for index in range(len(naming_rule_list) - 1, -1, -1)
                 if naming_rule_list[index].get("type") == ConventionType.CHEESE),
                None
            )

            if cheese_index is None:
                naming_rule_list.append(lesson_rule)
            else:
                naming_rule_list.insert(cheese_index + 1, lesson_rule)

            config.set(config.naming_rule_list, naming_rule_list)

            logger.info("商城课程命名规则已补入命名规则列表")

    # 完成修补，写入新的结构版本
    config.set(config.config_version, config.app_config_version)
    config.save()
