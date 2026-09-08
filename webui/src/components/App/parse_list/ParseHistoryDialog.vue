<script setup lang="ts">
/**
 * 解析历史
 *
 * 对应桌面版 `gui/dialog/misc/parse_history.py`。历史存在 `history.db` 里
 * （`util/misc/history.py`，不依赖 Qt），**两端共用同一个库** —— 桌面版解析过的链接
 * 在这里也看得到，反之亦然。
 *
 * 只保留最新 100 条，这是库那边定的（`HistoryDatabase.max_length`），
 * 由接口一并下发，不在前端写死。
 */
import { ref, watch } from 'vue'
import fluentDialog from '@/components/Fluent/components/dialog/FluentDialog.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import transparentToolButton from '@/components/Fluent/components/widgets/button/TransparentToolButton.vue'
import { parse as parseApi, ApiError } from '@/api'
import { t } from '@/i18n'

interface HistoryEntry {
  history_id: string
  title: string
  url: string
  type: string
  created_time: number
}

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  close: []
  /** 用户点了某一条，把链接填回去重新解析 */
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
  // 先从列表里拿掉再发请求：删一条历史失败了也没什么可挽回的，
  // 而等一个来回才消失会让人以为没点中
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
</script>

<template>
  <fluentDialog
    :open="open"
    :title="t('parse.history.title')"
    width="720px"
    @close="emit('close')"
  >
    <template #hint>{{ t('parse.history.limit', { count: maxLength }) }}</template>

    <div class="bar">
      <span v-if="error" class="error" role="alert">{{ error }}</span>
      <span class="stretch" />
      <pushButton
        :title="t('parse.history.clear')"
        :disabled="!entries.length"
        @click="clearAll"
      />
    </div>

    <div class="list">
      <p v-if="loading" class="empty">{{ t('parse.history.loading') }}</p>
      <p v-else-if="!entries.length" class="empty">{{ t('parse.history.empty') }}</p>

      <table v-else>
        <thead>
          <tr>
            <th class="col-index">{{ t('parse.history.no') }}</th>
            <th>{{ t('parse.history.name') }}</th>
            <th class="col-type">{{ t('parse.history.type') }}</th>
            <th class="col-time">{{ t('parse.history.time') }}</th>
            <th class="col-actions">{{ t('parse.history.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(entry, index) in entries" :key="entry.history_id">
            <td class="col-index">{{ index + 1 }}</td>
            <td :title="entry.url">
              <button type="button" class="link" @click="emit('pick', entry.url)">
                {{ entry.title || entry.url }}
              </button>
            </td>
            <td class="col-type">{{ entry.type }}</td>
            <td class="col-time">{{ formatTime(entry.created_time) }}</td>
            <td class="col-actions">
              <transparentToolButton
                icon="clear"
                :label="t('parse.history.remove')"
                @click="remove(entry)"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <template #actions>
      <pushButton :title="t('parse.history.close')" @click="emit('close')" />
    </template>
  </fluentDialog>
</template>

<style scoped>
.bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stretch {
  flex: 1 1 auto;
}

.list {
  flex: 1 1 auto;
  min-height: 200px;
  max-height: 46vh;
  overflow-y: auto;
  border-radius: 5px;
  border: 1px solid var(--card-stroke-default);
  background-color: var(--card-fill-default);
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

/* 表头度量与解析列表同源（QHeaderView::section：高 33、字号 13、居中、格线） */
th {
  position: sticky;
  top: 0;
  height: 33px;
  padding: 0 5px;
  font-weight: 400;
  color: var(--card-description);
  background-color: var(--card-fill-default);
  border-bottom: 1px solid var(--header-stroke);
  border-right: 1px solid var(--header-stroke);
}

th:last-child {
  border-right: none;
}

td {
  padding: 6px 5px;
  max-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

tr + tr td {
  border-top: 1px solid var(--card-stroke-default);
}

.col-index {
  width: 48px;
  text-align: center;
}

.col-type {
  width: 110px;
  text-align: center;
}

.col-time {
  width: 170px;
  text-align: center;
}

.col-actions {
  width: 64px;
  text-align: center;
}

.col-actions :deep(button) {
  margin: 0 auto;
}

/* 标题可点，点了把链接填回解析框 —— 桌面版那边是「重新解析」那一列的按钮 */
.link {
  font: inherit;
  padding: 0;
  margin: 0;
  border: none;
  background: none;
  cursor: pointer;
  color: var(--primary-color);
  text-align: left;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.link:hover {
  text-decoration: underline;
}

.empty {
  margin: 0;
  padding: 24px;
  text-align: center;
  font-size: 13px;
  color: var(--text-secondary);
}

.error {
  font-size: 12px;
  color: var(--text-danger);
}
</style>
