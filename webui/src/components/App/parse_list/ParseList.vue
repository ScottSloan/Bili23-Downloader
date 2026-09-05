<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import parseListCard from '@/components/App/parse_list/ParseListCard.vue'

let source = ref([])

// 模拟大数据集
for (let i = 0; i < 24; i++) {
  source.value.push({
    id: i + 1,
    title: `史子${i + 1}号`,
    cover: 'https://i0.hdslb.com/bfs/archive/d603727a3561c2293bbb082ac125e857444139b2.jpg',
    desc: `2026-4-12`,
    uploader: `史子 Fans`,
    checked: false,
  })
}

// 虚拟列表参数
const listRef = ref(null)
const containerWidth = ref(0)
const containerHeight = ref(0)
const scrollTop = ref(0)

// 卡片项的预估宽高含间距 (230px 宽 + 20px padding)
const itemOuterWidth = 250
const itemOuterHeight = 220
const gapX = 10
const gapY = 10

// 监听容器大小改变来计算列数
let resizeObserver
onMounted(() => {
  resizeObserver = new ResizeObserver((entries) => {
    for (let entry of entries) {
      containerWidth.value = entry.contentRect.width
      containerHeight.value = entry.contentRect.height
    }
  })
  if (listRef.value) {
    resizeObserver.observe(listRef.value)
  }
})

onUnmounted(() => {
  if (resizeObserver) resizeObserver.disconnect()
})

const onScroll = () => {
  if (listRef.value) {
    scrollTop.value = listRef.value.scrollTop
  }
}

const handleCheckedChange = (id, checked) => {
  const target = source.value.find((item) => item.id === id)

  if (target) {
    target.checked = checked
  }
}

// 动态计算列数和尺寸
const columnsCount = computed(() => {
  if (!containerWidth.value) return 1
  // 容器需容纳 列数 * itemOuterWidth + (列数 - 1) * gapX
  return Math.max(1, Math.floor((containerWidth.value + gapX) / (itemOuterWidth + gapX)))
})

const totalRows = computed(() => Math.ceil(source.value.length / columnsCount.value))
const totalHeight = computed(
  () =>
    totalRows.value * itemOuterHeight + (totalRows.value > 0 ? (totalRows.value - 1) * gapY : 0),
)

// 计算当前可见视口需要渲染的项目
const visibleItems = computed(() => {
  if (!containerHeight.value || source.value.length === 0) return []

  const rowHeight = itemOuterHeight + gapY

  // 计算可见起始行和结束行，适当增加缓冲区避免滚动闪烁
  const startRow = Math.max(0, Math.floor(scrollTop.value / rowHeight) - 2)
  const visibleRowsCount = Math.ceil(containerHeight.value / rowHeight)
  const endRow = Math.min(totalRows.value, startRow + visibleRowsCount + 4)

  const startIndex = startRow * columnsCount.value
  const endIndex = Math.min(source.value.length, endRow * columnsCount.value)

  // 计算每个可见项的绝对定位位置
  return source.value.slice(startIndex, endIndex).map((item, index) => {
    const actualIndex = startIndex + index
    const rowIndex = Math.floor(actualIndex / columnsCount.value)
    const colIndex = actualIndex % columnsCount.value

    return {
      ...item,
      _style: {
        position: 'absolute',
        top: `${rowIndex * rowHeight}px`,
        left: `${colIndex * (itemOuterWidth + gapX)}px`,
      },
    }
  })
})

// --- 框选功能 ---
const isSelecting = ref(false)
const startPoint = ref({ x: 0, y: 0 })
const currentPoint = ref({ x: 0, y: 0 })

// 选框样式计算
const selectionBoxStyle = computed(() => {
  if (!isSelecting.value) return { display: 'none' }

  const left = Math.min(startPoint.value.x, currentPoint.value.x)
  const top = Math.min(startPoint.value.y, currentPoint.value.y)
  const width = Math.abs(currentPoint.value.x - startPoint.value.x)
  const height = Math.abs(currentPoint.value.y - startPoint.value.y)

  return {
    position: 'absolute',
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    height: `${height}px`,
    backgroundColor: 'rgba(0, 120, 215, 0.2)',
    border: '1px solid rgba(0, 120, 215, 0.8)',
    pointerEvents: 'none',
    zIndex: 100,
  }
})

// 计算卡片是否在选框内
const calculateSelection = () => {
  const selectLeft = Math.min(startPoint.value.x, currentPoint.value.x)
  const selectTop = Math.min(startPoint.value.y, currentPoint.value.y)
  const selectRight = selectLeft + Math.abs(currentPoint.value.x - startPoint.value.x)
  const selectBottom = selectTop + Math.abs(currentPoint.value.y - startPoint.value.y)

  const rowHeight = itemOuterHeight + gapY
  const colWidth = itemOuterWidth + gapX

  const newSource = [...source.value]
  newSource.forEach((item, index) => {
    const rowIndex = Math.floor(index / columnsCount.value)
    const colIndex = index % columnsCount.value

    const itemLeft = colIndex * colWidth
    const itemTop = rowIndex * rowHeight
    const itemRight = itemLeft + itemOuterWidth
    const itemBottom = itemTop + itemOuterHeight

    // 碰撞检测
    const isIntersecting = !(
      itemRight < selectLeft ||
      itemLeft > selectRight ||
      itemBottom < selectTop ||
      itemTop > selectBottom
    )

    if (isIntersecting) {
      item.checked = true
    }
  })

  source.value = newSource
}

const handleMouseDown = (e) => {
  // 只有左键点击且没有点击卡片内部特定元素（如已有的checkbox）才触发框选
  if (e.button !== 0) return

  if (!listRef.value) return

  // 获取相对列表容器的位置，需加上滚动条的偏移
  const rect = listRef.value.getBoundingClientRect()
  const x = e.clientX - rect.left + listRef.value.scrollLeft
  const y = e.clientY - rect.top + listRef.value.scrollTop

  isSelecting.value = true
  startPoint.value = { x, y }
  currentPoint.value = { x, y }

  window.addEventListener('mousemove', handleMouseMove)
  window.addEventListener('mouseup', handleMouseUp)
}

const handleMouseMove = (e) => {
  if (!isSelecting.value) return

  const rect = listRef.value.getBoundingClientRect()
  const x = e.clientX - rect.left + listRef.value.scrollLeft
  const y = e.clientY - rect.top + listRef.value.scrollTop

  currentPoint.value = { x, y }
}

const handleMouseUp = () => {
  if (!isSelecting.value) return

  calculateSelection()

  isSelecting.value = false
  window.removeEventListener('mousemove', handleMouseMove)
  window.removeEventListener('mouseup', handleMouseUp)
}

onUnmounted(() => {
  if (resizeObserver) resizeObserver.disconnect()
  window.removeEventListener('mousemove', handleMouseMove)
  window.removeEventListener('mouseup', handleMouseUp)
})
</script>

<template>
  <div class="parse-list" ref="listRef" @scroll="onScroll" @mousedown="handleMouseDown">
    <div class="virtual-container" :style="{ height: totalHeight + 'px' }">
      <div :style="selectionBoxStyle" class="selection-box"></div>
      <parseListCard
        v-for="value in visibleItems"
        :key="value.id"
        :title="value.title"
        :cover="value.cover"
        :desc="value.desc"
        :uploader="value.uploader"
        :style="value._style"
        :checked="value.checked"
        @update:checked="handleCheckedChange(value.id, $event)"
      />
    </div>
  </div>
</template>

<style scoped>
.parse-list {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.virtual-container {
  position: relative;
  width: 100%;
}
</style>
