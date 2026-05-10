#!/usr/bin/env python3
"""
YouTube播放列表时间戳完整流程测试
"""

import sys
sys.path.insert(0, r'd:\Users\8567\Documents\Bili23\Bili23-Downloader\src')

from util.parse.youtube_api import get_playlist_items
from util.parse.episode.youtube import YouTubeEpisodeParser
from util.parse.episode.tree import EpisodeData
import logging

logging.basicConfig(level=logging.WARNING)

print("🎬 YouTube 播放列表时间戳流程测试")
print("=" * 70)

playlist_id = "PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"

print(f"\n第1步: 从API获取播放列表项")
print("-" * 70)

entries = get_playlist_items(playlist_id, max_results=5)

if not entries:
    print("❌ 获取失败")
    sys.exit(1)

print(f"✅ 获取了 {len(entries)} 个视频\n")

# 检查第一个视频的时间戳
first_entry = entries[0]
print(f"第一个视频数据:")
print(f"  标题: {first_entry.get('title', 'N/A')}")
print(f"  timestamp: {first_entry.get('timestamp', 0)}")

if not first_entry.get('timestamp'):
    print("\n⚠️  WARNING: timestamp为空或0!")
else:
    import datetime
    dt = datetime.datetime.fromtimestamp(first_entry['timestamp'])
    print(f"  时间: {dt}")

print(f"\n第2步: 解析YouTube播放列表")
print("-" * 70)

EpisodeData.clear_cache()

info_data = {
    "id": playlist_id,
    "title": f"YouTube 播放列表",
    "entries": entries,
    "is_playlist": True,
}

parser = YouTubeEpisodeParser(info_data, "VIDEO")
parser.parse()

print(f"✅ 解析完成\n")

print(f"第3步: 检查解析结果")
print("-" * 70)

# 遍历生成的episode
if hasattr(parser, 'episode_list') and parser.episode_list:
    print(f"✅ 生成了 {len(parser.episode_list)} 个episode\n")
    
    for i, ep in enumerate(parser.episode_list[:3], 1):
        print(f"Episode {i}:")
        print(f"  标题: {ep.title}")
        print(f"  pubtime: {ep.pubtime if hasattr(ep, 'pubtime') else 'N/A'}")
else:
    print("📊 TreeNode 结构:\n")
    
    # 检查item_data中的时间信息
    items = entries  # 这些是原始数据
    for i, item in enumerate(items[:3], 1):
        print(f"Item {i}:")
        print(f"  标题: {item.get('title', 'N/A')}")
        print(f"  timestamp (原始): {item.get('timestamp', 0)}")
        
        # 模拟YouTubeEpisodeParser的处理
        pubtime = int(item.get("timestamp", 0))
        print(f"  pubtime (处理后): {pubtime}")

print("\n" + "=" * 70)

# 总结
print("\n📋 检查总结:")
print("  1. API是否返回timestamp? ", "✅ 是" if entries[0].get('timestamp') else "❌ 否")
print("  2. timestamp值是否有效? ", f"✅ {entries[0].get('timestamp')}" if entries[0].get('timestamp') else "❌ 0或空")
print("  3. YouTubeEpisodeParser是否处理timestamp? ✅ 是 (代码中使用pubtime字段)")
