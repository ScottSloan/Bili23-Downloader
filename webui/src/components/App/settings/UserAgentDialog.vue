<script setup lang="ts">
/**
 * 自定义 User-Agent
 *
 * 对应桌面版 `gui/dialog/setting/user_agent.py`。那边也是一个对话框而不是设置页上的
 * 输入框 —— UA 串又长又不该误碰，摆在卡片右边既显示不全，改一半失焦还会存进去。
 *
 * 校验与桌面版同一条：不能为空。
 */
import { ref, watch } from 'vue'
import fluentDialog from '@/components/Fluent/components/dialog/FluentDialog.vue'
import lineEdit from '@/components/Fluent/components/widgets/line_edit/LineEdit.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import { t } from '@/i18n'

const props = defineProps<{
  open: boolean
  value: string
  /** 后端下发的默认值，「恢复默认」用它 */
  defaultValue: string
}>()

const emit = defineEmits<{
  close: []
  save: [value: string]
}>()

const draft = ref('')
const error = ref('')

watch(
  () => props.open,
  (open) => {
    if (open) {
      draft.value = props.value
      error.value = ''
    }
  },
)

function submit() {
  const text = draft.value.trim()

  if (!text) {
    error.value = t('settings.userAgent.empty')

    return
  }

  emit('save', text)
}
</script>

<template>
  <fluentDialog
    :open="open"
    :title="t('settings.userAgent.title')"
    width="640px"
    @close="emit('close')"
  >
    <lineEdit
      v-model="draft"
      :placeholder="t('settings.userAgent.placeholder')"
      :aria-label="t('settings.userAgent.title')"
      @update:model-value="error = ''"
      @submit="submit"
    />

    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <div class="bar">
      <pushButton
        :title="t('settings.userAgent.reset')"
        :disabled="!defaultValue || draft === defaultValue"
        @click="
          () => {
            draft = defaultValue
            error = ''
          }
        "
      />
    </div>

    <template #actions>
      <primaryPushButton :title="t('settings.dialog.save')" @click="submit" />
      <pushButton :title="t('settings.dialog.cancel')" @click="emit('close')" />
    </template>
  </fluentDialog>
</template>

<style scoped>
.bar {
  display: flex;
  justify-content: flex-start;
}

.error {
  margin: 0;
  font-size: 12px;
  color: var(--text-danger);
}
</style>
