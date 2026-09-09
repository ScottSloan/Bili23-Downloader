<script setup lang="ts">
import { ref, watch } from 'vue'
import fluentDialog from '@/components/Fluent/components/dialog/FluentDialog.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import transparentToolButton from '@/components/Fluent/components/widgets/button/TransparentToolButton.vue'
import { parse as parseApi, ApiError } from '@/api'
import { t, episodeTypeName } from '@/i18n'

interface HistoryEntry {
  history_id: string
  title: string
  url: string
  type: string
  created_time: number
}

const GRID_TEMPLATE = '60px minmax(0, 1fr) 120px 150px 75px'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  close: []
  /** 用户点了某一条的放大镜，把链接填回去重新解析 */
  pick: [url: string]
}>()

const entries = ref<HistoryEntry[]>([])
const maxLength = ref(100)
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''

  try {
    const result = await parseApi.history.list()

    entries.value = result.entries as HistoryEntry[]
    maxLength.value = result.max_length
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

watch(
  () => props.open,
  (open) => {
    if (open) {
      void load()
    }
  },
)

async function remove(entry: HistoryEntry) {
  entries.value = entries.value.filter((item) => item.history_id !== entry.history_id)

  try {
    await parseApi.history.remove(entry.history_id)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : String(e)

    void load()
  }
}

async function clearAll() {
  try {
    await parseApi.history.clear()

    entries.value = []
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : String(e)
  }
}

/** 时间戳是秒，按浏览器所在时区格式化 */
function formatTime(seconds: number): string {
  if (!seconds) {
    return ''
  }

  return new Date(seconds * 1000).toLocaleString()
}

function displayTitle(entry: HistoryEntry): string {
  return entry.title || episodeTypeName(entry.type)
}
</script>

<template>
  <fluentDialog
    :open="open"
    :title="t('parse.history.title')"
    width="750px"
    @close="emit('close')"
  >
    <!-- 「清除记录」跟提示挤在同一行的右端：单开一行的话左边空一大片 -->
    <template #hint>
      {{ t('parse.history.limit', { count: maxLength }) }}

      <transparentToolButton
        icon="clear"
        :label="t('parse.history.clear')"
        :text="t('parse.history.clear')"
        :disabled="!entries.length"
        @click="clearAll"
      />
    </template>

    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <div class="history-list">
      <div class="tree-header" :style="{ gridTemplateColumns: GRID_TEMPLATE }">
        <div class="header-cell is-center">{{ t('parse.history.no') }}</div>
        <div class="header-cell">{{ t('parse.history.name') }}</div>
        <div class="header-cell">{{ t('parse.history.type') }}</div>
        <div class="header-cell">{{ t('parse.history.time') }}</div>
        <div class="header-cell is-center">{{ t('parse.history.actions') }}</div>
      </div>

      <div class="tree-body">
        <p v-if="loading" class="empty">{{ t('parse.history.loading') }}</p>
        <p v-else-if="!entries.length" class="empty">{{ t('parse.history.empty') }}</p>

        <template v-else>
          <div
            v-for="(entry, index) in entries"
            :key="entry.history_id"
            class="tree-row"
            :style="{ gridTemplateColumns: GRID_TEMPLATE }"
          >
            <div class="body-cell is-center">{{ index + 1 }}</div>
            <div class="body-cell">
              <span class="cell-text" :title="entry.url">{{ displayTitle(entry) }}</span>
            </div>
            <div class="body-cell">
              <span class="cell-text">{{ episodeTypeName(entry.type) }}</span>
            </div>
            <div class="body-cell">
              <span class="cell-text">{{ formatTime(entry.created_time) }}</span>
            </div>
            <div class="body-cell is-actions">
              <transparentToolButton
                icon="search"
                :label="t('parse.history.reparse')"
                @click="emit('pick', entry.url)"
              />
              <transparentToolButton
                icon="delete"
                :label="t('parse.history.remove')"
                @click="remove(entry)"
              />
            </div>
          </div>
        </template>
      </div>
    </div>

    <template #actions>
      <primaryPushButton :title="t('settings.dialog.ok')" @click="emit('close')" />
    </template>
  </fluentDialog>
</template>

<style scoped>
.history-list {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  min-height: 240px;
  max-height: 46vh;
  border-radius: 5px;
  overflow: hidden;
  border: 1px solid var(--card-stroke-default);
  background-color: var(--card-fill-default);
}

.tree-header,
.tree-row {
  display: grid;
  align-items: center;
  /* 列之间不留间隙：表头的竖线要正好落在列边界上，靠单元格自己的内边距撑开 */
  column-gap: 0;
}

/* 度量取自 qfluentwidgets 的 tree_view.qss：高 33、字号 13、左右内边距 5 */
.tree-header {
  flex: 0 0 auto;
  min-height: 33px;
  font-size: 13px;
  border-bottom: 1px solid var(--header-stroke);
  color: var(--card-description);
  user-select: none;
}

.tree-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
}

/* 行高 40 —— 桌面版 `addRow` 给每项定的 `setSizeHint(0, QSize(0, 40))` */
.tree-row {
  position: relative;
  height: 40px;
  cursor: default;
}

/*
  悬停底色画在伪元素上，上下各缩 2px、圆角 4，与 `TreeItemDelegate._drawBackground`
  一致。画在行自己身上的话两行之间会连成一片
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

.tree-row:hover::before {
  background-color: var(--tree-row-highlight);
}

.history-list {
  --tree-row-highlight: rgba(0, 0, 0, 0.035);
}

:root[data-theme='dark'] .history-list {
  --tree-row-highlight: rgba(255, 255, 255, 0.035);
}

.header-cell,
.body-cell {
  display: flex;
  align-items: center;
  min-width: 0;
  padding: 0 5px;
  box-sizing: border-box;
}

/*
  表头跟着这一列**内容**的对齐方式走。桌面版的表头是居中的（`TreeView` 把
  `defaultAlignment` 设成了 AlignHCenter），而单元格里的文字一律靠左 ——
  两者本就对不上。与解析列表同一处取舍，理由见 ParseTree
*/
.header-cell {
  justify-content: flex-start;
  /* 每段右边一条竖线，最后一段没有 */
  border-right: 1px solid var(--header-stroke);
}

.header-cell:last-child {
  border-right: none;
}

.header-cell.is-center,
.body-cell.is-center {
  justify-content: center;
}

.body-cell {
  position: relative;
  z-index: 1;
  font-size: 13px;
}

.body-cell.is-actions {
  justify-content: center;
  gap: 2px;
  padding: 0;
}

.cell-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 空提示在整块列表区域里水平 + 垂直居中 */
.empty {
  height: 100%;
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: var(--text-tertiary);
}

.error {
  margin: 0;
  font-size: 12px;
  color: var(--text-danger);
}
</style>
