"""
Windows：经 DPAPI（CryptProtectData / CryptUnprotectData）加解密

密钥由系统托管，绑定当前用户的登录凭据。配置文件被拷到别的电脑、或同一台电脑的
其他用户账户下，都解不开。

只用 ctypes，且只在真正调用时才加载 crypt32。
"""
from functools import lru_cache

# DPAPI 的附加熵。不是密钥（写在源码里谈不上保密），作用是让其他程序拿到这段
# 密文后不能不加区分地直接 CryptUnprotectData 解开 —— 它还得知道这个值。
# 改动它会让所有已加密的字段解不开，用户需要重新登录
_ENTROPY = b"Bili23 Downloader/config-secret"

# 禁止 DPAPI 弹出任何交互界面。stdio 桥接没有界面，主程序也不应被它阻塞
_CRYPTPROTECT_UI_FORBIDDEN = 0x01

def encrypt(data: bytes) -> bytes:
    """失败抛 OSError"""
    return _dpapi_call("CryptProtectData", data)

def decrypt(data: bytes) -> bytes:
    """失败抛 OSError，最常见的原因是密文来自另一台电脑或另一个用户账户"""
    return _dpapi_call("CryptUnprotectData", data)

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
