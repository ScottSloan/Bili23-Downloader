"""
macOS：把敏感字段存进钥匙串

用 keyring 库的 macOS 后端（ctypes 调 Security 框架，纯 Python）。直接实例化这一个
后端，不走 keyring.get_keyring() 的自动选择：后者要遍历入口点发现全部后端，拖慢启动，
还可能选中用户自己装的 keyrings.alt 之类以明文存文件的后端。

条目在「钥匙串访问」里能看到，服务名为「Bili23 Downloader」，账户名为字段键（如
Cookie.SESSDATA）。钥匙串按应用签名授予访问权，应用签名变化后（如换了签名证书）
首次读取会弹窗请用户允许。

**本模块没有在 macOS 上实际验证过**：维护者手头没有 macOS 设备。它刻意只做最薄的一层
转发，所有平台相关的逻辑都在 keyring 库里。不可用（未安装 keyring、Security 框架
加载失败）时 open_store 返回 None，由上层退回明文。
"""
from . import SecretUnavailable

import logging

logger = logging.getLogger(__name__)

def open_store():
    try:
        from keyring.backends import macOS

    except ImportError:
        logger.info("未安装 keyring，敏感配置项将以明文保存")

        return None

    try:
        # priority 在平台不符或 Security 框架加载失败时抛 RuntimeError，是该后端自带的可用性检查
        macOS.Keyring.priority  # noqa: B018

    except RuntimeError as e:
        logger.info("钥匙串不可用，敏感配置项将以明文保存：%s", e)

        return None

    return KeychainStore(macOS.Keyring())

class KeychainStore:
    """
    各方法有意兜住全部异常，而不只是 keyring 的 KeyringError：调用方是配置的序列化，
    漏出去一个意料之外的异常（如 ctypes 调用出错），在 config.save 里会让整份配置都写不进去，
    在 qfluentwidgets 的 load 里会被静默吞掉、后面的配置项全部不再加载
    """

    def __init__(self, backend):
        self._backend = backend

    def get(self, service: str, name: str):
        """返回字段值，钥匙串里没有时返回 None"""
        try:
            return self._backend.get_password(service, name)

        except Exception as e:
            raise SecretUnavailable(f"读取钥匙串失败：{e}") from e

    def set(self, service: str, name: str, value: str):
        try:
            self._backend.set_password(service, name, value)

        except Exception as e:
            raise SecretUnavailable(f"写入钥匙串失败：{e}") from e

    def delete(self, service: str, name: str):
        # keyring 删除不存在的条目会抛 PasswordDeleteError，与真正的失败是同一个异常类型，
        # 因此先查一次。退出登录时才会走到这里，多一次查询无关紧要
        if self.get(service, name) is None:
            return

        try:
            self._backend.delete_password(service, name)

        except Exception as e:
            raise SecretUnavailable(f"删除钥匙串条目失败：{e}") from e
