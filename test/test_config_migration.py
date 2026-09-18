"""
util/common/config.py 的 patch_config() —— 配置文件跨版本迁移。

这段代码只在用户从旧版本升级时执行一次，且是就地改写用户的配置文件。
它错了不会崩溃，只会让某些设置悄悄失效或丢失：

* 2.14.0 的迁移若漏掉，SDR 增强画质（qn 122）不在优先级列表里，
  该画质永远选不中，而且优先级对话框保存一次就会把它彻底删掉；
* 2.20.0 的迁移若漏掉，收藏夹、个人空间里多P视频的稿件标题会被丢掉（#461）；
* 2.20.0 的迁移若漏掉，海外解析每次都要白占一个并发探测位去撞 Akamai 的 403。

2.15.0 那条「为会员购商城课程补默认规则」已经连同该命名类型一起删掉了
（见 ConventionType 的注释），这里不再有用例。

这类"升级一次性逻辑"最难人工验证：要复现就得手工造一个旧版配置文件再升级。
因此把每条迁移分支都钉成用例。

注意：patch_config 会改动全局 config 单例，每个用例前后做快照与还原。
"""

from util.common.config import config, patch_config, DefaultValue
from util.common.runtime import runtime
from util.common.enum import ProxyMode

import pytest


@pytest.fixture(autouse = True)
def restore_config():
    """迁移会写全局 config，用例之间必须互不影响"""
    saved = {
        "proxy_mode": config.get(config.proxy_mode),
        "video_quality_priority": list(config.get(config.video_quality_priority)),
        "naming_rule_list": [dict(entry) for entry in config.get(config.naming_rule_list)],
        "ov_cdn_server_list": [dict(entry) for entry in config.get(config.ov_cdn_server_list)],
        "config_version": config.get(config.config_version),
        "rules_reset": runtime.naming.rules_reset,
    }

    yield

    config.set(config.proxy_mode, saved["proxy_mode"])
    config.set(config.video_quality_priority, saved["video_quality_priority"])
    config.set(config.naming_rule_list, saved["naming_rule_list"])
    config.set(config.ov_cdn_server_list, saved["ov_cdn_server_list"])
    config.set(config.config_version, saved["config_version"])
    runtime.naming.rules_reset = saved["rules_reset"]


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


class TestNamingRuleReset:
    """
    2.20.0：命名规则的内置默认值连着变过两次，整张表换新

    先是改用 <> 可选段（个人空间、收藏夹这几类里单P与多P混在一起，旧写法只能顾及
    一种形态 —— 多P视频会丢掉稿件标题、全部平铺在同一层，GitHub #461），随后又把
    入口标签从 {parent_title} 拆进了 {source_title}（此前它兼着「来源列表入口标签」
    与「稿件标题」两种含义）。

    不再逐条比对「用户改过没有」：命名规则是用户可见、随时可改的东西，留一条已经
    用错变量的旧规则在配置里，出问题时比「规则没了」更难排查。代价是用户自建的规则
    与改过的内置规则一并舍弃，所以必须让用户知道 —— 见下面那条置标志的用例。
    """

    def test_any_older_config_gets_the_new_defaults(self):
        # 改过的内置规则、以及用户自建的规则，都会被覆盖掉
        rules = [dict(entry) for entry in DefaultValue.naming_rule_list]

        for entry in rules:
            if entry["type"] == 70:
                entry["rule"] = "{parent_title}/我自己的写法"

        rules.append({
            "id": "5f0f1c2e-0000-4000-8000-000000000001",
            "name": "自建规则",
            "type": 11,
            "rule": "{leaf_title}-{uploader}",
            "default": False
        })

        config.set(config.naming_rule_list, rules)

        patch_config(2100, {})

        assert config.get(config.naming_rule_list) == DefaultValue.naming_rule_list

    def test_reset_is_flagged_for_the_main_window(self):
        # patch_config 跑在导入期，那时界面上什么都没有 —— 只能先留个标志。
        # 少了它，用户会莫名发现规则变回了默认值，而界面上没有任何解释
        from util.common.runtime import runtime

        runtime.naming.rules_reset = False

        patch_config(2100, {})

        assert runtime.naming.rules_reset is True

    def test_already_current_is_not_reset(self):
        from util.common.runtime import runtime

        runtime.naming.rules_reset = False

        patch_config(config.app_config_version, {})

        assert runtime.naming.rules_reset is False

    def test_the_new_list_is_a_copy(self):
        # 必须 deepcopy 之后再交给 config.set：把 DefaultValue 上那一份直接装进配置，
        # 用户此后改一次规则就永久污染了进程内的默认值（conftest 的会话末校验会抓住）
        patch_config(2100, {})

        assert config.get(config.naming_rule_list) is not DefaultValue.naming_rule_list

    def test_all_default_rules_remain_representable(self):
        # 内置规则必须全都能在可视化编辑器里打开，否则用户一进去就看到降级提示
        from util.format.rule_model import parse_rule, RuleModel

        for entry in DefaultValue.naming_rule_list:
            assert isinstance(parse_rule(entry["rule"]), RuleModel), entry["name"]


class TestVersionBump:
    def test_version_written_after_patch(self):
        config.set(config.config_version, 2100)

        patch_config(2100, {})

        assert config.get(config.config_version) == config.app_config_version

    def test_all_migrations_apply_from_oldest_version(self):
        # 从很旧的版本一路升上来，每条迁移都要生效
        config.set(config.proxy_mode, ProxyMode.SYSTEM)
        config.set(config.video_quality_priority, [127, 120, 80])

        patch_config(2000, {"Advanced": {"proxy_enabled": True}})

        assert config.get(config.proxy_mode) == ProxyMode.MANUAL
        assert 122 in config.get(config.video_quality_priority)

    def test_oldest_version_does_not_gain_a_lesson_rule(self):
        """
        最旧的配置一路升上来，不该凭空多出会员购商城课程（31）的规则

        2.15.0 那段「给旧配置补 31 规则」的迁移已随该类型一起删掉。这条用例是
        「删掉它是安全的」的形式化证明：删之前它会补一条，删之后一条都不补
        """
        config.set(config.naming_rule_list, [
            dict(entry) for entry in DefaultValue.naming_rule_list
        ])

        patch_config(2000, {})

        assert not any(entry.get("type") == 31 for entry in config.get(config.naming_rule_list))


class TestCDNServerListMigration:
    """
    2.20.0：默认海外 CDN 列表移除 Akamai

    upos-hz-mirrorakam.akamaized.net 不能作为替换目标：把别的 host 的签名链接改写
    过去一律返回 403，直连与经代理结果一致、与出口地区无关。而这份列表的用途正是
    替换 host，探测它必然是白占一个并发槽。（B 站原生签发的 Akamai 链接可用，
    不受此影响。）

    这条迁移存在的唯一理由是 **config 是落盘的** —— 改掉 DefaultValue 对已有用户
    毫无影响，他们配置里那份副本得靠这里删。
    """

    AKAMAI_HOST = "upos-hz-mirrorakam.akamaized.net"

    @classmethod
    def legacy_list(cls):
        """旧版默认值：Akamai 在首位"""
        return [
            {"host": cls.AKAMAI_HOST, "provider": "AKAMAI"},
            {"host": "upos-sz-mirroraliov.bilivideo.com", "provider": "ALIYUN"},
            {"host": "upos-sz-mirrorcosov.bilivideo.com", "provider": "TENCENT"},
        ]

    def hosts(self):
        return [entry.get("host") for entry in config.get(config.ov_cdn_server_list)]

    def test_akamai_removed_and_rest_kept(self):
        config.set(config.ov_cdn_server_list, self.legacy_list())

        patch_config(2160, {})

        assert self.hosts() == [
            "upos-sz-mirroraliov.bilivideo.com",
            "upos-sz-mirrorcosov.bilivideo.com",
        ]

    def test_user_added_nodes_untouched(self):
        # 这份列表在设置界面里可编辑，用户自己加的节点不能被顺手清掉
        config.set(config.ov_cdn_server_list, self.legacy_list() + [
            {"host": "upos-sz-mirrorcoso1.bilivideo.com", "provider": "TENCENT"},
            {"host": "my.own.node.example.com", "provider": "CUSTOM"},
        ])

        patch_config(2160, {})

        assert self.hosts() == [
            "upos-sz-mirroraliov.bilivideo.com",
            "upos-sz-mirrorcosov.bilivideo.com",
            "upos-sz-mirrorcoso1.bilivideo.com",
            "my.own.node.example.com",
        ]

    def test_already_clean_list_is_untouched(self):
        # 用户早就自己删过 Akamai，迁移不该改动他的列表
        config.set(config.ov_cdn_server_list, [
            {"host": "upos-sz-mirroraliov.bilivideo.com", "provider": "ALIYUN"},
        ])

        patch_config(2160, {})

        assert self.hosts() == ["upos-sz-mirroraliov.bilivideo.com"]

    def test_not_applied_when_already_newer(self):
        config.set(config.ov_cdn_server_list, self.legacy_list())

        patch_config(2200, {})

        assert self.AKAMAI_HOST in self.hosts()

    def test_malformed_entries_are_safe(self):
        # 用户手改配置文件导致条目缺 host 时不能抛异常
        config.set(config.ov_cdn_server_list, [{}, {"provider": "ALIYUN"}])

        patch_config(2160, {})

        assert len(config.get(config.ov_cdn_server_list)) == 2

    def test_empty_list_is_safe(self):
        config.set(config.ov_cdn_server_list, [])

        patch_config(2160, {})

        assert config.get(config.ov_cdn_server_list) == []

    def test_default_value_no_longer_lists_akamai(self):
        # 默认值本身也不该再有 Akamai，否则新用户照样会拿到它
        assert all(
            entry.get("host") != self.AKAMAI_HOST
            for entry in DefaultValue.ov_cdn_server_list
        )
