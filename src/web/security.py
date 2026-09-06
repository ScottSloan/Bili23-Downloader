"""
单用户密码鉴权（D6）

qBittorrent 风格：配置里存一个用户名 + 密码 hash，登录换 session cookie，
不做多用户 / 角色 / OAuth。使用场景是个人 NAS 或局域网，但服务可能被暴露，裸奔不可接受。

## 密码 hash

用标准库的 `hashlib.pbkdf2_hmac`，**不引 bcrypt / argon2**：为了一个单用户口令多背一个
需要编译的依赖不划算，而 PBKDF2-HMAC-SHA256 配足够的迭代次数对这个场景是够的
（qBittorrent 用的也是 PBKDF2）。

存储格式沿用 Django 那套 `算法$迭代次数$盐$散列`，好处是迭代次数写在串里 ——
将来调高默认值时，老口令仍能用它自己那份参数校验通过，用户下次登录再悄悄升级。

## 会话

**存在内存里**，进程重启即失效。对单用户的自托管服务这是合理的：
落盘会话要么再开一张表，要么把签名密钥也存进配置，收益和复杂度不成比例；
而重启后重新登录一次的代价很小。qBittorrent 也是这么做的。

会话令牌用 `secrets.token_urlsafe`，比较口令时用 `hmac.compare_digest` —— 普通的 `==`
会因为提前返回而泄漏前缀信息，这类比较必须是常数时间的。
"""

from dataclasses import dataclass
from typing import Optional
import base64
import hashlib
import hmac
import logging
import secrets
import threading
import time

logger = logging.getLogger(__name__)

ALGORITHM = "pbkdf2_sha256"

# OWASP 2023 对 PBKDF2-HMAC-SHA256 的建议是 600000。本地登录一次的开销在百毫秒量级，
# 可以接受。调高这个值不会让老口令失效 —— 迭代次数是跟着 hash 串一起存的
DEFAULT_ITERATIONS = 600_000

SALT_BYTES = 16
TOKEN_BYTES = 32

SESSION_COOKIE = "BILI23_SID"

def hash_password(password: str, iterations: int = DEFAULT_ITERATIONS) -> str:
    """生成 `pbkdf2_sha256$迭代次数$盐$散列`"""
    salt = secrets.token_bytes(SALT_BYTES)

    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)

    return "{}${}${}${}".format(
        ALGORITHM,
        iterations,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )

def verify_password(password: str, encoded: str) -> bool:
    """
    校验口令。格式不对、算法不认识一律返回 False，不抛异常 ——
    配置可能被手工改坏，那种情况下应当是「登录失败」而不是「服务 500」
    """
    if not encoded:
        return False

    try:
        algorithm, iterations, salt_b64, digest_b64 = encoded.split("$")

        if algorithm != ALGORITHM:
            return False

        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)

        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))

    except Exception:
        logger.warning("密码 hash 格式无法解析，登录一律拒绝")

        return False

    # 常数时间比较：普通的 == 会因为提前返回而泄漏信息
    return hmac.compare_digest(actual, expected)

def generate_password(length: int = 12) -> str:
    """首次启动时用的随机口令"""
    return secrets.token_urlsafe(length)[:length]

@dataclass
class Session:
    token: str
    created_at: float
    expires_at: float

class SessionStore:
    """
    内存会话表

    单用户场景下条目极少，直接用 dict + 锁。每次查找时顺手清掉过期项，
    不另起清理线程 —— 那点收益不值得多一个需要在退出时收敛的线程
    """

    def __init__(self, ttl_seconds: float):
        self.ttl_seconds = ttl_seconds

        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def create(self) -> Session:
        now = time.time()

        session = Session(
            token = secrets.token_urlsafe(TOKEN_BYTES),
            created_at = now,
            expires_at = now + self.ttl_seconds,
        )

        with self._lock:
            self._purge_expired(now)

            self._sessions[session.token] = session

        return session

    def get(self, token: Optional[str]) -> Optional[Session]:
        if not token:
            return None

        now = time.time()

        with self._lock:
            self._purge_expired(now)

            session = self._sessions.get(token)

        if session is None:
            return None

        return session if session.expires_at > now else None

    def revoke(self, token: Optional[str]) -> None:
        if not token:
            return

        with self._lock:
            self._sessions.pop(token, None)

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()

    def _purge_expired(self, now: float) -> None:
        # 调用方已持锁
        expired = [token for token, s in self._sessions.items() if s.expires_at <= now]

        for token in expired:
            del self._sessions[token]

    def __len__(self) -> int:
        with self._lock:
            self._purge_expired(time.time())

            return len(self._sessions)
