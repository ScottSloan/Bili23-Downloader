<script setup lang="ts">
// 画质 / 音质 / 编码的优先级
//
// 配置里存的是一串 id，**顺序就是优先级**：下载时从上往下找第一个当前视频有的档位
// （见 `download/parse/video_info.py` 的 get_video_quality_id_by_priority）。
//
// 候选项来自后端的 `/api/settings/choices`，不在前端抄一份 —— B 站加一档新画质时，
// 抄的那份不会知道，而且不报错，只是那一档在这个列表里凭空消失。
//
// 排序方式与桌面版一致：**按住某一项直接拖**（那边是 `DragListWidget`）。
//
// 用 pointer 事件自己实现，不用 HTML5 的 draggable：后者在触摸屏上基本不工作，
// 而且拖动时的样式几乎不可控（浏览器会自己截一张半透明的图跟着走）。
//
// 上下按钮保留着，它们不是替代品而是补充：
//
// - 行上是 `touch-action: pan-y`，触屏上纵向手势要留给列表滚动，拖不动
// - 键盘用户根本发不出指针事件
//
// 也就是说鼠标用拖的（与桌面版同一个手感），触屏与键盘用按钮。

import { computed, ref, watch } from 'vue'
import { t } from '@/i18n'
import fluentDialog from '@/components/Fluent/components/dialog/FluentDialog.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'

export interface Choice {
  value: number | string
  label: string
}

const props = defineProps<{
  open: boolean
  title: string
  choices: Choice[]
  /** 配置里的当前顺序 */
  value: (number | string)[]
}>()

const emit = defineEmits<{
  close: []
  save: [value: (number | string)[]]
}>()

const order = ref<(number | string)[]>([])

const labels = computed(() => new Map(props.choices.map((choice) => [choice.value, choice.label])))

watch(
  () => props.open,
  (open) => {
    if (open) {
      reset()
    }
  },
)

/**
 * 按配置的顺序排开，**配置里没提到的候选项补在末尾**
 *
 * 不补的话，B 站新增一档画质（配置是旧的、还没有它）时，它在这个对话框里根本不出现，
 * 用户一保存就把它从优先级里彻底抹掉了 —— 而那一档其实是可选的，
 * 只是永远轮不到被优先选中
 */
function reset() {
  const known = new Set(props.choices.map((choice) => choice.value))

  const ordered = props.value.filter((entry) => known.has(entry))

  const missing = props.choices
    .map((choice) => choice.value)
    .filter((value) => !ordered.includes(value))

  order.value = [...ordered, ...missing]
}

function move(index: number, delta: number) {
  const target = index + delta

  if (target < 0 || target >= order.value.length) {
    return
  }

  const next = [...order.value]

  ;[next[index], next[target]] = [next[target], next[index]]

  order.value = next
}

// ---- 拖拽排序 ----

/** 正在拖的那一项**当前**在第几位。-1 表示没在拖 */
const dragIndex = ref(-1)
/** 被拖那一行相对它自己位置的视觉偏移 */
const dragOffset = ref(0)

let startY = 0
let startIndex = -1
let rowHeight = 0

function onPointerDown(event: PointerEvent, index: number) {
  // 只认主键。点在上下按钮上的不算拖拽，否则按一下按钮就被当成起手
  if (event.button !== 0 || (event.target as HTMLElement).closest('button')) {
    return
  }

  const row = event.currentTarget as HTMLElement

  rowHeight = row.getBoundingClientRect().height
  startY = event.clientY
  startIndex = index

  dragIndex.value = index
  dragOffset.value = 0

  /*
    捕获指针：之后的 move / up **一律派发到这一行上**，哪怕光标已经移出了列表。
    不捕获的话，稍微拖快一点光标就跑到别的行上，事件跟着断掉，
    表现是「拖到一半自己松手了」
  */
  row.setPointerCapture(event.pointerId)
}

function onPointerMove(event: PointerEvent) {
  if (dragIndex.value < 0) {
    return
  }

  const delta = event.clientY - startY

  const target = Math.min(
    Math.max(0, startIndex + Math.round(delta / rowHeight)),
    order.value.length - 1,
  )

  if (target !== dragIndex.value) {
    const next = [...order.value]

    next.splice(target, 0, ...next.splice(dragIndex.value, 1))

    order.value = next
    dragIndex.value = target
  }

  /*
    位移要**减掉已经换过去的那几行**

    列表是边拖边重排的，被拖那一行的落脚点跟着变；直接用光标位移当 transform，
    每换一位就会多算一行的高度，行会越拖越偏离光标
  */
  dragOffset.value = delta - (dragIndex.value - startIndex) * rowHeight
}

function onPointerUp(event: PointerEvent) {
  if (dragIndex.value < 0) {
    return
  }

  const row = event.currentTarget as HTMLElement

  if (row.hasPointerCapture(event.pointerId)) {
    row.releasePointerCapture(event.pointerId)
  }

  dragIndex.value = -1
  dragOffset.value = 0
  startIndex = -1
}
</script>

<template>
  <fluentDialog :open="open" :title="title" width="420px" @close="emit('close')">
    <template #hint>{{ t('settings.priority.hint') }}</template>

    <ul class="list">
      <li
        v-for="(entry, index) in order"
        :key="String(entry)"
        :class="{ 'is-dragging': index === dragIndex }"
        :style="index === dragIndex ? { transform: `translateY(${dragOffset}px)` } : undefined"
        @pointerdown="onPointerDown($event, index)"
        @pointermove="onPointerMove"
        @pointerup="onPointerUp"
        @pointercancel="onPointerUp"
      >
        <span class="rank">{{ index + 1 }}</span>
        <span class="label">{{ labels.get(entry) ?? entry }}</span>

        <button
          type="button"
          class="move"
          :disabled="index === 0"
          :aria-label="t('settings.priority.moveUp')"
          @click="move(index, -1)"
        >
          <svg viewBox="0 0 12 12">
            <path d="M2.5 7.5 L6 4 L9.5 7.5" fill="none" stroke="currentColor" stroke-width="1.3" />
          </svg>
        </button>
        <button
          type="button"
          class="move"
          :disabled="index === order.length - 1"
          :aria-label="t('settings.priority.moveDown')"
          @click="move(index, 1)"
        >
          <svg viewBox="0 0 12 12">
            <path d="M2.5 4.5 L6 8 L9.5 4.5" fill="none" stroke="currentColor" stroke-width="1.3" />
          </svg>
        </button>
      </li>
    </ul>

    <template #actions>
      <primaryPushButton :title="t('settings.dialog.save')" @click="emit('save', order)" />
      <pushButton :title="t('settings.dialog.cancel')" @click="emit('close')" />
    </template>
  </fluentDialog>
</template>

<style scoped>
.list {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  margin: 0;
  padding: 4px;
  list-style: none;
  border-radius: 6px;
  background-color: var(--control-fill-default);
  border: 1px solid var(--card-stroke-default);
}

.list li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: grab;
  /* 拖动时别把整行的文字选中 */
  user-select: none;
  /*
    纵向手势留给列表滚动 —— 触屏上这一列可能比屏幕长，拖不动没关系，
    那种场景用右边的上下按钮。鼠标不受这个属性影响，照样能拖
  */
  touch-action: pan-y;
}

.list li:hover {
  background-color: var(--subtle-fill-secondary);
}

/* 被拖起来的那一行：压在别人上面，加一点底色和投影，看得出是「拿起来了」 */
.list li.is-dragging {
  position: relative;
  z-index: 1;
  cursor: grabbing;
  background-color: var(--control-fill-secondary);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

/*
  让位的那几行是直接跳过去的，没有补间

  它们的位移来自 DOM 顺序变化引起的重排，**不是 transform**，给它们加
  `transition: transform` 一点用都没有（试过，纯属自我安慰）。要让它们滑过去
  得上 TransitionGroup 的 FLIP，而拖动时每隔几像素就重排一次，
  move 动画会不停打断重来，反而更糊。跳过去干脆，也看得清换到哪儿了
*/

.rank {
  width: 20px;
  flex: 0 0 auto;
  font-size: 13px;
  color: var(--text-secondary);
  text-align: right;
}

.label {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-primary);
}

.move {
  appearance: none;
  flex: 0 0 auto;
  width: 24px;
  height: 22px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  cursor: pointer;
  color: var(--text-secondary);
  background-color: transparent;
  border: 1px solid var(--control-stroke-default);
}

.move svg {
  width: 12px;
  height: 12px;
}

.move:not(:disabled):hover {
  color: var(--text-primary);
  background-color: var(--control-fill-secondary);
}

.move:disabled {
  cursor: default;
  color: var(--text-disabled);
  border-color: transparent;
}

.move:focus-visible {
  outline: 2px solid var(--focus-stroke-outer);
  outline-offset: 1px;
}
</style>
