<script setup lang="ts">
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
