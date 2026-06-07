"""
Cloudflare Workers AI HTTP 客户端

通过 Worker 中转调用 Workers AI 模型：
  - multipart/form-data 上传文件
  - JSON 模式纯文本对话
  - 三阶段字幕总结流水线（原始文案 → 精炼文案 + 要点文案）
  - 长文本自动分片分治（>6000 字符）
"""

import httpx
import logging

from util.common.config import config
from util.common.data.aisum_models import DEFAULT_MODEL_ID

logger = logging.getLogger(__name__)

# 长文本分片阈值（字符数，按纯文本计算）
# Llama 3.2 3B 输出上限约 1000-2000 字符，输入 ≈ 输出 时每段 ~1000 字符最佳
CHUNK_THRESHOLD = 1500
CHUNK_SIZE = 1000


class CloudflareClient:
    """Cloudflare Workers AI 客户端（单例）"""

    def __init__(self):
        self._endpoint = ""
        self._token = ""
        self._model = DEFAULT_MODEL_ID

    def configure(self, endpoint: str, token: str, model: str = ""):
        ep = endpoint.strip() if endpoint else ""
        if ep and not ep.startswith(("http://", "https://")):
            ep = "https://" + ep
        self._endpoint = ep.rstrip("/") if ep else ""
        self._token = token
        if model:
            self._model = model
        elif not self._model:
            self._model = DEFAULT_MODEL_ID

    def _load_from_config(self):
        ep = config.get(config.cloudflare_endpoint) or ""
        if ep and not ep.startswith(("http://", "https://")):
            ep = "https://" + ep
        self._endpoint = ep.rstrip("/") if ep else ""
        self._token = config.get(config.cloudflare_token) or ""
        self._model = config.get(config.cloudflare_model) or DEFAULT_MODEL_ID

    def _headers(self) -> dict:
        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    # ================================================================
    # 核心：三阶段字幕总结流水线
    # ================================================================
    def summarize_three_phase(
        self,
        json_text: str,
        title: str = "",
        desc: str = "",
        prompt_original: str = "",
        prompt_refined: str = "",
        prompt_keypoints: str = "",
    ) -> dict:
        """三阶段字幕总结流水线

        Phase 1: JSON 字幕 → 原始文案
        Phase 2: 原始文案 → 精炼文案
        Phase 3: 原始文案 → 要点文案

        Returns:
            {"original": "...", "refined": "...", "keypoints": "..."}
        """
        if not self._endpoint:
            self._load_from_config()
        if not self._endpoint:
            raise RuntimeError("Cloudflare API Endpoint 未配置，请在设置中填写")

        ctx = _build_context(title, desc)

        # Phase 1: JSON 字幕 → 原始文案
        # 先 Python 提取纯文本（去 JSON 开销），再决定是否需要分片
        plain_text = _json_to_text(json_text)
        if len(plain_text) > CHUNK_THRESHOLD:
            original = self._chunked_organize(plain_text, ctx, prompt_original)
        else:
            original = self._call_ai(f"{ctx}{prompt_original}\n\n{plain_text}")

        # Phase 2: 原始文案 → 精炼文案 (共用 Phase 1 输出)
        refined = self._call_ai(f"{ctx}{prompt_refined}\n\n{original}")

        # Phase 3: 原始文案 → 要点文案 (共用 Phase 1 输出)
        keypoints = self._call_ai(f"{ctx}{prompt_keypoints}\n\n{original}")

        return {
            "original": original,
            "refined": refined,
            "keypoints": keypoints,
        }

    # ------------------------ 长文本分片组织（Phase 1） ------------------------
    def _chunked_organize(self, text: str, context: str, prompt: str) -> str:
        """长文本：Python 预切分 → AI 逐段整理 → Python 拼接（无 AI merge）

        AI merge 是数据丢失的根源：合并后的输入过长，小模型输出截断。
        改为 Python 直接拼接，彻底消除瓶颈。"""
        chunks = _split_text(text, CHUNK_SIZE)
        logger.info(f"Phase 1 分片: {len(chunks)} 段 ({len(text)} 字符)")

        results = []
        for i, chunk in enumerate(chunks):
            logger.info(f"  整理 {i+1}/{len(chunks)} ({len(chunk)} 字符)")
            # 每段指令：禁止独立开头/结尾，要求等量输出
            extra = (
                f"\n\n"
                f"【重要】这是长文本被切分后的第 {i+1}/{len(chunks)} 段。\n"
                f"- 不要写开场白或收尾句，直接从内容开始整理\n"
                f"- 输出长度不得明显短于输入（输入约{len(chunk)}字）\n"
                f"- 每个句子的内容都不准遗漏"
            )
            r = self._call_ai(f"{context}{prompt}\n\n{chunk}{extra}")
            results.append(r)

        # 程序拼接：AI 不再参与合并
        joined = "\n\n".join(results)
        return joined

    # ------------------------ AI 调用底层 ------------------------
    def _call_ai(self, text: str) -> str:
        """通用 AI 单次调用"""
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": text}],
            "max_tokens": 2048,
        }
        try:
            resp = httpx.post(
                self._endpoint,
                json=payload,
                headers=self._headers(),
                timeout=600,
            )
            resp.raise_for_status()
            result = resp.json()
        except httpx.TimeoutException:
            raise RuntimeError("AI 请求超时，请检查网络或尝试更短的文本")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Cloudflare Worker 返回错误: HTTP {e.response.status_code}")
        except Exception as e:
            raise RuntimeError(f"AI 请求失败: {e}")

        return _extract_response(result)

    # ================================================================
    # Whisper 音频转录（Audio 模式三阶段流水线第一步）
    # ================================================================
    def transcribe_audio(self, file_path: str) -> str:
        """上传音频文件到 Worker whisper 转录，返回纯文本"""
        if not self._endpoint:
            self._load_from_config()
        if not self._endpoint:
            raise RuntimeError("Cloudflare API Endpoint 未配置，请在设置中填写")

        with open(file_path, "rb") as f:
            files = {"file": f}
            # whisper 不接受 prompt，但 Worker /transcribe 端点只需 file
            try:
                resp = httpx.post(
                    self._endpoint + "/transcribe",
                    files=files,
                    headers=self._headers(),
                    timeout=600,
                )
                resp.raise_for_status()
                result = resp.json()
            except httpx.TimeoutException:
                raise RuntimeError("音频上传超时，请检查网络")
            except httpx.HTTPStatusError as e:
                raise RuntimeError(f"转录请求失败: HTTP {e.response.status_code}")
            except Exception as e:
                raise RuntimeError(f"转录请求失败: {e}")

        return _extract_response(result)

    def summarize_text_three_phase(
        self,
        text: str,
        title: str = "",
        desc: str = "",
        prompt_original: str = "",
        prompt_refined: str = "",
        prompt_keypoints: str = "",
    ) -> dict:
        """对纯文本执行三阶段总结（Audio 模式用，无需 JSON 预处理）

        与 summarize_three_phase 区别：输入已是纯文本，跳过 _json_to_text
        """
        if not self._endpoint:
            self._load_from_config()
        if not self._endpoint:
            raise RuntimeError("Cloudflare API Endpoint 未配置，请在设置中填写")

        ctx = _build_context(title, desc)

        if len(text) > CHUNK_THRESHOLD:
            original = self._chunked_organize(text, ctx, prompt_original)
        else:
            original = self._call_ai(f"{ctx}{prompt_original}\n\n{text}")

        refined = self._call_ai(f"{ctx}{prompt_refined}\n\n{original}")
        keypoints = self._call_ai(f"{ctx}{prompt_keypoints}\n\n{original}")

        return {
            "original": original,
            "refined": refined,
            "keypoints": keypoints,
        }

    # ================================================================
    # 音频/视频总结接口（旧版兼容）
    def summarize_multipart(self, file_path: str, prompt: str) -> str:
        """通过 multipart/form-data 上传文件并获取总结"""
        if not self._endpoint:
            self._load_from_config()
        if not self._endpoint:
            raise RuntimeError("Cloudflare API Endpoint 未配置，请在设置中填写")

        with open(file_path, "rb") as f:
            files = {"file": f}
            data = {"model": self._model, "prompt": prompt}
            try:
                resp = httpx.post(
                    self._endpoint,
                    files=files,
                    data=data,
                    headers=self._headers(),
                    timeout=600,
                )
                resp.raise_for_status()
                result = resp.json()
            except httpx.TimeoutException:
                raise RuntimeError("上传超时，请检查网络或文件大小")
            except httpx.HTTPStatusError as e:
                raise RuntimeError(f"Cloudflare Worker 返回错误: HTTP {e.response.status_code}")
            except Exception as e:
                raise RuntimeError(f"请求失败: {e}")

        return _extract_response(result)

    def summarize_text(self, text: str) -> str:
        """通过 JSON 模式发送纯文本获取总结"""
        return self._call_ai(text)


def _json_to_text(json_text: str) -> str:
    """将 JSON 字幕提取为纯文本（去 JSON 开销，节约 30-50% 字符）"""
    import json as _json
    try:
        data = _json.loads(json_text)
        body = data.get("body", [])
    except Exception:
        return json_text

    lines = []
    for item in body:
        content = item.get("content", "").strip()
        if content:
            lines.append(content)
    return "\n".join(lines)


def _split_text(text: str, chunk_size: int) -> list:
    """将纯文本按字符数切分，尽量在句末/段末断开"""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            # 回退到最近的句号/换行处
            for sep in ("\n\n", "\n", "。", "）", "！", "？", "；", ".", "!", "?", ";"):
                pos = text.rfind(sep, start + chunk_size // 2, end)
                if pos > start:
                    end = pos + len(sep)
                    break
        chunks.append(text[start:end])
        start = end
    return chunks


def _extract_response(result: dict) -> str:
    """从 Cloudflare Workers AI 响应中提取文本"""
    if "result" in result:
        ai_result = result["result"]
        if isinstance(ai_result, dict) and "response" in ai_result:
            return ai_result["response"]
        return str(ai_result)
    if "error" in result:
        raise RuntimeError(f"Cloudflare 错误: {result['error']}")
    return str(result)


def _build_context(title: str, desc: str) -> str:
    """构建视频元数据上下文前缀"""
    parts = []
    if title:
        parts.append(f"【视频标题】{title}")
    if desc:
        parts.append(f"【视频简介】{desc}")
    if parts:
        return "\n".join(parts) + "\n\n"
    return ""


cloudflare_client = CloudflareClient()
