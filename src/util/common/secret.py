"""
配置文件中敏感字段（登录 Cookie、MCP 访问令牌）的加解密

Windows 上走 DPAPI（CryptProtectData / CryptUnprotectData）：密钥由系统托管，
绑定当前用户的登录凭据。配置文件被拷到别的电脑、或同一台电脑的其他用户账户下，
都解不开；用户把 config.json 附进 issue、网盘同步了 AppData 这类最常见的泄露
也就随之失效。

它防不了以同一用户身份运行的程序 —— 那样的程序可以直接调用同一个接口解密。
任何不要求用户输入口令的本地方案都止步于此，这里不假装能做到更多。

没有选「用机器信息派生密钥」：MachineGuid 之类的标识对本机所有用户可读，
离线拿到磁盘也能读出来，派生出的密钥本质上只是混淆；而且标准库没有 AES，
要么引入 cryptography 进打包运行时，要么自己拼一套对称加密，两样都不划算。

非 Windows 平台不加密，原样存储（配置文件改由 config.save 以 0600 权限写入）：
macOS 钥匙串与 Linux Secret Service 各要一套需要专门环境才能验证的代码，
后者在无桌面会话时还根本不可用。

本模块**只用标准库**，且不得导入任何 Qt 或 config 相关的东西 —— stdio 桥接
（util/mcp/stdio_bridge.py）要靠它解出配置文件里的 MCP 令牌，那个进程刻意
不加载 GUI 栈。ctypes 也只在真正调用 DPAPI 时才导入。
"""
from functools import lru_cache
import binascii
import base64
import sys

# 密文前缀。带版本号是为了日后更换算法时能区分新旧格式；
# 没有前缀的值一律视为旧版遗留的明文
PREFIX = "dpapi:v1:"

# DPAPI 的附加熵。不是密钥（写在源码里谈不上保密），作用是让其他程序拿到这段
# 密文后不能不加区分地直接 CryptUnprotectData 解开 —— 它还得知道这个值。
# 改动它会让所有已加密的字段解不开，用户需要重新登录
_ENTROPY = b"Bili23 Downloader/config-secret"

# 禁止 DPAPI 弹出任何交互界面。stdio 桥接没有界面，主程序也不应被它阻塞
_CRYPTPROTECT_UI_FORBIDDEN = 0x01

class SecretError(ValueError):
    """密文无法解开：格式损坏、来自别的电脑或用户账户、或当前平台不支持解密"""

def is_supported() -> bool:
    """当前平台是否会加密存储"""
    return sys.platform == "win32"

def is_protected(value) -> bool:
    """是否为本模块产出的密文"""
    return isinstance(value, str) and value.startswith(PREFIX)

def protect(plaintext: str) -> str:
    """
    加密一个字段值。空串与不支持加密的平台原样返回

    空串不加密：未登录时这几个字段都是空的，加密只会让配置文件里多出几段
    看不出含义的密文，还让每次保存都白调几次 DPAPI。

    DPAPI 调用失败时抛 OSError，由调用方决定如何兜底。
    """
    if not plaintext or not is_supported():
        return plaintext

    ciphertext = _dpapi_call("CryptProtectData", plaintext.encode("utf-8"))

    return PREFIX + base64.b64encode(ciphertext).decode("ascii")

def unprotect(value: str) -> str:
    """
    解密一个字段值。不带前缀的值视为旧版明文原样返回

    解不开时抛 SecretError，不返回空串 —— 「没有值」与「有值但解不开」对调用方
    是两回事：后者往往意味着配置是从别处拷来的，需要记日志、清理关联状态。
    """
    if not is_protected(value):
        return value

    if not is_supported():
        raise SecretError("该字段由 Windows DPAPI 加密，当前平台无法解密")

    try:
        ciphertext = base64.b64decode(value[len(PREFIX):], validate = True)

    except binascii.Error as e:
        raise SecretError(f"密文格式损坏：{e}") from e

    try:
        plaintext = _dpapi_call("CryptUnprotectData", ciphertext)

    except OSError as e:
        # 最常见的原因是配置来自另一台电脑或另一个用户账户（ERROR_INVALID_DATA 等）
        raise SecretError(f"DPAPI 解密失败：{e}") from e

    try:
        return plaintext.decode("utf-8")

    except UnicodeDecodeError as e:
        raise SecretError(f"解密结果不是有效的 UTF-8：{e}") from e

@lru_cache(maxsize = 1)
def _load_dpapi():
    import ctypes
    from ctypes import wintypes

    class DataBlob(ctypes.Structure):
        _fields_ = (
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_char)),
        )

    # 用独立的 WinDLL 实例而不是 ctypes.windll 上那个共享对象：下面要给函数设
    # argtypes / restype，设在共享对象上会改掉进程内其他代码看到的函数原型
    crypt32 = ctypes.WinDLL("crypt32", use_last_error = True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error = True)

    blob_ptr = ctypes.POINTER(DataBlob)

    # 两个函数的第二个参数不同（加密是输入的描述串，解密是输出的描述串指针），
    # 这里一律不用，按 void* 传 NULL 即可共用一份原型
    for func in (crypt32.CryptProtectData, crypt32.CryptUnprotectData):
        func.argtypes = (blob_ptr, ctypes.c_void_p, blob_ptr, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, blob_ptr)
        func.restype = wintypes.BOOL

    # 不设原型的话返回值按 int 截断，64 位下指针会被砍掉高位
    kernel32.LocalFree.argtypes = (ctypes.c_void_p,)
    kernel32.LocalFree.restype = ctypes.c_void_p

    return ctypes, DataBlob, crypt32, kernel32

def _dpapi_call(func_name: str, data: bytes) -> bytes:
    ctypes, DataBlob, crypt32, kernel32 = _load_dpapi()

    def make_blob(raw: bytes):
        # buffer 必须与 blob 一起存活到调用结束，blob 只持有它的裸指针
        buffer = ctypes.create_string_buffer(raw, len(raw))

        return buffer, DataBlob(len(raw), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))

    # 下划线前缀：这两个名字只为让 buffer 活到函数结束，之后不再读取
    _data_buffer, data_blob = make_blob(data)
    _entropy_buffer, entropy_blob = make_blob(_ENTROPY)
    out_blob = DataBlob()

    func = getattr(crypt32, func_name)

    if not func(ctypes.byref(data_blob), None, ctypes.byref(entropy_blob), None, None, _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(out_blob)):
        raise ctypes.WinError(ctypes.get_last_error())

    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)

    finally:
        # 输出缓冲区由 DPAPI 用 LocalAlloc 分配，必须由调用方释放
        kernel32.LocalFree(out_blob.pbData)
