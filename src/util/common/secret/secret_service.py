"""
Linux：经 D-Bus 调用 Secret Service 存取敏感字段

Secret Service 是 freedesktop 的标准接口，GNOME Keyring、KDE 的 KWallet、KeePassXC
都实现了它。字段值本身作为一个条目存进默认集合（通常是登录时自动解锁的「登录」钥匙环），
在「密码和密钥」（seahorse）里能看到，标签形如「Bili23 Downloader: Cookie.SESSDATA」。

直接用 jeepney（纯 Python 的 D-Bus 实现，无依赖），不用 keyring / SecretStorage：
后者依赖 cryptography 这个原生扩展，只为了与密钥库之间做一层 DH 协商加密传输。
而会话总线本身只对当前用户开放，规范也允许 plain 传输，这层加密换不来实际的安全收益，
却要往 Linux 包里多塞两个原生扩展、拖慢启动。

不可用（未安装 jeepney、没有会话总线、没有任何实现在运行、没有默认集合）时，
open_store 返回 None，由上层退回明文。
"""
from . import SecretError, SecretUnavailable

from importlib.util import find_spec
from threading import Lock
import logging

logger = logging.getLogger(__name__)

_BUS_NAME = "org.freedesktop.secrets"
_SERVICE_PATH = "/org/freedesktop/secrets"

_SERVICE_IFACE = "org.freedesktop.Secret.Service"
_COLLECTION_IFACE = "org.freedesktop.Secret.Collection"
_ITEM_IFACE = "org.freedesktop.Secret.Item"
_PROMPT_IFACE = "org.freedesktop.Secret.Prompt"

# D-Bus 用 "/" 表示「没有对象」，比如不需要用户确认时返回的 prompt
_NO_OBJECT = "/"

# 普通调用的超时。密钥库就在本机，正常情况下是毫秒级的
_CALL_TIMEOUT = 10

# 首次探测的超时，单独压短。总线上还没有 Secret Service 时，第一次调用会触发 D-Bus 按需
# 启动 gnome-keyring 之类的实现，正常几百毫秒就能接管服务名；但实测存在启动了却始终不接管
# 的情况（如在 dbus-run-session 开出的私有总线上），这时调用要一直等到超时 —— 而探测发生在
# 启动期加载配置时，按普通超时算就是界面出来前白等 10 秒。
#
# 误判为不可用是安全的：配置里已有的标记按「暂时不可用」处理，不会删掉库里的凭据；
# 新写入的值以明文保存，下次启动探测成功时再迁移进密钥库
_PROBE_TIMEOUT = 3

# 等待用户在解锁对话框里输入密码的时间上限。启动时读取凭据就可能触发它
# （如开启了自动登录的桌面，登录钥匙环不会被自动解锁），而那时界面还没出来，
# 太短会让动作慢的用户来不及输入，太长则会让程序看起来卡死
_PROMPT_TIMEOUT = 120

def open_store():
    if find_spec("jeepney") is None:
        logger.info("未安装 jeepney，敏感配置项将以明文保存")

        return None

    store = SecretServiceStore()

    try:
        store.probe()

    except SecretUnavailable as e:
        logger.info("Secret Service 不可用，敏感配置项将以明文保存：%s", e)

        return None

    return store

class SecretServiceStore:
    """
    全部操作串行化在一条 D-Bus 连接上

    config.set 会在任意线程上触发保存，jeepney 的阻塞连接不是线程安全的，
    因此每个公开方法都持锁。出错时丢弃连接，下次调用重新建立。
    """

    def __init__(self):
        self._lock = Lock()

        self._conn = None
        self._session = None

    def probe(self):
        """确认服务在运行、存在默认集合。不解锁，也就不会弹出对话框"""
        self._run(lambda: self._default_collection(timeout = _PROBE_TIMEOUT), timeout = _PROBE_TIMEOUT)

    def get(self, service: str, name: str):
        """返回字段值，库里没有时返回 None"""
        def op():
            items = self._search(service, name)

            if not items:
                return None

            secret = self._call(items[0], _ITEM_IFACE, "GetSecret", "o", (self._session,))[0]

            # secret 是 (session, parameters, value, content_type)，plain 传输下 value 即明文
            try:
                return bytes(secret[2]).decode("utf-8")

            except UnicodeDecodeError as e:
                raise SecretError(f"密钥库中的 {name} 不是有效的 UTF-8：{e}") from e

        return self._run(op)

    def set(self, service: str, name: str, value: str):
        def op():
            collection = self._default_collection()

            self._unlock([collection])

            properties = {
                "org.freedesktop.Secret.Item.Label": ("s", f"{service}: {name}"),
                "org.freedesktop.Secret.Item.Attributes": ("a{ss}", _attributes(service, name)),
            }

            secret = (self._session, b"", value.encode("utf-8"), "text/plain; charset=utf8")

            # replace = True：属性完全相同的旧条目被就地替换，不会越存越多
            _item, prompt = self._call(collection, _COLLECTION_IFACE, "CreateItem", "a{sv}(oayays)b", (properties, secret, True))

            self._complete_prompt(prompt)

        self._run(op)

    def delete(self, service: str, name: str):
        def op():
            for item in self._search(service, name):
                prompt = self._call(item, _ITEM_IFACE, "Delete")[0]

                self._complete_prompt(prompt)

        self._run(op)

    def _run(self, op, timeout = _CALL_TIMEOUT):
        with self._lock:
            try:
                self._ensure_connection(timeout)

                return op()

            except SecretError:
                raise

            # 有意兜住全部异常。jeepney 在连接阶段会抛 KeyError（没有会话总线地址）、
            # RuntimeError（不支持的传输方式）、ValueError（认证失败），通信阶段抛 OSError
            # 与 DBusErrorResponse —— 但调用方是配置的序列化：漏出去一个意料之外的异常，
            # 在 config.save 里会让整份配置都写不进去，在 qfluentwidgets 的 load 里会被静默吞掉、
            # 后面的配置项全部不再加载。密钥库出什么问题，都只该让这一个字段取不到
            except Exception as e:
                self._reset_connection()

                raise SecretUnavailable(f"Secret Service 通信失败：{e!r}") from e

    def _ensure_connection(self, timeout):
        if self._conn is not None:
            return

        from jeepney.io.blocking import open_dbus_connection

        self._conn = open_dbus_connection(bus = "SESSION")

        try:
            # plain：值以明文经会话总线传输，理由见模块说明。
            # 这是连接上的第一次调用，按需启动 Secret Service 的等待也落在这里
            _output, self._session = self._call(_SERVICE_PATH, _SERVICE_IFACE, "OpenSession", "sv", ("plain", ("s", "")), timeout = timeout)

        except BaseException:
            self._reset_connection()

            raise

    def _reset_connection(self):
        conn, self._conn, self._session = self._conn, None, None

        if conn is not None:
            try:
                conn.close()

            except OSError:
                logger.debug("关闭 D-Bus 连接失败", exc_info = True)

    def _call(self, path: str, interface: str, method: str, signature = None, body = (), timeout = _CALL_TIMEOUT):
        from jeepney import DBusAddress, new_method_call
        from jeepney.wrappers import unwrap_msg

        address = DBusAddress(path, bus_name = _BUS_NAME, interface = interface)

        reply = self._conn.send_and_get_reply(new_method_call(address, method, signature, body), timeout = timeout)

        # 错误回复不会自己抛出，要经 unwrap_msg 转成 DBusErrorResponse
        return unwrap_msg(reply)

    def _default_collection(self, timeout = _CALL_TIMEOUT) -> str:
        path = self._call(_SERVICE_PATH, _SERVICE_IFACE, "ReadAlias", "s", ("default",), timeout = timeout)[0]

        if path == _NO_OBJECT:
            # 新装的系统在第一次有程序存密码前可能还没有默认集合。创建它要弹窗让用户设密码，
            # 不值得为此打扰用户，按不可用处理（退回明文）
            raise SecretUnavailable("Secret Service 中没有默认集合")

        return path

    def _search(self, service: str, name: str) -> list:
        unlocked, locked = self._call(_SERVICE_PATH, _SERVICE_IFACE, "SearchItems", "a{ss}", (_attributes(service, name),))

        if locked:
            unlocked = list(unlocked) + self._unlock(locked)

        return list(unlocked)

    def _unlock(self, paths: list) -> list:
        """解锁给定对象，必要时弹出系统的解锁对话框。返回已解锁的对象"""
        unlocked, prompt = self._call(_SERVICE_PATH, _SERVICE_IFACE, "Unlock", "ao", (paths,))

        result = self._complete_prompt(prompt)

        if result is not None:
            # Unlock 的 prompt 结果是一个 ao 型的 variant：(签名, 已解锁的对象列表)
            unlocked = list(unlocked) + list(result[1])

        return list(unlocked)

    def _complete_prompt(self, prompt: str):
        """
        执行一个需要用户确认的操作（通常是输入密码解锁），等待其完成并返回结果 variant

        不需要确认时返回 None；用户取消或超时抛 SecretUnavailable。
        """
        if prompt == _NO_OBJECT:
            return None

        from jeepney import MatchRule
        from jeepney.bus_messages import message_bus
        from jeepney.wrappers import unwrap_msg

        # 不按 sender 过滤：信号头里是服务的唯一名（:1.23 之类），jeepney 在本地按字面
        # 比较，写知名名称 org.freedesktop.secrets 会让信号永远匹配不上
        rule = MatchRule(type = "signal", interface = _PROMPT_IFACE, member = "Completed", path = prompt)

        with self._conn.filter(rule) as queue:
            # 先订阅再触发，否则信号可能在订阅生效前就已经发出
            unwrap_msg(self._conn.send_and_get_reply(message_bus.AddMatch(rule), timeout = _CALL_TIMEOUT))

            self._call(prompt, _PROMPT_IFACE, "Prompt", "s", ("",))

            try:
                signal = self._conn.recv_until_filtered(queue, timeout = _PROMPT_TIMEOUT)

            except TimeoutError as e:
                # 不要调 Prompt.Dismiss 去撤掉还挂在屏幕上的对话框：GNOME Keyring 对解锁对话框
                # 执行 Dismiss 会触发自身的断言（gkd-secret-unlock.c perform_next_unlock:
                # assertion failed: (!self->current)），整个守护进程直接崩溃，用户的所有密钥环
                # 随之掉线 —— 在 Ubuntu 22.04 上实测如此。对话框留着无害：用户之后无论确认还是
                # 取消，都只是发出一个已经没人在听的信号
                raise SecretUnavailable("等待用户解锁密钥库超时") from e

        dismissed, result = signal.body

        if dismissed:
            raise SecretUnavailable("用户取消了密钥库解锁")

        return result

def _attributes(service: str, name: str) -> dict:
    # 查找条目只靠这两个属性。不复用 keyring 库的 service / username 约定 ——
    # 两边混用同一个条目没有好处，反而可能被别的程序误改
    return {"application": service, "name": name}
