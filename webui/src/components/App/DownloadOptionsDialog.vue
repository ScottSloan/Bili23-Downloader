<script setup lang="ts">
// 下载选项
//
// 三步串起来：**摘出勾选的剧集 → 取媒体信息 → 建任务**。
//
// 媒体信息（有哪些画质 / 编码 / 音质可选）必须在建任务之前取：档位是随视频变的，
// 拿全局默认值直接建会得到一个用户没选过的画质。后端的 `/api/preview` 会按候选顺序
// 尝试，首选没权限时自动换下一个 —— 那时 `from_fallback` 为真，**必须提示**，
// 否则用户看到的清晰度其实属于另一个视频。
//
// 这里刻意不复刻 GUI 那个多页签的下载选项对话框：先把主流程跑通，
// 弹幕样式、文件命名那些留给设置页。

import { ref, watch } from 'vue'
import { preview as previewApi, tasks as tasksApi, ApiError } from '@/api'
import type { PreviewResult } from '@/api'
import { t } from '@/i18n'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import transparentCheckBox from '@/components/Fluent/components/widgets/checkbox/TransparentCheckBox.vue'

const props = defineProps<{
  open: boolean
  /** 已勾选的剧集，原样来自解析结果的叶子 */
  episodes: Record<string, unknown>[]
}>()

const emit = defineEmits<{
  close: []
  created: [count: number]
}>()

const loading = ref(false)
const submitting = ref(false)
const error = ref('')
const info = ref<PreviewResult | null>(null)

const videoQuality = ref(0)
const videoCodec = ref(0)
const audioQuality = ref(0)

// 附加内容。默认全关：这是与 GUI 的一处有意差异 —— GUI 那边由用户的全局设置决定，
// 而 Web 端第一次用的人不该被默认下一堆弹幕字幕
const extras = ref({
  danmaku: false,
  subtitle: false,
  cover: false,
  metadata: false,
})

watch(
  () => props.open,
  (open) => {
    if (open) {
      load()
    }
  },
)

async function load() {
  loading.value = true
  error.value = ''
  info.value = null

  try {
    // 候选就是勾选的这些：首选取不到时后端会自动往下换
    const result = await previewApi.media(props.episodes.slice(0, 20))

    info.value = result

    videoQuality.value = firstValue(result.video_quality)
    videoCodec.value = firstValue(result.video_codec)
    audioQuality.value = firstValue(result.audio_quality)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

/**
 * 取第一个档位
 *
 * 后端把 'auto' 放在最前，正是我们想要的默认值。
 * 参数可选是因为模型里这几项有默认值，`unknown` 类型下 TS 会把它推成可能 undefined
 */
function firstValue(map?: Record<string, number>): number {
  const values = Object.values(map ?? {})

  return values.length ? values[0] : 0
}

async function confirm() {
  submitting.value = true
  error.value = ''

  try {
    const result = await tasksApi.create(props.episodes, {
      video_quality_id: videoQuality.value,
      video_codec_id: videoCodec.value,
      audio_quality_id: audioQuality.value,

      // 视频与音频都要：不给的话后端会回落到全局设置，而用户在这个对话框里
      // 看到的档位选择就没有意义了
      download_video_stream: true,
      download_audio_stream: true,

      download_danmaku: extras.value.danmaku,
      download_subtitle: extras.value.subtitle,
      download_cover: extras.value.cover,
      download_metadata: extras.value.metadata,
    })

    // 建出来的可能比请求的少：后端会拦掉重复下载与需要二次解析的。
    // 如实把两个数字都给出去，不然用户会以为「点了没反应」
    emit('created', result.created)
    emit('close')
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : String(e)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div v-if="open" class="mask" @click.self="emit('close')">
    <div class="dialog" role="dialog" aria-modal="true">
      <h2 class="title">{{ t('download.title', { count: episodes.length }) }}</h2>

      <p v-if="loading" class="hint">{{ t('download.loading') }}</p>

      <p v-else-if="error" class="error" role="alert">{{ error }}</p>

      <template v-else-if="info">
        <!-- 信息来自别的视频时必须说清楚，否则用户以为看的是他选的那一集 -->
        <p v-if="info.from_fallback" class="hint warn">
          {{ t('download.fallback', { title: info.episode_title }) }}
        </p>

        <label class="field">
          <span>{{ t('download.videoQuality') }}</span>
          <select v-model.number="videoQuality" class="select">
            <option v-for="(id, name) in info.video_quality" :key="name" :value="id">
              {{ name }}
            </option>
          </select>
        </label>

        <label class="field">
          <span>{{ t('download.videoCodec') }}</span>
          <select v-model.number="videoCodec" class="select">
            <option v-for="(id, name) in info.video_codec" :key="name" :value="id">
              {{ name }}
            </option>
          </select>
        </label>

        <label class="field">
          <span>{{ t('download.audioQuality') }}</span>
          <select v-model.number="audioQuality" class="select">
            <option v-for="(id, name) in info.audio_quality" :key="name" :value="id">
              {{ name }}
            </option>
          </select>
        </label>

        <div class="extras">
          <span class="extras-label">{{ t('download.extras') }}</span>

          <label class="extra">
            <transparentCheckBox v-model:checked="extras.danmaku" />
            <span>{{ t('download.danmaku') }}</span>
          </label>
          <label class="extra">
            <transparentCheckBox v-model:checked="extras.subtitle" />
            <span>{{ t('download.subtitle') }}</span>
          </label>
          <label class="extra">
            <transparentCheckBox v-model:checked="extras.cover" />
            <span>{{ t('download.cover') }}</span>
          </label>
          <label class="extra">
            <transparentCheckBox v-model:checked="extras.metadata" />
            <span>{{ t('download.metadata') }}</span>
          </label>
        </div>
      </template>

      <div class="actions">
        <pushButton :title="t('download.cancel')" @click="emit('close')" />
        <primaryPushButton
          :title="submitting ? t('download.submitting') : t('download.confirm')"
          :disabled="loading || submitting || !info"
          @click="confirm"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(0, 0, 0, 0.35);
  z-index: 100;
}

.dialog {
  width: 360px;
  max-height: 80vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 22px 24px;
  border-radius: 8px;
  background-color: var(--solid-bg-base);
  border: 1px solid var(--card-stroke-default);
}

.title {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary);
}

.hint {
  margin: 0;
  font-size: 12px;
  color: var(--text-secondary);
}

.hint.warn {
  color: var(--text-primary);
  padding: 6px 8px;
  border-radius: 4px;
  background-color: var(--control-fill-secondary);
}

.error {
  margin: 0;
  font-size: 12px;
  color: var(--text-critical, #c42b1c);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: var(--text-primary);
}

/* 原生 select：Fluent 组件里还没有下拉框，先用原生的 —— 它自带键盘可达与无障碍语义，
   自己糊一个反而更容易做丢这些 */
.select {
  padding: 6px 8px;
  border-radius: 5px;
  font-size: 13px;
  color: var(--text-primary);
  background-color: var(--control-fill-default);
  border: 1px solid var(--control-stroke-default);
}

.extras {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 12px;
  font-size: 13px;
  color: var(--text-primary);
}

.extras-label {
  width: 100%;
  color: var(--text-secondary);
  font-size: 12px;
}

.extra {
  display: flex;
  align-items: center;
  gap: 2px;
  cursor: pointer;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 4px;
}
</style>
