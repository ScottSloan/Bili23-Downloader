"""
AI 总结异步工作线程

负责在后台线程中执行：
  - B站内容下载 → 上传至 Cloudflare Worker → 调用 AI 模型总结
  - 本地文件上传 → 调用 AI 模型总结

字幕总结采用三阶段流水线：
  Phase 1（原始文案）: JSON 字幕 → 补标点 + 分段落 + 去口癖
  Phase 2（精炼文案）: 原始文案 → 压缩 1/3~1/6 + Markdown 编号
  Phase 3（要点文案）: 原始文案 → 分话题 + bullet + 每话题 1~3 句总结

输出三个文件：
  - {bvid}_subtitle.json        — 字幕 JSON 原文（由前端传入）
  - {ts}_original.txt            — 原始文案
  - {ts}_refined.md              — 精炼文案
  - {ts}_keypoints.md            — 要点文案
"""

from PySide6.QtCore import QObject, Signal
from pathlib import Path

from util.common.data.aisum_models import (
    SummaryType, SummaryUploadMethod, BUILTIN_PRESETS,
    deserialize_presets, DEFAULT_SLOT_MAPPING,
)
from util.common.config import config
from util.aisum.cloudflare import cloudflare_client
from util.aisum.bilibili import download_subtitle, download_audio, download_video

import logging
import re

logger = logging.getLogger(__name__)


def _sanitize_filename(name: str, max_len: int = 80) -> str:
    """清理文件名中的非法字符"""
    name = re.sub(r'[\\/:*?"<>|\n\r\t]', '', name)
    name = name.strip().rstrip('.')
    if len(name) > max_len:
        name = name[:max_len].rstrip()
    return name or "summary"


class SummaryWorker(QObject):
    """B 站总结工作线程"""

    finished = Signal()
    success = Signal(str, str, str, str)  # json_path, original_path, refined_path, keypoints_path
    error = Signal(str)

    def __init__(self, url: str, summary_type: SummaryType, parent=None):
        super().__init__(parent)
        self.url = url
        self.summary_type = summary_type

    @property
    def aisum_dir(self) -> Path:
        download_path = config.get(config.download_path)
        return Path(download_path) / "AISum"

    def run(self):
        try:
            # 1. 配置 Cloudflare 客户端
            endpoint = config.get(config.cloudflare_endpoint)
            token = config.get(config.cloudflare_token)
            model = config.get(config.cloudflare_model)
            cloudflare_client.configure(endpoint, token or "", model)

            if not config.get(config.cloudflare_endpoint):
                raise RuntimeError("请先在设置中配置 Cloudflare API Endpoint")

            upload_method = config.get(config.cloudflare_upload_method)
            title = ""

            # 2. 下载内容
            if self.summary_type == SummaryType.SUBTITLE:
                json_path, meta_path = download_subtitle(self.url)

                with open(json_path, "r", encoding="utf-8") as f:
                    json_text = f.read()

                title, desc = self._parse_meta(meta_path)

                # 3. 获取当前 slot 对应的提示词
                prompts = self._get_active_prompts()

                # 4. 三阶段流水线
                result = cloudflare_client.summarize_three_phase(
                    json_text,
                    title=title,
                    desc=desc,
                    prompt_original=prompts["original"],
                    prompt_refined=prompts["refined"],
                    prompt_keypoints=prompts["keypoints"],
                )

                # 5. 保存输出文件（文件名 = 标题 + _original/_refined/_keypoints）
                base = _sanitize_filename(title)
                original_path = self._save_file(result["original"], base, "_original", ext=".txt")
                refined_path = self._save_file(result["refined"], base, "_refined", ext=".md")
                keypoints_path = self._save_file(result["keypoints"], base, "_keypoints", ext=".md")

                self.success.emit(json_path, original_path, refined_path, keypoints_path)

            elif self.summary_type == SummaryType.AUDIO:
                # ====== Audio 模式：whisper 转录 → 三阶段总结 ======
                file_path = download_audio(self.url)

                # 获取视频元数据
                try:
                    from util.aisum.bilibili import _extract_bvid, _get_video_info
                    bvid = _extract_bvid(self.url)
                    info = _get_video_info(bvid)
                    title = info.get("title", "")
                    desc = info.get("desc", "") or info.get("description", "")
                except Exception:
                    title = ""
                    desc = ""

                # Step 1: whisper 转录
                transcript = cloudflare_client.transcribe_audio(file_path)

                # Step 2: 获取提示词
                prompts = self._get_active_prompts()

                # Step 3: 三阶段流水线
                result = cloudflare_client.summarize_text_three_phase(
                    transcript,
                    title=title,
                    desc=desc,
                    prompt_original=prompts["original"],
                    prompt_refined=prompts["refined"],
                    prompt_keypoints=prompts["keypoints"],
                )

                base = "audio_" + _sanitize_filename(title)
                original_path = self._save_file(result["original"], base, "_original", ext=".txt")
                refined_path = self._save_file(result["refined"], base, "_refined", ext=".md")
                keypoints_path = self._save_file(result["keypoints"], base, "_keypoints", ext=".md")

                self.success.emit("", original_path, refined_path, keypoints_path)

            elif self.summary_type == SummaryType.VIDEO:
                # ====== Video 模式：直接上传总结（单阶段） ======
                file_path = download_video(self.url)
                prompt = "请对以下视频内容进行总结"

                try:
                    from util.aisum.bilibili import _extract_bvid, _get_video_info
                    bvid = _extract_bvid(self.url)
                    info = _get_video_info(bvid)
                    title = info.get("title", "")
                except Exception:
                    title = ""

                if upload_method == SummaryUploadMethod.PRESIGNED_URL:
                    raise NotImplementedError("预签名 URL 上传方式暂未实现")

                result = cloudflare_client.summarize_multipart(file_path, prompt)
                summary_path = self._save_file(result, _sanitize_filename(title), "_summary", ext=".md")
                self.success.emit("", "", "", summary_path)
            else:
                raise RuntimeError(f"不支持的总结类型: {self.summary_type}")

        except Exception as e:
            logger.exception("总结失败")
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    def _get_active_prompts(self) -> dict:
        """从配置中读取当前 slot 对应的提示词"""
        presets_json = config.get(config.cloudflare_presets)
        presets = deserialize_presets(presets_json)
        preset_map = {p.id: p for p in presets}

        slot_original_id = config.get(config.cloudflare_slot_original) or DEFAULT_SLOT_MAPPING["original"]
        slot_refined_id = config.get(config.cloudflare_slot_refined) or DEFAULT_SLOT_MAPPING["refined"]
        slot_keypoints_id = config.get(config.cloudflare_slot_keypoints) or DEFAULT_SLOT_MAPPING["keypoints"]

        return {
            "original": preset_map.get(slot_original_id, BUILTIN_PRESETS[0]).prompt,
            "refined": preset_map.get(slot_refined_id, BUILTIN_PRESETS[1]).prompt,
            "keypoints": preset_map.get(slot_keypoints_id, BUILTIN_PRESETS[2]).prompt,
        }

    def _parse_meta(self, meta_path: str) -> tuple:
        """解析 _meta.txt，返回 (title, desc)"""
        title = ""
        desc = ""
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("title="):
                        title = line[6:]
                    elif line.startswith("desc="):
                        desc = line[5:]
        except Exception:
            pass
        return title, desc

    def _save_file(self, content: str, base_name: str, tag: str, ext: str = ".txt") -> str:
        """保存内容到 AISum 目录，文件名 = {base_name}{tag}{ext}"""
        self.aisum_dir.mkdir(parents=True, exist_ok=True)
        file_path = self.aisum_dir / f"{base_name}{tag}{ext}"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return str(file_path)


class LocalFileSummaryWorker(QObject):
    """本地文件总结工作线程（子页面 2：其他总结页）"""

    finished = Signal()
    success = Signal(str, str, str, str)  # original, refined, keypoints, combined
    error = Signal(str)

    def __init__(self, file_path: str, summary_type: SummaryType, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.summary_type = summary_type

    def run(self):
        try:
            endpoint = config.get(config.cloudflare_endpoint)
            if not endpoint:
                raise RuntimeError("请先在设置中配置 Cloudflare API Endpoint")

            token = config.get(config.cloudflare_token)
            model = config.get(config.cloudflare_model)
            cloudflare_client.configure(endpoint, token or "", model)

            upload_method = config.get(config.cloudflare_upload_method)

            if upload_method == SummaryUploadMethod.PRESIGNED_URL:
                raise NotImplementedError("预签名 URL 上传方式暂未实现")

            ext = Path(self.file_path).suffix.lower()

            if ext in (".txt", ".json", ".srt", ".ass", ".vtt", ".xml"):
                with open(self.file_path, "r", encoding="utf-8") as f:
                    text = f.read()

                if ext == ".json":
                    # JSON 字幕：三阶段流水线
                    presets_json = config.get(config.cloudflare_presets)
                    presets = deserialize_presets(presets_json)
                    preset_map = {p.id: p for p in presets}
                    prompts = {
                        "original": preset_map.get(
                            config.get(config.cloudflare_slot_original) or DEFAULT_SLOT_MAPPING["original"],
                            BUILTIN_PRESETS[0]
                        ).prompt,
                        "refined": preset_map.get(
                            config.get(config.cloudflare_slot_refined) or DEFAULT_SLOT_MAPPING["refined"],
                            BUILTIN_PRESETS[1]
                        ).prompt,
                        "keypoints": preset_map.get(
                            config.get(config.cloudflare_slot_keypoints) or DEFAULT_SLOT_MAPPING["keypoints"],
                            BUILTIN_PRESETS[2]
                        ).prompt,
                    }
                    result = cloudflare_client.summarize_three_phase(
                        text,
                        prompt_original=prompts["original"],
                        prompt_refined=prompts["refined"],
                        prompt_keypoints=prompts["keypoints"],
                    )
                    combined = (
                        "—— 原始文案 ——\n\n" + result["original"]
                        + "\n\n—— 精炼文案 ——\n\n" + result["refined"]
                        + "\n\n—— 要点文案 ——\n\n" + result["keypoints"]
                    )
                    self.success.emit(result["original"], result["refined"], result["keypoints"], combined)
                else:
                    combined = cloudflare_client.summarize_text(
                        "请对以下内容进行总结：\n\n" + text
                    )
                    self.success.emit("", "", "", combined)
            else:
                if self.summary_type == SummaryType.AUDIO:
                    prompt = "请对以下音频内容进行总结"
                else:
                    prompt = "请对以下视频内容进行总结"
                result = cloudflare_client.summarize_multipart(self.file_path, prompt)
                self.success.emit("", "", "", result)

        except Exception as e:
            logger.exception("总结失败")
            self.error.emit(str(e))
        finally:
            self.finished.emit()
