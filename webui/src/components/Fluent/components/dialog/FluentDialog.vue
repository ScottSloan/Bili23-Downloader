<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue'

/**
 * 对话框外壳：遮罩 + 面板 + 标题 + 底部按钮区
 *
 * 对应 GUI 的 `gui/component/dialog.py` 里的 `DialogBase`，也就是 qfluentwidgets 的
 * `MessageBoxBase` —— 设置页那 16 个对话框在桌面版全都是它。度量照抄：
 *
 * - 遮罩 `QColor(0, 0, 0, 76)`，淡入 200ms
 * - 面板圆角 10、1px 描边、阴影 `blurRadius 60 / offset (0, 10) / QColor(0, 0, 0, 50)`
 * - 内容区四周 24、行距 12；标题是 `SubtitleLabel`（20px DemiBold），提示是
 *   `BodyLabel`（14px）
 * - 底部按钮区**是一条独立的浅色带**：高 81、上边一条线、四周 24、按钮间距 12，
 *   且每个按钮 `stretch = 1` —— 两个按钮各占一半宽度，不是右下角两个小按钮。
 *   这条带子是桌面版对话框最显眼的特征，之前 Web 端没有它，一眼就能看出是两套东西
 *
 * 抽出来之前遮罩与面板的那段 CSS 已经被抄了三遍，而键盘与滚动这两件事**每抄一遍都会漏**：
 *
 * - Esc 关闭
 * - 打开时锁住背景滚动，否则在手机上滑动对话框会把底下的页面一起滑走
 */
const props = withDefaults(
  defineProps<{
    open: boolean
    title: string
    /** 面板宽度。内容差别很大，交给调用方定 */
    width?: string
    /** 点遮罩是否关闭。有未保存改动的对话框可以关掉这个 */
    closeOnMask?: boolean
  }>(),
  {
    width: '420px',
    closeOnMask: true,
  },
)

const emit = defineEmits<{
  close: []
}>()

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    emit('close')
  }
}

function lockScroll(locked: boolean) {
  if (typeof document === 'undefined') {
    return
  }

  document.body.style.overflow = locked ? 'hidden' : ''
}

watch(
  () => props.open,
  (open) => {
    lockScroll(open)

    if (open) {
      window.addEventListener('keydown', onKeydown)
    } else {
      window.removeEventListener('keydown', onKeydown)
    }
  },
  { immediate: true },
)

// 对话框还开着就被卸载（切页、路由变化）时，监听与滚动锁都要收回来 ——
// 漏掉的话页面会永久卡在不能滚动的状态，而且看不出是谁干的
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)

  lockScroll(false)
})
</script>

<template>
  <div v-if="open" class="mask" @click.self="closeOnMask && emit('close')">
    <div class="dialog" role="dialog" aria-modal="true" :style="{ width }">
      <div class="view">
        <h2 class="title">{{ title }}</h2>

        <p v-if="$slots.hint" class="hint"><slot name="hint" /></p>

        <div class="body">
          <slot />
        </div>
      </div>

      <!-- 没有 actions 就不画底部那条带子。登录对话框是这么用的 ——
           桌面版那边同样是 `buttonGroup.hide()` + 点遮罩关闭 -->
      <div v-if="$slots.actions" class="footer">
        <slot name="actions" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--dialog-mask);
  z-index: 100;
  animation: fade-in 0.2s ease-out;
}

.dialog {
  max-width: 92vw;
  max-height: 82vh;
  display: flex;
  flex-direction: column;
  border-radius: 10px;
  /* 底部按钮区要贴着面板下沿，圆角得由面板来裁 */
  overflow: hidden;
  box-sizing: border-box;
  background-color: var(--dialog-fill);
  border: 1px solid var(--dialog-stroke);
  box-shadow: 0 10px 60px rgba(0, 0, 0, 0.196);
  animation: pop-in 0.2s ease-out;
}

/* ---- 内容区 ---- */
.view {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 24px;
}

.title {
  margin: 0;
  /* SubtitleLabel = getFont(20, DemiBold) */
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.hint {
  margin: 0;
  /* BodyLabel = getFont(14) */
  font-size: 14px;
  color: var(--text-secondary);
}

/* 内容自己滚，标题与按钮固定 —— 否则长列表会把确定按钮推到屏幕外 */
.body {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* ---- 底部按钮区 ---- */
.footer {
  flex: 0 0 auto;
  box-sizing: border-box;
  min-height: 81px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px;
  background-color: var(--dialog-footer-fill);
  border-top: 1px solid var(--dialog-footer-stroke);
}

/*
  按钮各占等宽，把整行填满 —— MessageBoxBase 给每个按钮的 stretch 都是 1。
  非按钮的内容（字幕语言对话框左下角那句「已选 N 项」）不参与拉伸，留在左边，
  与桌面版 setBottomLeftWidget 的位置一致
*/
.footer > :deep(button) {
  flex: 1 1 0;
}

/*
  只有一个按钮时占右半边，不铺满整行 —— 桌面版 `hideCancelButton()` 是在按钮前面
  插了一个 stretch，剩下那个按钮于是只分到一半宽度。6px 是 12 的间距的一半
*/
.footer > :deep(button:only-child) {
  flex: 0 0 calc(50% - 6px);
  margin-left: auto;
}

@keyframes fade-in {
  from {
    opacity: 0;
  }
}

/* 面板比遮罩多一点位移，与桌面版 MaskDialogBase 的淡入是同一个时长 */
@keyframes pop-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .mask,
  .dialog {
    animation: none;
  }
}
</style>
