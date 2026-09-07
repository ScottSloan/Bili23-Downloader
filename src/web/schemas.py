"""
响应模型（S3-12 的补课）

FastAPI 只有在路由声明了 `response_model` 时才会把响应结构写进 OpenAPI。不声明的话
规格里那一段是空的，`openapi-typescript` 生成出来是 `unknown` —— **脚本照常跑、
`--check` 照常通过，但契约里什么都没有**。D3 说「经 OpenAPI 用 openapi-typescript
自动生成前端类型」，少了这一步等于没做。

## 不是每个接口都值得建模

有几处的返回天生是动态的，硬套模型只会得到一堆 `Any`，不如老实留空并写清原因：

- **解析树**是递归结构，且节点上的 `episode` 就是 `TaskInfo` 那套自由字典 ——
  前端按 `parse/session.py` 的 `serialize_node()` 自己写一份节点类型即可
- **配置项的 `value`** 横跨 bool / int / str / list / dict 五种，只能是 `Any`；
  但它外面那层（attr / group / type / range / options）是稳定的，值得建模

## 字段名跟着后端走

模型里的字段名与实际返回一字不差，不做驼峰转换。前端拿到什么就是什么，
少一层「这里为什么叫这个名字」的疑问。
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# ---------------- WebUI 自身的会话 ----------------

class SessionInfo(BaseModel):
    authenticated: bool
    username: str = ""

class LogoutResult(BaseModel):
    authenticated: bool = False

# ---------------- B 站账号 ----------------

class BilibiliStatus(BaseModel):
    logged_in: bool
    uname: str = ""
    uid: int | str = 0
    face: str = ""
    # 只有 refresh = true 那条路径会带上
    expired: bool = False
    vip_status: int = 0
    level: int = 0

class QRCodeInfo(BaseModel):
    """`url` 交给前端渲染成二维码，服务端不出图"""

    url: str
    key: str

class QRCodeStatus(BaseModel):
    code: int
    # 状态名而不是裸数字：改枚举值时不牵连前端
    status: str
    message: str = ""

class CaptchaInfo(BaseModel):
    """极验参数。前端拿 gt / challenge 调 initGeetest，token 发短信时带回来"""

    token: str
    gt: str
    challenge: str

class SMSSendResult(BaseModel):
    """captcha_key 是**发短信的返回值**，登录时才用，别与极验的三件套搞混"""

    captcha_key: str

class Region(BaseModel):
    code: str | int
    # 区号表里除 code 外还有别的字段，原样透传
    model_config = {"extra": "allow"}

class RegionList(BaseModel):
    regions: List[Region]

# ---------------- 任务 ----------------

class TaskView(BaseModel):
    """
    与 `web/download/view.py` 的 `task_view()` 一一对应

    **两边字段必须同步**：那边加了字段这里不加，前端就看不见；
    这里多写一个那边没有的，前端会拿到 undefined
    """

    task_id: str
    title: str
    cover_id: str = ""
    created_time: int = 0
    completed_time: int = 0

    # 状态名，取值见 DownloadStatus 的成员名小写
    status: str
    status_label: str = ""
    info_label: str = ""

    progress: int = 0
    speed: int = 0
    total_size: int = 0
    downloaded_size: int = 0

    # DownloadType 位掩码摊平后的名字
    type: List[str] = Field(default_factory = list)

    file_name: str = ""
    download_path: str = ""
    folder: str = ""

    video_quality: str = ""
    audio_quality: str = ""
    video_codec: str = ""
    duration: int = 0
    url: str = ""

class TaskSnapshot(BaseModel):
    """
    全量快照

    `cursor` 是发快照那一刻的事件编号，前端带着它连 WebSocket（`?since=cursor`），
    否则快照与增量之间会漏掉一段
    """

    cursor: int
    downloading: List[TaskView]
    completed: List[TaskView]

class TaskList(BaseModel):
    tasks: List[TaskView]
    sort_by: str
    ascending: bool

class TaskCount(BaseModel):
    downloading: int
    completed: int

class CreateResult(BaseModel):
    """实际建出来的可能比请求的少：重复下载与需要二次解析的会被拦掉"""

    requested: int
    created: int
    tasks: List[TaskView]

class DuplicateCheck(BaseModel):
    """
    每一条是否已经下载过，**与请求里的 episodes 一一对应、顺序一致**

    不用「已重复的下标列表」是因为那要求两边对「下标从哪算」有一致理解，
    而等长的布尔列表没有这个歧义
    """

    duplicates: List[bool]

class DeleteResult(BaseModel):
    deleted: int

class RetryResult(BaseModel):
    retried: int

class PauseResult(BaseModel):
    updated: int
    # 实际在 aria2 那边停掉/恢复的流数。aria2 没连上时为 0
    streams_affected: int
    status: str

# ---------------- 配置 ----------------

class SettingItem(BaseModel):
    attr: str
    group: str
    type: str
    # 横跨 bool / int / str / list / dict，只能是 Any
    value: Any = None
    default: Any = None
    restart: bool = False
    range: Optional[List[Any]] = None
    options: Optional[List[Any]] = None

class SettingsPayload(BaseModel):
    items: List[SettingItem]
    groups: List[str]

class SettingsUpdateResult(BaseModel):
    changed: List[str]
    # 回读纠正后的值：取值校验是「纠正而非拒绝」，用户传的可能被 clamp
    values: Dict[str, Any]

# ---------------- 系统 ----------------

class HealthInfo(BaseModel):
    status: str

class SystemStatus(BaseModel):
    version: str
    logged_in_bilibili: bool
    uname: str = ""
    uid: int | str = ""

class Aria2Status(BaseModel):
    """aria2 不可用不算错误，如实报告即可"""

    connected: bool
    error: Optional[str] = None
    version: Optional[str] = None
    active: int = 0
    waiting: int = 0
    stopped: int = 0
    download_speed: int = 0

# ---------------- 文件浏览 ----------------

class FileRoot(BaseModel):
    path: str
    name: str
    exists: bool

class FileRoots(BaseModel):
    roots: List[FileRoot]

class FileEntry(BaseModel):
    name: str
    is_dir: bool
    size: int
    modified: int
    # 链接可能指向根目录之外，点进去会被拒 —— 前端提前标出来
    is_link: bool

class DirectoryListing(BaseModel):
    path: str
    relative: Optional[str] = None
    # 已经在根上时为 None，前端据此禁用「上一级」
    parent: Optional[str] = None
    entries: List[FileEntry]
    truncated: bool

class MakeDirResult(BaseModel):
    path: str
    relative: Optional[str] = None

# ---------------- 预览 ----------------

class PreviewResult(BaseModel):
    episode_title: str = ""
    episode_number: str | int = ""
    # 首选取不到时自动换了下一个候选 —— **前端必须显示这一点**，
    # 否则用户看到的清晰度其实属于另一个视频
    from_fallback: bool = False
    media_type: str = "unknown"
    need_parse: bool = True
    # 显示名 → 档位 id
    video_quality: Dict[str, int] = Field(default_factory = dict)
    video_codec: Dict[str, int] = Field(default_factory = dict)
    audio_quality: Dict[str, int] = Field(default_factory = dict)
    bvid: str = ""
    cid: int = 0

# ---------------- 解析 ----------------

class EpisodeList(BaseModel):
    """`episode` 是 TaskInfo 那套自由字典，原样回传给创建任务的接口即可"""

    episodes: List[Dict[str, Any]]
