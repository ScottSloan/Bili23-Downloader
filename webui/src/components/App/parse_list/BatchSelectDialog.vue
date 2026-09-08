<script setup lang="ts">
/**
 * 批量选择：按序号勾选
 *
 * 对应桌面版 `gui/dialog/misc/batch_select.py`。输入 `1,3,5-10` 这样的序号表，
 * 勾上列表里 `number` 落在其中的行。
 *
 * 解析与校验放在这里而不是 store：它是这个对话框的输入格式，别处不会再用到。
 * 校验的三条与桌面版一致 —— 非空、每段都是正整数、区间的起点不大于终点。
 */
import { computed, ref, watch } from 'vue'
import fluentDialog from '@/components/Fluent/components/dialog/FluentDialog.vue'
import lineEdit from '@/components/Fluent/components/widgets/line_edit/LineEdit.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import { t } from '@/i18n'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  close: []
  select: [numbers: number[]]
}>()

const text = ref('')
const error = ref('')

watch(
  () => props.open,
  (open) => {
    if (open) {
      text.value = ''
      error.value = ''
    }
  },
)

/** 解析成序号列表。返回 null 表示格式不对，错误说明写在 error 里 */
const parsed = computed<number[] | null>(() => {
  const raw = text.value.trim()

  if (!raw) {
    return null
  }

  const numbers: number[] = []

  for (const part of raw.split(',')) {
    const piece = part.trim()

    if (!piece) {
      return null
    }

    if (piece.includes('-')) {
      const [start, end] = piece.split('-').map((value) => value.trim())

      if (!/^\d+$/.test(start) || !/^\d+$/.test(end)) {
        return null
      }

      const from = Number(start)
      const to = Number(end)

      if (from <= 0 || to <= 0 || from > to) {
        return null
      }

      for (let n = from; n <= to; n += 1) {
        numbers.push(n)
      }

      continue
    }

    if (!/^\d+$/.test(piece) || Number(piece) <= 0) {
      return null
    }

    numbers.push(Number(piece))
  }

  return numbers
})

function submit() {
  if (!text.value.trim()) {
    error.value = t('parse.batchSelect.empty')

    return
  }

  if (!parsed.value?.length) {
    error.value = t('parse.batchSelect.invalid')

    return
  }

  emit('select', parsed.value)
}
</script>

<template>
  <fluentDialog
    :open="open"
    :title="t('parse.batchSelect.title')"
    width="500px"
    @close="emit('close')"
  >
    <lineEdit
      v-model="text"
      :placeholder="t('parse.batchSelect.placeholder')"
      :aria-label="t('parse.batchSelect.title')"
      @update:model-value="error = ''"
      @submit="submit"
    />

    <p class="tip">{{ t('parse.batchSelect.guide') }}</p>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-else-if="parsed?.length" class="tip">
      {{ t('parse.batchSelect.count', { count: parsed.length }) }}
    </p>

    <template #actions>
      <primaryPushButton :title="t('parse.batchSelect.confirm')" @click="submit" />
      <pushButton :title="t('settings.dialog.cancel')" @click="emit('close')" />
    </template>
  </fluentDialog>
</template>

<style scoped>
.tip {
  margin: 0;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.error {
  margin: 0;
  font-size: 12px;
  color: var(--text-danger);
}
</style>
