import { defineStore } from 'pinia'
import { parse as parseApi } from '@/api'
import type { ParseNode, ParseResult } from '@/api'

// 组件从 store 取类型即可，不必再认识 api 层
export type { ParseNode }

/**
 * 勾选态
 *
 * **后端只发布尔值**（`serialize_node()` 的 `checked`）。三态是纯前端的事：
 * 半选只在「子项选了一部分」时出现，而那完全可以由前端算出来。
 * 取值仍与桌面版的 Qt.CheckState 对齐，方便对着看
 */
export const UNCHECKED = 0
export const PARTIAL = 1
export const CHECKED = 2

export type CheckState = typeof UNCHECKED | typeof PARTIAL | typeof CHECKED

/** 解析列表的一列。列名不在这里，由前端 i18n 按 key 提供（D12） */
export interface ParseColumn {
  key: string
  width: number
  show: boolean
}

// 列配置原先由后端的垫片一并返回，新后端没有这一项 —— 它在共用配置的
// `parse_list_column` 里，由设置页那条链路读回来。在读到之前先用这份默认的，
// 否则首屏的树会没有表头
const DEFAULT_COLUMNS: ParseColumn[] = [
  { key: 'number', width: 160, show: true },
  { key: 'title', width: 350, show: true },
  { key: 'badge', width: 90, show: true },
  { key: 'duration', width: 90, show: true },
  { key: 'dyn_time', width: 130, show: true },
]

/** 摊平后待渲染的一行 */
interface Row {
  node: ParseNode
  depth: number
  /**
   * 行标识
   *
   * 与 `node.id` 是同一个值，但在这里是**必填**的：`ParseNode.id` 声明成可选是因为
   * 后端不发它，而摊平出来的行一定已经派过 id 了。模板里用 row.id 就不必到处写 `!`
   */
  id: string
}

// 把树摊平成 id → 节点 / 父节点 的索引。
// 勾选要向下传递、向上回算，每次都递归整棵树在千级条目下会很吃力
//
// **id 是前端派的位置路径**（"0"、"0.1"）。后端不发 id：它那边的 episode_id 同一个
// 视频的所有分P 是共享的，拿来当行标识会让分P 之间互相干扰。位置路径天然唯一，
// 且重新解析时整棵树连同 id 一起替换，不存在陈旧引用
function indexTree(tree: ParseNode[]) {
  const nodes = new Map<string, ParseNode>()
  const parents = new Map<string, string | null>()

  const walk = (list: ParseNode[], parentId: string | null, prefix: string) => {
    list.forEach((node, index) => {
      const id = prefix ? `${prefix}.${index}` : String(index)

      node.id = id

      nodes.set(id, node)
      parents.set(id, parentId)

      if (node.children?.length) {
        walk(node.children, id, id)
      }
    })
  }

  walk(tree, null, '')

  return { nodes, parents }
}

interface ParseState {
  tree: ParseNode[]
  columns: ParseColumn[]
  category: string
  /** 解析出来的标题，用于历史记录与页面标题 */
  title: string
  /** 链接指向的那一集的定位方式，前端据此高亮 */
  current: { field: string; value: string | number } | null
  total: number
  loading: boolean
  error: string
  mediaError: string
  expanded: Set<string>
  checkState: Map<string, CheckState>
  _nodes: Map<string, ParseNode>
  _parents: Map<string, string | null>
}

export const useParseStore = defineStore('parse', {
  state: (): ParseState => ({
    tree: [],
    columns: DEFAULT_COLUMNS,
    category: '',
    title: '',
    current: null,
    total: 0,

    loading: false,
    error: '',

    // 媒体信息不可用时的提示（充电专属、付费等无权限内容）
    mediaError: '',

    expanded: new Set(),
    // id → 勾选态。与 tree 分开存，重新解析时整体替换
    checkState: new Map(),

    _nodes: new Map(),
    _parents: new Map(),
  }),

  getters: {
    visibleColumns: (state): ParseColumn[] => state.columns.filter((column) => column.show),

    // 按展开状态摊平出实际要渲染的行，附带层级用于缩进
    rows: (state): Row[] => {
      const result: Row[] = []

      const walk = (list: ParseNode[], depth: number) => {
        for (const node of list) {
          result.push({ node, depth, id: node.id as string })

          if (node.children?.length && state.expanded.has(node.id as string)) {
            walk(node.children, depth + 1)
          }
        }
      }

      walk(state.tree, 0)

      return result
    },

    checkedCount: (state): number => {
      let count = 0

      for (const [id, value] of state.checkState) {
        const node = state._nodes.get(id)

        // 树节点只是分组用的，不计入可下载条目数
        if (value === CHECKED && node && !node.is_node) {
          count += 1
        }
      }

      return count
    },
  },

  actions: {
    _load(payload: ParseResult) {
      // 后端给的是单个根节点，根本身不可见，渲染的是它的孩子
      this.tree = payload.tree?.children ?? []
      this.category = payload.category || ''
      this.title = payload.title || ''
      this.current = payload.current ?? null

      const { nodes, parents } = indexTree(this.tree)

      // 总数由前端数：后端不再返回 total，而「树节点不算下载项」这条规则
      // 前后端各有一份判据（后端是 is_node），这里照着同一条算
      this.total = [...nodes.values()].filter((node) => !node.is_node).length

      this._nodes = nodes
      this._parents = parents

      // 后端发的是布尔值，转成三态的两个端点；半选由 setChecked 回算时才产生
      this.checkState = new Map(
        [...nodes].map(([id, node]) => [id, node.checked ? CHECKED : UNCHECKED]),
      )

      // 默认只展开第一层。这是 Web 端有意偏离 GUI（GUI 默认全展开）的一处，见 D13。
      // 列表本身已经虚拟滚动，全展开不再是渲染压力，但千级条目一次铺开在网页上
      // 依然难以浏览，所以这条决策保留
      this.expanded = new Set(
        this.tree.filter((node) => node.children?.length).map((node) => node.id as string),
      )
    },

    toggleExpanded(id: string) {
      // Set 不是深响应的，替换成新实例才能触发重新渲染
      const next = new Set(this.expanded)

      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }

      this.expanded = next
    },

    setChecked(id: string, checked: boolean) {
      const node = this._nodes.get(id)

      if (!node) {
        return
      }

      const next = new Map(this.checkState)

      const applyDown = (target: ParseNode, value: CheckState) => {
        next.set(target.id as string, value)

        for (const child of target.children || []) {
          applyDown(child, value)
        }
      }

      applyDown(node, checked ? CHECKED : UNCHECKED)

      // 自底向上回算祖先：全选 → 选中，全不选 → 未选，否则半选
      let parentId = this._parents.get(id) ?? null

      while (parentId != null) {
        const parent = this._nodes.get(parentId)

        if (!parent) {
          break
        }

        const states = (parent.children || []).map(
          (child) => next.get(child.id as string) ?? UNCHECKED,
        )

        if (states.every((state) => state === CHECKED)) {
          next.set(parentId, CHECKED)
        } else if (states.every((state) => state === UNCHECKED)) {
          next.set(parentId, UNCHECKED)
        } else {
          next.set(parentId, PARTIAL)
        }

        parentId = this._parents.get(parentId) ?? null
      }

      this.checkState = next
    },

    async parse(url: string) {
      if (!url.trim()) {
        return
      }

      this.loading = true
      this.error = ''

      try {
        this._load(await parseApi.url(url.trim()))
      } catch (e) {
        this.error = e instanceof Error ? e.message : String(e)
      } finally {
        this.loading = false
      }
    },

    /**
     * 摘出勾选的剧集，交给创建任务的接口
     *
     * 走后端的 `/api/parse/episodes` 而不是自己遍历：**「树节点不算下载项」这条规则
     * 只该有一处**，两边各写一遍迟早对不上
     */
    async checkedEpisodes(): Promise<Record<string, unknown>[]> {
      if (!this.tree.length) {
        return []
      }

      // 把前端算出的三态写回节点，后端按 checked 摘
      const apply = (list: ParseNode[]) => {
        for (const node of list) {
          node.checked = this.checkState.get(node.id as string) === CHECKED

          if (node.children?.length) {
            apply(node.children)
          }
        }
      }

      apply(this.tree)

      const root: ParseNode = {
        title: '',
        number: '',
        badge: '',
        cover: '',
        duration: 0,
        attribute: 0,
        attributes: [],
        is_node: false,
        checked: false,
        children: this.tree,
      }

      const payload = await parseApi.episodes(root, true)

      return payload.episodes
    },
  },
})
