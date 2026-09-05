import { defineStore } from 'pinia'
import { api } from '@/api/client'
import { CHECKED, PARTIAL, UNCHECKED } from '@/api/types'
import type { CheckState, ParseColumn, ParseNode, ParseTreePayload } from '@/api/types'

export { CHECKED, PARTIAL, UNCHECKED }
export type { CheckState }

/** 摊平后待渲染的一行 */
interface Row {
  node: ParseNode
  depth: number
}

// 把树摊平成 id → 节点 / 父节点 的索引。
// 勾选要向下传递、向上回算，每次都递归整棵树在千级条目下会很吃力
function indexTree(tree: ParseNode[]) {
  const nodes = new Map<string, ParseNode>()
  const parents = new Map<string, string | null>()

  const walk = (list: ParseNode[], parentId: string | null) => {
    for (const node of list) {
      nodes.set(node.id, node)
      parents.set(node.id, parentId)

      if (node.children) {
        walk(node.children, node.id)
      }
    }
  }

  walk(tree, null)

  return { nodes, parents }
}

interface ParseState {
  tree: ParseNode[]
  columns: ParseColumn[]
  category: string
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
    columns: [],
    category: '',
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
          result.push({ node, depth })

          if (node.children && state.expanded.has(node.id)) {
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
    _load(payload: ParseTreePayload) {
      this.tree = payload.tree || []
      this.columns = payload.columns || []
      this.category = payload.category || ''
      this.total = payload.total || 0

      this.mediaError =
        payload.media_info_available === false
          ? payload.media_info_error || 'media information is unavailable'
          : ''

      const { nodes, parents } = indexTree(this.tree)

      this._nodes = nodes
      this._parents = parents

      this.checkState = new Map([...nodes].map(([id, node]) => [id, node.checked ?? UNCHECKED]))

      // 默认只展开第一层。这是 Web 端有意偏离 GUI（GUI 默认全展开）的一处，见 D13。
      // 列表本身已经虚拟滚动，全展开不再是渲染压力，但千级条目一次铺开在网页上
      // 依然难以浏览，所以这条决策保留
      this.expanded = new Set(this.tree.filter((node) => node.children).map((node) => node.id))
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
        next.set(target.id, value)

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

        const states = (parent.children || []).map((child) => next.get(child.id) ?? UNCHECKED)

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
        this._load(await api.parseUrl(url.trim()))
      } catch (e) {
        this.error = e instanceof Error ? e.message : String(e)
      } finally {
        this.loading = false
      }
    },

    // 刷新页面后恢复现场：桌面版进程里的解析结果还在
    async restore() {
      try {
        const payload = await api.getParseTree()

        if (payload.total) {
          this._load(payload)
        } else {
          this.columns = payload.columns || []
        }
      } catch (e) {
        this.error = e instanceof Error ? e.message : String(e)
      }
    },
  },
})
