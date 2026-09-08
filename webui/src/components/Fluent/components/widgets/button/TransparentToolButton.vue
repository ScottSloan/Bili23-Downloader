<script setup lang="ts">
/**
 * 只有图标的透明按钮
 *
 * 对应 qfluentwidgets 的 `TransparentToolButton`（解析页工具栏那四个就是它）：
 * 平时完全透明，悬停 `rgba(0,0,0,9/255)`、按下 `rgba(0,0,0,6/255)`，圆角 5。
 * 桌面版给它定死 28×28（`setFixedSize(28, 28)`）。
 *
 * 用原生 `<button>` 而不是加 @click 的 div：Tab 可达、回车与空格触发、disabled
 * 语义全部由浏览器提供。`label` 同时当 aria-label 与 title —— 图标按钮**必须**有名字，
 * 否则读屏软件念出来是空的，鼠标用户也无从知道这个图标是干什么的。
 */
import fluentIcon from '../../../icons/FluentIcon.vue'

withDefaults(
  defineProps<{
    /** 图标名，见 icons/fluentIcons.ts */
    icon: string
    /** 无障碍名称，同时作为鼠标悬停的气泡提示 */
    label: string
    disabled?: boolean
  }>(),
  {
    disabled: false,
  },
)
</script>

<template>
  <button
    type="button"
    class="transparent-tool-button"
    :disabled="disabled"
    :aria-label="label"
    :title="label"
  >
    <fluentIcon :name="icon" />
  </button>
</template>

<style scoped>
.transparent-tool-button {
  width: 28px;
  height: 28px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 5px;
  cursor: pointer;

  font: inherit;
  margin: 0;
  padding: 0;
  appearance: none;
  border: none;
  background-color: transparent;
  color: var(--text-primary);
  transition: background-color 0.1s ease;
}

.transparent-tool-button:not(:disabled):hover {
  background-color: var(--subtle-fill-secondary);
}

.transparent-tool-button:not(:disabled):active {
  background-color: var(--subtle-fill-tertiary);
}

.transparent-tool-button:focus-visible {
  outline: 2px solid var(--focus-stroke-outer);
  outline-offset: 1px;
  box-shadow: 0 0 0 1px var(--focus-stroke-inner);
}

.transparent-tool-button:disabled {
  cursor: default;
  color: var(--text-disabled);
  background-color: transparent;
}
</style>
