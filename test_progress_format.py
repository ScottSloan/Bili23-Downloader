import sys
import os

# 模拟 yt-dlp 的 progress hook 数据
print('=== 测试 yt-dlp 进度回调格式 ===')

test_data = {
    'status': 'downloading',
    'downloaded_bytes': 1024000,
    'total_bytes': 10485760,
    'total_bytes_estimate': 10485760,
    '_percent_str': '  9.8%',
    '_speed_str': '  1.2MiB/s',
    '_eta_str': '00:08',
    '_speed': 1258291,
}

print(f"percent_str: '{test_data['_percent_str']}'")
print(f"speed: {test_data['_speed']}")
print(f"downloaded: {test_data['downloaded_bytes']}")
print(f"total: {test_data['total_bytes']}")

# 测试解析
percent_str = test_data.get('_percent_str', '').strip()
print(f"解析后的 percent: '{percent_str}'")
try:
    percent = float(percent_str.replace('%', '').strip())
    print(f"转换后的 percent: {percent}")
except ValueError as e:
    print(f"转换失败: {e}")

# 测试当 percent_str 为空时
test_data2 = {
    'status': 'downloading',
    'downloaded_bytes': 1024000,
    'total_bytes': 10485760,
    '_percent_str': '',
}
percent_str2 = test_data2.get('_percent_str', '').strip()
print(f"空 percent_str: '{percent_str2}'")
if percent_str2:
    try:
        percent2 = float(percent_str2.replace('%', '').strip())
        print(f"转换后的 percent2: {percent2}")
    except ValueError as e:
        print(f"转换失败: {e}")
else:
    print("percent_str 为空，使用大小计算")
    downloaded = test_data2.get('downloaded_bytes', 0)
    total = test_data2.get('total_bytes', 0)
    if total > 0:
        percent2 = (downloaded / total) * 100
        print(f"计算后的 percent2: {percent2}")
