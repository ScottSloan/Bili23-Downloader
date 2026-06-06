"""
AI 总结模块数据模型与常量
"""

from enum import Enum
from dataclasses import dataclass


class SummaryType(Enum):
    """总结类型"""
    SUBTITLE = "Subtitle"
    VIDEO = "Video"
    AUDIO = "Audio"


class SummaryUploadMethod(Enum):
    """文件上传方式"""
    FORM_DATA = "multipart/form-data"
    PRESIGNED_URL = "Presigned URL (TBD)"


@dataclass
class SummaryModel:
    """AI 模型描述"""
    model_id: str
    display_name: str


# Cloudflare Workers AI 预定义模型列表（可扩展）
DEFAULT_MODELS = [
    SummaryModel("@cf/meta/llama-3.2-3b-instruct", "Llama 3.2 3B (Cloudflare)"),
]

DEFAULT_MODEL_ID = DEFAULT_MODELS[0].model_id
