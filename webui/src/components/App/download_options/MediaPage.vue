<script setup lang="ts">
/**
 * 下载选项 · 媒体设置页
 *
 * 对应桌面版 `gui/dialog/download_options/media.py` + `card.py` 的两张卡片：
 * 上面「媒体信息」选画质 / 音质 / 编码并显示所选档位的码率与文件大小，
 * 下面「媒体选项」决定下载哪几路流、要不要合并。
 *
 * ## 这一页的取值不写全局设置
 *
 * 与另外两页不同（那两页改的是 `/api/settings` 里的全局项）。桌面版这八项存在
 * `config.video_quality_id` 这类**纯运行时属性**上 —— 不落盘，进程一关就没。
 * WebUI 是另一个进程、且请求之间无状态，没有对应的地方可存，于是：
 *
 * - **本次下载**：随 `options` 传给建任务接口，只影响这一批
 * - **下次的预选值**：存 localStorage
 *
 * 这是对 D13 的一处有意偏离，理由与 D14（主题各存各的）同源：档位偏好本就更像
 * 每台设备的事，而不该是服务端一个粘在进程上的全局游标。
 *
 * ## 档位不是固定的
 *
 * 有哪些画质可选取决于视频本身与账号权限，所以每次打开都要现查（`/api/preview`）。
 * localStorage 里存的那一档这个视频没有时，回落到「自动」而不是硬选一个
 * —— 否则用户会拿到一个他没选过、也没提示过的画质
 */
import { computed, ref, watch } from 'vue'
import { preview as previewApi, ApiError } from '@/api'
import type { PreviewResult, StreamInfo, StreamPreviewResult } from '@/api'
import { t, mediaLabel } from '@/i18n'
import { useSettingsStore } from '@/stores/settingsStore'
import { formatFileSize } from '@/components/App/download/formatters'
import expandSettingCard from '@/components/Fluent/components/settings/ExpandSettingCard.vue'
import settingGroupRow from '@/components/Fluent/components/settings/SettingGroupRow.vue'
import comboBox from '@/components/Fluent/components/widgets/combo_box/ComboBox.vue'
import switchButton from '@/components/Fluent/components/widgets/switch_button/SwitchButton.vue'
import toolButton from '@/components/Fluent/components/widgets/button/ToolButton.vue'
import priorityDialog from '@/components/App/settings/PriorityDialog.vue'
import cardGuideLink from './CardGuideLink.vue'
import guideDialog from './GuideDialog.vue'

const props = defineProps<{
  /**
   * 媒体信息取自哪几集，按顺序试，首选取不到时后端自动换下一个
   *
   * **与「要下载哪些」是两回事**：这里是「这批内容长什么样」，
   * 由解析结果决定（链接指向的那一集，或列表第一个），与勾选无关 ——
   * 与桌面版 `tree_view.get_preview_candidates()` 同一套规则
   */
  candidates: Record<string, unknown>[]
}>()

const emit = defineEmits<{
  /** 下载内容变了，通知外壳刷新底部预览条 */
  previewChanged: []
}>()

const settingsStore = useSettingsStore()

// ---------------- 本地态 ----------------

const STORAGE_KEY = 'bili23:download-options:media'

/** 三个「自动」档的 id，与后端 `/api/preview/stream` 的默认值一致 */
const AUTO = { video: 200, codec: 20, audio: 30300 }

interface MediaState {
  video_quality_id: number
  video_codec_id: number
  audio_quality_id: number
  download_video_stream: boolean
  download_audio_stream: boolean
  merge_video_audio: boolean
  keep_original_files: boolean
  keep_original_files_type: number
}

function defaults(): MediaState {
  return {
    video_quality_id: AUTO.video,
    video_codec_id: AUTO.codec,
    audio_quality_id: AUTO.audio,
    download_video_stream: true,
    download_audio_stream: true,
    merge_video_audio: true,
    keep_original_files: false,
    keep_original_files_type: 0,
  }
}

/** localStorage 在隐私窗口、禁用站点数据时会直接抛，读写都要兜住 */
function readStored(): MediaState {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)

    return raw ? { ...defaults(), ...(JSON.parse(raw) as Partial<MediaState>) } : defaults()
  } catch {
    return defaults()
  }
}

const state = ref<MediaState>(defaults())

function persist() {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state.value))
  } catch {
    // 存不上就算了，只是下次的预选值回到默认，不影响本次下载
  }
}

// ---------------- 媒体信息 ----------------

const loading = ref(false)
const error = ref('')
const info = ref<PreviewResult | null>(null)

const videoStream = ref<StreamInfo | null>(null)
const audioStream = ref<StreamInfo | null>(null)
const streamLoading = ref(false)

/**
 * 正在飞的那次流详情请求
 *
 * 用户连着换三次画质就会发三次，而后端那边是**串行处理**的（预览要独占全局的
 * PreviewerInfo）。不取消的话，先发的那次可能后回来，把界面刷成上一个档位的信息
 */
let streamAbort: AbortController | null = null

/** 信息实际取自哪一集。回退发生时不是 episodes[0]，查流详情必须用同一个 */
const sourceEpisode = computed(() => props.candidates[info.value?.candidate_index ?? 0])

async function load() {
  loading.value = true
  error.value = ''
  info.value = null
  videoStream.value = null
  audioStream.value = null

  state.value = readStored()

  // 还没解析过，没有东西可预览。档位是随视频变的，凭空列一份出来只会误导 ——
  // 这时三个下拉留空并禁用，下面那几个媒体选项照常能改（它们与视频无关）
  if (!props.candidates.length) {
    loading.value = false

    return
  }

  try {
    const result = await previewApi.media(props.candidates.slice(0, 20))

    info.value = result

    // 存下来的那一档这个视频不一定有，没有就回落「自动」
    state.value.video_quality_id = pick(
      result.video_quality,
      state.value.video_quality_id,
      AUTO.video,
    )
    state.value.video_codec_id = pick(result.video_codec, state.value.video_codec_id, AUTO.codec)
    state.value.audio_quality_id = pick(
      result.audio_quality,
      state.value.audio_quality_id,
      AUTO.audio,
    )

    await loadStream()
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

/** 存下来的档位还在不在。不在就用「自动」，再不行取第一个 */
function pick(map: Record<string, number> | undefined, wanted: number, auto: number): number {
  const values = Object.values(map ?? {})

  if (values.includes(wanted)) {
    return wanted
  }

  return values.includes(auto) ? auto : (values[0] ?? auto)
}

async function loadStream() {
  const episode = sourceEpisode.value

  if (!episode || info.value?.need_parse === false) {
    return
  }

  streamAbort?.abort()

  const controller = new AbortController()

  streamAbort = controller
  streamLoading.value = true

  try {
    const result: StreamPreviewResult = await previewApi.stream(
      episode,
      {
        video_quality_id: state.value.video_quality_id,
        video_codec_id: state.value.video_codec_id,
        audio_quality_id: state.value.audio_quality_id,
      },
      controller.signal,
    )

    // 期间又换了一次档位：这次的结果已经过期，丢掉
    if (streamAbort !== controller) {
      return
    }

    videoStream.value = result.video ?? null
    audioStream.value = result.audio ?? null
  } catch (e) {
    if (streamAbort !== controller) {
      return
    }

    // 流详情取不到只影响那几行说明文字，不该把整页变成错误页 ——
    // 用户仍然可以选档位并下载（后端会按同一套优先级去挑）
    videoStream.value = null
    audioStream.value = null

    if (!(e instanceof DOMException && e.name === 'AbortError')) {
      console.warn('获取流详情失败', e)
    }
  } finally {
    if (streamAbort === controller) {
      streamLoading.value = false
      streamAbort = null
    }
  }
}

// ---------------- 选项联动（与桌面版逐条对齐）----------------

/**
 * 两路流都下才谈得上合并
 *
 * 桌面版 `on_change_download_stream_options`：只下一路时把「合并」置灰**并强制取消勾选**，
 * 两路都在时则强制勾上。照抄，包括那个「强制」—— 它避免了「合并开着却只有一路流」
 * 这种下载到一半才发现的状态
 */
function onStreamChanged() {
  const both = state.value.download_video_stream && state.value.download_audio_stream

  state.value.merge_video_audio = both

  if (!both) {
    state.value.keep_original_files = false
  }

  emit('previewChanged')
}

function onMergeChanged() {
  if (!state.value.merge_video_audio) {
    state.value.keep_original_files = false
  }
}

const canMerge = computed(
  () => state.value.download_video_stream && state.value.download_audio_stream,
)

const canKeepOriginal = computed(() => canMerge.value && state.value.merge_video_audio)

// ---------------- 描述文字 ----------------

const sourceDescription = computed(() => {
  if (loading.value) {
    return t('downloadOptions.media.fetching')
  }

  if (error.value) {
    return error.value
  }

  if (!props.candidates.length) {
    return t('downloadOptions.media.noEpisodes')
  }

  const title = info.value?.episode_title || t('downloadOptions.media.unknown')
  const number = info.value?.episode_number ?? ''

  const body = info.value?.from_fallback
    ? t('downloadOptions.media.fromFallback', { title })
    : title

  return number === '' ? body : `#${number} - ${body}`
})

/** 码率的写法与 `util/format/units.py` 的 format_bitrate 对齐：**1000 进制**、两位小数 */
function formatBitrate(bitrate: number): string {
  if (!bitrate) {
    return ''
  }

  const units = ['bps', 'Kbps', 'Mbps', 'Gbps', 'Tbps']

  let value = bitrate
  let index = 0

  while (value >= 1000 && index < units.length - 1) {
    value /= 1000
    index += 1
  }

  return `${value.toFixed(2)} ${units[index]}`
}

function formatFrameRate(raw: string): string {
  const value = Number.parseFloat(raw)

  return Number.isFinite(value) && value ? `${value.toFixed(1)} fps` : ''
}

function join(parts: (string | undefined | false)[]): string {
  return parts.filter(Boolean).join(', ')
}

const videoDescription = computed(() => {
  if (streamLoading.value) {
    return t('downloadOptions.media.fetching')
  }

  const stream = videoStream.value

  if (!stream) {
    return t('downloadOptions.media.videoAuto')
  }

  const container = info.value?.media_type

  return join([
    mediaLabel('video_quality', stream.quality_id, t('downloadOptions.media.unknownQuality')),
    formatFrameRate(stream.frame_rate ?? ''),
    formatBitrate(stream.bitrate ?? 0),
    formatFileSize(stream.file_size ?? 0),
    container === 'mp4' && 'MP4',
    container === 'flv' && 'FLV',
    // mp4 / flv 的响应可能只给试看片段，这时必须说出来
    stream.is_full_video === false && t('downloadOptions.media.previewOnly'),
  ])
})

const audioDescription = computed(() => {
  if (streamLoading.value) {
    return t('downloadOptions.media.fetching')
  }

  const stream = audioStream.value

  if (!stream) {
    // 音频流为空的原因不止一种，与桌面版 on_query_audio_info 一致地区分
    switch (info.value?.media_type) {
      case 'dash':
        return t('downloadOptions.media.noAudioTrack')

      case 'mp4':
      case 'flv':
        return t('downloadOptions.media.audioEmbedded')

      default:
        return t('downloadOptions.media.audioAuto')
    }
  }

  return join([
    mediaLabel('audio_quality', stream.quality_id, t('downloadOptions.media.unknownQuality')),
    stream.codec ?? '',
    formatBitrate(stream.bitrate ?? 0),
    formatFileSize(stream.file_size ?? 0),
  ])
})

const codecDescription = computed(() => {
  if (streamLoading.value) {
    return t('downloadOptions.media.fetching')
  }

  const stream = videoStream.value

  if (!stream) {
    return t('downloadOptions.media.codecAuto')
  }

  const tipKey = `downloadOptions.media.codecTip.${stream.codec_id}`
  const tip = t(tipKey)

  return join([
    mediaLabel('video_codec', stream.codec_id, t('downloadOptions.media.unknownCodec')),
    // 认不出的编码没有配套说明，t() 取不到时会原样返回 key，那不能显示出去
    tip === tipKey ? '' : tip,
  ])
})

// ---------------- 下拉选项 ----------------

/** 后端给的是 {显示名: id}，且那些名字是英文（服务端没有 Qt 翻译函数），前端自己翻（D12） */
function toOptions(group: string, map?: Record<string, number>) {
  return Object.entries(map ?? {}).map(([label, value]) => ({
    value,
    label: mediaLabel(group, value, label),
  }))
}

const videoOptions = computed(() => toOptions('video_quality', info.value?.video_quality))
const audioOptions = computed(() => toOptions('audio_quality', info.value?.audio_quality))
const codecOptions = computed(() => toOptions('video_codec', info.value?.video_codec))

const keepTypeOptions = computed(() =>
  [0, 1, 2].map((value) => ({
    value,
    label: t(`downloadOptions.media.keepType.${value}`),
  })),
)

// ---------------- 优先级编辑器 ----------------

// 与设置页共用同一个对话框与同一份候选表。改完立刻重查一次流详情：
// 当前选的是「自动」时，优先级一改，实际会挑中的档位就变了
const priorityAttr = ref<string | null>(null)

const PRIORITY_CHOICES: Record<string, 'video_quality' | 'audio_quality' | 'video_codec'> = {
  video_quality_priority: 'video_quality',
  audio_quality_priority: 'audio_quality',
  video_codec_priority: 'video_codec',
}

const priorityChoices = computed(() => {
  const group = priorityAttr.value ? PRIORITY_CHOICES[priorityAttr.value] : null
  const raw = group ? settingsStore.choices?.[group] : null

  return Array.isArray(raw)
    ? raw.map((entry) => ({
        value: entry.value as number,
        label: mediaLabel(group as string, entry.value as number, String(entry.label)),
      }))
    : []
})

function savePriority(value: (number | string)[]) {
  if (!priorityAttr.value) {
    return
  }

  settingsStore.set(priorityAttr.value, value as never)

  priorityAttr.value = null

  void loadStream()
}

// ---------------- 说明 ----------------

const guide = ref<'mediaInfo' | 'mediaOptions' | null>(null)

// ---------------- 对外 ----------------

watch(
  () => [state.value.video_quality_id, state.value.video_codec_id, state.value.audio_quality_id],
  () => void loadStream(),
)

defineExpose({
  load,

  /** 底部预览条要的那两项 */
  downloadPreview: () => ({
    video: state.value.download_video_stream,
    audio: state.value.download_audio_stream,
  }),

  hasMediaToDownload: () =>
    state.value.download_video_stream || state.value.download_audio_stream,

  /** 建任务时随 options 一起传的部分 */
  options: () => ({ ...state.value }),

  /** 确定时把这次的选择记成下次的预选值 */
  save: persist,

  state,
})
</script>

<template>
  <div class="media-page">
    <expandSettingCard
      icon="info"
      :title="t('downloadOptions.media.infoTitle')"
      :description="t('downloadOptions.media.infoDesc')"
      default-expanded
    >
      <!-- 「关于媒体信息」在桌面版是跟在卡片说明后面的，不是展开区里的一行 -->
      <template #link>
        <cardGuideLink :text="t('downloadOptions.media.aboutInfo')" @click="guide = 'mediaInfo'" />
      </template>

      <settingGroupRow
        icon="movie"
        :title="t('downloadOptions.media.source')"
        :description="sourceDescription"
      />

      <settingGroupRow
        icon="video"
        :title="t('downloadOptions.media.videoQuality')"
        :description="videoDescription"
      >
        <comboBox
          v-model="state.video_quality_id"
          :options="videoOptions"
          :disabled="loading || !videoOptions.length"
          :label="t('downloadOptions.media.videoQuality')"
        />
        <toolButton
          icon="setting"
          :label="t('downloadOptions.media.customPriority')"
          @click="priorityAttr = 'video_quality_priority'"
        />
      </settingGroupRow>

      <settingGroupRow
        icon="music"
        :title="t('downloadOptions.media.audioQuality')"
        :description="audioDescription"
      >
        <comboBox
          v-model="state.audio_quality_id"
          :options="audioOptions"
          :disabled="loading || !audioOptions.length"
          :label="t('downloadOptions.media.audioQuality')"
        />
        <toolButton
          icon="setting"
          :label="t('downloadOptions.media.customPriority')"
          @click="priorityAttr = 'audio_quality_priority'"
        />
      </settingGroupRow>

      <settingGroupRow
        icon="code"
        :title="t('downloadOptions.media.videoCodec')"
        :description="codecDescription"
      >
        <comboBox
          v-model="state.video_codec_id"
          :options="codecOptions"
          :disabled="loading || !codecOptions.length"
          :label="t('downloadOptions.media.videoCodec')"
        />
        <toolButton
          icon="setting"
          :label="t('downloadOptions.media.customPriority')"
          @click="priorityAttr = 'video_codec_priority'"
        />
      </settingGroupRow>

    </expandSettingCard>

    <expandSettingCard
      icon="options"
      :title="t('downloadOptions.media.optionsTitle')"
      :description="t('downloadOptions.media.optionsDesc')"
    >
      <template #link>
        <cardGuideLink
          :text="t('downloadOptions.media.aboutOptions')"
          @click="guide = 'mediaOptions'"
        />
      </template>

      <settingGroupRow
        :title="t('downloadOptions.media.downloadVideo')"
        :description="t('downloadOptions.media.downloadVideoDesc')"
      >
        <switchButton
          v-model="state.download_video_stream"
          :label="t('downloadOptions.media.downloadVideo')"
          @update:model-value="onStreamChanged"
        />
      </settingGroupRow>

      <settingGroupRow
        :title="t('downloadOptions.media.downloadAudio')"
        :description="t('downloadOptions.media.downloadAudioDesc')"
      >
        <switchButton
          v-model="state.download_audio_stream"
          :label="t('downloadOptions.media.downloadAudio')"
          @update:model-value="onStreamChanged"
        />
      </settingGroupRow>

      <settingGroupRow
        :title="t('downloadOptions.media.merge')"
        :description="t('downloadOptions.media.mergeDesc')"
        :disabled="!canMerge"
      >
        <switchButton
          v-model="state.merge_video_audio"
          :disabled="!canMerge"
          :label="t('downloadOptions.media.merge')"
          @update:model-value="onMergeChanged"
        />
      </settingGroupRow>

      <settingGroupRow
        :title="t('downloadOptions.media.keepOriginal')"
        :description="t('downloadOptions.media.keepOriginalDesc')"
        :disabled="!canKeepOriginal"
      >
        <switchButton
          v-model="state.keep_original_files"
          :disabled="!canKeepOriginal"
          :label="t('downloadOptions.media.keepOriginal')"
        />
      </settingGroupRow>

      <settingGroupRow
        :title="t('downloadOptions.media.keepOriginalType')"
        :description="t('downloadOptions.media.keepOriginalTypeDesc')"
        :disabled="!canKeepOriginal || !state.keep_original_files"
      >
        <comboBox
          v-model="state.keep_original_files_type"
          :options="keepTypeOptions"
          :disabled="!canKeepOriginal || !state.keep_original_files"
          :label="t('downloadOptions.media.keepOriginalType')"
        />
      </settingGroupRow>

    </expandSettingCard>

    <priorityDialog
      :open="priorityAttr !== null"
      :title="priorityAttr ? t(`settings.label.${priorityAttr}`) : ''"
      :choices="priorityChoices"
      :value="(settingsStore.value(priorityAttr ?? '') as (number | string)[]) ?? []"
      @close="priorityAttr = null"
      @save="savePriority"
    />

    <guideDialog
      :open="guide !== null"
      :title="t('downloadOptions.guideTitle')"
      :content="guide ? t(`downloadOptions.guide.${guide}`) : ''"
      @close="guide = null"
    />
  </div>
</template>

<style scoped>
.media-page {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
</style>
