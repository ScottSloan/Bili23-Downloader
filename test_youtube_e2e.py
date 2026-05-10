#!/usr/bin/env python3
"""
YouTube合集端到端解析测试
"""

import sys
sys.path.insert(0, r'd:\Users\8567\Documents\Bili23\Bili23-Downloader\src')

from util.parse.worker import ParseWorker
from util.parse.episode.tree import EpisodeData
from util.parse.episode.youtube import YouTubeEpisodeParser
from util.parse.youtube_api import extract_playlist_id, get_playlist_items
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

print("🎬 YouTube 合集端到端解析测试")
print("=" * 70)

# 测试URL
test_urls = [
    ("播放列表", "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"),
]

for test_name, url in test_urls:
    print(f"\n📍 测试: {test_name}")
    print(f"   URL: {url}")
    print("-" * 70)
    
    try:
        # 第一步：提取播放列表ID并获取数据
        playlist_id = extract_playlist_id(url)
        if not playlist_id:
            print("❌ 无法提取播放列表ID")
            continue
        
        print(f"✓ 播放列表ID: {playlist_id}")
        
        entries = get_playlist_items(playlist_id, max_results=5)
        if not entries:
            print("❌ 获取播放列表项目失败")
            continue
        
        print(f"✓ 获取了 {len(entries)} 个视频")
        
        # 第二步：构造info_data并测试解析器
        info_data = {
            "id": playlist_id,
            "title": f"测试播放列表 ({playlist_id})",
            "entries": entries,
            "is_playlist": True,
        }
        
        print(f"✓ 构造info_data")
        
        # 第三步：调用解析器
        EpisodeData.clear_cache()
        parser = YouTubeEpisodeParser(info_data, "VIDEO")
        parser.parse()
        
        print(f"✓ 解析完成")
        
        # 检查结果
        if EpisodeData.table:
            print(f"\n✅ 解析成功! 获得 {len(EpisodeData.table)} 个episode")
            for episode_id, episode_info in list(EpisodeData.table.items())[:3]:
                print(f"  📺 Episode {episode_id}:")
                for key, value in episode_info.items():
                    if isinstance(value, str) and len(value) > 50:
                        value = value[:50] + "..."
                    print(f"     {key}: {value}")
        else:
            print("⚠️  没有获得episode数据")
            
    except Exception as e:
        logger.error(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 70)
print("✅ 测试完成")
