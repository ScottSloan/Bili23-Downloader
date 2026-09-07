<script setup lang="ts">
/**
 * 可折叠的设置卡片
 *
 * 对应 qfluentwidgets 的 `ExpandGroupSettingCard`：一张头部卡片 + 展开后露出的若干行
 * （`SettingGroupRow`），行与行之间一条 1px 分隔线。桌面版设置页里**大多数卡片都是这个**
 * ——「弹幕下载设置」「代理设置」这些一张卡片装五六项，靠展开收起把页面压短。
 *
 * ## 高度动画用 grid-template-rows，不用 max-height
 *
 * `max-height` 那套要先量出内容高度再写成 px，内容一变（某行的说明折了行）就得重新量，
 * 于是要挂 ResizeObserver，还要在动画结束后把 max-height 改回 none 否则内容长了会被裁。
 * `0fr → 1fr` 由浏览器自己算高度，上面这些全都不需要。
 *
 * 代价是浏览器门槛：Chrome 117 / Firefox 120 / Safari 16.4（均为 2023 年）。
 * 更老的浏览器上动画不生效，展开收起变成瞬间切换 —— 功能不受影响。
 */
import { ref } from 'vue'
import fluentIcon from '../../icons/FluentIcon.vue'

withDefaults(
  defineProps<{
    title: string
    icon?: string
    description?: string
    /** 首屏是否展开。桌面版一律收起，这里跟着来 */
    defaultExpanded?: boolean
  }>(),
  {
    icon: '',
    description: '',
    defaultExpanded: false,
  },
)

const expanded = ref(false)
</script>

<template>
  <div class="expand-card" :class="{ 'is-expanded': expanded }">
    <!--
      整个头部都可点，与桌面版一致（那边给 card 装了事件过滤器，点哪儿都会触发展开）。
      用原生 button 而不是加 @click 的 div：Tab 可达、回车与空格触发、
      aria-expanded 读屏软件认得，这几样手搓都要重写一遍
    -->
    <button
      type="button"
      class="header"
      :class="{ 'has-description': description }"
      :aria-expanded="expanded"
      @click="expanded = !expanded"
    >
      <fluentIcon v-if="icon" :name="icon" class="icon" />

      <div class="text">
        <div class="title">{{ title }}</div>
        <div v-if="description" class="description">{{ description }}</div>
      </div>

      <span class="chevron">
        <svg viewBox="0 0 12 12" aria-hidden="true">
          <path d="M2 4.5 L6 8.5 L10 4.5" fill="none" stroke="currentColor" stroke-width="1.1" />
        </svg>
      </span>
    </button>

    <div class="body">
      <div class="view">
        <slot />
      </div>
    </div>
  </div>
</template>

<style scoped>
.expand-card {
  border-radius: 6px;
  /* 圆角要把头部与展开区一起裁住，否则展开时头部的直角会露在圆角外面 */
  overflow: hidden;
  border: 1px solid var(--card-stroke-default);
}

/* ---- 头部 ---- */
.header {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 16px;
  box-sizing: border-box;
  min-height: 50px;
  padding: 0 16px;
  cursor: pointer;
  text-align: left;

  /* 抹掉浏览器给 button 的默认外观 */
  font: inherit;
  margin: 0;
  appearance: none;
  border: none;
  background-color: var(--card-fill-default);
}

.header.has-description {
  min-height: 70px;
  padding-top: 10px;
  padding-bottom: 10px;
}

.header:focus-visible {
  outline: 2px solid var(--focus-stroke-outer);
  /* 焦点环画在里面：卡片外面被 overflow: hidden 裁掉了，画外面等于看不见 */
  outline-offset: -3px;
  box-shadow: inset 0 0 0 1px var(--focus-stroke-inner);
}

.text {
  flex: 1 1 auto;
  min-width: 0;
}

.title {
  font-size: 14px;
  color: var(--text-primary);
}

.description {
  margin-top: 2px;
  font-size: 11px;
  color: var(--card-description);
  line-height: 1.35;
}

/* ---- 展开箭头 ---- */
.chevron {
  flex: 0 0 auto;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  color: var(--text-primary);
  transition:
    transform 0.2s ease,
    background-color 0.1s ease;
}

.chevron svg {
  width: 10px;
  height: 10px;
}

/* 悬停高亮由整个头部触发 —— 桌面版就是这样，鼠标停在标题上箭头也会亮 */
.header:hover .chevron {
  background-color: var(--expand-button-hover);
}

/* 按下比悬停更淡，这是 qfluentwidgets 定的（hover 14/255，pressed 10/255） */
.header:active .chevron {
  background-color: var(--expand-button-pressed);
}

.expand-card.is-expanded .chevron {
  transform: rotate(180deg);
}

/* ---- 展开区 ---- */
.body {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  background-color: var(--card-fill-default);
}

.expand-card.is-expanded .body {
  grid-template-rows: 1fr;
}

.view {
  min-height: 0;
  overflow: hidden;
}

/*
  每一行的上边都画一条线，一条规则兼两用：第一行的那条是头部与展开区的分界，
  其余的是行间分隔（桌面版分别由 ExpandBorderWidget 与 GroupSeparator 画，同一个颜色）。
  线在 .view 内侧，收起时跟着内容一起被裁掉，不会在折叠状态下留一条孤零零的横线
*/
.view > :deep(*) {
  border-top: 1px solid var(--card-stroke-default);
}

@media (prefers-reduced-motion: reduce) {
  .body,
  .chevron {
    transition: none;
  }
}
</style>
