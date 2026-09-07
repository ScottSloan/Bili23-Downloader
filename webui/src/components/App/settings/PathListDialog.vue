<script setup lang="ts">
// 可浏览的根目录（`webui_browse_roots`）
//
// 这一项决定「选择文件夹」能去哪些地方。**只能手输**，不能用目录选择器挑 ——
// 那是个先有鸡还是先有蛋的问题：还没成为根目录的地方，浏览接口本来就不让看。
//
// 路径是**服务端上的**，不是浏览器所在机器上的。Docker 部署时填的是容器内的挂载点。
//
// 留空不等于什么都不能浏览：后端会把下载目录本身作为根（见 `web/paths.py`
// 的 browse_roots），那是最小可用范围，也是 Docker 的常态。

import { ref, watch } from 'vue'
import { t } from '@/i18n'
import fluentDialog from '@/components/Fluent/components/dialog/FluentDialog.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import lineEdit from '@/components/Fluent/components/widgets/line_edit/LineEdit.vue'

const props = defineProps<{
  open: boolean
  value: string[]
}>()

const emit = defineEmits<{
  close: []
  save: [value: string[]]
}>()

const paths = ref<string[]>([])
const draft = ref('')

watch(
  () => props.open,
  (open) => {
    if (open) {
      paths.value = [...props.value]
      draft.value = ''
    }
  },
)

function add() {
  const value = draft.value.trim()

  // 重复的不加：加了也没有额外效果，只会让列表越来越长
  if (!value || paths.value.includes(value)) {
    draft.value = ''

    return
  }

  paths.value = [...paths.value, value]
  draft.value = ''
}

function remove(index: number) {
  paths.value = paths.value.filter((_, position) => position !== index)
}
</script>

<template>
  <fluentDialog
    :open="open"
    :title="t('settings.browseRoots.title')"
    width="520px"
    @close="emit('close')"
  >
    <template #hint>{{ t('settings.browseRoots.hint') }}</template>

    <div class="add">
      <lineEdit
        v-model="draft"
        :placeholder="t('settings.browseRoots.placeholder')"
        @submit="add"
      />
      <pushButton :title="t('settings.browseRoots.add')" :disabled="!draft.trim()" @click="add" />
    </div>

    <ul class="list">
      <li v-for="(path, index) in paths" :key="path">
        <span class="path" :title="path">{{ path }}</span>
        <button
          type="button"
          class="remove"
          :aria-label="t('settings.browseRoots.remove')"
          @click="remove(index)"
        >
          <svg viewBox="0 0 12 12">
            <path d="M3 3 L9 9 M9 3 L3 9" fill="none" stroke="currentColor" stroke-width="1.3" />
          </svg>
        </button>
      </li>

      <li v-if="!paths.length" class="empty">{{ t('settings.browseRoots.empty') }}</li>
    </ul>

    <template #actions>
      <primaryPushButton :title="t('settings.dialog.save')" @click="emit('save', paths)" />
      <pushButton :title="t('settings.dialog.cancel')" @click="emit('close')" />
    </template>
  </fluentDialog>
</template>

<style scoped>
.add {
  display: flex;
  gap: 8px;
}

.add :deep(.fluent-line-edit) {
  flex: 1 1 auto;
  min-width: 0;
}

.list {
  flex: 1 1 auto;
  min-height: 140px;
  max-height: 40vh;
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
}

.list li:hover {
  background-color: var(--subtle-fill-secondary);
}

.path {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-primary);
  font-size: 10.5pt;
}

.remove {
  appearance: none;
  flex: 0 0 auto;
  width: 22px;
  height: 22px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  cursor: pointer;
  color: var(--text-secondary);
  background: transparent;
  border: 1px solid var(--control-stroke-default);
}

.remove svg {
  width: 12px;
  height: 12px;
}

.remove:hover {
  color: var(--text-danger);
  background-color: var(--control-fill-secondary);
}

.remove:focus-visible {
  outline: 2px solid var(--focus-stroke-outer);
  outline-offset: 1px;
}

.empty {
  font-size: 12px;
  color: var(--text-secondary);
  padding: 10px 8px;
}
</style>
