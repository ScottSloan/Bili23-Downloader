"""
AI 总结模块数据模型与常量
"""

from enum import Enum
from dataclasses import dataclass
import json
from pathlib import Path


class SummaryType(Enum):
    """总结类型"""
    SUBTITLE = "Subtitle"
    VIDEO = "Video"
    AUDIO = "Audio"


class SummaryUploadMethod(Enum):
    """文件上传方式"""
    FORM_DATA = "multipart/form-data"
    PRESIGNED_URL = "Presigned URL (TBD)"


class PromptSlot(Enum):
    """提示词槽位"""
    ORIGINAL = "original"
    REFINED = "refined"
    KEYPOINTS = "keypoints"


class ProviderType(Enum):
    """AI 模型提供者"""
    CLOUDFLARE = "cloudflare"
    OPENAI = "openai"
    OLLAMA = "ollama"
    CUSTOM = "custom"


# Cloudflare Workers AI whisper 转录模型（固定）
WHISPER_MODEL_ID = "@cf/openai/whisper"
WHISPER_MODEL_NAME = "Whisper (Cloudflare)"


@dataclass
class AISumModelConfig:
    """AI 模型配置"""
    id: str                # 唯一标识 (e.g. "cf_llama_3b")
    title: str             # 显示名称 (e.g. "Llama 3.2 3B")
    model_id: str          # 模型 ID (e.g. "@cf/meta/llama-3.2-3b-instruct")
    provider: ProviderType = ProviderType.CLOUDFLARE
    endpoint: str = ""     # 自定义 API endpoint (非 Cloudflare 必填)
    api_key: str = ""      # 自定义 API key (非 Cloudflare 必填)

    @property
    def is_cloudflare(self) -> bool:
        return self.provider == ProviderType.CLOUDFLARE


@dataclass
class SummaryModel:
    """AI 模型描述（旧版兼容，保留给 DEFAULT_MODELS）"""
    model_id: str
    display_name: str


@dataclass
class PromptPreset:
    """提示词预设"""
    id: str                          # 唯一标识
    title: str                       # 预设标题
    prompt: str                      # 系统提示词
    builtin: bool = False            # 是否为内置预设


# Cloudflare Workers AI 预定义模型列表（旧版兼容）
DEFAULT_MODELS = [
    SummaryModel("@cf/meta/llama-3.2-3b-instruct", "Llama 3.2 3B (Cloudflare)"),
]

DEFAULT_MODEL_ID = DEFAULT_MODELS[0].model_id

# ---- 模型配置 JSON 存储 ----
def _models_json_path() -> Path:
    """模型配置文件路径（与 config.json 同级）"""
    from util.common.config import config_path
    return config_path.parent / "aisum_models.json"


def load_aisum_models() -> list:
    """从 aisum_models.json 加载模型列表"""
    path = _models_json_path()
    if not path.exists():
        return _default_model_list()
    try:
        data = json.loads(path.read_text("utf-8"))
        models = []
        for d in data.get("models", []):
            models.append(AISumModelConfig(
                id=d["id"],
                title=d["title"],
                model_id=d["model_id"],
                provider=ProviderType(d.get("provider", "cloudflare")),
                endpoint=d.get("endpoint", ""),
                api_key=d.get("api_key", ""),
            ))
        return models if models else _default_model_list()
    except Exception:
        return _default_model_list()


def save_aisum_models(models: list):
    """保存模型列表到 aisum_models.json"""
    path = _models_json_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "models": [{
            "id": m.id,
            "title": m.title,
            "model_id": m.model_id,
            "provider": m.provider.value,
            "endpoint": m.endpoint,
            "api_key": m.api_key,
        } for m in models],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


def _default_model_list() -> list:
    return [
        AISumModelConfig(
            id="cf_llama_3b",
            title="Llama 3.2 3B (Cloudflare)",
            model_id="@cf/meta/llama-3.2-3b-instruct",
            provider=ProviderType.CLOUDFLARE,
        ),
    ]

# ================================================================
# 内置提示词预设
# ================================================================
_BUILTIN_ORIGINAL_PROMPT = (
    "你是一位资深的文案编辑。请将以下 JSON 格式的字幕文本整理为流畅完整的文案。"
    "要求：\n"
    "1. 自动补全标点符号（句号、逗号、感叹号等）\n"
    "2. 根据语义划分自然段落（每段 3~5 句，不同主题之间空行分隔）\n"
    "3. 修正 AI 语音识别导致的错别字和不通顺表达\n"
    '4. 适当去掉\u201c然后\u201d\u201c就是说\u201d\u201c这个啊\u201d等口语填充词\n'
    "5. 保持语义完整，不脑补内容\n"
    "直接输出整理后的文案，不要附加说明。"
)

_BUILTIN_REFINED_PROMPT = (
    "你是一位专业的内容提炼编辑。请对以下整理后的文本进行浓缩总结。要求如下：\n"
    "1. 去粗取精：删除重复论述和冗余修饰，保留核心观点与逻辑链条\n"
    "2. 语言风格：精炼、客观、专业\n"
    "3. 输出格式：使用 Markdown 编号列表\n"
    "4. 篇幅控制：总字数控制在原文 1/3 以内，越精炼越好，但不要少于 1/6\n"
    "注意：\n"
    "- 如果原文是教程/方法类内容，操作步骤不可省略\n"
    "- 直接输出，不要附加说明"
)

_BUILTIN_KEYPOINTS_PROMPT = (
    "你是一位内容分析师。请对以下文本进行话题要点分析。要求如下：\n"
    "1. 列出他或者他们讨论的所有话题要点\n"
    "2. 基于每个话题用 bullet points 列出要点\n"
    "3. 严格以话题为章节/段落，用 1~3 个自然段/句话总结每个话题的内容，"
    "总结每个话题时不要用 bullet points\n"
    "直接输出，不要附加说明。"
)

# 内置预设（builtin=True，不可删除/编辑标题和提示词）
DEFAULT_ORIGINAL_PRESET = PromptPreset(
    id="builtin_original",
    title="原始文案",
    prompt=_BUILTIN_ORIGINAL_PROMPT,
    builtin=True,
)
DEFAULT_REFINED_PRESET = PromptPreset(
    id="builtin_refined",
    title="精炼文案",
    prompt=_BUILTIN_REFINED_PROMPT,
    builtin=True,
)
DEFAULT_KEYPOINTS_PRESET = PromptPreset(
    id="builtin_keypoints",
    title="要点文案",
    prompt=_BUILTIN_KEYPOINTS_PROMPT,
    builtin=True,
)

BUILTIN_PRESETS = [
    DEFAULT_ORIGINAL_PRESET,
    DEFAULT_REFINED_PRESET,
    DEFAULT_KEYPOINTS_PRESET,
]

# 默认 slot → 预设 ID 映射
DEFAULT_SLOT_MAPPING = {
    PromptSlot.ORIGINAL.value: DEFAULT_ORIGINAL_PRESET.id,
    PromptSlot.REFINED.value: DEFAULT_REFINED_PRESET.id,
    PromptSlot.KEYPOINTS.value: DEFAULT_KEYPOINTS_PRESET.id,
}


def serialize_presets(presets: list) -> str:
    """序列化预设列表为 JSON 字符串"""
    return json.dumps([{
        "id": p.id,
        "title": p.title,
        "prompt": p.prompt,
        "builtin": p.builtin,
    } for p in presets], ensure_ascii=False)


def deserialize_presets(json_str: str) -> list:
    """从 JSON 字符串反序列化预设列表"""
    try:
        data = json.loads(json_str)
        return [PromptPreset(
            id=d["id"], title=d["title"], prompt=d["prompt"], builtin=d.get("builtin", False)
        ) for d in data]
    except Exception:
        return list(BUILTIN_PRESETS)


def serialize_slot_mapping(mapping: dict) -> str:
    """序列化 slot 映射为 JSON"""
    return json.dumps(mapping, ensure_ascii=False)


def deserialize_slot_mapping(json_str: str) -> dict:
    """反序列化 slot 映射"""
    try:
        return json.loads(json_str)
    except Exception:
        return dict(DEFAULT_SLOT_MAPPING)
