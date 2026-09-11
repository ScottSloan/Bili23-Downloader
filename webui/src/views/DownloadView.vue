<script setup lang="ts">
/**
 * 下载页
 *
 * 布局对着桌面版 `gui/interface/download.py`：
 *
 * - 左上角一个 Pivot（正在下载 / 下载完成），右上角一排操作按钮，两者同一行
 * - 页面四周 `25 15`（`main_layout.setContentsMargins(25, 15, 25, 15)`）
 * - 「正在下载」那一排：排序、打开目录 | 全部开始、全部暂停、全部删除
 * - 「下载完成」那一排：排序、打开目录 | 清空
 *
 * **两处有意偏离**：
 *
 * - **没有「打开下载目录」** —— 浏览器开不了本机的资源管理器（也不该能）。
 *   一度做成「复制路径」，但那对用户没用：他要的是打开文件夹，
 *   拿到一串路径还得自己去粘贴。宁可没有这个按钮
 * - 排序做成下拉，不是浮出面板 —— 只有两个选项（按什么排、正倒序），
 *   为它搭一层浮层不划算
 *
 * 现场由 taskStore 维护：全量快照恢复 + WebSocket 增量（后端 S3-9）。
 * **所有操作都不在本地先改状态**，等服务端的事件推回来 —— 本地先改的话，
 * 操作失败时界面已经变了，而用户不会知道。
 */
import { computed, onActivated, ref, watch } from 'vue'
import { useTaskStore } from '@/stores/taskStore'
import { useToastStore } from '@/stores/toastStore'
import { t } from '@/i18n'
import type { TaskView } from '@/api'
import fluentPivot from '@/components/Fluent/components/navigation/FluentPivot.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import toolButton from '@/components/Fluent/components/widgets/button/ToolButton.vue'
import fluentComboBox from '@/components/Fluent/components/widgets/combo_box/ComboBox.vue'
import downloadItem from '@/components/App/download/DownloadItem.vue'
import { formatSpeed } from '@/components/App/download/formatters'

const store = useTaskStore()
const toast = useToastStore()

const tab = ref<'downloading' | 'completed'>('downloading')

const tabs = computed(() => [
  { key: 'downloading', label: t('task.tabDownloading') },
  { key: 'completed', label: t('task.tabCompleted') },
])

// 任务列表的错误也走气泡。这一页大部分操作（暂停 / 重试 / 删除）是即发即忘的，
// 失败了没有别的地方会说
watch(
  () => store.error,
  (message) => {
    if (message) {
      toast.error(t('toast.loadFailed'), message)
    }
  },
)

// 任务流的起停归 App.vue 管（跟着登录态），这里不再自己开关 ——
// 导航栏的下载数角标要求它在任何页面上都是新的。
//
// 进页面时仍然 start() 一次：它自带幂等（已经连着就直接返回），
// 用来兜住「连接断了而用户正好切回来」这种情况
onActivated(() => store.start())

// ---- 排序 ----
//
// 键与桌面版 `on_show_downloading_list_sort_flyout` 那份一致

const SORT_KEYS = {
  downloading: ['created_time', 'title', 'total_size', 'progress'],
  completed: ['completed_time', 'title', 'total_size'],
} as const

const sortBy = ref<Record<string, string>>({
  downloading: 'created_time',
  completed: 'completed_time',
})

const ascending = ref<Record<string, boolean>>({
  downloading: true,
  completed: false,
})

const sortOptions = computed(() =>
  SORT_KEYS[tab.value].map((key) => ({ value: key, label: t(`task.sortBy.${key}`) })),
)

const list = computed<TaskView[]>(() => {
  const source = tab.value === 'downloading' ? store.downloading : store.completed

  const key = sortBy.value[tab.value]
  const factor = ascending.value[tab.value] ? 1 : -1

  // 拷一份再排：直接排 store 里那个数组会把增量事件的插入顺序也搅乱
  return [...source].sort((a, b) => {
    if (key === 'title') {
      return a.title.localeCompare(b.title) * factor
    }

    const left = (a as unknown as Record<string, number>)[key] || 0
    const right = (b as unknown as Record<string, number>)[key] || 0

    return (left - right) * factor
  })
})

// ---- 选择 ----

const selectedIds = computed(() => list.value.map((task) => task.task_id).filter((id) => store.selected.has(id)))

// ---- 操作 ----

/**
 * 一行上那个主按钮
 *
 * 与桌面版 `_pressEvent` 同一套分支：排队与暂停的开始、失败的重来、其余暂停。
 *
 * **少了「完成的打开目录」那一条** —— 浏览器开不了本机的资源管理器（也不该能）。
 * 一度做成「复制路径」，但那对用户没有任何用处：他要的是打开文件夹，
 * 拿到一串路径还得自己去粘贴。宁可没有这个按钮
 */
function onItemAction(task: TaskView) {
  switch (task.status) {
    case 'queued':
    case 'paused':
    case 'ffmpeg_queued':
      store.resume([task.task_id])

      break

    case 'failed':
    case 'ffmpeg_failed':
      store.retry([task.task_id])

      break

    default:
      store.pause([task.task_id])
  }
}

function onItemRemove(task: TaskView) {
  store.remove([task.task_id], task.status === 'completed')
}

function batchStart() {
  store.resume(store.downloading.map((task) => task.task_id))
}

function batchPause() {
  store.pause(store.downloading.map((task) => task.task_id))
}

function batchRemove() {
  const ids = (tab.value === 'downloading' ? store.downloading : store.completed).map(
    (task) => task.task_id,
  )

  if (ids.length) {
    store.remove(ids, tab.value === 'completed')
  }
}

</script>

<template>
  <div class="page-view">
    <div class="top">
      <fluentPivot v-model="tab" :items="tabs" style="gap: 24px;"/>

      <span v-if="!store.live" class="offline none-select">{{ t('task.offline') }}</span>

      <span class="flex-stretch"></span>

      <div class="toolbar">
        <fluentComboBox
          class="sort-key"
          :model-value="sortBy[tab]"
          :options="sortOptions"
          :label="t('task.sort')"
          @update:model-value="(value: string | number) => (sortBy[tab] = String(value))"
        />

        <toolButton
          icon="sort"
          :label="ascending[tab] ? t('task.ascending') : t('task.descending')"
          :class="{ 'is-descending': !ascending[tab] }"
          @click="ascending[tab] = !ascending[tab]"
        />

        <span class="separator" />

        <template v-if="tab === 'downloading'">
          <primaryPushButton
            icon="play"
            :title="t('task.startAll')"
            :disabled="!store.downloading.length"
            @click="batchStart"
          />
          <pushButton
            icon="pause"
            :title="t('task.pauseAll')"
            :disabled="!store.downloading.length"
            @click="batchPause"
          />
          <pushButton
            icon="delete"
            :title="t('task.deleteAll')"
            :disabled="!store.downloading.length"
            @click="batchRemove"
          />
        </template>

        <pushButton
          v-else
          icon="clear"
          :title="t('task.clearAll')"
          :disabled="!store.completed.length"
          @click="batchRemove"
        />
      </div>
    </div>

    <div v-if="!store.live || selectedIds.length" class="notice">
      <template v-if="selectedIds.length">
        <span class="selection">{{ t('task.selected', { count: selectedIds.length }) }}</span>

        <pushButton :title="t('task.pause')" @click="store.pause(selectedIds)" />
        <pushButton :title="t('task.resume')" @click="store.resume(selectedIds)" />
        <pushButton :title="t('task.retry')" @click="store.retry(selectedIds)" />
        <pushButton
          :title="t('task.remove')"
          @click="store.remove(selectedIds, tab === 'completed')"
        />
      </template>

      <span class="flex-stretch" />

      <span v-if="tab === 'downloading' && store.totalSpeed" class="total-speed">
        {{ formatSpeed(store.totalSpeed) }}
      </span>
    </div>

    <div class="task-list">
      <p v-if="!list.length" class="empty none-select">
        {{ tab === 'downloading' ? t('task.emptyDownloading') : t('task.emptyCompleted') }}
      </p>

      <downloadItem
        v-for="task in list"
        :key="task.task_id"
        :task="task"
        :selected="store.selected.has(task.task_id)"
        @update:selected="store.toggleSelected(task.task_id)"
        @action="onItemAction(task)"
        @remove="onItemRemove(task)"
      />
    </div>
  </div>
</template>

<style scoped>
.page-view {
  /* 与桌面版 main_layout 的 25 / 15 一致 */
  padding: 15px 25px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  height: 100%;
  box-sizing: border-box;
}

.top {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

.flex-stretch {
  flex: 1 1 auto;
}

.toolbar {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.sort-key {
  min-width: 120px;
}

/* 倒序时把排序图标翻过来，与桌面版那两个互斥按钮（SORT / SORT_REVERSE）等价 */
.is-descending :deep(.fluent-icon) {
  transform: scaleY(-1);
}

/* 桌面版工具栏里那条竖线：宽 5、上下留 5、alpha 50/255 */
.separator {
  flex: 0 0 auto;
  width: 1px;
  height: 22px;
  margin: 0 4px;
  background-color: rgba(0, 0, 0, 0.196);
}

:root[data-theme='dark'] .separator {
  background-color: rgba(255, 255, 255, 0.196);
}

.notice {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary);
}

.offline {
  padding: 2px 8px;
  border-radius: 10px;
  background-color: var(--control-fill-secondary);
}

.total-speed {
  font-size: 13px;
  color: var(--text-secondary);
}

.task-list {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  /* 桌面版列表项之间没有间距，行与行是贴着的 */
  gap: 0;
}

/* 空提示在整块列表区域里居中，不是贴着顶 */
.empty {
  flex: 1 1 auto;
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
}
</style>
