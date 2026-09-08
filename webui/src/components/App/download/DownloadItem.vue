<script setup lang="ts">
/**
 * 下载列表里的一行
 *
 * 对着桌面版 `gui/component/download_list/item_delegate.py` 的 `UIRect` 逐项抄的：
 *
 * | | 值 | 出处 |
 * |---|---|---|
 * | 行高 | 100 | `sizeHint` |
 * | 四周留白 | 10 | `UIRect.margin` |
 * | 封面 | 144×80，圆角 5 | `getCoverRect` / `_drawPixmap` |
 * | 封面到标题 | 20 | `spacer = margin * 2` |
 * | 标题 | 14px | `_drawText` |
 * | 信息 / 大小 / 状态 | 14px，次级灰 | `_drawDescriptionText` |
 * | 进度条 | 宽 200、高 16 的槽，条本身 4px | `getProgressBarRect` / `_drawProgressBar` |
 * | 两个按钮 | 32×32，圆角 5 | `UIRect.buttonSize` |
 *
 * 桌面版整行是画出来的，没有卡片底色，只有悬停 / 选中时那层薄薄的灰
 * （`_drawBackground`，圆角 5）。**这边此前是一张带边框的卡片**，那是最显眼的一处不像。
 *
 * 封面**由浏览器直接加载**：桌面版把它取下来存进 thumbnail.db 是为了 QPixmap，
 * 而 QPixmap 交不给浏览器。页面带 referrer=no-referrer，B 站图床不会拒。
 */
import { computed, ref, watch } from 'vue'
import type { TaskView } from '@/api'
import fluentCheckBox from '@/components/Fluent/components/widgets/checkbox/CheckBox.vue'
import toolButton from '@/components/Fluent/components/widgets/button/ToolButton.vue'
import IconApp from '@/components/Fluent/icons/IconApp.vue'
import { t, mediaLabel } from '@/i18n'
import { formatFileSize, formatSpeed, formatTimestamp } from './formatters'

const props = defineProps<{
  task: TaskView
  selected: boolean
}>()

const emit = defineEmits<{
  'update:selected': [value: boolean]
  action: []
  remove: []
}>()

// 封面取不回来时才画占位图。换了任务要复位，否则一次失败会让这一行永远显示占位
const coverFailed = ref(false)

watch(
  () => props.task.cover,
  () => {
    coverFailed.value = false
  },
)

const isCompleted = computed(() => props.task.status === 'completed')
const isFailed = computed(
  () => props.task.status === 'failed' || props.task.status === 'ffmpeg_failed',
)
const isPaused = computed(() => props.task.status === 'paused')

/**
 * 左下角那行媒体信息
 *
 * 桌面版 `getInfoText`：完成了显示完成时间，否则显示 `info_label`。
 * **`info_label` 不能直接用** —— 服务端进程里没有 Qt 的翻译函数，
 * 画质那一档拼出来是英文（D12）。所以带视频流的任务这边按 `video_quality_id`
 * 自己查译文，只有 MP4 / FLV / 「附加内容」这类固定文案才落回后端给的那份
 */
const infoText = computed(() => {
  if (isCompleted.value) {
    return formatTimestamp(props.task.completed_time)
  }

  // 200 是「按优先级自动选择」，那不是一档画质 —— 真正下到哪一档要等解析完才知道。
  // 桌面版这时候 info_label 也是空的，跟着空着即可
  if (props.task.video_quality_id && props.task.video_quality_id !== 200) {
    return mediaLabel('video_quality', props.task.video_quality_id, props.task.info_label)
  }

  return props.task.info_label
})

const sizeText = computed(() => {
  const total = props.task.total_size

  if (!total) {
    return ''
  }

  // 已经下完、进了 FFmpeg 那几档只显示总大小，不再显示「已下 / 共」
  const settled = ['completed', 'ffmpeg_queued', 'merging', 'converting', 'ffmpeg_failed']

  if (settled.includes(props.task.status)) {
    return formatFileSize(total)
  }

  return `${formatFileSize(props.task.downloaded_size)} / ${formatFileSize(total)}`
})

/** 桌面版 `getStatusText`：下载中显示速度，其余显示状态名 */
const statusText = computed(() => {
  if (props.task.status === 'downloading') {
    return formatSpeed(props.task.speed)
  }

  if (props.task.status === 'merging' || props.task.status === 'converting') {
    // FFmpeg 要吐出第一条进度才有百分比可显示，之前只给文案，
    // 免得挂着一个始终停在 0% 的数字
    const key = `task.status.${props.task.status}`

    return props.task.progress > 0
      ? `${t(key)} ${props.task.progress}%`
      : t(key)
  }

  if (props.task.status === 'additional_processing' && props.task.status_label) {
    return props.task.status_label
  }

  return t(`task.status.${props.task.status}`)
})

/**
 * 主按钮的图标，桌面版 `getButtonIcon`
 *
 * 已完成的那一行**没有主按钮**：桌面版那里是「打开文件所在位置」，
 * 浏览器做不到，摆一个点了没反应的按钮更糟。只留删除
 */
const actionIcon = computed(() => {
  switch (props.task.status) {
    case 'queued':
    case 'paused':
    case 'ffmpeg_queued':
      return 'play'

    case 'failed':
    case 'ffmpeg_failed':
      return 'retry'

    default:
      return 'pause'
  }
})

const actionLabel = computed(() => {
  switch (actionIcon.value) {
    case 'play':
      return t('task.resume')

    case 'retry':
      return t('task.retry')

    default:
      return t('task.pause')
  }
})
</script>

<template>
  <div class="download-item" :class="{ 'is-selected': selected }">
    <fluentCheckBox
      class="pick"
      :state="selected ? 2 : 0"
      :label="task.title"
      @change="(value) => emit('update:selected', value)"
    />

    <div class="cover">
      <!-- 加载失败时退回占位图。B 站的旧封面地址会 404，那时一个破图标比空白强。
           两者互斥而不是叠着 —— 叠的话画层顺序一变就会露出下面那个 -->
      <img
        v-if="task.cover && !coverFailed"
        :src="task.cover"
        alt=""
        referrerpolicy="no-referrer"
        loading="lazy"
        @error="coverFailed = true"
      />
      <IconApp v-else class="placeholder" />
    </div>

    <div class="main">
      <div class="title" :title="task.title">{{ task.title }}</div>

      <div class="meta">
        <span class="info">{{ infoText }}</span>
        <span class="size">{{ sizeText }}</span>
      </div>
    </div>

    <div class="right">
      <!-- 完成的任务也画（`_paintItemUI` 里这一笔是无条件的），只是它已经满了 -->
      <div class="progress">
        <span class="track" />
        <span
          class="bar"
          :class="{ 'is-error': isFailed, 'is-paused': isPaused }"
          :style="{ width: `${task.progress}%` }"
        />
      </div>

      <div class="status" :class="{ 'is-error': isFailed }" :title="task.status_label">
        {{ statusText }}
      </div>
    </div>

    <div class="actions">
      <toolButton
        v-if="!isCompleted"
        :icon="actionIcon"
        :label="actionLabel"
        variant="primary"
        @click="emit('action')"
      />
      <toolButton icon="delete" :label="t('task.remove')" @click="emit('remove')" />
    </div>
  </div>
</template>

<style scoped>
.download-item {
  position: relative;
  height: 100px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
  padding: 0 10px;
  border-radius: 5px;
}

/* 悬停 / 选中那层薄灰，取值与 FluentStyledItemDelegate._drawBackground 一致
   （未选中悬停 12/255，选中 17/255，选中且悬停 25/255） */
.download-item:hover {
  background-color: rgba(0, 0, 0, 0.047);
}

.download-item.is-selected {
  background-color: rgba(0, 0, 0, 0.067);
}

.download-item.is-selected:hover {
  background-color: rgba(0, 0, 0, 0.098);
}

:root[data-theme='dark'] .download-item:hover {
  background-color: rgba(255, 255, 255, 0.047);
}

:root[data-theme='dark'] .download-item.is-selected {
  background-color: rgba(255, 255, 255, 0.067);
}

:root[data-theme='dark'] .download-item.is-selected:hover {
  background-color: rgba(255, 255, 255, 0.098);
}

.pick {
  margin-right: 2px;
}

/* ---- 封面 ---- */

.cover {
  position: relative;
  flex: 0 0 auto;
  width: 144px;
  height: 80px;
  border-radius: 5px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  /* 占位底色取自 _drawPixmap 的 QColor(227, 229, 231) */
  background-color: rgb(227, 229, 231);
}

:root[data-theme='dark'] .cover {
  background-color: rgb(60, 60, 60);
}

.cover img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  /* 桌面版是「按比例填满后从中间裁一刀」（KeepAspectRatioByExpanding + copy） */
  object-fit: cover;
}

.cover .placeholder {
  width: 40px;
  height: 40px;
  opacity: 0.55;
}

/* ---- 中间 ---- */

.main {
  flex: 1 1 auto;
  min-width: 0;
  height: 80px;
  display: flex;
  flex-direction: column;
  /* 标题贴上、信息贴下，中间空着 —— 桌面版的标题在封面顶部下 5px，
     信息那行在底边上方 15px */
  justify-content: space-between;
  padding: 5px 10px 5px 10px;
  box-sizing: border-box;
}

.title {
  font-size: 14px;
  line-height: 20px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.meta {
  display: flex;
  flex-direction: row;
  align-items: center;
  font-size: 14px;
  line-height: 20px;
  color: var(--text-secondary);
}

/* 桌面版这两块是定宽的（info 125 / 已完成 175，size 150），
   窄屏上定宽会把标题挤没，所以这里给下限而不是定死 */
.info {
  flex: 0 1 auto;
  min-width: 0;
  max-width: 175px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.size {
  flex: 0 0 auto;
  margin-left: 10px;
  white-space: nowrap;
}

/* ---- 右侧进度与状态 ---- */

/*
  进度条在整行的垂直中线上（`getProgressBarRect` 的 top 是 (height-16)/2），
  状态文字则与左边那行信息同高（`getStatusRect` 的 top 取自 infoRect）。
  用 flex 排不出这个关系 —— 两者的基准不是同一个，所以直接定位
*/
.right {
  position: relative;
  flex: 0 0 auto;
  width: 200px;
  /* 整行高，两个元素各自按行内的绝对位置摆 */
  height: 100%;
}

/* top 40 = (100 - 16) / 2 - 2，即 getProgressBarRect 再减 _drawProgressBar 那 2px */
.progress {
  position: absolute;
  left: 0;
  right: 0;
  top: 40px;
  height: 4px;
}

.track,
.bar {
  position: absolute;
  left: 0;
  top: 0;
  height: 4px;
  border-radius: 2px;
}

.track {
  width: 100%;
  /* 桌面版画的是一条 alpha 155 的线 */
  background-color: rgba(0, 0, 0, 0.16);
}

:root[data-theme='dark'] .track {
  background-color: rgba(255, 255, 255, 0.16);
}

.bar {
  background-color: var(--primary-color);
  transition: width 0.2s ease;
}

/* 出错与暂停的配色照抄 _drawProgressBar */
.bar.is-error {
  background-color: rgb(196, 43, 28);
}

.bar.is-paused {
  background-color: rgb(157, 93, 0);
}

:root[data-theme='dark'] .bar.is-error {
  background-color: rgb(255, 153, 164);
}

:root[data-theme='dark'] .bar.is-paused {
  background-color: rgb(252, 225, 0);
}

/* bottom 15 = 100 - 20（行高） - 10（margin） - 5，与左边那行信息同高 */
.status {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 15px;
  font-size: 14px;
  line-height: 20px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status.is-error {
  color: rgb(196, 43, 28);
}

:root[data-theme='dark'] .status.is-error {
  color: rgb(255, 153, 164);
}

/* ---- 按钮 ---- */

.actions {
  flex: 0 0 auto;
  display: flex;
  flex-direction: row;
  align-items: center;
  /* 两个按钮间距 10、删除键离右边 30，都是 UIRect 那几个式子算出来的 */
  gap: 10px;
  margin-left: 10px;
  margin-right: 20px;
}

/* 窄屏：右边那一列先让位，标题优先 */
@media (max-width: 900px) {
  .right {
    width: 140px;
  }

  .actions {
    margin-right: 0;
  }
}
</style>
