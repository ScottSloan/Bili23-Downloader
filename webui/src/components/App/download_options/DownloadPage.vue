<script setup lang="ts">
/**
 * 下载选项 · 下载设置页
 *
 * 对应桌面版 `gui/dialog/download_options/download.py`：下载目录、下载格式、
 * 命名规则、是否每次弹这个对话框、编号方式。
 *
 * ## 哪些写全局、哪些只作用于本次
 *
 * 与桌面版逐项对齐：
 *
 * | | 桌面版 | 这里 |
 * |---|---|---|
 * | 下载目录 | 点「确定」时 `config.set(config.download_path, …)` | 写全局设置 |
 * | 下载格式 / 是否弹窗 / 编号方式 | 绑定 config，改完立刻落盘 | 写全局设置 |
 * | 命名规则 | 存进运行时属性 `config.target_naming_rule_id` | **随 options 传，只管这一批** |
 *
 * 命名规则那一项是唯一走 options 的：桌面版存的那个运行时属性会在下一次解析时被清空
 * （预览器的 clear_cache），本身就是「只对这一次有效」的语义。WebUI 没有进程级的粘性
 * 状态可用，也不该有 —— 所以它在 S4-3 里被固化进了 `TaskInfo.Options`。
 *
 * ## 「全局顺序起始编号」那一行没有照搬
 *
 * 桌面版那一行读写 `config.global_starting_number`，是个**纯运行时属性**：不落盘、
 * 不在 `/api/settings` 里，WebUI 无处可存也无处可读。这里换成「本批起始编号」——
 * 它对应 core 里 `starting_number` 这个 option，只在「每批从 1 开始」那一档下有意义，
 * 其余档位置灰。
 */
import { computed, ref, watch } from 'vue'
import { files as filesApi, settings as settingsApi } from '@/api'
import type { NamingRuleOption } from '@/api'
import { useSettingsStore } from '@/stores/settingsStore'
import { t } from '@/i18n'
import { expandCard, SPEC_BY_ATTR } from '@/components/App/settings/spec'
import { formatFileSize } from '@/components/App/download/formatters'
import settingRow from '@/components/App/settings/SettingRow.vue'
import directoryPickerDialog from '@/components/App/settings/DirectoryPickerDialog.vue'
import settingCard from '@/components/Fluent/components/settings/SettingCard.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import settingGroupRow from '@/components/Fluent/components/settings/SettingGroupRow.vue'
import expandSettingCard from '@/components/Fluent/components/settings/ExpandSettingCard.vue'
import comboBox from '@/components/Fluent/components/widgets/combo_box/ComboBox.vue'
import spinBox from '@/components/Fluent/components/widgets/spin_box/SpinBox.vue'
import cardGuideLink from './CardGuideLink.vue'
import guideDialog from './GuideDialog.vue'

const props = defineProps<{
  /**
   * 当前这批内容的位标志，用来筛选可用的命名规则
   *
   * 与桌面版一样取自被预览的那一集（`PreviewerInfo.attribute`）。
   * 「仅配置」模式下没有剧集，此时为 undefined，命名规则整行不可用
   */
  attribute?: number
  /**
   * 这次是不是真的要建一批任务
   *
   * 「仅配置」模式下没有「本批」可言，起始编号那一行也就无从谈起，直接不显示 ——
   * 摆一个点了不起作用的控件，正是这个对话框此前被诟病的地方
   */
  perBatch?: boolean
}>()

const store = useSettingsStore()

// ---------------- 清单里现成的几项 ----------------

const showDialogSpec = SPEC_BY_ATTR.show_download_options_dialog
const numberingSpec = SPEC_BY_ATTR.numbering_type

const formatCard = computed(() => expandCard('downloadFormat'))

// ---------------- 磁盘空间 ----------------

const space = ref<{ free: number; filesystem: string } | null>(null)

const pickerOpen = ref(false)

function onPickPath(path: string) {
  store.set('download_path', path)

  pickerOpen.value = false
}

const downloadPath = computed(() => String(store.value('download_path') ?? ''))

/**
 * 下载目录那一行的说明：「{路径}（可用 {空间}）」
 *
 * 与桌面版 `DownloadPathSettingCard.on_disk_space_ready` 同一个写法 —— 路径就在说明里，
 * 不另外占一格。空间还没查回来（或查不到）时只显示路径，不留一个空括号
 */
const pathDescription = computed(() => {
  const path = downloadPath.value

  if (!space.value) {
    return path
  }

  const free = t('downloadOptions.download.freeSpace', {
    free: formatFileSize(space.value.free),
  })

  // 文件系统类型是桌面版那张卡片也会显示的（FAT 系不支持稀疏文件时要提醒）
  const detail = space.value.filesystem ? `${free} · ${space.value.filesystem}` : free

  return `${path}（${detail}）`
})

async function refreshSpace() {
  const path = downloadPath.value

  space.value = null

  if (!path) {
    return
  }

  try {
    const result = await filesApi.space(path)

    // 期间用户又换了目录，这次的结果已经过期
    if (path !== downloadPath.value) {
      return
    }

    space.value = result.available ? { free: result.free, filesystem: result.filesystem } : null
  } catch {
    // 取不到就不显示那半句，不值得为它弹错误 ——
    // 目录在白名单外时后端会返回 403，而那种情况下面的选目录对话框会拦住
    space.value = null
  }
}

watch(downloadPath, () => void refreshSpace(), { immediate: true })

// ---------------- 命名规则 ----------------

const rules = ref<NamingRuleOption[]>([])
const rulesLoading = ref(false)

/** 选中的规则 id。null 表示按媒体类型取默认规则（不往 options 里放这一项） */
const ruleId = ref<string | null>(null)

const ruleOptions = computed(() =>
  rules.value.map((rule) => ({
    value: rule.id,
    // 内置规则的 name 是待翻译的键，前端自己查表（D12）；自定义规则的名字原样显示
    label: translateRuleName(rule.name),
  })),
)

function translateRuleName(name: string): string {
  const key = `settings.namingRule.preset.${name}`
  const text = t(key)

  return text === key ? name : text
}

async function loadRules() {
  rules.value = []
  ruleId.value = null

  if (props.attribute === undefined) {
    return
  }

  rulesLoading.value = true

  try {
    const result = await settingsApi.namingRuleAvailable(props.attribute)

    rules.value = result.rules ?? []

    // 与桌面版一致：默认选中标了 default 的那一条
    ruleId.value = rules.value.find((rule) => rule.default)?.id ?? rules.value[0]?.id ?? null
  } catch {
    rules.value = []
  } finally {
    rulesLoading.value = false
  }
}

/** 这一类媒体支不支持自定义命名规则。桌面版查不到时把下拉整个禁用掉 */
const ruleAvailable = computed(() => rules.value.length > 0)

// ---------------- 编号 ----------------

/** NumberingType.FROM_SPECIFIED = 0，「每批从 1 开始」。只有这一档用得上起始编号 */
const FROM_SPECIFIED = 0

const startingNumber = ref(1)

const numberingType = computed(() => Number(store.value('numbering_type') ?? 2))

const startingNumberEnabled = computed(() => numberingType.value === FROM_SPECIFIED)

const guideOpen = ref(false)

// ---------------- 对外 ----------------

async function load() {
  startingNumber.value = 1

  await Promise.all([loadRules(), refreshSpace()])
}

defineExpose({
  load,

  /**
   * 建任务时随 options 一起传的部分
   *
   * 下载目录不在这里 —— 它已经写进全局设置了，core 那边取不到 options 里的
   * `download_path` 时正好回落到同一个值。多传一份等于制造第二个真相源
   */
  options: () => {
    const result: Record<string, unknown> = {}

    if (ruleId.value) {
      result.target_naming_rule_id = ruleId.value
    }

    if (props.perBatch && startingNumberEnabled.value) {
      result.starting_number = startingNumber.value
    }

    return result
  },
})
</script>

<template>
  <div class="download-page">
    <settingCard
      icon="folder"
      :title="t('settings.label.download_path')"
      :description="pathDescription"
    >
      <pushButton :title="t('settings.picker.title')" @click="pickerOpen = true" />
    </settingCard>

    <directoryPickerDialog
      :open="pickerOpen"
      :current="downloadPath"
      @close="pickerOpen = false"
      @select="onPickPath"
    />

    <expandSettingCard
      v-if="formatCard"
      :icon="formatCard.icon"
      :title="t(`settings.card.${formatCard.key}.title`)"
      :description="t(`settings.card.${formatCard.key}.desc`)"
    >
      <settingRow v-for="spec in formatCard.items" :key="spec.attr" :spec="spec" in-group />
    </expandSettingCard>

    <settingCard
      icon="document"
      :title="t('downloadOptions.download.namingRule')"
      :description="
        ruleAvailable || rulesLoading
          ? t('downloadOptions.download.namingRuleDesc')
          : t('downloadOptions.download.namingRuleUnavailable')
      "
      :disabled="!ruleAvailable"
    >
      <comboBox
        v-if="ruleAvailable"
        v-model="ruleId"
        :options="ruleOptions"
        :label="t('downloadOptions.download.namingRule')"
      />
      <span v-else class="unavailable">{{ t('downloadOptions.download.notAvailable') }}</span>
    </settingCard>

    <settingRow v-if="showDialogSpec" :spec="showDialogSpec" />

    <expandSettingCard
      icon="numbers"
      :title="t('downloadOptions.download.numbering')"
      :description="t('downloadOptions.download.numberingDesc')"
    >
      <template #link>
        <cardGuideLink
          :text="t('downloadOptions.download.aboutNumbering')"
          @click="guideOpen = true"
        />
      </template>

      <settingRow v-if="numberingSpec" :spec="numberingSpec" in-group />

      <settingGroupRow
        v-if="perBatch"
        :title="t('downloadOptions.download.startingNumber')"
        :description="t('downloadOptions.download.startingNumberDesc')"
        :disabled="!startingNumberEnabled"
      >
        <spinBox
          v-model="startingNumber"
          :min="1"
          :max="99999"
          :disabled="!startingNumberEnabled"
          :label="t('downloadOptions.download.startingNumber')"
        />
      </settingGroupRow>

    </expandSettingCard>

    <guideDialog
      :open="guideOpen"
      :title="t('downloadOptions.guideTitle')"
      :content="t('downloadOptions.guide.numbering')"
      @close="guideOpen = false"
    />
  </div>
</template>

<style scoped>
.download-page {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.unavailable {
  font-size: 12px;
  color: var(--text-disabled);
}
</style>
