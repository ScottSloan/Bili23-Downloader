"""
配置文件中敏感字段（登录 Cookie、MCP 访问令牌）的落盘保护

三个平台各走一条路，思路取自 Chromium 的 OSCrypt —— 交给操作系统托管，
拿不到系统设施时老实退回明文，不自造密钥：

| 平台 | 做法 | 配置文件里存的 |
| --- | --- | --- |
| Windows | DPAPI 加密（dpapi.py） | `dpapi:v1:<base64 密文>` |
| Linux | 值本身存进 Secret Service（secret_service.py） | `keyring:v1` 标记 |
| macOS | 值本身存进钥匙串（keychain.py） | `keyring:v1` 标记 |
| 以上都不可用 | 明文，配置文件以 0600 权限写入（见 config.py） | 明文 |

Linux / macOS 往密钥库里存的是字段值本身，而不是像 Chromium 那样存一个密钥再自己做
对称加密：我们只有几个字段，直接存值就不需要 AES，也就不必为此引入 cryptography。

能防的是「配置文件离开这台机器」—— 用户把 config.json 附进 issue、网盘同步了配置
目录。防不了以同一用户身份运行的程序：它可以调用同样的接口拿到明文。任何不要求
用户输入口令的本地方案都止步于此，这里不假装能做到更多。

没有选「用机器信息派生密钥」：MachineGuid、/etc/machine-id 之类的标识对本机所有
用户可读，离线也能读出来，派生出的密钥本质上只是混淆。Chromium 在任何平台上也都
没有这样做。

本包**只用标准库**（各平台的第三方库在真正用到时才导入，且导入失败按「不可用」处理），
不得导入任何 Qt 或 config 相关的东西 —— stdio 桥接（util/mcp/stdio_bridge.py）
要靠它取出 MCP 令牌，那个进程刻意不加载 GUI 栈。
"""
from functools import lru_cache
import binascii
import base64
import sys

# 带版本号是为了日后更换算法时能区分新旧格式；不是这两种形态的值一律视为明文
DPAPI_PREFIX = "dpapi:v1:"
KEYRING_MARKER = "keyring:v1"

# 系统密钥库里条目的归属标识。测试会把它换成独立的名字（见 test/conftest.py），
# 否则在装有密钥库的开发机上跑一次测试，就会改写开发者自己的登录凭据
SERVICE = "Bili23 Downloader"

class SecretError(ValueError):
    """值取不出来，且重试也没有用：密文损坏、来自别的电脑或用户账户、平台不支持"""

class SecretNotFound(SecretError):
    """配置文件说值在密钥库里，密钥库里却没有（被用户手动删除、或配置来自别处）"""

class SecretUnavailable(SecretError):
    """
    密钥库暂时用不了：服务没有运行、被锁定且用户没有解锁、通信出错

    与 SecretError 区分开，是因为凭据此时多半还好好地存在密钥库里 ——
    调用方不能把它当作「没有值」处理，否则下次保存时会把密钥库里的凭据一并删掉。
    """

def is_supported() -> bool:
    """当前环境是否会保护敏感字段（否则以明文保存）"""
    return sys.platform == "win32" or _store() is not None

def is_protected(value) -> bool:
    """是否为本模块产出的落盘形式"""
    return isinstance(value, str) and (value.startswith(DPAPI_PREFIX) or value == KEYRING_MARKER)

def protect(plaintext: str, name: str) -> str:
    """
    把字段值转为落盘形式。name 是字段在配置中的键（如 Cookie.SESSDATA），密钥库按它存取

    空串不加密也不入库：未登录时这几个字段都是空的。但在用密钥库的平台上，空串意味着
    要把库里的旧条目删掉 —— 退出登录不能把凭据留在密钥库里。

    失败抛 SecretError。
    """
    if sys.platform == "win32":
        if not plaintext:
            return ""

        from .dpapi import encrypt

        try:
            ciphertext = encrypt(plaintext.encode("utf-8"))

        except OSError as e:
            raise SecretError(f"DPAPI 加密失败：{e}") from e

        return DPAPI_PREFIX + base64.b64encode(ciphertext).decode("ascii")

    store = _store()

    if store is None:
        return plaintext

    if not plaintext:
        store.delete(SERVICE, name)

        return ""

    store.set(SERVICE, name, plaintext)

    return KEYRING_MARKER

def unprotect(value: str, name: str) -> str:
    """
    把落盘形式还原为字段值。不是本模块产出的值视为明文原样返回

    取不出来时抛 SecretError 的某个子类，而不是返回空串 —— 「没有值」「有值但永远
    取不出」「有值但暂时取不出」对调用方是三回事。
    """
    if not is_protected(value):
        return value

    if value == KEYRING_MARKER:
        return _unprotect_keyring(name)

    return _unprotect_dpapi(value)

def _unprotect_keyring(name: str) -> str:
    store = _store()

    if store is None:
        if sys.platform == "win32":
            # 配置是从 Linux / macOS 拷过来的，Windows 上永远取不到
            raise SecretError("该字段存放在 Linux / macOS 的系统密钥库中，当前平台无法读取")

        # 同一台机器上换了个没有桌面会话的环境启动（如 SSH 登录），凭据多半还在
        raise SecretUnavailable("系统密钥库不可用")

    plaintext = store.get(SERVICE, name)

    if plaintext is None:
        raise SecretNotFound(f"系统密钥库中没有 {name}")

    return plaintext

def _unprotect_dpapi(value: str) -> str:
    if sys.platform != "win32":
        raise SecretError("该字段由 Windows DPAPI 加密，当前平台无法解密")

    try:
        ciphertext = base64.b64decode(value[len(DPAPI_PREFIX):], validate = True)

    except binascii.Error as e:
        raise SecretError(f"密文格式损坏：{e}") from e

    from .dpapi import decrypt

    try:
        plaintext = decrypt(ciphertext)

    except OSError as e:
        # 最常见的原因是配置来自另一台电脑或另一个用户账户（ERROR_INVALID_DATA 等）
        raise SecretError(f"DPAPI 解密失败：{e}") from e

    try:
        return plaintext.decode("utf-8")

    except UnicodeDecodeError as e:
        raise SecretError(f"解密结果不是有效的 UTF-8：{e}") from e

@lru_cache(maxsize = 1)
def _store():
    """
    当前平台可用的系统密钥库，不可用时返回 None。整个进程只探测一次

    返回的对象提供 get / set / delete(service, name)，失败时抛 SecretUnavailable。
    """
    if sys.platform.startswith("linux"):
        from .secret_service import open_store

    elif sys.platform == "darwin":
        from .keychain import open_store

    else:
        return None

    return open_store()
