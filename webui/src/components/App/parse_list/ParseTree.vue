<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useVirtualizer } from '@tanstack/vue-virtual'
import type { VirtualItem } from '@tanstack/vue-virtual'
import { useParseStore } from '@/stores/parseStore'
import { useSettingsStore } from '@/stores/settingsStore'
import fluentCheckBox from '@/components/Fluent/components/widgets/checkbox/CheckBox.vue'
import { cellText } from './formatters'
import type { CheckState, ParseNode } from '@/stores/parseStore'
import { t, columnName } from '@/i18n'

const store = useParseStore()
const settingsStore = useSettingsStore()

/**
 * 隔行换色
 *
 * 桌面版由 `parse_list_alternate_row_color` 控制（`tree_view.py` 的
 * `update_alternate_row_color`），取值也照它：浅色 5% 黑、深色 8% 白。
 * 配置读不回来时按关处理 —— 多一条底纹不如没有
 */
const alternate = computed(() => Boolean(settingsStore.value('parse_list_alternate_row_color')))


/**
 * 表头的列名
 *
 * 时间那一列在不同来源下含义不同（投稿看发布时间、收藏夹看收藏时间、
 * 历史记录看上次观看时间）。桌面版的表头会跟着换成对应的那一个，
 * 不是把三个名字并排写出来 —— 那样又长又只有一个是对的。
 *
 * 该显示哪一个由后端随解析结果给（`time_column`）
 */
function headerName(key: string): string {
  return columnName(key === 'dyn_time' ? store.timeColumn : key)
}

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
/**
 * 行高
 *
 * 桌面版 `setUniformRowHeights(True)`，行高是齐的；这边行也定死成 34
 * （`QTreeView::item` 的 padding 4 + 上下 margin 各 2 + 19px 复选框撑起来的内容高）。
 *
 * **因此不再逐行测量。** 之前用 `measureElement` 量真实行高，量到的结果会分批到达，
 * 中间那些帧里 virtualizer 手上是一份「前面几行高度为 0」的表，于是窗口算到了列表中段
 * —— 表现为解析完成的一瞬间列表从第十几行开始画，上面一片空白，而且不会自己恢复
 * （scrollTop 本来就是 0，不会触发 scroll 事件去重算）。行高既然是定的，
 * 量它没有任何收益，只带来这个毛病。
 */
const ROW_HEIGHT = 34

const virtualizer = useVirtualizer<HTMLElement, HTMLElement>(
  computed(() => ({
    count: store.rows.length,
    getScrollElement: () => bodyRef.value,
    estimateSize: () => ROW_HEIGHT,
    // 用节点 id 而不是下标做键：展开 / 折叠会让同一个节点换下标
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

/**
 * 命中当前的筛选词
 *
 * 桌面版是给标题那一列换前景色（`model.py` 的 `_get_highlight_brush`，用的是主题色），
 * 这里照做 —— 不加底色也不过滤，命中项在整张列表里的位置才看得出来
 */
function isMatch(node: { title?: string }): boolean {
  if (!store.searchKeyword) {
    return false
  }

  return (node.title || '').toLowerCase().includes(store.searchKeyword.toLowerCase())
}

</script>

<template>
  <div class="parse-tree">
    <div class="tree-header" :style="{ gridTemplateColumns: gridTemplate }">
      <div v-for="column in store.visibleColumns" :key="column.key" class="header-cell">
        {{ headerName(column.key) }}
      </div>
    </div>

    <div ref="bodyRef" class="tree-body">
      <p v-if="!store.rows.length" class="empty">{{ t('parse.empty') }}</p>

      <div v-else class="tree-canvas" :style="{ height: `${totalSize}px` }">
        <div
          v-for="{ item, node, depth, id: rowId } in virtualRows"
          :key="rowId"
          :data-index="item.index"
          class="tree-row"
          :class="{
            'is-node': node.is_node,
            'is-reparse': node.attributes.includes('need_parse_bit'),
            'is-downloaded': store.downloaded.has(rowId),
            'is-match': isMatch(node),
            'is-selected': store.selected === rowId,
            'is-odd': alternate && item.index % 2 === 1,
          }"
          :style="{
            gridTemplateColumns: gridTemplate,
            transform: `translateY(${item.start}px)`,
          }"
          @click="store.selected = rowId"
        >
          <div
            v-for="(column, index) in store.visibleColumns"
            :key="column.key"
            class="body-cell"
            :style="index === 0 ? { paddingLeft: `${depth * 20 + 4}px` } : null"
          >
            <template v-if="index === 0">
              <!-- 收起时朝右、展开时朝下。资源里那两个箭头的图形只占视口一小角，
                   缩到 9px 是个点，所以自己画 -->
              <span
                v-if="node.children?.length"
                class="chevron"
                :class="{ 'is-open': store.expanded.has(rowId) }"
                role="button"
                :aria-expanded="store.expanded.has(rowId)"
                @click.stop="store.toggleExpanded(rowId)"
              >
                <svg viewBox="0 0 12 12" aria-hidden="true">
                  <path
                    d="M4.5 2.5 L8.5 6 L4.5 9.5"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.3"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                </svg>
              </span>
              <span v-else class="chevron is-empty"></span>

              <!-- 19 而不是默认的 18：树形列表那个由 tree_view.py 的委托手画，
                   库里它跟普通复选框本来就差 1px -->
              <fluentCheckBox
                :state="stateOf(rowId)"
                :label="node.title"
                :size="19"
                @change="(checked: boolean) => store.setChecked(rowId, checked)"
              />
            </template>

            <span class="cell-text" :title="cellText(node, column.key)">
              {{ cellText(node, column.key) }}
            </span>

            <span v-if="index === 1 && store.downloaded.has(rowId)" class="tag">{{
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
  /*
    列之间不留间隙，改由单元格自己的左右内边距撑开 —— 表头的竖分隔线要正好落在
    列的边界上（`QHeaderView::section` 是靠每段的右边框画的），有间隙的话
    那条线会歪在离下一列 8px 的地方
  */
  column-gap: 0;
}

/* 度量取自 qfluentwidgets 的 tree_view.qss：高 33、字号 13、左右内边距 5 */
.tree-header {
  min-height: 33px;
  font-size: 13px;
  border-top: 1px solid var(--header-stroke);
  border-bottom: 1px solid var(--header-stroke);
  /* 与卡片副标题同一档灰，桌面版这两处的取值差 5/255，不值得单开一个 token */
  color: var(--card-description);
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

/*
  行高 34：桌面版是 `QTreeView::item` 的 padding 4 + 上下 margin 各 2，
  再加上 19px 的复选框撑起来的内容高。`setUniformRowHeights(True)` 那边行高是齐的，
  这里也写死，顺带让虚拟滚动不必逐行测量
*/
.tree-row {
  height: 34px;
  padding: 0 4px;
  user-select: none;
  cursor: default;
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

/*
  悬停与选中的底色画在伪元素上，上下各缩 2px、圆角 4 —— 与
  `TreeItemDelegate._drawBackground` 一致（那边是 top+2、height-4、radius 4）。
  画在 .tree-row 自己身上的话，底色会顶满行高，两行之间连成一片
*/
.tree-row::before {
  content: '';
  position: absolute;
  left: 4px;
  right: 0;
  top: 2px;
  bottom: 2px;
  border-radius: 4px;
  pointer-events: none;
  background-color: transparent;
}

.tree-row:hover::before,
.tree-row.is-selected::before {
  background-color: var(--tree-row-highlight);
}

/* 选中行左边那道竖条（_drawIndicator：宽 3、圆角 1.5、主题色） */
.tree-row.is-selected::after {
  content: '';
  position: absolute;
  left: 4px;
  top: 9px;
  bottom: 9px;
  width: 3px;
  border-radius: 1.5px;
  pointer-events: none;
  background-color: var(--primary-color);
}

/* 隔行换色。压在悬停底色下面，所以用单独一层 */
.tree-row.is-odd {
  background-color: var(--tree-row-alternate);
}

.parse-tree {
  --tree-row-highlight: rgba(0, 0, 0, 0.035);
  --tree-row-alternate: rgba(0, 0, 0, 0.05);
}

:root[data-theme='dark'] .parse-tree {
  --tree-row-highlight: rgba(255, 255, 255, 0.035);
  --tree-row-alternate: rgba(255, 255, 255, 0.08);
}

.tree-row.is-node {
  font-weight: 600;
}

.tree-row.is-reparse .cell-text {
  color: var(--text-tertiary);
}

/* 已下过的整行变淡，与桌面版一致（model.py 里给这类行上的是灰色画刷）。
   除了淡，还挂了一枚标签 —— 网页上没有鼠标悬停解释的余地，
   光靠颜色深浅，用户认不出这是「已下载」还是「不可用」 */
.tree-row.is-downloaded .cell-text {
  color: var(--text-tertiary);
}

/* 命中筛选词。放在已下载那条之后，两者同时成立时以命中为准 —— 用户正在找它 */
.tree-row.is-match .cell-text {
  color: var(--primary-color);
}

.header-cell,
.body-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  padding: 0 5px;
  box-sizing: border-box;
}

/* 内容压在行底色（::before）之上 */
.body-cell {
  position: relative;
  z-index: 1;
  /* 行内文字 13px，与桌面版 delegate 的 getFont(13) 一致 */
  font-size: 13px;
}

/* 表头文字居中，正文靠左 —— 与桌面版 QHeaderView 的默认对齐一致 */
.header-cell {
  justify-content: center;
  /* 每段右边一条竖线，最后一段没有（qss 里的 `section:horizontal:last`） */
  border-right: 1px solid var(--header-stroke);
}

.header-cell:last-child {
  border-right: none;
}

.cell-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chevron {
  flex: 0 0 auto;
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border-radius: 4px;
  color: var(--text-secondary);
}

.chevron svg {
  width: 11px;
  height: 11px;
  transition: transform 0.15s ease;
}

.chevron.is-open svg {
  transform: rotate(90deg);
}

.chevron:hover {
  background-color: var(--subtle-fill-tertiary);
}

/* 没有子节点的行也要占住这一格，否则同一层的复选框会左右错开 */
.chevron.is-empty {
  cursor: default;
}

.chevron.is-empty:hover {
  background-color: transparent;
}


.tag {
  flex: 0 0 auto;
  font-size: 11px;
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
