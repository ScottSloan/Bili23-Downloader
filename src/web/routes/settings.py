"""
配置读写（S3-11）

## 红线：不要绕过 config

`config.json` 由桌面版与 WebUI **共用**（D5）。保存走的是「读盘再合并」——
磁盘上认不出来的键一律原样保留。绕过 `config.set()` 直接写文件，
会把桌面版刚存的东西整段抹掉，而且不报错。

所以这一层只做三件事：把配置项摊成 JSON、按 attr 找回配置项对象、调 `config.set()`。
取值校验交给 core 那边的 `coerce`（语义是**纠正而非拒绝**：越界 clamp、
认不出的值回落默认），这里不再自己判一遍 —— 判两遍迟早判出两套结果。

## 哪些不给读

口令哈希、B 站的 Cookie、aria2 的 RPC 令牌都在同一个 `config.json` 里。
把整份配置直接吐给前端等于把它们一起送出去。**默认不给，且是白名单之外一律不给**，
不是「列一张黑名单挨个排除」—— 后者迟早漏掉一个新加的敏感项。
"""

from typing import Any, Dict, List
import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from util.common._config.schema import ITEMS, ValueType
from util.common.config import config

logger = logging.getLogger(__name__)

router = APIRouter(tags = ["settings"])

# **不下发也不允许改的配置项。** 判据是「泄漏了会直接造成损失」：
# 登录凭证、口令哈希、RPC 令牌。它们各有专门的接口去改（登录、改密码），
# 不该从通用的配置接口走
SECRET_ATTRS = frozenset({
    "webui_password_hash",
    "aria2_rpc_secret",
    "SESSDATA", "bili_jct", "DedeUserID", "DedeUserID__ckMd5",
    "buvid3", "buvid4", "buvid_fp", "b_lsid", "b_nut", "uuid",
    "bili_ticket", "bili_ticket_expires", "buvid_expires",
    "img_key", "sub_key",
})

# 这些组是桌面窗口专用的，发给前端没有意义
SKIP_GROUPS = frozenset({"QFluentWidgets", "Window"})

def _visible_items():
    for spec in ITEMS:
        if spec.attr in SECRET_ATTRS or spec.group in SKIP_GROUPS:
            continue

        yield spec

def _describe(spec) -> dict:
    item = getattr(config, spec.attr)

    data = {
        "attr": spec.attr,
        "group": spec.group,
        "type": spec.type.value,
        "value": config.get(item),
        "default": item.defaultValue,
        "restart": bool(spec.restart),
    }

    if spec.range:
        data["range"] = list(spec.range)

    if spec.type == ValueType.ENUM and spec.options is not None:
        # 枚举下发成员的值，前端照着做下拉框
        data["options"] = [member.value for member in spec.options]

    elif isinstance(spec.options, (list, tuple)):
        data["options"] = list(spec.options)

    return data

class UpdateSettingsRequest(BaseModel):
    # {attr: value}
    values: Dict[str, Any] = Field(min_length = 1)

@router.get("/settings")
async def read_settings():
    """
    读配置

    附带每一项的类型、默认值、取值范围与可选值 —— 前端据此把设置界面画出来，
    不必自己维护一份与 schema 平行的表（那份表迟早对不上）
    """
    items = [_describe(spec) for spec in _visible_items()]

    return {"items": items, "groups": sorted({item["group"] for item in items})}

@router.post("/settings")
async def update_settings(payload: UpdateSettingsRequest):
    """
    改配置

    一次可以改多项。认不出的 attr 与敏感项**直接拒绝整个请求**，不做「部分成功」——
    改配置是用户在设置界面点保存，半对半错的结果比明确报错更难收拾
    """
    unknown = []
    forbidden = []

    allowed = {spec.attr for spec in _visible_items()}

    for attr in payload.values:
        if attr in SECRET_ATTRS:
            forbidden.append(attr)

        elif attr not in allowed:
            unknown.append(attr)

    if forbidden:
        return JSONResponse(
            {"detail": "These settings cannot be changed here", "attrs": sorted(forbidden)},
            status_code = 403)

    if unknown:
        return JSONResponse(
            {"detail": "Unknown settings", "attrs": sorted(unknown)}, status_code = 400)

    changed = []

    for attr, value in payload.values.items():
        item = getattr(config, attr)

        # 逐项 set 但先不落盘：批量改动只写一次文件，少几次「读盘 + 合并 + 替换」
        config.set(item, value, save = False)

        changed.append(attr)

    # 落盘走 config 自己的路径 —— 它会读盘再合并，保住桌面版写进去的键
    config.save()

    # 回读一遍再返回：取值校验的语义是「纠正而非拒绝」，用户传进来的值可能被
    # clamp 或回落成默认值。不回读的话前端会以为自己设成功了
    return {"changed": changed,
            "values": {attr: config.get(getattr(config, attr)) for attr in changed}}
