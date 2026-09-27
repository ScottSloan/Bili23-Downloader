from .config import config, DefaultValue
from .translator import Translator

from copy import deepcopy

def load_rules():
    """
    读命名规则列表的独立副本

    必须深拷贝：config.get() 返回的是配置里的那个 list 本身，元素也是原字典，
    就地编辑等于绕过保存动作改写配置（用户点取消也已生效）。而配置文件尚未
    创建时，被污染的更是 DefaultValue 上的类属性本身 —— 进程内的默认值从此
    带着用户的改动，且没有任何报错。
    """
    return deepcopy(config.get(config.naming_rule_list))

def load_default_rules():
    """读内置默认规则的独立副本，供「重置为默认值」使用"""
    return deepcopy(DefaultValue.naming_rule_list)

def save_rules(rule_list: list):
    config.set(config.naming_rule_list, rule_list)

def display_name(entry: dict):
    """
    取规则的显示名

    内置规则的 name 字段存的是翻译键（DEFAULT_FOR_NORMAL 之类），用户自建规则
    存的就是名字本身，查不到键时原样返回。

    **不写回 entry** —— 写回去就把当前语言的译文持久化进了配置，用户切一次
    界面语言，翻译键便再也匹配不上，这条规则的名字从此固定在旧语言上。
    """
    name = entry.get("name")

    return Translator.DEFAULT_RULE_NAMES().get(name, name)
