"""平滑滚动的统一配置

qfluentwidgets 的滚动控件默认使用 FixedStepSmoothScrollEngine，它按帧计数推进：一次滚轮固定
分成 fps * duration / 1000 帧，每次定时器超时才走一帧。项目数量多或单项绘制较重时，单帧绘制
超过 16ms，定时器不会补偿，动画的实际时长就被拉长成 帧数 × 单帧耗时，表现为松开滚轮后列表还
在滚。自适应引擎以 QElapsedTimer 的实际间隔消耗动画时间，掉帧只会让单帧位移变大，不会拖长动画，
并且在队列积压时会合并滚轮事件，不再堆积未处理的滚动量。

引擎的选择取决于 widthThreshold（默认 2560 物理像素），窗口宽度达不到该阈值时一律回退到按帧
计数的引擎，因此需要显式置 0 才能恒定使用自适应引擎。
"""

# 50ms 的倍数
SMOOTH_SCROLL_DURATION = 250
SMOOTH_SCROLL_MIN_DURATION = 80

def getScrollDelegate(widget):
    """取得控件的平滑滚动委托

    qfluentwidgets 中 TreeView、TableView、ScrollArea 保存为 scrollDelagate（库内的拼写错误），
    而 ListView、ListWidget 保存为 scrollDelegate，两种拼写都需要兼容，否则取不到委托会静默失效。
    """
    for attr_name in ("scrollDelagate", "scrollDelegate"):
        scroll_delegate = getattr(widget, attr_name, None)

        if scroll_delegate:
            return scroll_delegate

    return None

def applySmoothScroll(widget, duration: int = SMOOTH_SCROLL_DURATION, min_duration: int = SMOOTH_SCROLL_MIN_DURATION):
    """强制使用按实际耗时推进的滚动引擎，并缩短动画时长"""
    scroll_delegate = getScrollDelegate(widget)

    if not scroll_delegate:
        return

    for smooth_scroll in (scroll_delegate.verticalSmoothScroll, scroll_delegate.horizonSmoothScroll):
        # 阈值置 0 后引擎选择不再取决于屏幕宽度，恒定返回自适应引擎
        smooth_scroll.widthThreshold = 0

        for engine in (smooth_scroll.fixedStepScrollEngine, smooth_scroll.adaptiveScrollEngine):
            engine.duration = duration

        smooth_scroll.adaptiveScrollEngine.minDuration = min_duration
