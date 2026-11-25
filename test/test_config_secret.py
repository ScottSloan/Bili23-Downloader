"""
敏感配置项（登录 Cookie、MCP 访问令牌）的落盘加密 —— util/common/secret.py 与 SecretSerializer。

这套东西出错的表现都很安静：
* 加密悄悄没生效，Cookie 照旧明文躺在 config.json 里，功能上毫无异常；
* 旧版明文没被识别，升级后用户莫名其妙掉登录；
* 解不开的密文没被兜住，界面显示已登录，请求却带着空的 SESSDATA 发出去。

DPAPI 只在 Windows 上可用，相关用例在其他平台跳过；CI 的测试矩阵里有 windows-latest。
"""

from util.common.config import config, settle_secrets
from util.common.serializer import SecretSerializer
from util.common import secret
from util.mcp.stdio_bridge import _decrypt_token

import pytest
import stat
import sys
import os

windows_only = pytest.mark.skipif(sys.platform != "win32", reason = "DPAPI 仅 Windows 可用")
posix_only = pytest.mark.skipif(sys.platform == "win32", reason = "文件权限约束只针对非 Windows 平台")

SECRET_ITEMS = ("bili_jct", "DedeUserID", "DedeUserID__ckMd5", "SESSDATA", "mcp_token")

# 足够特殊，出现在配置文件里只可能是明文泄露
SENTINEL = "sentinel-sessdata-7c3e9a%2C1764000000"


@pytest.fixture(autouse = True)
def restore_config():
    """用例会改全局 config 与类级迁移标志，前后快照还原"""
    saved = {name: config.get(getattr(config, name)) for name in (*SECRET_ITEMS, "is_login")}
    saved_flag = SecretSerializer.legacy_plaintext_found

    yield

    for name, value in saved.items():
        config.set(getattr(config, name), value)

    SecretSerializer.legacy_plaintext_found = saved_flag


class TestSecretModule:
    def test_empty_and_plaintext_pass_through_unprotect(self):
        # 不带前缀即视为旧版明文，必须原样放行，否则升级后所有人都会掉登录
        assert secret.unprotect("") == ""
        assert secret.unprotect("legacy-plain-value") == "legacy-plain-value"

    def test_empty_is_not_encrypted(self):
        assert secret.protect("") == ""

    @windows_only
    def test_roundtrip(self):
        value = "含中文与符号 %2C,=;"

        stored = secret.protect(value)

        assert secret.is_protected(stored)
        assert value not in stored
        assert secret.unprotect(stored) == value

    @windows_only
    def test_corrupted_base64_raises(self):
        with pytest.raises(secret.SecretError):
            secret.unprotect(secret.PREFIX + "@@not-base64@@")

    @windows_only
    def test_foreign_ciphertext_raises(self):
        # 合法 base64 但不是本用户的 DPAPI 密文 —— 等价于配置从别的电脑拷来
        with pytest.raises(secret.SecretError):
            secret.unprotect(secret.PREFIX + "AAAAAAAAAAAA")

    @windows_only
    def test_entropy_is_required(self, monkeypatch):
        # 换掉附加熵就解不开：其他程序拿到密文不能直接 CryptUnprotectData
        stored = secret.protect("value")

        monkeypatch.setattr(secret, "_ENTROPY", b"something else")

        with pytest.raises(secret.SecretError):
            secret.unprotect(stored)

    def test_non_windows_stores_plaintext(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")

        assert secret.protect("value") == "value"

        # Windows 上加密过的配置拷到别的平台：解不开，必须报错而不是把密文当 Cookie 用
        with pytest.raises(secret.SecretError):
            secret.unprotect(secret.PREFIX + "AAAA")


class TestSecretSerializer:
    def test_each_item_has_its_own_serializer(self):
        # 实例上缓存着明文与密文，共用一个实例会让字段之间互相串值
        serializers = [getattr(config, name).serializer for name in SECRET_ITEMS]

        assert all(isinstance(s, SecretSerializer) for s in serializers)
        assert len({id(s) for s in serializers}) == len(serializers)

    def test_undecryptable_becomes_empty(self):
        assert SecretSerializer().deserialize(secret.PREFIX + "@@broken@@") == ""

    def test_non_string_becomes_empty(self):
        assert SecretSerializer().deserialize(None) == ""
        assert SecretSerializer().deserialize(123) == ""

    @windows_only
    def test_roundtrip_and_stable_ciphertext(self):
        serializer = SecretSerializer()

        stored = serializer.serialize(SENTINEL)

        # 同一个值反复保存不重新加密，配置文件里的密文不会每次都变
        assert serializer.serialize(SENTINEL) == stored
        assert SecretSerializer().deserialize(stored) == SENTINEL

    @windows_only
    def test_legacy_plaintext_is_flagged(self):
        SecretSerializer.legacy_plaintext_found = False

        assert SecretSerializer().deserialize("legacy-plain-value") == "legacy-plain-value"
        assert SecretSerializer.legacy_plaintext_found

    def test_encrypt_failure_does_not_fall_back_to_plaintext(self, monkeypatch):
        def fail(_):
            raise OSError("模拟 DPAPI 失败")

        monkeypatch.setattr("util.common.serializer.protect", fail)

        assert SecretSerializer().serialize(SENTINEL) == ""


class TestConfigFile:
    @windows_only
    def test_secrets_are_not_written_in_plaintext(self):
        config.set(config.SESSDATA, SENTINEL)
        config.set(config.mcp_token, SENTINEL + "-token")

        content = config.file.read_text(encoding = "utf-8")

        assert SENTINEL not in content
        assert secret.PREFIX in content

        # 内存中仍是明文，调用方感知不到加密
        assert config.get(config.SESSDATA) == SENTINEL

    @posix_only
    def test_config_file_is_private(self):
        config.set(config.SESSDATA, SENTINEL)

        assert stat.S_IMODE(os.stat(config.file).st_mode) == 0o600


class TestSettleSecrets:
    def test_login_reset_when_sessdata_missing(self):
        # 解密失败后 SESSDATA 为空，is_login 却还是 True
        config.set(config.SESSDATA, "")
        config.set(config.is_login, True)

        settle_secrets()

        assert config.get(config.is_login) is False

    def test_login_kept_when_sessdata_present(self):
        config.set(config.SESSDATA, SENTINEL)
        config.set(config.is_login, True)

        settle_secrets()

        assert config.get(config.is_login) is True

    @windows_only
    def test_legacy_plaintext_is_migrated(self):
        # 模拟旧版配置：内存里是明文、文件也是明文
        config.set(config.SESSDATA, SENTINEL)
        config.file.write_text(config.file.read_text(encoding = "utf-8").replace(config.SESSDATA.serialize(), SENTINEL), encoding = "utf-8")

        SecretSerializer.legacy_plaintext_found = True

        settle_secrets()

        assert not SecretSerializer.legacy_plaintext_found
        assert SENTINEL not in config.file.read_text(encoding = "utf-8")


class TestStdioBridgeToken:
    def test_missing_token(self):
        assert _decrypt_token(None) is None

    def test_legacy_plaintext_token(self):
        assert _decrypt_token("plain-token") == "plain-token"

    def test_undecryptable_token(self):
        assert _decrypt_token(secret.PREFIX + "@@broken@@") is None

    @windows_only
    def test_encrypted_token(self):
        assert _decrypt_token(secret.protect("real-token")) == "real-token"
