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

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from util.common._config.schema import ITEMS, ValueType
from util.common.config import config

from ..schemas import (
    FontFamilies, NamingRulePreview, NamingRuleTypes, NamingRuleVariables, SettingChoices,
    SettingsPayload, SettingsUpdateResult,
)

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

@router.get("/settings", response_model = SettingsPayload)
async def read_settings():
    """
    读配置

    附带每一项的类型、默认值、取值范围与可选值 —— 前端据此把设置界面画出来，
    不必自己维护一份与 schema 平行的表（那份表迟早对不上）
    """
    items = [_describe(spec) for spec in _visible_items()]

    return {"items": items, "groups": sorted({item["group"] for item in items})}

@router.get("/settings/choices", response_model = SettingChoices)
async def read_choices():
    """
    结构化配置项的候选值：画质 / 音质 / 编码 / 字幕语言

    **这些表只有 core 里那一份。** 前端再抄一遍的话，B 站加一档新画质时桌面版认得、
    WebUI 不认得，而且没有任何报错 —— 只是那一档在优先级列表里凭空消失。

    画质与音质里的 `auto` 不下发：优先级列表本身回答的就是「auto 时按什么顺序挑」，
    把 auto 放进这个顺序里没有意义（配置的默认值里也没有它）
    """
    from util.common.data import (
        audio_quality_map, subtitles_alignment_map, subtitles_language_list, video_codec_map,
        video_quality_map,
    )
    from util.common.translator import Translator

    def media_choices(source: dict, translate) -> list:
        return [
            {"value": value, "label": translate(name)}
            for name, value in source.items()
            if name != "auto"
        ]

    return {
        "video_quality": media_choices(video_quality_map, Translator.VIDEO_QUALITY),
        "audio_quality": media_choices(audio_quality_map, Translator.AUDIO_QUALITY),
        # 编码名本身就是 AVC/H.264 这种写法，没有可翻译的部分
        "video_codec": media_choices(video_codec_map, lambda name: name),
        "subtitle_language": [
            {"value": entry["lan"], "label": entry["doc_zh"]}
            for entry in subtitles_language_list
        ],
        # 只给纯标签。**编号由前端拼**（ASS 的 1–9 是小键盘方位，光看数字认不出
        # 是哪个角，所以界面上显示成「说明（编号）」）—— 后端也拼一遍的话，
        # 前端用自己的译文时会变成「底部居中 (2) (2)」
        "subtitle_alignment": [
            {"value": value, "label": Translator.SUBTITLES_ALIGNMENT(name)}
            for name, value in subtitles_alignment_map.items()
        ],
    }

@router.get("/settings/fonts", response_model = FontFamilies)
async def read_fonts():
    """
    服务端装了哪些字体

    **这里会惰性拉起 offscreen 的 QGuiApplication**（`web/qt_runtime.py`），
    与生成 ASS 弹幕走的是同一条路 —— 也正因如此，列出来的就是那时真正能用的字体。

    必须在事件循环线程（= 主线程）上调用：QGuiApplication 只能在主线程构造。
    所以这个函数是 async 且**不能**丢给 `run_in_executor`。

    ## 空列表是常态，不是错误

    实测：**Windows 上 `QT_QPA_PLATFORM=offscreen` 一款字体都枚举不到**
    （`QFontDatabase.families()` 返回空，systemFont 是 "Sans Serif"）。
    Linux 容器里走 fontconfig 通常能列出来，但也取决于镜像里装没装字体。

    所以 `available` 的含义是「**这份列表能用吗**」，不是「Qt 在不在」——
    列表为空时前端会退回自由输入框，让用户自己填字体名。
    报 available 却给一个空列表，比直接说不可用更糟：前端会画出一个点不开的空下拉框。

    顺带一提：枚举不到字体也就意味着 ASS 弹幕的轨道排布是按 fallback 字体量的，
    宽度会有偏差。那属于 D16 已经接受的近似（见 PROGRESS 的待解决第 4 条）
    """
    from ..qt_runtime import ensure_gui_application

    if not ensure_gui_application():
        # 镜像里没装 PySide6 时就是这条路
        return {"available": False, "families": []}

    try:
        from PySide6.QtGui import QFontDatabase

        families = list(QFontDatabase.families())

    except Exception:
        logger.exception("枚举字体失败")

        return {"available": False, "families": []}

    if not families:
        logger.info("当前平台在 offscreen 下枚举不到字体，字体名改由用户自行填写")

    return {"available": bool(families), "families": families}

class NamingRulePreviewRequest(BaseModel):
    type: int
    rule: str = Field(max_length = 1000)

@router.get("/settings/naming-rule/types", response_model = NamingRuleTypes)
async def read_naming_rule_types():
    """规则类型。名字与编号都由 core 给，前端不自己维护一份对照表"""
    from util.common.data import convention_type_map
    from util.common.translator import Translator

    return {
        "types": [
            {"value": int(value), "label": Translator.CONVENTION_TYPE(name)}
            for name, value in convention_type_map.items()
        ]
    }

@router.get("/settings/naming-rule/variables", response_model = NamingRuleVariables)
async def read_naming_rule_variables(type: int = Query(...)):
    """某个规则类型能用哪些变量。认不出的类型返回空表而不是报错"""
    from util.format.naming_rule import variables_for

    return {"variables": variables_for(type)}

@router.post("/settings/naming-rule/preview", response_model = NamingRulePreview)
async def preview_naming_rule(payload: NamingRulePreviewRequest):
    """
    校验一条规则并套上示例数据

    **非法的规则也返回 200**：这里回答的是「这条规则行不行」，
    不合法是一个正常的答案，不是请求出错。用 4xx 的话前端得把「校验没通过」
    和「请求本身失败」分开处理，而它们在界面上是两回事
    """
    from util.format.naming_rule import preview_rule

    ok, message, result = preview_rule(payload.type, payload.rule)

    if not ok:
        return {"valid": False, "message": message}

    return {
        "valid": True,
        "folder": str(result.parent) if str(result.parent) != "." else "",
        "filename": result.stem,
    }

@router.post("/settings", response_model = SettingsUpdateResult)
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
            {"detail": "These settings cannot be changed here",
             "code": "SETTINGS_FORBIDDEN", "attrs": sorted(forbidden)},
            status_code = 403)

    if unknown:
        return JSONResponse(
            {"detail": "Unknown settings", "code": "SETTINGS_UNKNOWN",
             "attrs": sorted(unknown)}, status_code = 400)

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
