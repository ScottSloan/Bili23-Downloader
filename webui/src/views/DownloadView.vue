<script setup lang="ts">
// 下载页
//
// 现场由 taskStore 维护：全量快照恢复 + WebSocket 增量（后端 S3-9）。
// 进入页面时开始订阅，离开时断开 —— 页面不在前台时没必要占着一条连接。
//
// **所有操作都不在本地先改状态**，等服务端的事件推回来。本地先改的话，
// 操作失败时界面已经变了，而用户不会知道。

import { computed, onActivated, onDeactivated } from 'vue'
import { useTaskStore } from '@/stores/taskStore'
import { t } from '@/i18n'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import transparentCheckBox from '@/components/Fluent/components/widgets/checkbox/TransparentCheckBox.vue'

const store = useTaskStore()

// keep-alive 下用 onActivated 而不是 onMounted：组件只挂载一次，
// 之后来回切页面走的是 activated / deactivated
onActivated(() => store.start())
onDeactivated(() => store.stop())

const selectedIds = computed(() => [...store.selected])
const hasSelection = computed(() => selectedIds.value.length > 0)

function formatSize(bytes: number): string {
  if (!bytes) {
    return '—'
  }

  const units = ['B', 'KB', 'MB', 'GB', 'TB']

  let value = bytes
  let index = 0

  while (value >= 1024 && index < units.length - 1) {
    value /= 1024
    index += 1
  }

  return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`
}

function formatSpeed(bytes: number): string {
  return bytes > 0 ? `${formatSize(bytes)}/s` : ''
}

function statusText(status: string): string {
  // 后端发的是状态名（DownloadStatus 的成员名小写），前端按 key 翻译。
  // 缺翻译时回落到原文，好让界面上一眼看出漏了哪条
  return t(`task.status.${status}`)
}
</script>

<template>
  <div class="page-view">
    <div class="toolbar">
      <span class="summary">
        {{ t('task.summary', { active: store.activeCount, total: store.downloading.length }) }}
        <template v-if="store.totalSpeed">· {{ formatSpeed(store.totalSpeed) }}</template>
      </span>

      <!-- 断线时明确标出来：不标的话，「没有进度」看起来与「网络很慢」一模一样 -->
      <span v-if="!store.live" class="offline">{{ t('task.offline') }}</span>

      <span class="flex-stretch" />

      <pushButton
        :title="t('task.pause')"
        :disabled="!hasSelection"
        @click="store.pause(selectedIds)"
      />
      <pushButton
        :title="t('task.resume')"
        :disabled="!hasSelection"
        @click="store.resume(selectedIds)"
      />
      <pushButton
        :title="t('task.retry')"
        :disabled="!hasSelection"
        @click="store.retry(selectedIds)"
      />
      <pushButton
        :title="t('task.remove')"
        :disabled="!hasSelection"
        @click="store.remove(selectedIds)"
      />
    </div>

    <p v-if="store.error" class="error" role="alert">{{ store.error }}</p>

    <div class="task-list">
      <p v-if="!store.downloading.length && !store.completed.length" class="empty">
        {{ t('task.empty') }}
      </p>

      <template v-else>
        <div v-for="task in store.downloading" :key="task.task_id" class="task-row">
          <transparentCheckBox
            :checked="store.selected.has(task.task_id)"
            @update:checked="store.toggleSelected(task.task_id)"
          />

          <div class="task-main">
            <div class="task-title" :title="task.title">{{ task.title }}</div>

            <div class="progress-track">
              <div
                class="progress-fill"
                :class="{ 'is-error': task.status === 'failed' || task.status === 'ffmpeg_failed' }"
                :style="{ width: `${task.progress}%` }"
              />
            </div>

            <div class="task-meta">
              <span>{{ task.status_label || statusText(task.status) }}</span>
              <span>{{ task.progress }}%</span>
              <span v-if="task.total_size">
                {{ formatSize(task.downloaded_size) }} / {{ formatSize(task.total_size) }}
              </span>
              <span v-if="task.speed">{{ formatSpeed(task.speed) }}</span>
              <span v-if="task.info_label" class="tag">{{ task.info_label }}</span>
            </div>
          </div>
        </div>

        <div v-if="store.completed.length" class="section-title">
          {{ t('task.completedSection', { count: store.completed.length }) }}
        </div>

        <div v-for="task in store.completed" :key="task.task_id" class="task-row is-done">
          <transparentCheckBox
            :checked="store.selected.has(task.task_id)"
            @update:checked="store.toggleSelected(task.task_id)"
          />

          <div class="task-main">
            <div class="task-title" :title="task.title">{{ task.title }}</div>

            <div class="task-meta">
              <span>{{ statusText(task.status) }}</span>
              <span v-if="task.total_size">{{ formatSize(task.total_size) }}</span>
              <span v-if="task.info_label" class="tag">{{ task.info_label }}</span>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.page-view {
  padding: 15px 25px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  height: 100%;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.summary {
  font-size: 13px;
  color: var(--text-secondary);
}

.offline {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
  color: var(--text-secondary);
  background-color: var(--control-fill-secondary);
}

.error {
  margin: 0;
  font-size: 12px;
  color: var(--text-critical, #c42b1c);
}

.task-list {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.empty {
  margin: 24px 0;
  text-align: center;
  color: var(--text-secondary);
}

.section-title {
  margin-top: 12px;
  font-size: 12px;
  color: var(--text-secondary);
}

.task-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 6px;
  background-color: var(--control-fill-default);
  border: 1px solid var(--card-stroke-default);
}

.task-row.is-done {
  opacity: 0.75;
}

.task-main {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.task-title {
  font-size: 13px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.progress-track {
  height: 4px;
  border-radius: 2px;
  background-color: var(--control-fill-secondary);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background-color: var(--primary-color);
  transition: width 0.2s ease;
}

.progress-fill.is-error {
  background-color: var(--text-critical, #c42b1c);
}

.task-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  font-size: 11px;
  color: var(--text-secondary);
}

.tag {
  padding: 0 6px;
  border-radius: 8px;
  background-color: var(--control-fill-secondary);
}
</style>
