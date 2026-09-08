<script setup lang="ts">
/**
 * 退出 WebUI 会话
 *
 * **退的是这个网页的登录，不是 B 站账号** —— 两者都叫「登录」，界面上必须说清楚，
 * 否则用户会以为一点就把 B 站账号也退掉了（`authStore` 的注释里记着同一件事）。
 *
 * 要确认这一步：口令是首次启动时**只打印一次**的随机串，误点之后用户手上多半
 * 没有那串东西，代价远不止「再登一次」。
 */
import fluentDialog from '@/components/Fluent/components/dialog/FluentDialog.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import { t } from '@/i18n'

defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  close: []
  confirm: []
}>()
</script>

<template>
  <fluentDialog :open="open" :title="t('user.logoutTitle')" width="440px" @close="emit('close')">
    <template #hint>{{ t('user.logoutHint') }}</template>

    <template #actions>
      <primaryPushButton :title="t('user.logoutConfirm')" @click="emit('confirm')" />
      <pushButton :title="t('settings.dialog.cancel')" @click="emit('close')" />
    </template>
  </fluentDialog>
</template>
