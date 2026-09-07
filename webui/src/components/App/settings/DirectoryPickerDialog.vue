<script setup lang="ts">
// 选下载目录
//
// 浏览器里没有「选择文件夹」这回事 —— `<input type="file" webkitdirectory>` 选的是
// **浏览器所在机器**上的目录，而下载是在服务端落盘的，两者常常不是同一台机器
// （Docker 部署时更是必然）。所以只能由服务端列目录、前端来点。
//
// 后端在 `web/routes/files.py`，只读、且只在白名单根目录内。这里对应地**不给用户
// 输入任意路径的机会**：能去的地方只有根目录列表和从那里点进去的子目录。
// 手输一个路径再提交，后端也会以 403 挡回来，但界面上先不给这个口子。

import { ref, watch } from 'vue'
import { files as filesApi, ApiError } from '@/api'
import type { FileEntry } from '@/api'
import { t } from '@/i18n'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import lineEdit from '@/components/Fluent/components/widgets/line_edit/LineEdit.vue'
import fluentDialog from '@/components/Fluent/components/dialog/FluentDialog.vue'

const props = defineProps<{
  open: boolean
  /** 打开时定位到这个目录。不在允许范围内则退回第一个根目录 */
  current: string
}>()

const emit = defineEmits<{
  close: []
  select: [path: string]
}>()

interface Root {
  path: string
  name: string
  exists: boolean
}

const roots = ref<Root[]>([])
const path = ref('')
const relative = ref('')
const parent = ref<string | null>(null)
const entries = ref<FileEntry[]>([])
const truncated = ref(false)
const loading = ref(false)
const error = ref('')

const creating = ref(false)
const newName = ref('')

watch(
  () => props.open,
  (open) => {
    if (open) {
      void start()
    }
  },
)

async function start() {
  error.value = ''
  creating.value = false
  newName.value = ''

  try {
    roots.value = (await filesApi.roots()).roots
  } catch (e) {
    error.value = describe(e)

    return
  }

  // 先试当前配置的目录，被拒就退到第一个根 —— 配置里的下载路径完全可能在
  // 可浏览范围之外（桌面版设的），那时不该直接报错，而是让用户从根开始挑
  if (props.current && (await navigate(props.current, true))) {
    return
  }

  if (roots.value.length) {
    await navigate(roots.value[0].path)
  }
}

/** 返回是否成功。quiet 为真时失败不显示错误（用于「先试试看」） */
async function navigate(target: string, quiet = false): Promise<boolean> {
  loading.value = true

  try {
    const listing = await filesApi.list(target, true)

    path.value = listing.path
    // relative / parent 在 schema 里是可选的（后端在根目录时不发 parent），
    // 这里补上兜底值，免得界面上出现 undefined
    relative.value = listing.relative ?? ''
    parent.value = listing.parent ?? null
    entries.value = listing.entries
    truncated.value = listing.truncated
    error.value = ''

    return true
  } catch (e) {
    if (!quiet) {
      error.value = t('settings.picker.failed', { message: describe(e) })
    }

    return false
  } finally {
    loading.value = false
  }
}

async function createFolder() {
  const name = newName.value.trim()

  if (!name) {
    return
  }

  try {
    const created = await filesApi.mkdir(path.value, name)

    creating.value = false
    newName.value = ''

    // 建完直接进去，省得用户再找一次
    await navigate(created.path)
  } catch (e) {
    error.value = describe(e)
  }
}

function describe(e: unknown): string {
  return e instanceof ApiError ? e.message : String(e)
}
</script>

<template>
  <fluentDialog
    :open="open"
    :title="t('settings.picker.title')"
    width="460px"
    @close="emit('close')"
  >
    <p v-if="!roots.length && !loading" class="hint">{{ t('settings.picker.noRoots') }}</p>

    <div v-if="roots.length" class="roots">
      <span class="roots-label">{{ t('settings.picker.locations') }}</span>
      <button
        v-for="root in roots"
        :key="root.path"
        type="button"
        class="root"
        :class="{ 'is-current': root.path === path }"
        @click="navigate(root.path)"
      >
        {{ root.name }}
      </button>
    </div>

    <div class="breadcrumb">
      <pushButton
        :title="t('settings.picker.parent')"
        :disabled="!parent"
        @click="parent && navigate(parent)"
      />
      <!-- 在根目录上时后端给的 relative 是 "."，那个点单独摆在面包屑里没人看得懂，
             换成完整路径 -->
      <span class="path" :title="path">{{ relative && relative !== '.' ? relative : path }}</span>
    </div>

    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <ul class="entries">
      <li v-for="entry in entries" :key="entry.name">
        <button type="button" @click="navigate(`${path}/${entry.name}`)">
          <svg class="folder" viewBox="0 0 16 16" aria-hidden="true">
            <path
              d="M1.5 4.2a1 1 0 0 1 1-1h3.3l1.2 1.4h6.5a1 1 0 0 1 1 1v6.2a1 1 0 0 1-1 1h-11a1 1 0 0 1-1-1z"
              fill="currentColor"
              opacity="0.75"
            />
          </svg>
          <span class="name">{{ entry.name }}</span>
          <!-- 链接可能指向根目录之外，点进去会被后端拒。提前标出来，
                 比让用户撞一次墙好 -->
          <span v-if="entry.is_link" class="link-tag">link</span>
        </button>
      </li>

      <li v-if="!entries.length && !loading" class="empty">
        {{ t('settings.picker.empty') }}
      </li>
    </ul>

    <p v-if="truncated" class="hint">
      {{ t('settings.picker.truncated', { count: entries.length }) }}
    </p>

    <div v-if="creating" class="new-folder">
      <lineEdit
        v-model="newName"
        :placeholder="t('settings.picker.newFolderPlaceholder')"
        @submit="createFolder"
      />
      <pushButton :title="t('settings.picker.create')" @click="createFolder" />
    </div>

    <template #actions>
      <pushButton
        v-if="!creating"
        :title="t('settings.picker.newFolder')"
        :disabled="!path"
        @click="creating = true"
      />
      <span class="spacer"></span>
      <pushButton :title="t('settings.picker.cancel')" @click="emit('close')" />
      <primaryPushButton
        :title="t('settings.picker.choose')"
        :disabled="!path"
        @click="emit('select', path)"
      />
    </template>
  </fluentDialog>
</template>

<style scoped>
.roots {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.roots-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.root {
  appearance: none;
  font: inherit;
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 12px;
  cursor: pointer;
  color: var(--text-primary);
  background-color: var(--control-fill-default);
  border: 1px solid var(--control-stroke-default);
}

.root:hover {
  background-color: var(--control-fill-secondary);
}

.root.is-current {
  color: var(--text-on-accent);
  background-color: var(--primary-color);
  border-color: var(--primary-color);
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.path {
  font-size: 12px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.entries {
  flex: 1 1 auto;
  min-height: 160px;
  max-height: 42vh;
  overflow-y: auto;
  margin: 0;
  padding: 4px;
  list-style: none;
  border-radius: 6px;
  background-color: var(--control-fill-default);
  border: 1px solid var(--card-stroke-default);
}

.entries button {
  appearance: none;
  font: inherit;
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--text-primary);
  cursor: pointer;
  text-align: left;
}

.entries button:hover {
  background-color: var(--subtle-fill-secondary);
}

.entries button:focus-visible {
  outline: 2px solid var(--focus-stroke-outer);
  outline-offset: -2px;
}

.folder {
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
  color: var(--primary-color);
}

.name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.link-tag {
  font-size: 10px;
  padding: 0 5px;
  border-radius: 8px;
  color: var(--text-secondary);
  background-color: var(--subtle-fill-tertiary);
}

.empty,
.hint {
  margin: 0;
  padding: 10px 8px;
  font-size: 12px;
  color: var(--text-secondary);
}

.error {
  margin: 0;
  font-size: 12px;
  color: var(--text-danger);
}

.new-folder {
  display: flex;
  gap: 8px;
}

.new-folder :deep(.fluent-line-edit) {
  flex: 1 1 auto;
}

.spacer {
  flex: 1 1 auto;
}
</style>
