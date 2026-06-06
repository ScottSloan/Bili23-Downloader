"""
AI 总结异步工作线程

负责在后台线程中执行：
  - B站内容下载 → 上传至 Cloudflare Worker → 调用 AI 模型总结
  - 本地文件上传 → 调用 AI 模型总结

字幕总结采用两阶段流水线：
  Phase 1: JSON 字幕 → 补全标点、分段落、修正错字、去口癖 → 流畅文案
  Phase 2: 流畅文案 → 去粗取精、层次化要点 → 精炼总结

输出三个文件：
  - {bvid}_subtitle.json        — 字幕 JSON 原文
  - {bvid}_organized.txt        — Phase 1 整理后文案
  - {bvid}_summary.md           — Phase 2 要点总结
"""

from PySide6.QtCore import QObject, Signal
from pathlib import Path
import time

from util.common.data.aisum_models import SummaryType, SummaryUploadMethod
from util.common.config import config
from util.aisum.cloudflare import cloudflare_client
from util.aisum.bilibili import download_subtitle, download_audio, download_video

import logging

logger = logging.getLogger(__name__)


class SummaryWorker(QObject):
    """B 站总结工作线程"""

    finished = Signal()
    success = Signal(str, str, str)  # json_path, organized_path, summary_path
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

            # 2. 下载内容
            if self.summary_type == SummaryType.SUBTITLE:
                json_path, meta_path = download_subtitle(self.url)

                # 读取 JSON 原文 + 元数据
                with open(json_path, "r", encoding="utf-8") as f:
                    json_text = f.read()

                # 解析元数据
                title, desc = self._parse_meta(meta_path)

                # 3. 两阶段流水线总结
                result = cloudflare_client.summarize_subtitle_pipeline(json_text, title, desc)

                organized_text = result["phase1"]
                summary_text = result["phase2"]

                # 4. 保存输出文件
                organized_path = self._save_file(organized_text, "organized", ext=".txt")
                summary_path = self._save_file(summary_text, "summary", ext=".md")

                self.success.emit(json_path, organized_path, summary_path)

            elif self.summary_type in (SummaryType.AUDIO, SummaryType.VIDEO):
                if self.summary_type == SummaryType.AUDIO:
                    file_path = download_audio(self.url)
                    prompt = "请对以下音频内容进行总结"
                else:
                    file_path = download_video(self.url)
                    prompt = "请对以下视频内容进行总结"

                if upload_method == SummaryUploadMethod.PRESIGNED_URL:
                    raise NotImplementedError("预签名 URL 上传方式暂未实现")

                result = cloudflare_client.summarize_multipart(file_path, prompt)
                summary_path = self._save_file(result, "summary", ext=".md")
                self.success.emit("", "", summary_path)
            else:
                raise RuntimeError(f"不支持的总结类型: {self.summary_type}")

        except Exception as e:
            logger.exception("总结失败")
            self.error.emit(str(e))
        finally:
            self.finished.emit()

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

    def _save_file(self, content: str, tag: str, ext: str = ".txt") -> str:
        """保存内容到 AISum 目录，使用时间戳命名"""
        self.aisum_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        file_path = self.aisum_dir / f"aisum_{ts}_{tag}{ext}"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return str(file_path)


class LocalFileSummaryWorker(QObject):
    """本地文件总结工作线程（子页面 2：其他总结页）"""

    finished = Signal()
    success = Signal(str)  # result text
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
                    # JSON 字幕：使用两阶段流水线
                    result = cloudflare_client.summarize_subtitle_pipeline(text)
                    combined = (
                        "—— 整理后文案 ——\n\n" + result["phase1"]
                        + "\n\n—— 要点总结 ——\n\n" + result["phase2"]
                    )
                else:
                    combined = cloudflare_client.summarize_text(
                        "请对以下内容进行总结：\n\n" + text
                    )
                self.success.emit(combined)
            else:
                if self.summary_type == SummaryType.AUDIO:
                    prompt = "请对以下音频内容进行总结"
                else:
                    prompt = "请对以下视频内容进行总结"
                result = cloudflare_client.summarize_multipart(self.file_path, prompt)
                self.success.emit(result)

        except Exception as e:
            logger.exception("总结失败")
            self.error.emit(str(e))
        finally:
            self.finished.emit()
