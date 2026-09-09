<script setup lang="ts">
/**
 * 下拉框
 *
 * ## 为什么不用原生 `<select>` 了
 *
 * 收起态的样子能控住，但展开后的选项列表是系统画的 —— 只有 color 与 background-color
 * 两条能被采纳，圆角、留白、悬停高亮、当前项左边那道指示条、展开动画一概没有。
 * 与桌面版摆在一起，一眼就是两个东西。
 *
 * 所以这里自己搭一个浮层，照 qfluentwidgets 的 `ComboBoxMenu` 来：
 *
 * - 列表圆角 9、1px 描边、底色 `rgb(249,249,249)` / `rgb(43,43,43)`，四周留 6
 * - 每项高 33、圆角 5、左右内边距 10，项间距 4
 * - **当前项左边一道 3×15 的主题色指示条**（`IndicatorMenuItemDelegate`），圆角 1.5
 * - 浮层宽度不小于收起态，水平居中对齐；下方放不下就朝上开
 * - 展开 250ms OutQuad，从半高展开（`DropDownMenuAnimationManager`）
 *
 * ## 浮层挂在 body 上
 *
 * 折叠卡片（`ExpandSettingCard`）与对话框（`FluentDialog`）都带 `overflow: hidden`
 * —— 它们要靠它裁圆角。浮层要是留在组件的 DOM 里，**在这两处都会被裁掉半截**，
 * 而设置页几乎每个下拉都在折叠卡片里。原生 `<select>` 没这个问题（系统画的），
 * 换成自绘就得自己解决。
 *
 * 于是 teleport 到 body、用 fixed 定位。**颜色因此要走全局 token** ——
 * 浮层已经不是组件的后代了，定义在组件根上的自定义属性它继承不到。
 *
 * 页面滚动或窗口尺寸变化时重算一次跟着走。直接关掉也是一种做法，
 * 但用滚轮翻页时下拉突然消失更烦人。
 *
 * 代价是键盘与无障碍要自己实现，下面按 WAI-ARIA 的 listbox 模式做了：
 * 上下 / Home / End 移动、回车或空格选中、Esc 关闭、首字母跳转。
 */
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

export interface ComboBoxOption {
  /** 提交回后端的值。允许数字 —— 后端的枚举有一半是整数 */
  value: string | number
  label: string
}

const props = withDefaults(
  defineProps<{
    modelValue?: string | number | null
    options: ComboBoxOption[]
    disabled?: boolean
    label?: string
  }>(),
  {
    modelValue: null,
    disabled: false,
    label: '',
  },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: string | number): void
}>()

const root = ref<HTMLElement | null>(null)
const listRef = ref<HTMLElement | null>(null)
const open = ref(false)
/** 键盘高亮的那一项。与「已选中」是两回事 —— 移动光标不等于选中 */
const active = ref(-1)
/** 朝下开还是朝上开 */
const dropUp = ref(false)
/** 浮层的 fixed 坐标。挂在 body 上之后位置得自己算 */
const flyoutStyle = ref<Record<string, string>>({})

const selectedIndex = computed(() =>
  props.options.findIndex((option) => option.value === props.modelValue),
)

const currentLabel = computed(() => props.options[selectedIndex.value]?.label ?? '')

function choose(index: number) {
  const option = props.options[index]

  if (option) {
    emit('update:modelValue', option.value)
  }

  close()
}

function close() {
  open.value = false
  active.value = -1
}

async function toggle() {
  if (props.disabled) {
    return
  }

  if (open.value) {
    close()

    return
  }

  open.value = true
  active.value = selectedIndex.value

  await nextTick()

  reposition()

  scrollActiveIntoView()
}

/**
 * 把浮层摆到收起态的下面（或上面）
 *
 * 水平居中对齐，与桌面版 `_showComboMenu` 里那句
 * `x = -menu.width()//2 + ... + self.width()//2` 是一个意思
 */
function reposition() {
  const box = root.value?.getBoundingClientRect()
  const list = listRef.value

  if (!box || !list) {
    return
  }

  const height = list.offsetHeight
  const width = Math.max(box.width, list.offsetWidth)
  const below = window.innerHeight - box.bottom

  // 下方放不下就朝上开。桌面版是比较上下两侧能容纳的高度，取大的那边
  dropUp.value = below < height + 8 && box.top > below

  // 居中之后别越出视口左右边
  const left = Math.min(
    Math.max(8, box.left + box.width / 2 - width / 2),
    Math.max(8, window.innerWidth - width - 8),
  )

  flyoutStyle.value = {
    left: `${Math.round(left)}px`,
    minWidth: `${Math.round(box.width)}px`,
    ...(dropUp.value
      ? { bottom: `${Math.round(window.innerHeight - box.top + 4)}px` }
      : { top: `${Math.round(box.bottom + 4)}px` }),
  }
}

function scrollActiveIntoView() {
  const item = listRef.value?.querySelector<HTMLElement>(`[data-index="${active.value}"]`)

  item?.scrollIntoView({ block: 'nearest' })
}

function move(delta: number) {
  if (!props.options.length) {
    return
  }

  const from = active.value < 0 ? selectedIndex.value : active.value
  const next = Math.min(props.options.length - 1, Math.max(0, from + delta))

  active.value = next

  void nextTick(scrollActiveIntoView)
}

function onKeydown(event: KeyboardEvent) {
  if (props.disabled) {
    return
  }

  // 收起时按上下或回车先把它打开，这是原生 select 的习惯，保留
  if (!open.value) {
    if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(event.key)) {
      event.preventDefault()

      void toggle()
    }

    return
  }

  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault()
      move(1)
      break

    case 'ArrowUp':
      event.preventDefault()
      move(-1)
      break

    case 'Home':
      event.preventDefault()
      active.value = 0
      void nextTick(scrollActiveIntoView)
      break

    case 'End':
      event.preventDefault()
      active.value = props.options.length - 1
      void nextTick(scrollActiveIntoView)
      break

    case 'Enter':
    case ' ':
      event.preventDefault()
      choose(active.value < 0 ? selectedIndex.value : active.value)
      break

    case 'Escape':
      event.preventDefault()
      close()
      break

    case 'Tab':
      // Tab 走开就当放弃选择，不拦它
      close()
      break

    default:
      // 首字母跳转
      if (event.key.length === 1) {
        const needle = event.key.toLowerCase()
        const found = props.options.findIndex((option) =>
          option.label.toLowerCase().startsWith(needle),
        )

        if (found >= 0) {
          active.value = found

          void nextTick(scrollActiveIntoView)
        }
      }
  }
}

function onDocumentPointerDown(event: PointerEvent) {
  const target = event.target as Node

  if (root.value?.contains(target) || listRef.value?.contains(target)) {
    return
  }

  close()
}

// 捕获阶段监听滚动：设置页滚的是 .page-view 而不是 window，冒泡阶段收不到
function onScrollOrResize() {
  reposition()
}

watch(open, (isOpen) => {
  if (isOpen) {
    document.addEventListener('pointerdown', onDocumentPointerDown)
    document.addEventListener('scroll', onScrollOrResize, true)
    window.addEventListener('resize', onScrollOrResize)
  } else {
    document.removeEventListener('pointerdown', onDocumentPointerDown)
    document.removeEventListener('scroll', onScrollOrResize, true)
    window.removeEventListener('resize', onScrollOrResize)
  }
})

// 展开着就被卸载（切页、条件渲染）时监听要收回来
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onDocumentPointerDown)
  document.removeEventListener('scroll', onScrollOrResize, true)
  window.removeEventListener('resize', onScrollOrResize)
})
</script>

<template>
  <div ref="root" class="fluent-combo-box" :class="{ 'is-disabled': disabled, 'is-open': open }">
    <button
      type="button"
      class="box"
      :disabled="disabled"
      role="combobox"
      aria-haspopup="listbox"
      :aria-expanded="open"
      :aria-label="label || undefined"
      @click="toggle"
      @keydown="onKeydown"
    >
      <span class="value">{{ currentLabel }}</span>

      <svg class="chevron" viewBox="0 0 12 12" aria-hidden="true">
        <path d="M2 4.5 L6 8.5 L10 4.5" fill="none" stroke="currentColor" stroke-width="1.2" />
      </svg>
    </button>

    <!--
      挂到 body：折叠卡片与对话框都有 overflow: hidden，留在原地会被裁掉。
      scoped 的 data-v 属性跟着节点一起搬走，所以样式仍然生效；
      但组件根上的自定义属性继承不到，颜色因此走全局 token
    -->
    <teleport to="body">
      <transition :name="dropUp ? 'pull-up' : 'drop-down'">
        <div
          v-if="open"
          ref="listRef"
          class="flyout"
          :style="flyoutStyle"
          role="listbox"
          :aria-label="label || undefined"
        >
          <div
            v-for="(option, index) in options"
            :key="String(option.value)"
            class="item"
            :class="{ 'is-selected': index === selectedIndex, 'is-active': index === active }"
            :data-index="index"
            role="option"
            :aria-selected="index === selectedIndex"
            @click="choose(index)"
            @mousemove="active = index"
          >
            <span class="indicator"></span>
            <span class="item-label">{{ option.label }}</span>
          </div>
        </div>
      </transition>
    </teleport>
  </div>
</template>

<style scoped>
.fluent-combo-box {
  position: relative;
  display: inline-flex;
  flex: 0 0 auto;
}

/* ---- 收起态。度量来自 combo_box.qss ---- */
.box {
  font: inherit;
  margin: 0;
  appearance: none;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 140px;
  max-width: 260px;
  padding: 5px 11px 6px 11px;
  border-radius: 5px;
  cursor: pointer;
  text-align: left;
  outline: none;
  transition:
    background-color 0.2s ease,
    border-color 0.2s ease;

  color: var(--text-primary);
  background-color: var(--control-fill-default);
  border: 1px solid var(--control-stroke-default);
  border-bottom-color: var(--control-stroke-accent);
}

:root[data-theme='dark'] .box {
  border-bottom-color: var(--control-stroke-default);
  border-top-color: var(--control-stroke-accent);
}

.value {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chevron {
  flex: 0 0 auto;
  width: 12px;
  height: 12px;
  color: var(--text-secondary);
  transition: transform 0.2s ease;
}

.fluent-combo-box.is-open .chevron {
  transform: rotate(180deg);
}

.box:not(:disabled):hover {
  background-color: var(--control-fill-secondary);
}

.box:not(:disabled):active {
  color: var(--text-pressed);
  background-color: var(--control-fill-tertiary);
}

.box:focus-visible {
  outline: 2px solid var(--focus-stroke-outer);
  outline-offset: 1px;
  box-shadow: 0 0 0 1px var(--focus-stroke-inner);
}

.box:disabled {
  cursor: default;
  color: var(--text-disabled);
  background-color: var(--control-fill-tertiary);
  border-color: var(--control-stroke-default);
}

.fluent-combo-box.is-disabled .chevron {
  color: var(--text-disabled);
}

/* ---- 浮层。度量来自 menu.qss 的 MenuActionListWidget ---- */
.flyout {
  position: fixed;
  /*
    **必须高于对话框的 100。** 浮层 teleport 到了 body，与对话框是兄弟节点，
    层级低就会被对话框盖住 —— 表现是「点了下拉没反应」，而其实它在下面画着。
    全局的顺序：对话框 100 < 浮层 150 < 气泡 200
  */
  z-index: 150;
  max-height: 320px;
  overflow-y: auto;
  box-sizing: border-box;
  /* 四周 6：qss 里是每项 margin-left/right 6，加上 viewportMargins 的 (0,2,0,6) */
  padding: 6px;
  border-radius: 9px;

  background-color: var(--flyout-fill);
  border: 1px solid var(--flyout-stroke);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.18);
}

.item {
  position: relative;
  display: flex;
  align-items: center;
  /* 每项 33 高，与 setItemHeight(33) 一致 */
  height: 33px;
  padding: 0 10px;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
  color: var(--text-primary);
}

.item + .item {
  /* #comboListWidget::item { margin-top: 4px } */
  margin-top: 4px;
}

.item.is-active {
  background-color: var(--subtle-fill-secondary);
}

.item:active {
  background-color: var(--subtle-fill-tertiary);
}

.item-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 当前项左边那道竖条：3×15、圆角 1.5、主题色（IndicatorMenuItemDelegate） */
.indicator {
  position: absolute;
  left: 0;
  width: 3px;
  height: 15px;
  border-radius: 1.5px;
  background-color: transparent;
}

.item.is-selected .indicator {
  background-color: var(--primary-color);
}

/* ---- 展开动画 ----
   桌面版是 250ms OutQuad 从半高展开（DropDownMenuAnimationManager：起点比终点高
   半个身位，同时用 mask 把露出来的部分裁掉）。网页上用 scaleY + 变换原点做等价效果，
   看上去同样是「从贴着输入框的那条边展开」 */
.drop-down-enter-active,
.pull-up-enter-active {
  transition:
    transform 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94),
    opacity 0.15s ease-out;
}

.drop-down-leave-active,
.pull-up-leave-active {
  transition:
    transform 0.12s ease-in,
    opacity 0.12s ease-in;
}

.drop-down-enter-active,
.drop-down-leave-active {
  transform-origin: top center;
}

.pull-up-enter-active,
.pull-up-leave-active {
  transform-origin: bottom center;
}

.drop-down-enter-from,
.drop-down-leave-to,
.pull-up-enter-from,
.pull-up-leave-to {
  transform: scaleY(0.5);
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .drop-down-enter-active,
  .drop-down-leave-active,
  .pull-up-enter-active,
  .pull-up-leave-active,
  .chevron {
    transition: none;
  }
}
</style>
