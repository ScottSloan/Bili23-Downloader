"""
媒体信息预览（S3-11）

给前端在下载前显示「这个视频有哪些画质 / 编码 / 音质可选」。

档位计算与桌面版同一份（`preview/quality_base.py`），URL 构造也同一份
（`preview/session.py`）—— 两端因此不会出现「桌面能选 4K 而网页里没有」这种对不上的情况。

## 候选项不是可有可无的

首选的那一集常常是充电专属或付费内容，取不到媒体信息。桌面版会自动往下换一个候选，
并在界面上标注信息来自别的视频。这里保留同样的行为：前端把整组候选传进来，
返回里带 `from_fallback` —— **前端一定要把它显示出来**，否则用户看到的清晰度
其实属于另一个视频，而他不知道。
"""

from typing import List
import asyncio
import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from util.parse.preview.session import PreviewSession
from util.thread import background

from ..schemas import PreviewResult, StreamPreviewResult

logger = logging.getLogger(__name__)

router = APIRouter(tags = ["preview"])

class PreviewRequest(BaseModel):
    # 按顺序尝试，取不到就换下一个。用户手动指定某一集时只传这一项，失败即失败
    candidates: List[dict] = Field(min_length = 1, max_length = 20)

class StreamPreviewRequest(BaseModel):
    """
    查某一集在指定档位下的流详情

    只收**一个** episode，不是候选列表：这一步是「用户已经在对话框里看着某一集、
    刚换了画质」，换成别的视频的信息毫无意义。候选回退发生在上一步的 /api/preview
    """

    episode: dict

    # 200 / 20 / 30300 分别是画质、编码、音质的「自动」，此时按用户配置的优先级挑
    video_quality_id: int = 200
    video_codec_id: int = 20
    audio_quality_id: int = 30300

@router.post("/preview", response_model = PreviewResult)
async def preview(payload: PreviewRequest):
    """取一次媒体信息，返回可选的画质 / 编码 / 音质"""
    session = PreviewSession()

    try:
        return await asyncio.wrap_future(
            background.submit(session.preview, payload.candidates))

    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code = 400)

    except Exception as e:
        logger.warning("获取媒体信息失败：%s", e)

        # 全部候选都取不到 —— 多半是没权限（充电专属、付费），原样把原因透给前端
        return JSONResponse({"detail": str(e)}, status_code = 502)

@router.post("/preview/stream", response_model = StreamPreviewResult)
async def preview_stream(payload: StreamPreviewRequest):
    """
    选定档位下这两路流有多大、什么码率

    对应桌面版下载选项对话框里「媒体信息」那张卡片的描述文字
    （`gui/dialog/download_options/card.py` 的 `update_video_quality_description`）。

    **两路流分开对待**：音频取不到是常态（无声视频，或音轨已经并在视频流里），
    那一路给 null 即可，不该让整个请求失败 —— 前端按 `media_type` 说明原因。
    """
    session = PreviewSession()

    try:
        return await asyncio.wrap_future(
            background.submit(session.preview_stream, payload.episode,
                              payload.video_quality_id, payload.video_codec_id,
                              payload.audio_quality_id))

    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code = 400)

    except Exception as e:
        logger.warning("获取流详情失败：%s", e)

        return JSONResponse({"detail": str(e)}, status_code = 502)
