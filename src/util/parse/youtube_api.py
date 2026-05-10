from util.network.request import SyncNetWorkRequest, ResponseType
from util.common import config

import logging
import re

logger = logging.getLogger(__name__)

YOUTUBE_API_KEY = "AIzaSyD_-BdmOovYzUBvQiVdeZHV5J6BLCwZbd4"

def extract_video_id(url: str) -> str | None:
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def extract_playlist_id(url: str) -> str | None:
    match = re.search(r'[?&]list=([a-zA-Z0-9_-]+)', url)
    return match.group(1) if match else None

def get_video_info(video_id: str) -> dict | None:
    try:
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": video_id,
            "key": YOUTUBE_API_KEY,
        }
        request = SyncNetWorkRequest(url, params=params, response_type=ResponseType.JSON, timeout=5)
        response = request.run()

        items = response.get("items", [])
        if not items:
            logger.warning(f"YouTube API: 未找到视频 {video_id}")
            return None

        item = items[0]
        snippet = item.get("snippet", {})
        content_details = item.get("contentDetails", {})

        duration_iso = content_details.get("duration", "PT0S")
        duration_seconds = _parse_iso_duration(duration_iso)

        return {
            "id": video_id,
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "thumbnail": _get_best_thumbnail(snippet.get("thumbnails", {})),
            "duration": duration_seconds,
            "uploader": snippet.get("channelTitle", ""),
            "uploader_id": snippet.get("channelId", ""),
            "timestamp": _parse_timestamp(snippet.get("publishedAt", "")),
            "view_count": int(item.get("statistics", {}).get("viewCount", 0)),
            "webpage_url": f"https://www.youtube.com/watch?v={video_id}",
        }
    except Exception as e:
        logger.warning(f"YouTube API 请求失败: {e}")
        return None

def get_playlist_items(playlist_id: str, max_results: int = 500) -> list[dict] | None:
    try:
        url = "https://www.googleapis.com/youtube/v3/playlistItems"
        entries = []
        page_token = None
        pages_fetched = 0

        while True:  # 使用无限循环以获取所有可用项
            params = {
                "part": "snippet,contentDetails",
                "playlistId": playlist_id,
                "maxResults": min(50, max_results - len(entries)) if len(entries) < max_results else 0,
                "key": YOUTUBE_API_KEY,
            }
            
            if len(entries) >= max_results:
                break  # 已达到所需数量
            
            if page_token:
                params["pageToken"] = page_token

            request = SyncNetWorkRequest(url, params=params, response_type=ResponseType.JSON, timeout=5)
            response = request.run()

            items = response.get("items", [])
            if not items:
                break  # 没有更多项

            for item in items:
                if len(entries) >= max_results:
                    break
                    
                snippet = item.get("snippet", {})
                resource_id = snippet.get("resourceId", {})
                video_id = resource_id.get("videoId", "")

                entries.append({
                    "id": video_id,
                    "title": snippet.get("title", ""),
                    "thumbnail": _get_best_thumbnail(snippet.get("thumbnails", {})),
                    "duration": 0,  # 播放列表API不返回duration，需要通过视频API获取
                    "uploader": snippet.get("videoOwnerChannelTitle", ""),
                    "webpage_url": f"https://www.youtube.com/watch?v={video_id}",
                    "timestamp": _parse_timestamp(snippet.get("publishedAt", "")),  # 添加发布时间
                })

            pages_fetched += 1
            
            # 检查是否有下一页
            page_token = response.get("nextPageToken")
            if not page_token or len(entries) >= max_results:
                break
            
            # 日志记录分页进度（仅在获取大量项时）
            if pages_fetched % 5 == 0:
                logger.info(f"已获取 {len(entries)}/{max_results} 个播放列表项目...")

        logger.info(f"播放列表 {playlist_id} 共获取 {len(entries)} 个项目（{pages_fetched} 页）")
        return entries if entries else None
    except Exception as e:
        logger.warning(f"YouTube API 播放列表请求失败: {e}")
        return None

def _parse_iso_duration(duration: str) -> int:
    import re
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds

def _get_best_thumbnail(thumbnails: dict) -> str:
    for quality in ["maxres", "high", "medium", "standard", "default"]:
        if quality in thumbnails:
            return thumbnails[quality].get("url", "")
    return ""

def _parse_timestamp(published_at: str) -> int:
    import datetime
    try:
        dt = datetime.datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        return int(dt.timestamp())
    except Exception:
        return 0