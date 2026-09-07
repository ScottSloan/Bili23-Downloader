import { defineStore } from 'pinia'
import { tasks as tasksApi, ApiError } from '@/api'
import type { TaskView } from '@/api'
import { EventStream } from '@/api/events'
import type { ServerEvent } from '@/api/events'
import { t } from '@/i18n'

/**
 * 下载任务的现场
 *
 * 数据来源是两条路径合起来的（后端 S3-9）：**全量快照**负责刷新页面后恢复现场，
 * **增量事件**负责之后的变化。缺一不可 —— 只有增量的话刷新后手里什么都没有，
 * 只有快照的话就退回轮询了。
 *
 * 两条路径之间的缝由事件编号补上：快照带 `cursor`，WebSocket 带着它连，
 * 服务端补发这之后的。补不上就整份重来。
 */
interface TaskState {
  downloading: TaskView[]
  completed: TaskView[]
  loading: boolean
  error: string
  /** WebSocket 是否连着。断开时界面上要标出来，否则「不动」看起来和「很慢」一样 */
  live: boolean
  /** 选中的任务，供批量操作 */
  selected: Set<string>
}

let stream: EventStream | null = null

// 重新同步的节流：一串乱序事件可能连着触发好几次，没必要每次都拉一遍全量
let resyncTimer: number | null = null

export const useTaskStore = defineStore('task', {
  state: (): TaskState => ({
    downloading: [],
    completed: [],
    loading: false,
    error: '',
    live: false,
    selected: new Set(),
  }),

  getters: {
    /** 正在下载 / 合并中的任务数，给导航栏上的角标用 */
    activeCount: (state): number =>
      state.downloading.filter((task) =>
        ['downloading', 'merging', 'converting', 'additional_processing'].includes(task.status),
      ).length,

    totalSpeed: (state): number =>
      state.downloading.reduce((sum, task) => sum + (task.speed || 0), 0),
  },

  actions: {
    // ---- 快照 ----

    async refresh(): Promise<number> {
      this.loading = true

      try {
        const snapshot = await tasksApi.snapshot()

        this.downloading = snapshot.downloading
        this.completed = snapshot.completed
        this.error = ''

        // 选中的任务可能已经被删掉，清掉不存在的，否则批量操作会带上幽灵 id
        const alive = new Set([...this.downloading, ...this.completed].map((task) => task.task_id))

        this.selected = new Set([...this.selected].filter((id) => alive.has(id)))

        return snapshot.cursor
      } catch (error) {
        this.error = error instanceof ApiError ? error.message : String(error)

        return 0
      } finally {
        this.loading = false
      }
    },

    // ---- 实时 ----

    async start() {
      if (stream) {
        return
      }

      // **先快照再连**，顺序不能反 —— 理由见 api/events.ts
      const cursor = await this.refresh()

      stream = new EventStream({
        onEvent: (event) => this.apply(event),
        onResync: () => this.scheduleResync(),
        onOpen: () => {
          this.live = true
        },
        onClose: () => {
          this.live = false
        },
      })

      stream.connect(cursor)
    },

    stop() {
      stream?.close()
      stream = null

      this.live = false

      if (resyncTimer !== null) {
        window.clearTimeout(resyncTimer)

        resyncTimer = null
      }
    },

    scheduleResync() {
      if (resyncTimer !== null) {
        return
      }

      resyncTimer = window.setTimeout(async () => {
        resyncTimer = null

        const cursor = await this.refresh()

        stream?.resume(cursor)
      }, 200)
    },

    // ---- 增量 ----

    apply(event: ServerEvent) {
      switch (event.type) {
        case 'task.added':
          this.upsertMany(event.data as TaskView[])

          break

        case 'task.updated':
          this.upsert(event.data as TaskView)

          break

        case 'task.completed':
          // 完成的任务要从「下载中」挪到「已完成」，不然会同时出现在两个列表里
          for (const task of event.data as TaskView[]) {
            this.downloading = this.downloading.filter((item) => item.task_id !== task.task_id)

            this.upsertCompleted(task)
          }

          break

        case 'task.removed': {
          const id = (event.data as { task_id: string }).task_id

          this.downloading = this.downloading.filter((task) => task.task_id !== id)
          this.completed = this.completed.filter((task) => task.task_id !== id)

          this.selected.delete(id)

          break
        }

        // stream.progress 是 aria2 那一侧的流级快照，任务级的进度已经由
        // task.updated 覆盖了，这里不再重复处理
        default:
          break
      }
    },

    upsert(task: TaskView) {
      const index = this.downloading.findIndex((item) => item.task_id === task.task_id)

      if (index >= 0) {
        // 整条替换而不是逐字段合并：后端发的就是完整视图，合并只会让漏发的字段留旧值
        this.downloading[index] = task

        return
      }

      // 已完成列表里的任务也可能收到更新（比如重试后又回到下载中）
      const done = this.completed.findIndex((item) => item.task_id === task.task_id)

      if (done >= 0) {
        if (task.status === 'completed') {
          this.completed[done] = task
        } else {
          this.completed.splice(done, 1)

          this.downloading.push(task)
        }

        return
      }

      this.downloading.push(task)
    },

    upsertMany(list: TaskView[]) {
      for (const task of list) {
        this.upsert(task)
      }
    },

    upsertCompleted(task: TaskView) {
      const index = this.completed.findIndex((item) => item.task_id === task.task_id)

      if (index >= 0) {
        this.completed[index] = task
      } else {
        // 新完成的排在最前：用户最关心的就是刚下完的那个
        this.completed.unshift(task)
      }
    },

    // ---- 选择 ----

    toggleSelected(taskId: string) {
      const next = new Set(this.selected)

      if (next.has(taskId)) {
        next.delete(taskId)
      } else {
        next.add(taskId)
      }

      this.selected = next
    },

    clearSelection() {
      this.selected = new Set()
    },

    // ---- 操作 ----
    //
    // 都不在本地改状态，等服务端的事件推回来 —— 本地先改的话，
    // 操作失败时界面已经变了，而用户不会知道

    async pause(taskIds: string[]) {
      await this.run(() => tasksApi.pause(taskIds))
    },

    async resume(taskIds: string[]) {
      await this.run(() => tasksApi.resume(taskIds))
    },

    async retry(taskIds: string[]) {
      await this.run(() => tasksApi.retry(taskIds))
    },

    async remove(taskIds: string[], completed = false) {
      await this.run(() => tasksApi.remove(taskIds, completed))

      this.clearSelection()
    },

    async run(action: () => Promise<unknown>) {
      try {
        await action()

        this.error = ''
      } catch (error) {
        this.error = error instanceof ApiError ? error.message : t('error.requestFailed', { status: 0 })
      }
    },
  },
})
