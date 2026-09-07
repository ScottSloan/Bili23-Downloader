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
import { t, mediaLabel } from '@/i18n'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import transparentCheckBox from '@/components/Fluent/components/widgets/checkbox/TransparentCheckBox.vue'
import comboBox from '@/components/Fluent/components/widgets/combo_box/ComboBox.vue'
import fluentDialog from '@/components/Fluent/components/dialog/FluentDialog.vue'

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
 * 后端给的是 {档位名: id}，ComboBox 要的是 [{value, label}]
 *
 * **档位名用前端自己那份翻译**（D12）：后端那些名字来自 `Translator`，
 * 而服务端进程里没装 Qt 的翻译函数，拿到的一律是英文（`8K UHD`）。
 * 认不出的 id 才回落到后端给的名字 —— B 站加新档位时至少还看得懂
 */
function toOptions(group: string, map?: Record<string, number>) {
  return Object.entries(map ?? {}).map(([label, value]) => ({
    value,
    label: mediaLabel(group, value, label),
  }))
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
  <fluentDialog
    :open="open"
    :title="t('download.title', { count: episodes.length })"
    width="360px"
    @close="emit('close')"
  >
    <p v-if="loading" class="hint">{{ t('download.loading') }}</p>

    <p v-else-if="error" class="error" role="alert">{{ error }}</p>

    <template v-else-if="info">
      <!-- 信息来自别的视频时必须说清楚，否则用户以为看的是他选的那一集 -->
      <p v-if="info.from_fallback" class="hint warn">
        {{ t('download.fallback', { title: info.episode_title }) }}
      </p>

      <label class="field">
        <span>{{ t('download.videoQuality') }}</span>
        <comboBox
          v-model="videoQuality"
          :options="toOptions('video_quality', info.video_quality)"
          :label="t('download.videoQuality')"
        />
      </label>

      <label class="field">
        <span>{{ t('download.videoCodec') }}</span>
        <comboBox
          v-model="videoCodec"
          :options="toOptions('video_codec', info.video_codec)"
          :label="t('download.videoCodec')"
        />
      </label>

      <label class="field">
        <span>{{ t('download.audioQuality') }}</span>
        <comboBox
          v-model="audioQuality"
          :options="toOptions('audio_quality', info.audio_quality)"
          :label="t('download.audioQuality')"
        />
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

    <template #actions>
      <pushButton :title="t('download.cancel')" @click="emit('close')" />
      <primaryPushButton
        :title="submitting ? t('download.submitting') : t('download.confirm')"
        :disabled="loading || submitting || !info"
        @click="confirm"
      />
    </template>
  </fluentDialog>
</template>

<style scoped>
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
  color: var(--text-danger);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: var(--text-primary);
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
</style>
