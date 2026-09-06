"""系统信息与健康检查"""

from fastapi import APIRouter

from util.common.config import config

router = APIRouter(tags = ["system"])

@router.get("/health")
async def health():
    """
    健康检查。**不需要登录** —— 反向代理与容器编排要靠它判断存活，
    因此这里也不能泄漏任何有意义的信息
    """
    return {"status": "ok"}

@router.get("/status")
async def status():
    """登录后可见的运行状态"""
    return {
        "version": config.app_version,
        "logged_in_bilibili": bool(config.get(config.is_login)),
        "uname": config.user_uname or "",
        "uid": config.user_uid or "",
    }
