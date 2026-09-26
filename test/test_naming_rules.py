"""
util/common/naming_rules.py —— 命名规则的读写与显示名。

这里的每一条都在守同一件事：**配置对象绝不能被就地修改**。
qfluentwidgets 的 config.get() 返回的是配置里那个 list 本身，元素也是原字典；
配置文件尚未创建时，它甚至就是 DefaultValue 上的类属性。界面上随手改一个
字段（把翻译键换成译名是最常见的一种），改动就永久留在了进程内的默认值上，
全程没有任何报错 —— conftest 的 pytest_sessionfinish 会在整场测试结束时才
发现，报错点离肇事代码很远。
"""

from util.common.naming_rules import load_rules, load_default_rules, display_name
from util.common.config import config, DefaultValue
from util.common.enum import ConventionType

from util.format.file_name import FileNameFormatter
from util.parse.episode.tree import Attribute


class TestCopyIsolation:
    def test_load_rules_returns_a_new_list_each_time(self):
        assert load_rules() is not load_rules()

    def test_load_rules_deep_copies_entries(self):
        # 浅拷贝挡不住这一层：元素仍是配置里那个字典
        first = load_rules()
        second = load_rules()

        assert first[0] is not second[0]

    def test_mutating_loaded_rules_does_not_touch_config(self):
        rules = load_rules()
        original = rules[0]["rule"]

        rules[0]["rule"] = "{leaf_title}_被改过了"

        assert config.get(config.naming_rule_list)[0]["rule"] == original

    def test_mutating_default_rules_does_not_touch_default_value(self):
        rules = load_default_rules()
        original = rules[0]["name"]

        rules[0]["name"] = "被改过了"

        assert DefaultValue.naming_rule_list[0]["name"] == original

    def test_rule_list_from_attribute_is_detached(self):
        # 下载选项对话框拿到这份列表后会改 name 来显示译名，
        # 改动不得回流到配置
        formatter = FileNameFormatter()
        rule_list = formatter.get_rule_list_from_attribute(Attribute.SPACE_BIT)

        assert rule_list, "个人空间应当至少有一条默认规则"

        rule_list[0]["name"] = "被改过了"

        for entry in config.get(config.naming_rule_list):
            if entry["type"] == ConventionType.SPACE:
                assert entry["name"] != "被改过了"


class TestDisplayName:
    def test_builtin_key_is_translated(self):
        entry = {"name": "DEFAULT_FOR_NORMAL"}

        # 测试环境未安装翻译器，译文回落为英文原文；
        # 此处只关心「不是翻译键本身」
        assert display_name(entry) != "DEFAULT_FOR_NORMAL"

    def test_custom_name_passes_through(self):
        entry = {"name": "我自己建的规则"}

        assert display_name(entry) == "我自己建的规则"

    def test_does_not_write_back(self):
        entry = {"name": "DEFAULT_FOR_NORMAL"}

        display_name(entry)

        assert entry["name"] == "DEFAULT_FOR_NORMAL"
