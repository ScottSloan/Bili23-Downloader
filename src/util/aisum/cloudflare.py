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
from pathlib import Path

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
    _MAX_RETRIES = 3          # 最大重试次数
    _RETRY_DELAY_SEC = 2      # 初始退避延迟（秒）

    def _call_ai(self, text: str) -> str:
        """通用 AI 单次调用（含指数退避重试）"""
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": text}],
            "max_tokens": 2048,
        }
        last_error = None
        for attempt in range(self._MAX_RETRIES + 1):
            try:
                resp = httpx.post(
                    self._endpoint,
                    json=payload,
                    headers=self._headers(),
                    timeout=600,
                )
                resp.raise_for_status()
                return _extract_response(resp.json())
            except httpx.TimeoutException:
                last_error = RuntimeError("AI 请求超时，请检查网络或尝试更短的文本")
            except httpx.HTTPStatusError as e:
                # 5xx 可重试，4xx 不重试
                if 500 <= e.response.status_code < 600 and attempt < self._MAX_RETRIES:
                    logger.warning(f"AI 调用 {e.response.status_code}，{self._RETRY_DELAY_SEC * (2 ** attempt)}s 后重试({attempt + 1}/{self._MAX_RETRIES})")
                    import time
                    time.sleep(self._RETRY_DELAY_SEC * (2 ** attempt))
                    continue
                last_error = RuntimeError(f"Cloudflare Worker 返回错误: HTTP {e.response.status_code}")
                break
            except Exception as e:
                if attempt < self._MAX_RETRIES:
                    logger.warning(f"AI 调用失败，{self._RETRY_DELAY_SEC * (2 ** attempt)}s 后重试({attempt + 1}/{self._MAX_RETRIES}): {e}")
                    import time
                    time.sleep(self._RETRY_DELAY_SEC * (2 ** attempt))
                    continue
                last_error = RuntimeError(f"AI 请求失败: {e}")
                break
        raise last_error

    # ================================================================
    # Whisper 音频转录（Audio 模式三阶段流水线第一步）
    # ================================================================
    _MAX_UPLOAD_SIZE = 10 * 1024 * 1024   # 10MB，Whisper 实际受限，超过易触发 3006
    _CHUNK_DURATION_SEC = 300             # 每段 5 分钟，48kbps ≈ 1.8MB

    def transcribe_audio(self, file_path: str) -> str:
        """上传音频文件到 Worker whisper 转录，返回纯文本

        流程：ffmpeg 压缩至 48kbps mono → 检查大小
          - < 10MB：直接上传转录
          - ≥ 10MB：ffmpeg 分段 → 逐段转录 → 本地拼接
        """
        if not self._endpoint:
            self._load_from_config()
        if not self._endpoint:
            raise RuntimeError("Cloudflare API Endpoint 未配置，请在设置中填写")

        import subprocess
        import tempfile

        # Step 1: 压缩音频至 48kbps mono
        compressed = tempfile.NamedTemporaryFile(suffix=".m4a", delete=False)
        compressed.close()
        try:
            subprocess.run([
                "ffmpeg", "-y", "-i", file_path,
                "-ac", "1", "-ar", "16000", "-b:a", "48k",
                compressed.name,
            ], capture_output=True, check=True)
            upload_path = compressed.name
        except (subprocess.CalledProcessError, FileNotFoundError):
            upload_path = file_path

        try:
            # Step 2: 检查文件大小
            file_size = Path(upload_path).stat().st_size
            logger.info(f"压缩后音频: {file_size / 1024 / 1024:.1f}MB")

            if file_size < self._MAX_UPLOAD_SIZE:
                return self._transcribe_single(upload_path)
            else:
                logger.info(f"文件超过 {self._MAX_UPLOAD_SIZE / 1024 / 1024:.0f}MB，启用分段转录")
                return self._transcribe_chunked(upload_path)
        finally:
            if upload_path != file_path:
                try:
                    Path(upload_path).unlink(missing_ok=True)
                except Exception:
                    pass

    def _transcribe_single(self, file_path: str) -> str:
        """上传单个音频文件到 /transcribe 并返回文本（含重试）"""
        last_error = None
        for attempt in range(self._MAX_RETRIES + 1):
            try:
                with open(file_path, "rb") as f:
                    files = {"file": f}
                    resp = httpx.post(
                        self._endpoint + "/transcribe",
                        files=files,
                        headers=self._headers(),
                        timeout=600,
                    )
                if resp.status_code != 200:
                    # 5xx 可重试
                    if 500 <= resp.status_code < 600 and attempt < self._MAX_RETRIES:
                        logger.warning(f"转录 {resp.status_code}，{self._RETRY_DELAY_SEC * (2 ** attempt)}s 后重试({attempt + 1}/{self._MAX_RETRIES})")
                        import time
                        time.sleep(self._RETRY_DELAY_SEC * (2 ** attempt))
                        continue
                    raise RuntimeError(f"转录失败 ({resp.status_code}): {resp.text[:500]}")
                return _extract_response(resp.json())
            except RuntimeError:
                raise
            except httpx.TimeoutException:
                last_error = RuntimeError("音频上传超时，请检查网络")
            except Exception as e:
                last_error = RuntimeError(f"转录请求失败: {e}")

            if attempt < self._MAX_RETRIES:
                logger.warning(f"转录失败，{self._RETRY_DELAY_SEC * (2 ** attempt)}s 后重试({attempt + 1}/{self._MAX_RETRIES}): {last_error}")
                import time
                time.sleep(self._RETRY_DELAY_SEC * (2 ** attempt))

        raise last_error

    def _transcribe_chunked(self, file_path: str) -> str:
        """ffmpeg 精确时间分段 → 逐段 whisper 转录 → 本地拼接

        优先用 ffprobe 获取时长做精确切段；ffprobe 不可用时回退到 segment muxer。
        """
        import subprocess
        import tempfile
        import shutil

        out_dir = tempfile.mkdtemp(prefix="aisum_seg_")
        try:
            # ffprobe 获取音频总时长
            try:
                probe = subprocess.run([
                    "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", file_path,
                ], capture_output=True, text=True, check=True)
                total_sec = float(probe.stdout.strip())
            except Exception:
                total_sec = 0
                logger.warning("ffprobe 不可用，回退到 segment muxer 切段")

            if total_sec > self._CHUNK_DURATION_SEC:
                # 精确切段
                seg_count = int(total_sec // self._CHUNK_DURATION_SEC) + (1 if total_sec % self._CHUNK_DURATION_SEC > 30 else 0)
                seg_count = max(seg_count, 1)
                logger.info(f"音频 {total_sec:.0f}s，分为 {seg_count} 段（每段 {self._CHUNK_DURATION_SEC}s）")

                transcripts = []
                try:
                    for i in range(seg_count):
                        start = i * self._CHUNK_DURATION_SEC
                        seg_path = Path(out_dir) / f"seg_{i:03d}.m4a"
                        logger.info(f"  切段 {i + 1}/{seg_count}: {start}s ~ {start + self._CHUNK_DURATION_SEC}s")
                        subprocess.run([
                            "ffmpeg", "-y", "-i", file_path,
                            "-ss", str(start), "-to", str(start + self._CHUNK_DURATION_SEC),
                            "-ac", "1", "-ar", "16000", "-b:a", "48k",
                            str(seg_path),
                        ], capture_output=True, check=True)
                        text = self._transcribe_single(str(seg_path))
                        transcripts.append(text)
                finally:
                    shutil.rmtree(out_dir, ignore_errors=True)
                return "\n".join(transcripts)

            # 回退：segment muxer 切段（按 keyframe，可能有少量重叠）
            seg_pattern = Path(out_dir) / "seg_%03d.m4a"
            subprocess.run([
                "ffmpeg", "-y", "-i", file_path,
                "-f", "segment", "-segment_time", str(self._CHUNK_DURATION_SEC),
                "-c", "copy", str(seg_pattern),
            ], capture_output=True, check=True)

            seg_files = sorted(Path(out_dir).glob("seg_*.m4a"))
            if not seg_files:
                raise RuntimeError("音频分段失败：未生成任何分段文件")

            logger.info(f"segment muxer 分为 {len(seg_files)} 段，开始逐段转录")
            transcripts = []
            for i, seg_path in enumerate(seg_files):
                logger.info(f"  转录 {i + 1}/{len(seg_files)} ({seg_path.stat().st_size / 1024:.0f}KB)")
                text = self._transcribe_single(str(seg_path))
                transcripts.append(text)
            return "\n".join(transcripts)
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

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
