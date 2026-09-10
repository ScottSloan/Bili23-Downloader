<script setup lang="ts">
/**
 * 确定前的提醒
 *
 * 对应桌面版那两个 `MessageBox`：「只下视频流会没有声音」「没开合并会得到两个文件」，
 * 以及「什么都没选」那个只有确定按钮的。
 *
 * 这些提醒是这个对话框最有价值的部分之一 —— 它们拦住的都是「下完才发现不对」的情况，
 * 而那时文件已经写到磁盘上了
 */
import { t } from '@/i18n'
import fluentDialog from '@/components/Fluent/components/dialog/FluentDialog.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'

withDefaults(
  defineProps<{
    open: boolean
    title: string
    content: string
    /** 只有一个「确定」，用于「什么都没选」那种没得选的情况 */
    okOnly?: boolean
  }>(),
  { okOnly: false },
)

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()
</script>

<template>
  <fluentDialog
    :open="open"
    :title="title"
    width="440px"
    :close-on-mask="false"
    @close="emit('cancel')"
  >
    <p class="content">{{ content }}</p>

    <template #actions>
      <primaryPushButton :title="t('settings.dialog.ok')" @click="emit('confirm')" />
      <pushButton v-if="!okOnly" :title="t('settings.dialog.cancel')" @click="emit('cancel')" />
    </template>
  </fluentDialog>
</template>

<style scoped>
.content {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary);
  /* 原文里的空行是分段用的，保留 */
  white-space: pre-line;
}
</style>
