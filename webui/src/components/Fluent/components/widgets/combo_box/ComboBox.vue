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

/**
 * 浮层最高多少，超过就滚动
 *
 * 量到自然高度之后由脚本夹一次，再写进 `--flyout-height` 交给 CSS 当收尾值。
 * 样式里那个同名的兜底数字只在「还没量到」的那一帧用得上
 */
const MAX_HEIGHT = 320

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

  /*
    自然高度要量**内层**，不能量浮层自己

    这一刻浮层身上还挂着 `enter-from`，`max-height` 被压到了一半，
    `list.offsetHeight` 量出来的是压过的值 —— 拿它去算「下面放不放得下」会偏小，
    拿它去算动画起点更会自我循环。内层不受 max-height 影响，量它才对。

    `scrollHeight` 也不行：内容比盒子矮时它返回的是盒子的高度，短列表会量偏大
  */
  const content = list.firstElementChild as HTMLElement | null

  const height = Math.min(content?.offsetHeight ?? list.offsetHeight, MAX_HEIGHT)
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

  /*
    动画那两个变量**必须同步写到元素上**，不能跟着上面的 :style 走

    `flyoutStyle` 是响应式的，Vue 要等下一次 flush 才刷进 DOM，而那时动画早开始了。

    写之前先用 `is-measuring` 把过渡整个摁住，这一步不能省：**元素这时已经挂上了
    `enter-active`**，改 `--flyout-height` 会让 `max-height` 从 `calc()` 的兜底值
    （320/2 = 160）跳到真实的半高，而这一跳自己就是一次属性变化 —— 浏览器当场
    起一段 160 → 59.5 的过渡，接着 `enter-from` 被摘掉又把它改道去 119。
    最终看到的是**从 160 缩到 119**，方向反了，而且完全不报错。

    中间读一次 offsetHeight 也是故意的：逼浏览器带着新值、在「没有过渡」的状态下
    把起点落定，之后再把过渡交还给 `enter-active`
  */
  list.classList.add('is-measuring')

  list.style.setProperty('--flyout-height', `${height}px`)

  // 朝下开时内容从上方半个身位滑下来；朝上开不用，理由见样式里的说明
  list.style.setProperty('--content-shift', dropUp.value ? '0px' : `${-height / 2}px`)

  void list.offsetHeight

  list.classList.remove('is-measuring')
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
      <!--
        朝上朝下**共用一个转场名**。分成两个名字会踩坑：转场名在元素插入的那一刻
        就定下来了，而「朝上还是朝下」要等浮层渲染出来量过高度才知道 ——
        插入时用的是上一次的值，`enter-from` 于是可能拿到反方向的那一套。

        两个方向的差别只有两处：定位是贴上沿还是下沿（flyoutStyle 里的 top / bottom），
        以及内容要不要位移（--content-shift）。两处都在量完之后同步写进元素，赶得上
      -->
      <transition name="flyout">
        <div
          v-if="open"
          ref="listRef"
          class="flyout"
          :style="flyoutStyle"
          role="listbox"
          :aria-label="label || undefined"
        >
          <!--
            多包一层只为动画：朝下开时内容要相对盒子往下滑（见样式里的说明）。
            role 留在外层，中间这层不参与无障碍树
          -->
          <div class="flyout-content">
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
  /*
    收尾高度就是实测到的自然高度（脚本里已按 MAX_HEIGHT 夹过一次）。

    **不能写成固定的 320**：那样 max-height 会一路涨到 320，而盒子的可见高度
    早在它越过内容高度时就满了 —— 展开在前几十毫秒就结束，内容却还在滑，两者对不上。
    兜底的 320 只在量到高度之前那一帧用得上，与脚本里的 MAX_HEIGHT 对应
  */
  max-height: var(--flyout-height, 320px);
  overflow-y: auto;
  box-sizing: border-box;
  border-radius: 9px;

  background-color: var(--flyout-fill);
  border: 1px solid var(--flyout-stroke);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.18);
}

/*
  内边距放在内层而不是浮层上：外层量高度时要的是「内容加内边距」这一整块，
  内边距留在外层的话就得在脚本里补一个写死的 12，两边迟早对不上。

  四周 6：qss 里是每项 margin-left/right 6，加上 viewportMargins 的 (0,2,0,6)
*/
.flyout-content {
  padding: 6px;
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

  桌面版是 250ms OutQuad。`DropDownMenuAnimationManager` 干的事是：
  **整扇菜单窗口从终点上方半个身位滑下来，同时每帧把遮罩往上收**
  （`setMask(QRegion(0, endY - currentY, w, h))`）。两者叠起来的净效果是：

  - 盒子的**上沿钉在锚点不动**，下沿从半高长到满高
  - 盒子里的内容相对盒子**往下滑**半个身位

  **内容自始至终是原尺寸的**。之前这里用的是 `scaleY(0.5)`，那是把整块内容压扁了
  再抻开 —— 字会跟着变形，和桌面版根本不是一个东西，一眼能看出来。

  改成拿 `max-height` 做「长开」（起点是浮层实际高度的一半，那个值由 JS 量好写进
  `--flyout-height`，CSS 里算不出来），拿内层的 `translateY` 做「内容下滑」。
  用 max-height 而不是 clip-path：盒子有投影，clip-path 会把投影一起裁掉，
  而 max-height 是真的把盒子变小，投影跟着盒子走，那才是对的。

  朝上开（PullUp）那一支**不需要内容位移**：浮层是用 `bottom` 定位的，
  max-height 变小时下沿不动、上沿下移，内容跟着盒子一起走 —— 这与 Qt 那边
  `PullUpMenuAnimationManager` 的遮罩方向恰好一致。两支不对称是照抄来的，不是漏写。

  退场桌面版没有动画（菜单是直接 hide 的），这里留一段极短的淡出，
  免得在网页上「啪」地消失 */
/* 写动画起点的那一瞬间用它摁住过渡，理由见 reposition() 里的说明 */
.flyout.is-measuring,
.flyout.is-measuring .flyout-content {
  transition: none !important;
}

.flyout-enter-active {
  transition:
    max-height 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94),
    opacity 0.1s linear;
  /* 长开的过程中别冒出滚动条 */
  overflow: hidden;
}

.flyout-enter-active .flyout-content {
  transition: transform 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.flyout-enter-from {
  max-height: calc(var(--flyout-height, 320px) / 2);
  opacity: 0;
}

/* 位移量由脚本按方向写进 --content-shift：朝下是负半个身位，朝上是 0 */
.flyout-enter-from .flyout-content {
  transform: translateY(var(--content-shift, 0px));
}

.flyout-leave-active {
  transition: opacity 0.12s ease-in;
}

.flyout-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .flyout-enter-active,
  .flyout-enter-active .flyout-content,
  .flyout-leave-active,
  .chevron {
    transition: none;
  }
}
</style>
