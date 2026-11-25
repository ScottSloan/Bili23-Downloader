from PySide6.QtCore import QLocale

from qfluentwidgets import ConfigSerializer

from .enum import Language, Scaling
from .secret import SecretError, is_protected, is_supported, protect, unprotect

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
    敏感字段（登录 Cookie、MCP 访问令牌）落盘加密、读取解密，算法见 util/common/secret.py

    只在序列化边界上做转换：ConfigItem.value 里始终是明文，config.get / config.set
    的调用方完全感知不到加密的存在。

    每个 ConfigItem 必须持有自己的实例 —— 实例上缓存着该字段最近一次的明文与密文。
    """

    # 加载阶段是否读到了旧版遗留的明文。由 config.py 在加载完成后检查，
    # 立即保存一次把它们转成密文，而不是等到下一次碰巧有设置被改动
    legacy_plaintext_found: ClassVar[bool] = False

    def __init__(self):
        # (明文, 落盘值)。config.set 每次都会整体重写配置文件，不缓存的话
        # 每次保存都要把所有敏感字段重新加密一遍，配置文件里的密文也会无谓地每次都变
        self._cache = ("", "")

    def serialize(self, value: str):
        if not value:
            return ""

        if self._cache[0] == value:
            return self._cache[1]

        try:
            stored = protect(value)

        except OSError:
            # 宁可落盘一个空值（重启后需要重新登录），也不悄悄退回明文 ——
            # 退回明文等于让这套加密在出错时自动失效，且用户不会知道。
            # 内存中的值不受影响，本次会话照常使用
            logger.exception("敏感配置项加密失败，本次不保存该字段")

            return ""

        self._cache = (value, stored)

        return stored

    def deserialize(self, value):
        if not isinstance(value, str) or not value:
            return ""

        if not is_protected(value):
            # 旧版明文。支持加密的平台上登记一下，由加载流程统一迁移
            if is_supported():
                SecretSerializer.legacy_plaintext_found = True

            return value

        try:
            plaintext = unprotect(value)

        except SecretError as e:
            # 不记录密文本身。多半是配置从另一台电脑或另一个用户账户拷贝而来
            logger.warning("敏感配置项无法解密，已按空值处理：%s", e)

            return ""

        self._cache = (plaintext, value)

        return plaintext
