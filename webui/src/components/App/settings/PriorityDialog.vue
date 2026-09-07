<script setup lang="ts">
// 画质 / 音质 / 编码的优先级
//
// 配置里存的是一串 id，**顺序就是优先级**：下载时从上往下找第一个当前视频有的档位
// （见 `download/parse/video_info.py` 的 get_video_quality_id_by_priority）。
//
// 候选项来自后端的 `/api/settings/choices`，不在前端抄一份 —— B 站加一档新画质时，
// 抄的那份不会知道，而且不报错，只是那一档在这个列表里凭空消失。
//
// **与 GUI 的一处差异**：桌面版是拖拽排序，这里用上下按钮。HTML5 的拖放在触摸屏上
// 基本不可用，而键盘用户根本够不着；按钮两样都能用。

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
</script>

<template>
  <fluentDialog :open="open" :title="title" width="420px" @close="emit('close')">
    <template #hint>{{ t('settings.priority.hint') }}</template>

    <ul class="list">
      <li v-for="(entry, index) in order" :key="String(entry)">
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
      <pushButton :title="t('settings.dialog.cancel')" @click="emit('close')" />
      <primaryPushButton :title="t('settings.dialog.save')" @click="emit('save', order)" />
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
}

.list li:hover {
  background-color: var(--subtle-fill-secondary);
}

.rank {
  width: 20px;
  flex: 0 0 auto;
  font-size: 10pt;
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
