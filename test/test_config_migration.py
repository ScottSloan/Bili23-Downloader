"""
util/common/config.py 的 patch_config() —— 配置文件跨版本迁移。

这段代码只在用户从旧版本升级时执行一次，且是就地改写用户的配置文件。
它错了不会崩溃，只会让某些设置悄悄失效或丢失：

* 2.14.0 的迁移若漏掉，SDR 增强画质（qn 122）不在优先级列表里，
  该画质永远选不中，而且优先级对话框保存一次就会把它彻底删掉；
* 2.15.0 的迁移若漏掉，商城课程找不到命名规则，get_rule_from_config()
  返回 None，格式化文件名直接失败 —— 任务连名字都取不到。

这类"升级一次性逻辑"最难人工验证：要复现就得手工造一个旧版配置文件再升级。
因此把每条迁移分支都钉成用例。

注意：patch_config 会改动全局 config 单例，每个用例前后做快照与还原。
"""

from util.common.config import config, patch_config, DefaultValue
from util.common.enum import ProxyMode, ConventionType

import pytest


@pytest.fixture(autouse = True)
def restore_config():
    """迁移会写全局 config，用例之间必须互不影响"""
    saved = {
        "proxy_mode": config.get(config.proxy_mode),
        "video_quality_priority": list(config.get(config.video_quality_priority)),
        "naming_rule_list": [dict(entry) for entry in config.get(config.naming_rule_list)],
        "config_version": config.get(config.config_version),
    }

    yield

    config.set(config.proxy_mode, saved["proxy_mode"])
    config.set(config.video_quality_priority, saved["video_quality_priority"])
    config.set(config.naming_rule_list, saved["naming_rule_list"])
    config.set(config.config_version, saved["config_version"])


class TestProxyMigration:
    """2.13.0：代理由 proxy_enabled 布尔开关改为 proxy_mode 三态"""

    def test_enabled_becomes_manual(self):
        config.set(config.proxy_mode, ProxyMode.SYSTEM)

        patch_config(2120, {"Advanced": {"proxy_enabled": True}})

        assert config.get(config.proxy_mode) == ProxyMode.MANUAL

    def test_disabled_keeps_default(self):
        # 旧版没开代理的，迁移后应保持默认的跟随系统，而不是被改成手动
        config.set(config.proxy_mode, ProxyMode.SYSTEM)

        patch_config(2120, {"Advanced": {"proxy_enabled": False}})

        assert config.get(config.proxy_mode) == ProxyMode.SYSTEM

    def test_absent_key_is_safe(self):
        config.set(config.proxy_mode, ProxyMode.SYSTEM)

        patch_config(2120, {})      # 字段整个缺失也不能抛异常

        assert config.get(config.proxy_mode) == ProxyMode.SYSTEM

    def test_not_applied_when_already_newer(self):
        config.set(config.proxy_mode, ProxyMode.SYSTEM)

        # 已经是 2130 及以上的配置不该再被这条迁移改动
        patch_config(2130, {"Advanced": {"proxy_enabled": True}})

        assert config.get(config.proxy_mode) == ProxyMode.SYSTEM


class TestVideoQualityMigration:
    """2.14.0：画质优先级列表需补入 SDR 增强（qn 122）"""

    def test_inserted_before_4k(self):
        config.set(config.video_quality_priority, [127, 126, 125, 120, 116, 80])

        patch_config(2130, {})

        priority = config.get(config.video_quality_priority)

        assert 122 in priority
        # 位置与默认值一致：HDR 之后、4K(120) 之前
        assert priority.index(122) == priority.index(120) - 1

    def test_appended_when_4k_missing(self):
        # 找不到 4K 作为锚点时兜底追加，至少保证该画质可被选中
        config.set(config.video_quality_priority, [127, 126, 80])

        patch_config(2130, {})

        assert config.get(config.video_quality_priority)[-1] == 122

    def test_existing_122_not_duplicated(self):
        original = [127, 122, 120, 80]
        config.set(config.video_quality_priority, list(original))

        patch_config(2130, {})

        assert config.get(config.video_quality_priority) == original

    def test_user_order_preserved(self):
        # 用户自定义过的顺序不能被迁移打乱
        config.set(config.video_quality_priority, [80, 120, 127])

        patch_config(2130, {})

        priority = config.get(config.video_quality_priority)

        assert [q for q in priority if q != 122] == [80, 120, 127]


class TestLessonRuleMigration:
    """2.15.0：命名规则列表需补入会员购商城课程（type 31）"""

    @staticmethod
    def rules_without_lesson():
        return [
            dict(entry) for entry in DefaultValue.naming_rule_list
            if entry["type"] != ConventionType.LESSON
        ]

    def test_lesson_rule_added(self):
        config.set(config.naming_rule_list, self.rules_without_lesson())

        patch_config(2140, {})

        types = [entry["type"] for entry in config.get(config.naming_rule_list)]

        assert ConventionType.LESSON in types

    def test_inserted_after_last_cheese_rule(self):
        rules = self.rules_without_lesson()
        # 用户可能为课程建过多条自定义规则，新规则要插在最后一条之后，不拆开这一组
        cheese = next(r for r in rules if r["type"] == ConventionType.CHEESE)
        rules.insert(rules.index(cheese) + 1, {**cheese, "id": "custom", "default": False})
        config.set(config.naming_rule_list, rules)

        patch_config(2140, {})

        types = [entry["type"] for entry in config.get(config.naming_rule_list)]
        last_cheese = len(types) - 1 - types[::-1].index(ConventionType.CHEESE)

        assert types.index(ConventionType.LESSON) == last_cheese + 1

    def test_appended_when_no_cheese_rule(self):
        rules = [r for r in self.rules_without_lesson() if r["type"] != ConventionType.CHEESE]
        config.set(config.naming_rule_list, rules)

        patch_config(2140, {})

        assert config.get(config.naming_rule_list)[-1]["type"] == ConventionType.LESSON

    def test_existing_lesson_rule_not_duplicated(self):
        config.set(config.naming_rule_list, [dict(e) for e in DefaultValue.naming_rule_list])

        patch_config(2140, {})

        types = [entry["type"] for entry in config.get(config.naming_rule_list)]

        assert types.count(ConventionType.LESSON) == 1


class TestVersionBump:
    def test_version_written_after_patch(self):
        config.set(config.config_version, 2100)

        patch_config(2100, {})

        assert config.get(config.config_version) == config.app_config_version

    def test_all_migrations_apply_from_oldest_version(self):
        # 从很旧的版本一路升上来，每条迁移都要生效
        config.set(config.proxy_mode, ProxyMode.SYSTEM)
        config.set(config.video_quality_priority, [127, 120, 80])
        config.set(config.naming_rule_list, TestLessonRuleMigration.rules_without_lesson())

        patch_config(2000, {"Advanced": {"proxy_enabled": True}})

        assert config.get(config.proxy_mode) == ProxyMode.MANUAL
        assert 122 in config.get(config.video_quality_priority)
        assert any(e["type"] == ConventionType.LESSON for e in config.get(config.naming_rule_list))
