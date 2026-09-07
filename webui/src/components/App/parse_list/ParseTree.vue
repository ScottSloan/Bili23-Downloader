<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { ComponentPublicInstance } from 'vue'
import { useVirtualizer } from '@tanstack/vue-virtual'
import type { VirtualItem } from '@tanstack/vue-virtual'
import { useParseStore, CHECKED, PARTIAL } from '@/stores/parseStore'
import { cellText } from './formatters'
import type { CheckState, ParseNode } from '@/stores/parseStore'
import { t, columnName } from '@/i18n'

const store = useParseStore()

// 用 CSS grid 列宽复刻 GUI 的列配置：标题列吃掉剩余空间，其余按配置的像素宽度
const gridTemplate = computed(() =>
  store.visibleColumns
    .map((column) => (column.key === 'title' ? 'minmax(0, 1fr)' : `${column.width}px`))
    .join(' '),
)

// ---------------------------------------------------------------------------
// 虚拟滚动
//
// 番剧「凡人修仙传」实测 1376 项，全量渲染时每次勾选 / 展开都要让上千个 DOM 节点
// 参与重排，卡顿肉眼可见。这里接 @tanstack/vue-virtual。
//
// 选它是因为它是 headless 的：只负责算「当前该渲染哪几行、各行偏移多少、总高多少」，
// DOM 结构与样式仍然由本组件自己写。所以列布局（CSS grid）、缩进、三态勾选、hover
// 全部保持原样，一行样式都不用为虚拟滚动让路。
//
// 之所以不手写：虚拟滚动叠加树展开的边界情况极多——折叠导致总高突变、滚动位置越界后
// 浏览器夹取 scrollTop、实测行高与估算值不符时要反向修正滚动偏移。本仓库此前手写过
// 一版已经踩过坑，PLAN.md 的 S1-8 因此明确写死了「用成熟库」。
//
// store 的 rows getter 已按展开状态把树摊平成扁平数组，这里面对的就是一个定高列表，
// 不需要在虚拟化层再处理树的递归。
// ---------------------------------------------------------------------------

const bodyRef = ref<HTMLElement | null>(null)

// 行高的初始估算值。真实行高取决于字体回退（Segoe UI / 微软雅黑 / PingFang 各不相同）、
// 浏览器缩放，以及行内徽标的高度，没法在代码里写死，所以这个常量只作兜底：
// 首屏量到真实行高后立刻被覆盖，见 measureRow
const ESTIMATED_ROW_HEIGHT = 30

const rowHeight = ref(ESTIMATED_ROW_HEIGHT)
let rowHeightSettled = false

const virtualizer = useVirtualizer<HTMLElement, HTMLElement>(
  computed(() => ({
    count: store.rows.length,
    getScrollElement: () => bodyRef.value,
    estimateSize: () => rowHeight.value,
    // 用节点 id 而不是下标做键：展开 / 折叠会让同一个节点换下标，
    // 以 id 为键时库内的行高缓存能跟着节点走，折叠后再展开不会拿错行高
    getItemKey: (index: number) => store.rows[index]?.id ?? index,
    overscan: 10,
  })),
)

/** 落到模板上的一行：虚拟化元信息 + store 里对应的节点 */
interface VirtualRow {
  item: VirtualItem
  node: ParseNode
  depth: number
  /** 行标识，来自 store 派发的位置路径 */
  id: string
}

// 只把窗口内的行映射成渲染数据。count 变小的那一帧里 virtualizer 可能还持有旧下标，
// 越界的先滤掉，避免读到 undefined
const virtualRows = computed<VirtualRow[]>(() => {
  const rows = store.rows

  return virtualizer.value
    .getVirtualItems()
    .map((item) => {
      const row = rows[item.index]

      return row ? { item, node: row.node, depth: row.depth, id: row.id } : null
    })
    .filter((entry): entry is VirtualRow => entry !== null)
})

// 撑高层的高度。滚动条长度靠它体现真实行数，不能省
const totalSize = computed(() => virtualizer.value.getTotalSize())

// 行的实测交给库自己做（它内部用 ResizeObserver，按 data-index 定位是哪一行），
// 顺带把第一次量到的高度回填给 estimateSize。
//
// 回填这一步不是多余的：没被渲染过的行一律按估算值累加偏移，估算值哪怕只差 1px，
// 1376 行累计下来也有上千像素，表现为滚动条长度随滚动来回伸缩。只取第一次的结果
// 并就此定死，是为了避免个别带徽标的行把估算值带偏、引起反复的选项变更。
function measureRow(el: Element | ComponentPublicInstance | null) {
  virtualizer.value.measureElement(el as HTMLElement | null)

  if (!rowHeightSettled && el instanceof HTMLElement) {
    const height = el.getBoundingClientRect().height

    if (height > 0) {
      rowHeightSettled = true
      rowHeight.value = height
    }
  }
}

// 换了一批解析结果就回到顶部。虚拟滚动下这一步省不得：若上次停在第 1000 行，
// 新结果只有几行时撑高层会瞬间变矮，浏览器把 scrollTop 夹回 0 却不保证抛出 scroll
// 事件，virtualizer 仍按旧偏移取窗口，列表会短暂空白
watch(
  () => store.tree,
  () => virtualizer.value.scrollToOffset(0),
)

function stateOf(id: string): CheckState {
  return store.checkState.get(id) ?? 0
}

function onToggle(id: string, event: Event) {
  store.setChecked(id, (event.target as HTMLInputElement).checked)
}
</script>

<template>
  <div class="parse-tree">
    <div class="tree-header" :style="{ gridTemplateColumns: gridTemplate }">
      <div v-for="column in store.visibleColumns" :key="column.key" class="header-cell">
        {{ columnName(column.key) }}
      </div>
    </div>

    <div ref="bodyRef" class="tree-body">
      <p v-if="!store.rows.length" class="empty">{{ t('parse.empty') }}</p>

      <div v-else class="tree-canvas" :style="{ height: `${totalSize}px` }">
        <div
          v-for="{ item, node, depth, id: rowId } in virtualRows"
          :key="rowId"
          :ref="measureRow"
          :data-index="item.index"
          class="tree-row"
          :class="{ 'is-node': node.is_node, 'is-reparse': node.attributes.includes('need_parse_bit') }"
          :style="{
            gridTemplateColumns: gridTemplate,
            transform: `translateY(${item.start}px)`,
          }"
        >
          <div
            v-for="(column, index) in store.visibleColumns"
            :key="column.key"
            class="body-cell"
            :style="index === 0 ? { paddingLeft: `${depth * 20 + 8}px` } : null"
          >
            <template v-if="index === 0">
              <span
                class="chevron"
                :class="{ open: store.expanded.has(rowId), hidden: !node.children }"
                @click="store.toggleExpanded(rowId)"
              >
                &#9656;
              </span>

              <input
                type="checkbox"
                class="row-check"
                :checked="stateOf(rowId) === CHECKED"
                :indeterminate="stateOf(rowId) === PARTIAL"
                @change="onToggle(rowId, $event)"
              />
            </template>

            <span class="cell-text" :title="cellText(node, column.key)">
              {{ cellText(node, column.key) }}
            </span>

            <span v-if="index === 1 && false /* 已下载标记待接后端（原垫片字段） */" class="tag">{{
              t('parse.tagDownloaded')
            }}</span>
            <span v-if="index === 1 && node.attributes.includes('need_parse_bit')" class="tag">{{
              t('parse.tagNeedsReparse')
            }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.parse-tree {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 0;
}

.tree-header,
.tree-row {
  display: grid;
  align-items: center;
  column-gap: 8px;
}

.tree-header {
  padding: 6px 4px;
  font-size: 10pt;
  border-bottom: 1px solid var(--divider-stroke);
  color: var(--text-tertiary);
  user-select: none;
}

.tree-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
}

/*
  虚拟滚动的撑高层：高度等于全部行的总高度，滚动条长度由它决定。
  行相对它绝对定位，所以这里必须是定位上下文
*/
.tree-canvas {
  position: relative;
  width: 100%;
}

.tree-row {
  padding: 5px 4px;
  border-radius: 4px;
  user-select: none;
  /*
    用 left/right 而不是 width: 100% 来横向铺满：本项目没有全局的
    box-sizing: border-box，width: 100% 会把 4px 的左右内边距加到外面去，
    行比容器宽 8px，横向多出一条滚动条
  */
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
}

.tree-row:hover {
  background-color: var(--subtle-fill-secondary);
}

.tree-row.is-node {
  font-weight: 600;
}

.tree-row.is-reparse .cell-text {
  color: var(--text-tertiary);
}

.header-cell,
.body-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.cell-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chevron {
  flex: 0 0 auto;
  width: 14px;
  text-align: center;
  cursor: pointer;
  transition: transform 0.15s ease;
  color: var(--text-tertiary);
}

.chevron.open {
  transform: rotate(90deg);
}

.chevron.hidden {
  visibility: hidden;
  cursor: default;
}

.row-check {
  flex: 0 0 auto;
  margin: 0;
  accent-color: var(--primary-color);
}

.tag {
  flex: 0 0 auto;
  font-size: 8pt;
  padding: 1px 5px;
  border-radius: 3px;
  color: var(--text-tertiary);
  border: 1px solid var(--divider-stroke);
}

.empty {
  color: var(--text-tertiary);
  padding: 12px 4px;
}
</style>
