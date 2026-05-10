#!/usr/bin/env python3
"""
YouTube合集解析测试脚本
"""

import sys
sys.path.insert(0, r'd:\Users\8567\Documents\Bili23\Bili23-Downloader\src')

from util.parse.worker import ParseWorker
from util.parse.episode.tree import EpisodeData
from PySide6.QtCore import QCoreApplication
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)

logger = logging.getLogger(__name__)

# 测试URL列表
TEST_URLS = [
    # 播放列表示例
    "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf",
    # 单个视频示例  
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
]

def test_youtube_parsing():
    """测试YouTube解析"""
    app = QCoreApplication(sys.argv)
    
    for url in TEST_URLS:
        print(f"\n{'='*60}")
        print(f"🔍 测试URL: {url}")
        print('='*60)
        
        worker = ParseWorker(url)
        
        # 连接信号
        def on_success(type_str, data):
            print(f"\n✅ 解析成功!")
            print(f"  类型: {type_str}")
            print(f"  缓存数据: {EpisodeData.table}")
            app.quit()
        
        def on_error(err_msg):
            print(f"\n❌ 解析失败: {err_msg}")
            app.quit()
        
        def on_finished():
            print("任务完成")
        
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        worker.finished.connect(on_finished)
        
        # 运行解析
        worker.run()

if __name__ == "__main__":
    test_youtube_parsing()
