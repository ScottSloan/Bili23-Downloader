"""
Cloudflare Workers AI HTTP 客户端

通过 Worker 中转调用 Workers AI 模型：
  - multipart/form-data 上传文件
  - JSON 模式纯文本对话
  - 两阶段字幕总结流水线（Phase1 文案整理 + Phase2 要点总结）
  - 长文本自动分片分治（>6000 字符）
"""

import httpx
import logging

from util.common.config import config
from util.common.data.aisum_models import SummaryUploadMethod, DEFAULT_MODEL_ID

logger = logging.getLogger(__name__)

# 长文本分片触发阈值（字符数）
CHUNK_THRESHOLD = 6000
CHUNK_SIZE = 4000


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
    # 核心：两阶段字幕总结流水线
    # ================================================================
    def summarize_subtitle_pipeline(self, json_text: str, title: str = "", desc: str = "") -> dict:
        """两阶段字幕总结流水线

        Returns:
            {"phase1": "整理后文案", "phase2": "要点总结"}
        """
        if not self._endpoint:
            self._load_from_config()
        if not self._endpoint:
            raise RuntimeError("Cloudflare API Endpoint 未配置，请在设置中填写")

        # 构建上下文前缀
        ctx = _build_context(title, desc)

        # 检测是否需要分片
        if len(json_text) > CHUNK_THRESHOLD:
            organized = self._phase1_chunked(json_text, ctx)
        else:
            organized = self._phase1_organize(json_text, ctx)

        summary = self._phase2_summarize(organized, ctx)

        return {"phase1": organized, "phase2": summary}

    # ------------------------ Phase 1: 文案整理 ------------------------
    def _phase1_organize(self, json_text: str, context: str = "") -> str:
        """单段 JSON 字幕 → 流畅完整文案"""
        prompt = (
            "你是一位资深的文案编辑。请将以下 JSON 格式的字幕文本整理为流畅完整的文案。"
            "要求：\n"
            "1. 自动补全标点符号（句号、逗号、感叹号等）\n"
            "2. 根据语义划分自然段落（每段 3~5 句，不同主题之间空行分隔）\n"
            "3. 修正 AI 语音识别导致的错别字和不通顺表达\n"
            '4. 适当去掉\u201c然后\u201d\u201c就是说\u201d\u201c这个啊\u201d等口语填充词\n'
            "5. 保持语义完整，不脑补内容\n"
            "直接输出整理后的文案，不要附加说明。"
        )
        full_prompt = f"{context}{prompt}\n\n{json_text}"
        return self._call_ai(full_prompt)

    def _phase1_chunked(self, json_text: str, context: str = "") -> str:
        """长文本：分片 → 每段整理 → 合并"""
        chunks = self._split_chunks(json_text)
        if len(chunks) == 1:
            return self._phase1_organize(chunks[0], context)

        summaries = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Phase 1 分段处理 {i+1}/{len(chunks)}")
            s = self._phase1_chunk_organize(chunk, context)
            summaries.append(s)

        merge_prompt = (
            "请将以下多段文案合并为一份连贯的完整文案，"
            "消除重复内容，保持逻辑流畅，按自然段落组织。"
        )
        return self._call_ai(f"{context}{merge_prompt}\n\n" + "\n\n---\n\n".join(summaries))

    def _phase1_chunk_organize(self, chunk: str, context: str = "") -> str:
        """单段文案整理（分片模式）"""
        prompt = (
            "请将以下 JSON 格式的字幕段落整理为流畅的文案。"
            "补全标点、修正错别字、去掉口语填充词。"
            "保持语义完整，不要附加说明。"
        )
        return self._call_ai(f"{context}{prompt}\n\n{chunk}")

    # ------------------------ Phase 2: 要点总结 ------------------------
    def _phase2_summarize(self, organized_text: str, context: str = "") -> str:
        """整理后文案 → 层次化要点总结"""
        prompt = (
            "你是一位专业的内容提炼编辑。请对以下整理后的文本进行浓缩总结。要求如下：\n"
            "1. 去粗取精：删除重复论述和冗余修饰，保留核心观点与逻辑链条\n"
            "2. 语言风格：精炼、客观、专业\n"
            "3. 输出格式：使用 Markdown 标题层级（# 一级要点, ## 二级要点, - 细节）\n"
            "4. 篇幅控制：总字数控制在原文 1/3 以内\n"
            "注意：\n"
            "- 如果原文是教程/方法类内容，操作步骤不可省略\n"
            "- 直接输出，不要附加说明"
        )
        return self._call_ai(f"{context}{prompt}\n\n{organized_text}")

    # ------------------------ 长文本分片工具 ------------------------
    def _split_chunks(self, text: str) -> list:
        """按 JSON body 条目边界切分为 ~CHUNK_SIZE 字符的段"""
        import json as _json
        try:
            data = _json.loads(text)
            body = data.get("body", [])
        except Exception:
            return [text[i:i + CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]

        chunks = []
        current_lines = []
        current_len = 0

        for item in body:
            item_str = _json.dumps(item, ensure_ascii=False)
            item_len = len(item_str)
            if current_len + item_len > CHUNK_SIZE and current_lines:
                chunk_data = {"body": current_lines}
                chunks.append(_json.dumps(chunk_data, ensure_ascii=False))
                current_lines = []
                current_len = 0
            current_lines.append(item)
            current_len += item_len

        if current_lines:
            chunk_data = {"body": current_lines}
            chunks.append(_json.dumps(chunk_data, ensure_ascii=False))

        return chunks or [text]

    # ------------------------ AI 调用底层 ------------------------
    def _call_ai(self, text: str) -> str:
        """通用 AI 单次调用"""
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": text}],
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
    # 旧版兼容接口
    # ================================================================
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
        """通过 JSON 模式发送纯文本获取总结（旧版兼容）"""
        return self._call_ai(text)


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
