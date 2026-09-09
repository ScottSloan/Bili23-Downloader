<script setup lang="ts">
/**
 * 滑块
 *
 * 对应桌面版 `gui/component/setting/widget.py` 的 `SettingSlider`：
 * **左边一个数字、右边一根 230px 的滑轨**，线程数与并行数两项用的都是它。
 * Web 端原先把这两项做成了数字输入框，看着是另一回事。
 *
 * 度量照 qfluentwidgets 的 `Slider`（它是自绘的，没有 qss 可抄，值取自 `slider.py`）：
 *
 * - 控件高 22，滑轨高 4、圆角 2，**两端各让开半个滑块**（`_drawHorizonGroove`
 *   从 x=r 画到 w-r，r 是滑块半径）
 * - 未填充段 `rgba(0,0,0,100/255)`，深色 `rgba(255,255,255,115/255)`；已填充段是主题色
 * - 滑块是白色（深色主题 `rgb(69,69,69)`）圆片加一圈极淡的描边，
 *   **中间一个主题色的圆点**，半径平时 5、悬停 6、按下 4，100ms 动画
 *
 * 用原生 `<input type="range">` 而不是自己拿 pointer 事件拼一个：键盘方向键、
 * Home/End、`aria-valuenow`、触屏拖动全都由浏览器给，自己实现必然漏掉几样。
 * 代价是滑轨与滑块只能靠伪元素画，且 WebKit 与 Firefox 各有一套伪元素名。
 */
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue: number
    min: number
    max: number
    step?: number
    disabled?: boolean
    /** 无障碍名称 */
    label?: string
  }>(),
  {
    step: 1,
    disabled: false,
    label: '',
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: number]
}>()

/**
 * 已填充的比例，**0~1 的无单位数**
 *
 * 不能写成百分比：轨道那两层背景的宽度是 `calc((100% - 20px) * var(--fill))`，
 * 而 calc 里长度只能乘**纯数**，乘百分比整条声明会被判为非法 —— 于是整个轨道
 * 一声不响地不画了，页面上只剩一个孤零零的滑块圆点
 */
const ratio = computed(() => {
  const span = props.max - props.min

  if (!Number.isFinite(span) || span <= 0) {
    return 0
  }

  return Math.min(Math.max((props.modelValue - props.min) / span, 0), 1)
})

function onInput(event: Event) {
  emit('update:modelValue', Number((event.target as HTMLInputElement).value))
}
</script>

<template>
  <div class="fluent-slider" :class="{ 'is-disabled': disabled }">
    <!-- 数字在左边，与桌面版一致。定宽，免得拖动时滑轨跟着数字位数左右跳 -->
    <span class="value">{{ modelValue }}</span>

    <input
      type="range"
      class="track"
      :style="{ '--fill': String(ratio) }"
      :value="modelValue"
      :min="min"
      :max="max"
      :step="step"
      :disabled="disabled"
      :aria-label="label || undefined"
      @input="onInput"
    />
  </div>
</template>

<style scoped>
.fluent-slider {
  display: flex;
  align-items: center;
  gap: 10px;
}

.value {
  flex: 0 0 auto;
  min-width: 24px;
  text-align: right;
  font-size: 13px;
  /* 桌面版给它写死了 rgb(96,96,96) / rgb(159,159,159)，正好是次级文字那一档 */
  color: var(--text-secondary);
}

/*
  滑轨。两层背景：上面一层是已填充段（主题色），下面一层是整条底轨。
  两层都往里缩 10px —— 滑块半径 —— 让轨道正好从滑块圆心起、到圆心止，
  与 `_drawHorizonGroove` 里那个 `QRectF(r, r-2, w-r*2, 4)` 一致
*/
.track {
  flex: 0 0 auto;
  width: 230px;
  height: 22px;
  margin: 0;
  padding: 0;
  appearance: none;
  background: transparent;
  cursor: pointer;
}

.track::-webkit-slider-runnable-track {
  height: 22px;
  border-radius: 2px;
  background:
    linear-gradient(var(--primary-color), var(--primary-color)) no-repeat 10px center /
      calc((100% - 20px) * var(--fill, 0)) 4px,
    linear-gradient(var(--slider-groove), var(--slider-groove)) no-repeat 10px center /
      calc(100% - 20px) 4px;
}

.track::-moz-range-track {
  height: 22px;
  border-radius: 2px;
  background:
    linear-gradient(var(--primary-color), var(--primary-color)) no-repeat 10px center /
      calc((100% - 20px) * var(--fill, 0)) 4px,
    linear-gradient(var(--slider-groove), var(--slider-groove)) no-repeat 10px center /
      calc(100% - 20px) 4px;
}

/*
  滑块：20 的白色圆片 + 一圈极淡描边，中心一个主题色圆点（半径 5，即直径 10）。
  圆点用径向渐变画，内外各留半像素过渡 —— 硬边在缩放后会有锯齿
*/
.track::-webkit-slider-thumb {
  appearance: none;
  width: 20px;
  height: 20px;
  margin-top: 1px;
  box-sizing: border-box;
  border-radius: 50%;
  border: 1px solid var(--slider-handle-stroke);
  background:
    radial-gradient(
      circle at center,
      var(--primary-color) 0 calc(var(--dot, 5px) - 0.5px),
      transparent calc(var(--dot, 5px) + 0.5px)
    ),
    var(--slider-handle-fill);
}

.track::-moz-range-thumb {
  width: 20px;
  height: 20px;
  box-sizing: border-box;
  border-radius: 50%;
  border: 1px solid var(--slider-handle-stroke);
  background:
    radial-gradient(
      circle at center,
      var(--primary-color) 0 calc(var(--dot, 5px) - 0.5px),
      transparent calc(var(--dot, 5px) + 0.5px)
    ),
    var(--slider-handle-fill);
}

/*
  圆点大小：悬停 6、按下 4。改的是自定义属性，两套伪元素各自取值 ——
  `--dot` 不是可动画的注册属性，所以变化是瞬时的（Qt 那边有 100ms 缓动）。
  为它 `@property` 注册一个可插值的长度不值得，这点差别肉眼看不出
*/
.track:not(:disabled):hover {
  --dot: 6px;
}

.track:not(:disabled):active {
  --dot: 4px;
}

.track:focus-visible {
  outline: 2px solid var(--focus-stroke-outer);
  outline-offset: 2px;
  border-radius: 4px;
}

.fluent-slider.is-disabled .value {
  color: var(--text-disabled);
}

.track:disabled {
  cursor: default;
  opacity: 0.5;
}

/* ---- 配色。取值来自 slider.py 的 paintEvent ---- */
.fluent-slider {
  --slider-groove: rgba(0, 0, 0, 0.392);
  --slider-handle-fill: #fff;
  --slider-handle-stroke: rgba(0, 0, 0, 0.098);
}

:root[data-theme='dark'] .fluent-slider {
  --slider-groove: rgba(255, 255, 255, 0.451);
  --slider-handle-fill: rgb(69, 69, 69);
  --slider-handle-stroke: rgba(0, 0, 0, 0.353);
}
</style>
