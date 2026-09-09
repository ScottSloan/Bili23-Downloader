<script setup lang="ts">
/**
 * Cookie 登录
 *
 * 对应桌面版 `gui/dialog/login.py` 的 `CookieLoginDialog`：一个输入框、一句格式说明，
 * 确定时**先校验再关**（那边 `validate()` 返回 False 挡住关闭，等接口回来才 accept）。
 *
 * 校验不通过时后端不会把无效 Cookie 留在 client 上（`session.login_with_cookie` 会回滚），
 * 所以这里失败只需把话说清楚，不用做任何清理。
 */
import { ref, watch } from 'vue'
import fluentDialog from '@/components/Fluent/components/dialog/FluentDialog.vue'
import lineEdit from '@/components/Fluent/components/widgets/line_edit/LineEdit.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import { login, ApiError } from '@/api'
import { t } from '@/i18n'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  close: []
  success: []
}>()

const text = ref('')
const error = ref('')
const submitting = ref(false)

watch(
  () => props.open,
  (open) => {
    if (open) {
      text.value = ''
      error.value = ''
      submitting.value = false
    }
  },
)

async function submit() {
  if (submitting.value) {
    return
  }

  if (!text.value.trim()) {
    error.value = t('login.cookie.empty')

    return
  }

  submitting.value = true
  error.value = ''

  try {
    await login.withCookie(text.value.trim())

    emit('success')
  } catch (e) {
    // 后端把「格式不对 / 缺 SESSDATA / 验证不过」都判成 400 并附一句话，原样显示
    error.value = e instanceof ApiError && e.message ? e.message : t('login.cookie.failed')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <fluentDialog
    :open="open"
    :title="t('login.cookie.title')"
    width="560px"
    @close="emit('close')"
  >
    <template #hint>{{ t('login.cookie.hint') }}</template>

    <lineEdit
      v-model="text"
      placeholder="SESSDATA=xxx;bili_jct=xxx;DedeUserID=xxx;DedeUserID__ckMd5=xxx"
      :aria-label="t('login.cookie.title')"
      @update:model-value="error = ''"
      @submit="submit"
    />

    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <template #actions>
      <primaryPushButton
        :title="submitting ? t('login.cookie.submitting') : t('login.cookie.confirm')"
        :disabled="submitting"
        @click="submit"
      />
      <pushButton :title="t('settings.dialog.cancel')" @click="emit('close')" />
    </template>
  </fluentDialog>
</template>

<style scoped>
.error {
  margin: 0;
  font-size: 12px;
  color: var(--text-danger);
}
</style>
