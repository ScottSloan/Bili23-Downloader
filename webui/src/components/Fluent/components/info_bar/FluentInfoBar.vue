<script setup lang="ts">
/**
 * 一条气泡提示
 *
 * 对应 qfluentwidgets 的 `InfoBar`。度量与配色照 `info_bar.qss` 与
 * `components/widgets/info_bar.py` 抄：
 *
 * - 外圈四周 6、圆角 6、1px 描边，底色按分类换（信息灰 / 成功绿 / 警告黄 / 错误红）
 * - 图标占 36×36 的方格，文字区上下 8、左 1，标题与正文间距 5（横排时再加 7）
 * - 标题 14px 粗体，正文 14px，都是纯黑 / 纯白（**不跟着底色变**）
 * - 文字区右边固定留 12，关闭按钮 36×36（那 12 在 Qt 里是按钮前的 `addSpacing`，
 *   按钮隐藏时也照样占位）
 *
 * 图标保留自己的颜色，深浅主题各一份 —— 那正是这个控件的语义，
 * 换成 currentColor 就全变成一个色了。
 */
import { computed } from 'vue'
import { INFO_BAR_ICONS } from '../../icons/fluentIcons'
import { useThemeStore } from '@/stores/themeStore'
import type { ToastCategory } from '@/stores/toastStore'

const props = withDefaults(
  defineProps<{
    category: ToastCategory
    title: string
    content?: string
    closable?: boolean
    /** 横排（标题与正文一行）还是竖排。桌面版短提示横排、长消息竖排 */
    vertical?: boolean
  }>(),
  {
    content: '',
    closable: false,
    vertical: false,
  },
)

const emit = defineEmits<{
  close: []
}>()

const themeStore = useThemeStore()

const icon = computed(() => {
  const pair = INFO_BAR_ICONS[props.category] ?? INFO_BAR_ICONS.info

  return themeStore.theme === 'dark' ? pair.dark : pair.light
})
</script>

<template>
  <div class="info-bar" :class="[`is-${category}`, { 'is-vertical': vertical }]" role="status">
    <span class="icon">
      <!-- eslint-disable-next-line vue/no-v-html -->
      <svg :viewBox="icon.viewBox" aria-hidden="true" v-html="icon.body" />
    </span>

    <div class="text">
      <span v-if="title" class="title">{{ title }}</span>
      <span v-if="content" class="content">{{ content }}</span>
    </div>

    <button v-if="closable" type="button" class="close" :aria-label="title" @click="emit('close')">
      <svg viewBox="0 0 12 12" aria-hidden="true">
        <path d="M2.5 2.5 L9.5 9.5 M9.5 2.5 L2.5 9.5" stroke="currentColor" stroke-width="1.1" />
      </svg>
    </button>
  </div>
</template>

<style scoped>
.info-bar {
  display: flex;
  align-items: flex-start;
  box-sizing: border-box;
  max-width: min(560px, 92vw);
  padding: 6px;
  border-radius: 6px;
  pointer-events: auto;

  background-color: var(--info-bar-fill);
  border: 1px solid var(--info-bar-stroke);
  /* qfluentwidgets 没给它阴影，但那边是画在窗口里的；网页上浮在内容之上，
     没有一点投影会和底下的卡片糊在一起 */
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12);
}

.icon {
  flex: 0 0 auto;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon svg {
  width: 16px;
  height: 16px;
}

.text {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  align-items: baseline;
  /* 标题与正文之间 5 + 横排时额外的 7 */
  gap: 12px;
  padding: 8px 0 8px 1px;
  /*
    文字与右边缘之间的 12 —— Qt 那边是 `hBoxLayout.addSpacing(12)`，
    **加在关闭按钮之前，且无条件**：按钮 `setVisible(False)` 时布局里没了按钮，
    这段间距仍然在。

    原先把它写成关闭按钮的 margin-left，于是不可关闭的那些气泡（解析失败、
    保存失败……）右边只剩外层那 6px，文字几乎贴着边
  */
  margin-right: 12px;
}

.info-bar.is-vertical .text {
  flex-direction: column;
  align-items: flex-start;
  gap: 5px;
}

.title {
  flex: 0 0 auto;
  font-size: 14px;
  font-weight: bold;
  /* 底色是浅色块，文字一律纯黑 / 纯白，不用 --text-primary 之外的档 */
  color: var(--text-primary);
}

.content {
  font-size: 14px;
  color: var(--text-primary);
  overflow-wrap: anywhere;
}

.info-bar.is-vertical .content {
  max-height: 200px;
  overflow-y: auto;
}

.close {
  flex: 0 0 auto;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 5px;
  cursor: pointer;

  font: inherit;
  padding: 0;
  appearance: none;
  border: none;
  background-color: transparent;
  color: var(--text-primary);
}

.close svg {
  width: 12px;
  height: 12px;
  fill: none;
}

.close:hover {
  background-color: var(--subtle-fill-secondary);
}

.close:active {
  background-color: var(--subtle-fill-tertiary);
}

/* ---- 四种底色。取值来自 info_bar.qss，深浅各一套 ---- */
.info-bar.is-info {
  --info-bar-fill: rgb(244, 244, 244);
}

.info-bar.is-success {
  --info-bar-fill: rgb(223, 246, 221);
}

.info-bar.is-warning {
  --info-bar-fill: rgb(255, 244, 206);
}

.info-bar.is-error {
  --info-bar-fill: rgb(253, 231, 233);
}

.info-bar {
  --info-bar-stroke: rgb(229, 229, 229);
}

:root[data-theme='dark'] .info-bar {
  --info-bar-stroke: rgb(29, 29, 29);
}

:root[data-theme='dark'] .info-bar.is-info {
  --info-bar-fill: rgb(39, 39, 39);
}

:root[data-theme='dark'] .info-bar.is-success {
  --info-bar-fill: rgb(57, 61, 27);
}

:root[data-theme='dark'] .info-bar.is-warning {
  --info-bar-fill: rgb(67, 53, 25);
}

:root[data-theme='dark'] .info-bar.is-error {
  --info-bar-fill: rgb(68, 39, 38);
}
</style>
