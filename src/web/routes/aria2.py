"""aria2 的运行状态"""

from fastapi import APIRouter, Request

from ..aria2 import Aria2NotConnected

from ..schemas import Aria2Status

router = APIRouter(tags = ["aria2"])

@router.get("/status", response_model = Aria2Status)
async def aria2_status(request: Request):
    """
    aria2 是否可用

    **不可用不算错误**：服务本身照常跑，这里如实报告状态即可 ——
    前端据此显示「aria2 未连接」并给出原因，比整个后端起不来强
    """
    client = getattr(request.app.state, "aria2", None)
    error = getattr(request.app.state, "aria2_error", None)

    if client is None:
        return {"connected": False, "error": "aria2 未初始化", "version": None}

    if not client.connected:
        return {"connected": False, "error": error or "尚未连接", "version": None}

    try:
        version = await client.get_version()

    except Aria2NotConnected as e:
        return {"connected": False, "error": str(e), "version": None}

    stat = await client.get_global_stat()

    return {
        "connected": True,
        "error": None,
        "version": version.get("version"),
        "active": int(stat.get("numActive", 0)),
        "waiting": int(stat.get("numWaiting", 0)),
        "stopped": int(stat.get("numStopped", 0)),
        "download_speed": int(stat.get("downloadSpeed", 0)),
    }
