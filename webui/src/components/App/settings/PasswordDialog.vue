<script setup lang="ts">
/**
 * 修改 WebUI 登录口令
 *
 * 桌面版没有对应物 —— 那边没有服务端，也就没有会话口令这回事。
 *
 * 口令 hash 存在 `config.json` 的 `webui_password_hash` 里，但**它不在
 * `/api/settings` 的白名单中**（机密一律不下发），所以这一项不能像别的设置那样
 * 「读出来改一改再存回去」，只能走一条专用接口：带旧口令去换新的。
 *
 * 改成功后后端会**清掉包括当前这个在内的所有会话**，再给我们发一个新 cookie。
 * 也就是说这台机器上不用重新登录，其他设备要。这里把这件事明说，
 * 否则用户会以为是自己把哪儿点坏了
 */
import { ref, watch } from 'vue'
import fluentDialog from '@/components/Fluent/components/dialog/FluentDialog.vue'
import lineEdit from '@/components/Fluent/components/widgets/line_edit/LineEdit.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import { auth, ApiError } from '@/api'
import { useToastStore } from '@/stores/toastStore'
import { t } from '@/i18n'

/** 与后端 `MIN_PASSWORD_LENGTH` 对齐。前端先拦一道，省一个来回 */
const MIN_LENGTH = 8

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const toast = useToastStore()

const current = ref('')
const next = ref('')
const repeat = ref('')
const error = ref('')
const submitting = ref(false)

watch(
  () => props.open,
  (open) => {
    if (open) {
      current.value = ''
      next.value = ''
      repeat.value = ''
      error.value = ''
      submitting.value = false
    }
  },
)

async function submit() {
  if (submitting.value) {
    return
  }

  if (!current.value || !next.value) {
    error.value = t('settings.password.empty')

    return
  }

  if (next.value.length < MIN_LENGTH) {
    error.value = t('settings.password.tooShort', { count: MIN_LENGTH })

    return
  }

  if (next.value !== repeat.value) {
    error.value = t('settings.password.mismatch')

    return
  }

  submitting.value = true
  error.value = ''

  try {
    await auth.changePassword(current.value, next.value)

    toast.success(t('settings.password.done'), t('settings.password.doneDetail'))

    emit('close')
  } catch (e) {
    // 后端对「旧口令不对」「新旧相同」「失败太多次」各带一个 code，
    // client.ts 已经按 `error.code.<CODE>` 查过前端的译文了，这里直接显示
    error.value = e instanceof ApiError && e.message ? e.message : t('settings.password.failed')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <fluentDialog
    :open="open"
    :title="t('settings.password.title')"
    width="480px"
    @close="emit('close')"
  >
    <template #hint>{{ t('settings.password.hint') }}</template>

    <label class="field">
      <span class="field-label">{{ t('settings.password.current') }}</span>
      <lineEdit
        v-model="current"
        type="password"
        autocomplete="current-password"
        :aria-label="t('settings.password.current')"
        @update:model-value="error = ''"
      />
    </label>

    <label class="field">
      <span class="field-label">{{ t('settings.password.new') }}</span>
      <lineEdit
        v-model="next"
        type="password"
        autocomplete="new-password"
        :aria-label="t('settings.password.new')"
        @update:model-value="error = ''"
      />
    </label>

    <label class="field">
      <span class="field-label">{{ t('settings.password.repeat') }}</span>
      <lineEdit
        v-model="repeat"
        type="password"
        autocomplete="new-password"
        :aria-label="t('settings.password.repeat')"
        @update:model-value="error = ''"
        @submit="submit"
      />
    </label>

    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <template #actions>
      <primaryPushButton
        :title="submitting ? t('settings.password.submitting') : t('settings.dialog.save')"
        :disabled="submitting"
        @click="submit"
      />
      <pushButton :title="t('settings.dialog.cancel')" @click="emit('close')" />
    </template>
  </fluentDialog>
</template>

<style scoped>
.field {
  display: flex;
  align-items: center;
  gap: 12px;
}

.field-label {
  flex: 0 0 auto;
  width: 90px;
  font-size: 14px;
  color: var(--text-primary);
}

/* 输入框吃满剩下的宽度。<input> 有自己的固有宽度，不写 min-width: 0 会被它撑住 */
.field :deep(input) {
  min-width: 0;
  width: 100%;
}

.error {
  margin: 0;
  font-size: 12px;
  color: var(--text-danger);
}
</style>
