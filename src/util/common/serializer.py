from PySide6.QtCore import QLocale

from qfluentwidgets import ConfigSerializer

from .enum import Language, Scaling
from .secret import SecretError, SecretUnavailable, is_protected, is_supported, protect, unprotect

from typing import ClassVar
import logging

logger = logging.getLogger(__name__)

class LanguageSerializer(ConfigSerializer):
    def serialize(self, language: Language):
        return language.value.name() if language != Language.AUTO else "Auto"

    def deserialize(self, value: str):
        return Language(QLocale(value)) if value != "Auto" else Language.AUTO

class ScalingSerializer(ConfigSerializer):
    def serialize(self, scaling: Scaling):
        return scaling.value if scaling != Scaling.AUTO else "Auto"

    def deserialize(self, value: str):
        return Scaling(value) if value != "Auto" else Scaling.AUTO

class SecretSerializer(ConfigSerializer):
    """
    敏感字段（登录 Cookie、MCP 访问令牌）的落盘保护，各平台的做法见 util/common/secret

    只在序列化边界上做转换：ConfigItem.value 里始终是明文，config.get / config.set
    的调用方完全感知不到保护的存在。

    每个 ConfigItem 必须持有自己的实例 —— 实例上记着字段名（密钥库按它存取），
    缓存着该字段最近一次的明文与落盘值。用 config.SecretConfigItem 声明即可。
    """

    # 加载阶段是否读到了旧版遗留的明文。由 config.py 在加载完成后检查，
    # 立即保存一次把它们转成受保护的形式，而不是等到下一次碰巧有设置被改动
    legacy_plaintext_found: ClassVar[bool] = False

    # 加载阶段是否有字段因密钥库暂时不可用而没读出来。config.py 据此区分
    # 「凭据没了，该重置为未登录」与「凭据还在，只是这次读不到」
    unavailable_found: ClassVar[bool] = False

    def __init__(self, name: str):
        self.name = name

        # (明文, 落盘值)。config.set 每次都会整体重写配置文件，不缓存的话每次保存都要
        # 把所有敏感字段重新处理一遍：DPAPI 白白重新加密，密钥库则是每次都重写条目
        self._cache = ("", "")

    def serialize(self, value: str):
        value = value or ""

        if self._cache[0] == value:
            return self._cache[1]

        try:
            stored = protect(value, self.name)

        except SecretError:
            # 宁可落盘一个空值（重启后需要重新登录），也不悄悄退回明文 ——
            # 退回明文等于让这套保护在出错时自动失效，且用户不会知道。
            # 内存中的值不受影响，本次会话照常使用
            logger.exception("敏感配置项 %s 保存失败，本次不保存该字段", self.name)

            return ""

        self._cache = (value, stored)

        return stored

    def deserialize(self, value):
        if not isinstance(value, str) or not value:
            return ""

        if not is_protected(value):
            # 旧版明文。支持保护的环境下登记一下，由加载流程统一迁移
            if is_supported():
                SecretSerializer.legacy_plaintext_found = True

            return value

        try:
            plaintext = unprotect(value, self.name)

        except SecretUnavailable as e:
            logger.warning("敏感配置项 %s 暂时无法读取，本次按空值处理：%s", self.name, e)

            SecretSerializer.unavailable_found = True

            # 凭据多半还在密钥库里。把落盘值原样记进缓存，之后只要字段一直是空的，
            # 保存时就原样写回这个标记 —— 否则下一次保存会把空值当作「已退出登录」，
            # 删掉密钥库里的凭据，一次读不到就变成了永久丢失
            self._cache = ("", value)

            return ""

        except SecretError as e:
            # 不记录落盘值本身。多半是配置从另一台电脑或另一个用户账户拷贝而来
            logger.warning("敏感配置项 %s 无法读取，已按空值处理：%s", self.name, e)

            return ""

        self._cache = (plaintext, value)

        return plaintext
