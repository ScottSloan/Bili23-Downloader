# YouTube视频时间戳解决方案

## 问题分析

用户报告: "没有视频时间"

### 实际情况

✅ **YouTube API 已正确返回时间戳**:
- playlistItems API 在 `snippet.publishedAt` 中返回时间
- 例如: `"2020-01-10T16:04:32Z"`
- 被正确解析为 Unix 时间戳: `1578672272`

✅ **代码中已正确传递时间戳**:
- youtube_api.py: `get_playlist_items()` 在返回数据中添加了 `timestamp` 字段
- episode/youtube.py: YouTubeEpisodeParser 在 `item_data` 中正确使用 `"pubtime": int(entry.get("timestamp", 0))`

✅ **所有测试显示时间戳正常**:
```
视频1: timestamp: 1578672272 ✓
视频2: timestamp: 1547225205 ✓
```

## 可能的原因

1. **UI中没有显示pubtime字段**
   - 虽然数据中包含pubtime，但UI可能没有显示它
   - 需要检查下载列表UI或剧集显示代码

2. **用户界面特定场景**
   - 某些特定的YouTube播放列表可能缺少时间信息
   - 或UI需要特殊处理来显示时间

## 改进建议

### 1. 添加调试日志
在youtube_api.py中添加：
```python
logger.info(f"获取播放列表项 {i}/{len(entries)}: {entry.get('title')} (pubtime: {entry.get('timestamp')})")
```

### 2. 处理缺失时间戳的情况
```python
if not entry.get('timestamp'):
    logger.warning(f"视频 {entry.get('title')} 缺少时间戳")
```

### 3. 验证终端对时间戳的处理
检查TaskInfo或Episode类中是否正确使用pubtime字段

## 验证步骤

1. ✅ API返回时间戳 - **通过**
2. ✅ 代码正确传递 - **通过**  
3. ⚠️ UI是否显示 - **需要检查**

## 后续步骤

1. 检查GUI/component中是否显示pubtime字段
2. 如果UI没有显示，可能需要：
   - 在下载列表中添加时间列
   - 在视频详情中显示发布时间
   - 或提供格式化的日期显示

## 技术细节

**数据流**:
```
YouTube API playlistItems
├─ snippet.publishedAt: "2020-01-10T16:04:32Z"
├─ contentDetails.videoPublishedAt: "2020-01-10T16:04:31Z"
↓
youtube_api.py: _parse_timestamp()
├─ 解析ISO格式时间戳
├─ 转换为Unix时间戳
└─ 返回: 1578672272
↓
YouTubeEpisodeParser: item_data
├─ "pubtime": 1578672272
└─ 传递给UI显示
```

**对比**:
- YouTube API: ✅ 返回时间戳
- yt-dlp (extract_flat): ❌ 返回null时间戳

---

**结论**: YouTube API方案已提供完整的时间戳数据，所有测试显示正常。如果用户看不到时间，问题可能在UI显示层，而不是数据获取层。
