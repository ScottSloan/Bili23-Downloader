<script setup lang="ts">
/**
 * 底部那排「将会下载：视频 音频 弹幕…」
 *
 * 对应桌面版 `gui/dialog/download_options/preview.py` 的 `DownloadPreviewBar`。
 * 七种可下载内容各一个颜色，勾掉的标签直接不显示；一个都不剩时换成灰色的占位标签
 * —— 那是这条预览条最有用的一刻：它当场告诉用户「这么点下去什么都不会下」。
 *
 * 颜色照抄桌面版那份 tag_info，一个都不改：两边并排看的时候，颜色是最先被认出来的东西
 */
import { computed } from 'vue'
import { t } from '@/i18n'
import tagLabel from '@/components/Fluent/components/widgets/label/TagLabel.vue'

const props = defineProps<{
  /** 各类内容要不要下载，键与桌面版 get_download_preview() 一致 */
  state: Record<string, boolean>
}>()

const TAGS = [
  { key: 'video', color: '#0078D4' },
  { key: 'audio', color: '#13A10E' },
  { key: 'danmaku', color: '#8764B8' },
  { key: 'subtitle', color: '#DA6A1E' },
  { key: 'cover', color: '#00B7C3' },
  { key: 'chapter', color: '#EF6950' },
  { key: 'metadata', color: '#C239B3' },
]

const visible = computed(() => TAGS.filter((tag) => props.state[tag.key]))
</script>

<template>
  <div class="preview-bar">
    <span class="tip">{{ t('downloadOptions.preview.willDownload') }}</span>

    <tagLabel
      v-for="tag in visible"
      :key="tag.key"
      :text="t(`downloadOptions.preview.${tag.key}`)"
      :color="tag.color"
    />

    <tagLabel
      v-if="!visible.length"
      :text="t('downloadOptions.preview.nothing')"
      color="#8A8A8A"
    />
  </div>
</template>

<style scoped>
.preview-bar {
  display: flex;
  align-items: center;
  /* 桌面版是 QHBoxLayout 的 spacing 4 */
  gap: 4px;
  flex-wrap: wrap;
  min-width: 0;
}

/* 对应桌面版的 TipCaptionLabel：比正文小一号、用次级灰 */
.tip {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
  margin-right: 2px;
}
</style>
