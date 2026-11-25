"""
敏感配置项（登录 Cookie、MCP 访问令牌）的落盘保护 —— util/common/secret 与 SecretSerializer。

这套东西出错的表现都很安静：
* 保护悄悄没生效，Cookie 照旧明文躺在 config.json 里，功能上毫无异常；
* 旧版明文没被识别，升级后用户莫名其妙掉登录；
* 取不出的值没被兜住，界面显示已登录，请求却带着空的 SESSDATA 发出去；
* 密钥库一次读不到，下一次保存就把库里的凭据删掉，暂时的问题变成永久登出。

配置的导入导出不迁移登录态：导出剔除凭据，导入保留本机现有的登录。

DPAPI 只在 Windows 上可用；Secret Service 只在有桌面会话的 Linux 上可用，CI 上没有，
相关用例需要在 Linux 桌面上手动跑。其余用例用一个假的密钥库覆盖 Linux / macOS 的逻辑。
"""

from util.common.config import config, settle_secrets, login_state_items, restrict_permission
from util.common._json import dumps_std, loads
from util.common.serializer import SecretSerializer
from util.common.runtime import runtime
from util.common import secret
from util.mcp.stdio_bridge import _decrypt_token, MCP_TOKEN_NAME

import pytest
import stat
import sys
import os

windows_only = pytest.mark.skipif(sys.platform != "win32", reason = "DPAPI 仅 Windows 可用")
posix_only = pytest.mark.skipif(sys.platform == "win32", reason = "文件权限约束只针对非 Windows 平台")
protected_only = pytest.mark.skipif(not secret.is_supported(), reason = "当前环境没有可用的保护手段（DPAPI / 系统密钥库）")
secret_service_only = pytest.mark.skipif(
    not sys.platform.startswith("linux") or secret._store() is None,
    reason = "需要有桌面会话、运行着 Secret Service 的 Linux"
)

SECRET_ITEMS = ("bili_jct", "DedeUserID", "DedeUserID__ckMd5", "SESSDATA", "mcp_token")

# 足够特殊，出现在配置文件里只可能是明文泄露
SENTINEL = "sentinel-sessdata-7c3e9a%2C1764000000"


@pytest.fixture(autouse = True)
def restore_config():
    """用例会改全局 config、类级标志与运行时登录态，前后快照还原"""
    saved = {name: config.get(getattr(config, name)) for name in (*SECRET_ITEMS, "is_login", "download_thread", "img_key")}
    saved_flags = (SecretSerializer.legacy_plaintext_found, SecretSerializer.unavailable_found)
    saved_expired = runtime.auth.is_expired

    yield

    for name, value in saved.items():
        config.set(getattr(config, name), value)

    SecretSerializer.legacy_plaintext_found, SecretSerializer.unavailable_found = saved_flags
    runtime.auth.is_expired = saved_expired


class FakeStore:
    """内存里的密钥库，用来在任何平台上覆盖 Linux / macOS 的逻辑"""

    def __init__(self):
        self.data = {}
        self.deleted = []
        self.fail = False

    def _check(self):
        if self.fail:
            raise secret.SecretUnavailable("模拟密钥库被锁定")

    def get(self, service, name):
        self._check()

        return self.data.get((service, name))

    def set(self, service, name, value):
        self._check()

        self.data[(service, name)] = value

    def delete(self, service, name):
        self._check()

        self.deleted.append(name)
        self.data.pop((service, name), None)


@pytest.fixture
def fake_store(monkeypatch):
    """
    把当前进程伪装成有密钥库的 Linux

    注意：伪装期间不能调用 config.set —— 保存配置会走 Linux 分支的 os.fchmod，Windows 上没有它。
    这些用例因此直接操作 SecretSerializer
    """
    store = FakeStore()

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(secret, "_store", lambda: store)

    return store


class TestSecretModule:
    def test_empty_and_plaintext_pass_through_unprotect(self):
        # 不带前缀即视为旧版明文，必须原样放行，否则升级后所有人都会掉登录
        assert secret.unprotect("", "Cookie.SESSDATA") == ""
        assert secret.unprotect("legacy-plain-value", "Cookie.SESSDATA") == "legacy-plain-value"

    @windows_only
    def test_empty_is_not_encrypted(self):
        assert secret.protect("", "Cookie.SESSDATA") == ""

    @windows_only
    def test_roundtrip(self):
        value = "含中文与符号 %2C,=;"

        stored = secret.protect(value, "Cookie.SESSDATA")

        assert secret.is_protected(stored)
        assert value not in stored
        assert secret.unprotect(stored, "Cookie.SESSDATA") == value

    @windows_only
    def test_corrupted_base64_raises(self):
        with pytest.raises(secret.SecretError):
            secret.unprotect(secret.DPAPI_PREFIX + "@@not-base64@@", "Cookie.SESSDATA")

    @windows_only
    def test_foreign_ciphertext_raises(self):
        # 合法 base64 但不是本用户的 DPAPI 密文 —— 等价于配置从别的电脑拷来
        with pytest.raises(secret.SecretError):
            secret.unprotect(secret.DPAPI_PREFIX + "AAAAAAAAAAAA", "Cookie.SESSDATA")

    @windows_only
    def test_entropy_is_required(self, monkeypatch):
        # 换掉附加熵就解不开：其他程序拿到密文不能直接 CryptUnprotectData
        from util.common.secret import dpapi

        stored = secret.protect("value", "Cookie.SESSDATA")

        monkeypatch.setattr(dpapi, "_ENTROPY", b"something else")

        with pytest.raises(secret.SecretError):
            secret.unprotect(stored, "Cookie.SESSDATA")

    def test_no_store_stores_plaintext(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(secret, "_store", lambda: None)

        assert not secret.is_supported()
        assert secret.protect("value", "Cookie.SESSDATA") == "value"

        # Windows 上加密过的配置拷到别的平台：解不开，必须报错而不是把密文当 Cookie 用
        with pytest.raises(secret.SecretError):
            secret.unprotect(secret.DPAPI_PREFIX + "AAAA", "Cookie.SESSDATA")

    def test_test_service_name_is_isolated(self):
        # conftest 换掉了归属标识，测试才不会碰到开发机上的真实凭据
        assert secret.SERVICE != "Bili23 Downloader"

    def test_store_roundtrip(self, fake_store):
        stored = secret.protect(SENTINEL, "Cookie.SESSDATA")

        # 配置里只留标记，值本身进密钥库
        assert stored == secret.KEYRING_MARKER
        assert fake_store.data == {(secret.SERVICE, "Cookie.SESSDATA"): SENTINEL}
        assert secret.unprotect(stored, "Cookie.SESSDATA") == SENTINEL

    def test_store_empty_deletes_entry(self, fake_store):
        # 退出登录不能把凭据留在密钥库里
        secret.protect(SENTINEL, "Cookie.SESSDATA")

        assert secret.protect("", "Cookie.SESSDATA") == ""
        assert fake_store.data == {}

    def test_store_missing_entry_raises_not_found(self, fake_store):
        with pytest.raises(secret.SecretNotFound):
            secret.unprotect(secret.KEYRING_MARKER, "Cookie.SESSDATA")

    def test_store_gone_is_unavailable_on_posix(self, monkeypatch):
        # 同一台机器上换了个没有桌面会话的环境启动：凭据多半还在，属于暂时取不到
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(secret, "_store", lambda: None)

        with pytest.raises(secret.SecretUnavailable):
            secret.unprotect(secret.KEYRING_MARKER, "Cookie.SESSDATA")

    def test_keyring_marker_on_windows_is_permanent(self, monkeypatch):
        # 配置从 Linux 拷到 Windows：永远取不到，不能当作「暂时」处理
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setattr(secret, "_store", lambda: None)

        with pytest.raises(secret.SecretError) as info:
            secret.unprotect(secret.KEYRING_MARKER, "Cookie.SESSDATA")

        assert not isinstance(info.value, secret.SecretUnavailable)


class TestSecretSerializer:
    def test_each_item_has_its_own_serializer(self):
        # 实例上记着字段名并缓存着明文与落盘值，共用一个实例会让字段之间互相串值
        serializers = [getattr(config, name).serializer for name in SECRET_ITEMS]

        assert all(isinstance(s, SecretSerializer) for s in serializers)
        assert len({id(s) for s in serializers}) == len(serializers)

    def test_serializer_name_matches_item_key(self):
        # 密钥库按这个名字存取，与声明对不上就会读到别的字段或读不到
        for name in SECRET_ITEMS:
            item = getattr(config, name)

            assert item.serializer.name == item.key

    def test_undecryptable_becomes_empty(self):
        assert SecretSerializer("Cookie.SESSDATA").deserialize(secret.DPAPI_PREFIX + "@@broken@@") == ""

    def test_non_string_becomes_empty(self):
        assert SecretSerializer("Cookie.SESSDATA").deserialize(None) == ""
        assert SecretSerializer("Cookie.SESSDATA").deserialize(123) == ""

    @windows_only
    def test_roundtrip_and_stable_ciphertext(self):
        serializer = SecretSerializer("Cookie.SESSDATA")

        stored = serializer.serialize(SENTINEL)

        # 同一个值反复保存不重新加密，配置文件里的密文不会每次都变
        assert serializer.serialize(SENTINEL) == stored
        assert SecretSerializer("Cookie.SESSDATA").deserialize(stored) == SENTINEL

    @windows_only
    def test_legacy_plaintext_is_flagged(self):
        SecretSerializer.legacy_plaintext_found = False

        assert SecretSerializer("Cookie.SESSDATA").deserialize("legacy-plain-value") == "legacy-plain-value"
        assert SecretSerializer.legacy_plaintext_found

    def test_protect_failure_does_not_fall_back_to_plaintext(self, monkeypatch):
        def fail(value, name):
            raise secret.SecretError("模拟保护失败")

        monkeypatch.setattr("util.common.serializer.protect", fail)

        assert SecretSerializer("Cookie.SESSDATA").serialize(SENTINEL) == ""

    def test_store_write_is_cached(self, fake_store):
        serializer = SecretSerializer("Cookie.SESSDATA")

        assert serializer.serialize(SENTINEL) == secret.KEYRING_MARKER

        # 每次保存配置都会序列化全部字段，值没变就不该再写密钥库
        fake_store.fail = True

        assert serializer.serialize(SENTINEL) == secret.KEYRING_MARKER

    def test_store_logout_deletes_entry(self, fake_store):
        serializer = SecretSerializer("Cookie.SESSDATA")

        serializer.serialize(SENTINEL)

        assert serializer.serialize("") == ""
        assert fake_store.data == {}

    def test_unavailable_keeps_marker_and_entry(self, fake_store):
        # 密钥库这次读不到：按空值处理，但下一次保存必须原样写回标记，不能删掉库里的凭据
        fake_store.data[(secret.SERVICE, "Cookie.SESSDATA")] = SENTINEL
        fake_store.fail = True

        SecretSerializer.unavailable_found = False

        serializer = SecretSerializer("Cookie.SESSDATA")

        assert serializer.deserialize(secret.KEYRING_MARKER) == ""
        assert SecretSerializer.unavailable_found

        assert serializer.serialize("") == secret.KEYRING_MARKER
        assert fake_store.deleted == []

        # 之后重新登录则照常写入
        fake_store.fail = False

        assert serializer.serialize("new-value") == secret.KEYRING_MARKER
        assert fake_store.data[(secret.SERVICE, "Cookie.SESSDATA")] == "new-value"

    def test_not_found_drops_marker(self, fake_store):
        # 库里确实没有了：标记失去意义，下次保存写空值
        SecretSerializer.unavailable_found = False

        serializer = SecretSerializer("Cookie.SESSDATA")

        assert serializer.deserialize(secret.KEYRING_MARKER) == ""
        assert not SecretSerializer.unavailable_found
        assert serializer.serialize("") == ""

    def test_legacy_plaintext_is_flagged_with_store(self, fake_store):
        SecretSerializer.legacy_plaintext_found = False

        assert SecretSerializer("Cookie.SESSDATA").deserialize("legacy-plain-value") == "legacy-plain-value"
        assert SecretSerializer.legacy_plaintext_found

    def test_legacy_plaintext_not_flagged_without_store(self, monkeypatch):
        # 没有保护手段时明文就是正常形态，不必迁移
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(secret, "_store", lambda: None)

        SecretSerializer.legacy_plaintext_found = False

        SecretSerializer("Cookie.SESSDATA").deserialize("plain-value")

        assert not SecretSerializer.legacy_plaintext_found


class TestConfigFile:
    @protected_only
    def test_secrets_are_not_written_in_plaintext(self):
        config.set(config.SESSDATA, SENTINEL)
        config.set(config.mcp_token, SENTINEL + "-token")

        content = config.file.read_text(encoding = "utf-8")

        assert SENTINEL not in content
        assert secret.DPAPI_PREFIX in content or secret.KEYRING_MARKER in content

        # 内存中仍是明文，调用方感知不到保护
        assert config.get(config.SESSDATA) == SENTINEL

    @posix_only
    def test_config_file_is_private(self):
        config.set(config.SESSDATA, SENTINEL)

        assert stat.S_IMODE(os.stat(config.file).st_mode) == 0o600


class TestSettleSecrets:
    def test_login_reset_when_sessdata_missing(self):
        # 凭据取不出来后 SESSDATA 为空，is_login 却还是 True
        config.set(config.SESSDATA, "")
        config.set(config.is_login, True)

        SecretSerializer.unavailable_found = False

        settle_secrets()

        assert config.get(config.is_login) is False

    def test_login_kept_when_store_temporarily_unavailable(self):
        # 密钥库只是这次读不到：不能落盘成未登录，否则下次能读了用户也已经被登出
        config.set(config.SESSDATA, "")
        config.set(config.is_login, True)

        runtime.auth.is_expired = False
        SecretSerializer.unavailable_found = True

        settle_secrets()

        assert config.get(config.is_login) is True
        assert runtime.auth.is_expired is True
        assert not SecretSerializer.unavailable_found

    def test_login_kept_when_sessdata_present(self):
        config.set(config.SESSDATA, SENTINEL)
        config.set(config.is_login, True)

        settle_secrets()

        assert config.get(config.is_login) is True

    @protected_only
    def test_legacy_plaintext_is_migrated(self):
        # 模拟读到旧版配置：字段经反序列化读入明文
        config.SESSDATA.deserializeFrom(SENTINEL)

        assert SecretSerializer.legacy_plaintext_found

        settle_secrets()

        assert not SecretSerializer.legacy_plaintext_found
        assert config.get(config.SESSDATA) == SENTINEL
        assert SENTINEL not in config.file.read_text(encoding = "utf-8")


class TestSecretServiceStore:
    """真实的 Secret Service（GNOME Keyring 等）。只在 Linux 桌面上运行"""

    NAME = "Cookie.pytest_probe"

    @pytest.fixture(autouse = True)
    def cleanup(self):
        yield

        store = secret._store()

        if store is not None:
            store.delete(secret.SERVICE, self.NAME)

    @secret_service_only
    def test_set_get_delete(self):
        store = secret._store()

        store.set(secret.SERVICE, self.NAME, "含中文与符号 %2C,=;")

        assert store.get(secret.SERVICE, self.NAME) == "含中文与符号 %2C,=;"

        store.delete(secret.SERVICE, self.NAME)

        assert store.get(secret.SERVICE, self.NAME) is None

    @secret_service_only
    def test_overwrite_replaces_entry(self):
        store = secret._store()

        store.set(secret.SERVICE, self.NAME, "first")
        store.set(secret.SERVICE, self.NAME, "second")

        assert store.get(secret.SERVICE, self.NAME) == "second"

        # replace = True：同属性的条目只留一个，删一次就干净
        store.delete(secret.SERVICE, self.NAME)

        assert store.get(secret.SERVICE, self.NAME) is None

    @secret_service_only
    def test_delete_missing_is_noop(self):
        secret._store().delete(secret.SERVICE, self.NAME)

    @secret_service_only
    def test_config_roundtrip(self):
        # 走完整条链：config.set → 密钥库 → 配置里只有标记 → 重新读回
        config.set(config.SESSDATA, SENTINEL)

        assert loads(config.file.read_text(encoding = "utf-8"))["Cookie"]["SESSDATA"] == secret.KEYRING_MARKER
        assert SecretSerializer("Cookie.SESSDATA").deserialize(secret.KEYRING_MARKER) == SENTINEL

        config.set(config.SESSDATA, "")

        assert secret._store().get(secret.SERVICE, "Cookie.SESSDATA") is None


class TestStdioBridgeToken:
    def test_token_name_matches_config(self):
        # 桥接不能导入 config，只能写死这个名字
        assert MCP_TOKEN_NAME == config.mcp_token.key

    def test_keyring_token(self, fake_store):
        fake_store.data[(secret.SERVICE, MCP_TOKEN_NAME)] = "real-token"

        assert _decrypt_token(secret.KEYRING_MARKER) == "real-token"

    def test_keyring_token_unavailable(self, fake_store):
        fake_store.fail = True

        assert _decrypt_token(secret.KEYRING_MARKER) is None

    def test_missing_token(self):
        assert _decrypt_token(None) is None

    def test_legacy_plaintext_token(self):
        assert _decrypt_token("plain-token") == "plain-token"

    def test_undecryptable_token(self):
        assert _decrypt_token(secret.DPAPI_PREFIX + "@@broken@@") is None

    @windows_only
    def test_encrypted_token(self):
        assert _decrypt_token(secret.protect("real-token", MCP_TOKEN_NAME)) == "real-token"


class TestLoginStateItems:
    def test_covers_all_secrets_and_is_login(self):
        names = {item.name for item in login_state_items()}

        assert names == {*SECRET_ITEMS, "is_login"}


class TestExport:
    def test_login_state_is_stripped(self, tmp_path):
        config.set(config.SESSDATA, SENTINEL)
        config.set(config.bili_jct, SENTINEL + "-jct")
        config.set(config.mcp_token, SENTINEL + "-token")
        config.set(config.is_login, True)
        config.set(config.download_thread, 7)

        target = tmp_path / "exported.json"

        assert config.export_to(target)

        text = target.read_text(encoding = "utf-8")
        data = loads(text)

        assert SENTINEL not in text
        assert secret.DPAPI_PREFIX not in text
        assert data["Cookie"]["SESSDATA"] == ""
        assert data["Cookie"]["is_login"] is False
        assert data["MCP"]["mcp_token"] == ""

        # 普通设置照常导出
        assert data["Download"]["download_thread"] == 7

    def test_does_not_touch_in_memory_config(self, tmp_path):
        # 旧实现借一个临时 APPConfig 去 load，配置项是类属性，等于把磁盘内容读回了
        # 全局配置：save = False 写入的值会被磁盘上的旧值覆盖，登录态也会被一并改写
        config.set(config.SESSDATA, SENTINEL)
        config.set(config.is_login, True)
        config.set(config.img_key, "memory-only-key", save = False)

        assert config.export_to(tmp_path / "exported.json")

        assert config.get(config.img_key) == "memory-only-key"
        assert config.get(config.SESSDATA) == SENTINEL
        assert config.get(config.is_login) is True

    def test_unwritable_target_returns_false(self, tmp_path):
        assert not config.export_to(tmp_path / "missing-dir" / "exported.json")


class TestImport:
    def _write(self, path, data):
        path.write_text(dumps_std(data, indent = 4), encoding = "utf-8")

        return path

    def test_login_state_is_preserved(self, tmp_path):
        config.set(config.SESSDATA, SENTINEL)
        config.set(config.mcp_token, "local-token")
        config.set(config.is_login, True)
        config.set(config.download_thread, 4)

        source = self._write(tmp_path / "foreign.json", {
            "Download": {"download_thread": 7},
            "Cookie": {
                # 别的电脑导出的密文，以及旧版导出文件里的明文
                "SESSDATA": secret.DPAPI_PREFIX + "AAAAAAAAAAAA",
                "bili_jct": "foreign-plain-jct",
                "is_login": False,
            },
            "MCP": {"mcp_token": "foreign-token"},
        })

        assert config.import_from(source)

        assert config.get(config.download_thread) == 7
        assert config.get(config.SESSDATA) == SENTINEL
        assert config.get(config.bili_jct) != "foreign-plain-jct"
        assert config.get(config.mcp_token) == "local-token"
        assert config.get(config.is_login) is True

    def test_imported_plaintext_does_not_trigger_migration(self, tmp_path):
        SecretSerializer.legacy_plaintext_found = False

        source = self._write(tmp_path / "legacy.json", {"Cookie": {"SESSDATA": "legacy-plain"}})

        assert config.import_from(source)
        assert not SecretSerializer.legacy_plaintext_found

    def test_import_is_saved(self, tmp_path):
        source = self._write(tmp_path / "settings.json", {"Download": {"download_thread": 9}})

        assert config.import_from(source)

        assert loads(config.file.read_text(encoding = "utf-8"))["Download"]["download_thread"] == 9

    def test_export_then_import_roundtrip(self, tmp_path):
        config.set(config.download_thread, 6)

        target = tmp_path / "roundtrip.json"

        assert config.export_to(target)

        config.set(config.download_thread, 2)

        assert config.import_from(target)
        assert config.get(config.download_thread) == 6

    @pytest.mark.parametrize("content", ["{not json", "[1, 2, 3]"])
    def test_malformed_file_is_rejected(self, tmp_path, content):
        config.set(config.download_thread, 4)

        source = tmp_path / "broken.json"
        source.write_text(content, encoding = "utf-8")

        assert not config.import_from(source)
        assert config.get(config.download_thread) == 4

    def test_missing_file_is_rejected(self, tmp_path):
        assert not config.import_from(tmp_path / "missing.json")


class TestRestrictPermission:
    @posix_only
    def test_loose_permission_is_tightened(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text("{}", encoding = "utf-8")
        os.chmod(path, 0o644)

        restrict_permission(path)

        assert stat.S_IMODE(os.stat(path).st_mode) == 0o600

    def test_missing_file_is_ignored(self, tmp_path):
        restrict_permission(tmp_path / "missing.json")
