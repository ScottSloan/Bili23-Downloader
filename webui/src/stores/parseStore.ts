import { defineStore } from 'pinia'
import { parse as parseApi, tasks as tasksApi } from '@/api'
import type { ParseNode, ParseResult } from '@/api'
import { useSettingsStore } from './settingsStore'

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

// 列配置在共用配置的 `parse_list_column` 里，由 `loadColumns()` 从 `/api/settings`
// 读回来（那是与桌面版同一份配置，两边的列设置因此是一致的）。
// 这份默认值只在还没读到、或配置里那一项坏掉时兜底，否则首屏的树会没有表头
const DEFAULT_COLUMNS: ParseColumn[] = [
  { key: 'number', width: 160, show: true },
  { key: 'title', width: 350, show: true },
  { key: 'badge', width: 90, show: true },
  { key: 'duration', width: 90, show: true },
  { key: 'dyn_time', width: 130, show: true },
]

/**
 * 按某一列比大小
 *
 * 列名直接就是节点上的字段名（number / title / badge / duration），只有时间那一列
 * 例外：`dyn_time` 该看发布、收藏还是观看时间由后端挑好，存在 `timeColumn` 里。
 *
 * 数字与字符串分开处理。**字符串用 `localeCompare`**，这一处与桌面版不同：
 * Python 的 `sorted` 按码位排，中文标题排出来的顺序对人没有意义
 */
function sortComparator(
  key: string,
  order: 'asc' | 'desc',
  timeColumn: string,
): ((a: ParseNode, b: ParseNode) => number) | null {
  if (!key) {
    return null
  }

  const field = key === 'dyn_time' ? timeColumn : key
  const sign = order === 'desc' ? -1 : 1

  const valueOf = (node: ParseNode): string | number =>
    (node as unknown as Record<string, string | number | undefined>)[field] ?? ''

  return (a, b) => {
    const left = valueOf(a)
    const right = valueOf(b)

    if (typeof left === 'number' && typeof right === 'number') {
      return (left - right) * sign
    }

    return String(left).localeCompare(String(right), undefined, { numeric: true }) * sign
  }
}

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
  /**
   * 按哪一列排序。空串表示不排，用后端给的顺序
   *
   * 与桌面版一致（那边是 `setSortingEnabled(True)` + `model.sort()`）：
   * **每一层各自排**，不是把树摊平了排 —— 分 P 只在自己那一组里换位置，
   * 不会跑到别的剧集下面去
   */
  sortKey: string
  sortOrder: 'asc' | 'desc'
  category: string
  /**
   * 时间列这一次显示的是哪一个
   *
   * 投稿看发布时间、收藏夹与稍后再看看收藏时间、历史记录看上次观看时间 ——
   * 桌面版的表头就是这么随类别变的。**由后端挑好**（`dyn_time_attr_key`，
   * 与桌面版表头同一个函数），这边只负责按它取列名。
   *
   * 没解析过时按发布时间，与桌面版 `_category_name` 为空时的结论一致
   */
  timeColumn: string
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
  /** 已经下过的行。**服务端会静默跳过它们**，所以必须在列表上标出来 */
  downloaded: Set<string>
  /** 解析用的链接（后端解析短链后返回的那条），翻页与服务端搜索都复用它 */
  url: string
  /**
   * 后端随解析结果给的附加信息
   *
   * 搜索要看其中三样：`server_search`（接口支不支持按关键词搜）、`pagination`
   * （结果分不分页，决定本地筛选够不够用）、`keyword`（链接里已生效的关键词）
   */
  extra: Record<string, unknown>
  /** 本地筛选的关键词。命中的行标题用主题色显示，与桌面版一致（那边是 ForegroundRole） */
  searchKeyword: string
  /** 批量解析的进度。null 表示没在跑 */
  batch: { done: number; total: number; failed: number } | null
  /**
   * 当前选中的行
   *
   * 与勾选是两回事：勾选决定下载哪些，选中只是「光标停在哪一行」，
   * 桌面版靠它画左边那道竖条与右键菜单的作用对象（`SingleSelection`）
   */
  selected: string
  _nodes: Map<string, ParseNode>
  _parents: Map<string, string | null>
}

export const useParseStore = defineStore('parse', {
  state: (): ParseState => ({
    tree: [],
    columns: DEFAULT_COLUMNS,
    sortKey: '',
    sortOrder: 'asc',
    category: '',
    timeColumn: 'pubtime',
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

    downloaded: new Set(),

    url: '',
    extra: {},
    searchKeyword: '',
    batch: null,
    selected: '',

    _nodes: new Map(),
    _parents: new Map(),
  }),

  getters: {
    visibleColumns: (state): ParseColumn[] => state.columns.filter((column) => column.show),

    /** 接口本身支持按关键词搜索（个人空间、收藏夹、历史记录、稍后再看） */
    serverSearchAvailable: (state): boolean => Boolean(state.extra.server_search),

    /** 结果分页。接口不支持搜索时，本地筛选只覆盖当前页，要提示用户 */
    paginated: (state): boolean => Boolean(state.extra.pagination),

    /** 链接里已生效的搜索关键词，打开搜索框时回显 */
    currentKeyword: (state): string =>
      typeof state.extra.keyword === 'string' ? state.extra.keyword : '',

    // 按展开状态摊平出实际要渲染的行，附带层级用于缩进
    rows: (state): Row[] => {
      const result: Row[] = []

      const compare = sortComparator(state.sortKey, state.sortOrder, state.timeColumn)

      const walk = (list: ParseNode[], depth: number) => {
        // 排序**不动 state.tree**：那棵树是身份的来源（id 是位置路径，
        // checkState / expanded 都挂在上面）。这里只重排渲染出来的顺序，
        // 每一层单独排一次，与桌面版 `_sort_recursive` 同构
        const ordered = compare ? [...list].sort(compare) : list

        for (const node of ordered) {
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
      this.timeColumn = payload.time_column || 'pubtime'
      this.title = payload.title || ''
      this.current = payload.current ?? null
      this.url = payload.url || ''
      this.extra = payload.extra ?? {}

      // 上一次的筛选词跟着结果一起作废：换了一棵树，高亮的还是旧的命中项就成了噪声
      this.searchKeyword = ''

      // 排序也一起清掉，回到后端给的顺序。**那个顺序本身是有意义的** ——
      // 分 P、剧集、收藏夹都是按平台的排列给过来的，新解析出来的东西
      // 不该继续套用上一次为了找某一集而临时点出来的排序
      this.sortKey = ''

      // 选中的行同理 —— id 是位置路径，换棵树之后同一个 id 指的是另一集
      this.selected = ''

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

      // 与桌面版一致：**整棵树递归展开**（那边是 tree_view.py 的 _schedule_expand_all）。
      //
      // 之前只展开第一层，理由是「千级条目一次铺开难以浏览」。那个理由站不住：
      // 剧集的「正片 / 章节 / PV」这些分支收起来之后，用户看到的是几个空壳标题，
      // 要点开才知道里面有什么 —— 而列表本来就是虚拟滚动的，展开不增加渲染成本
      this.expanded = new Set(this._nodeIds(this.tree))

      // 上一次解析的标记必须先清掉：id 是位置路径，换了一棵树之后同一个 id
      // 指的完全是另一集
      this.downloaded = new Set()

      // 不 await：查重是锦上添花，慢一点不该拖住列表出现
      void this.checkDownloaded()
    },

    /**
     * 可下载的叶子，连同它们的行 id
     *
     * 判据取自后端在每个节点上给的两个字段（`is_node` 与 `episode`），
     * 与 `parse/session.py` 的 `collect_episodes()` 是同一条 —— 那边也是
     * 「没有孩子 + 有 episode + 不是树节点」。
     *
     * 这里没有改走后端的 `/api/parse/episodes`，是因为**那个接口只返回 episode 列表，
     * 认不出哪一条属于哪一行**；而标记要落到具体的行上，必须有 id ↔ episode 的配对
     */
    /** 所有有子节点的行 id，用于一次性全展开 */
    _nodeIds(list: ParseNode[]): string[] {
      const found: string[] = []

      const walk = (nodes: ParseNode[]) => {
        for (const node of nodes) {
          if (node.children?.length) {
            found.push(node.id as string)

            walk(node.children)
          }
        }
      }

      walk(list)

      return found
    },

    _leaves(): { id: string; episode: Record<string, unknown> }[] {
      const found: { id: string; episode: Record<string, unknown> }[] = []

      const walk = (list: ParseNode[]) => {
        for (const node of list) {
          if (node.children?.length) {
            walk(node.children)

            continue
          }

          if (node.episode && !node.is_node) {
            found.push({ id: node.id as string, episode: node.episode })
          }
        }
      }

      walk(this.tree)

      return found
    },

    /**
     * 媒体信息预览用哪几集
     *
     * **与勾选无关**，这一点与桌面版一致（`tree_view.get_preview_candidates`）：
     *
     * - 首选**链接指向的那一集**（后端给的 `current` 是「按哪个字段找、找什么值」——
     *   番剧按 ep_id、分P 按 cid，各自不同，所以传的是字段名而不是某个固定的键）
     * - 链接没指向具体某一集时退回列表里的第一个
     * - 其余作为备选，**带备注的排到最后** —— 那多半是充电专属、付费之类取不到
     *   媒体信息的项，拿它当首选会让整个解析结果显示成「不可下载」
     *
     * 在此之前 Web 端是拿「已勾选的那些」去预览的，于是不勾就看不到画质，
     * 工具栏那个入口更是压根没有媒体信息。那是两件事被当成一件：
     * **预览看的是这批内容长什么样，下载的才是勾选的那些**
     */
    previewCandidates(limit = 3): Record<string, unknown>[] {
      const leaves = this._leaves()

      if (!leaves.length) {
        return []
      }

      const primaryIndex = this._currentIndex(leaves)
      const primary = leaves[primaryIndex]

      const backups = leaves
        .filter((_, index) => index !== primaryIndex)
        .sort((a, b) => Number(Boolean(a.episode.badge)) - Number(Boolean(b.episode.badge)))

      return [primary, ...backups.slice(0, Math.max(0, limit - 1))].map((leaf) => leaf.episode)
    },

    /** 链接指向的那一集在叶子里的下标，找不到给 0（退回第一个） */
    _currentIndex(leaves: { episode: Record<string, unknown> }[]): number {
      const locator = this.current

      if (!locator) {
        return 0
      }

      // 后端给的 value 与 episode 里的取值可能一个是数字一个是字符串，
      // 按字符串比 —— 严格相等会让定位静默失败，表现是「预览的总是第一集」
      const wanted = String(locator.value)

      const index = leaves.findIndex(
        (leaf) => String(leaf.episode[locator.field] ?? '') === wanted,
      )

      return index >= 0 ? index : 0
    },

    /** 问后端这批条目里哪些已经下过，标到行上 */
    async checkDownloaded() {
      const leaves = this._leaves()

      if (!leaves.length) {
        return
      }

      try {
        const result = await tasksApi.duplicates(leaves.map((leaf) => leaf.episode))

        const marked = new Set<string>()

        result.duplicates.forEach((isDuplicate, index) => {
          if (isDuplicate && leaves[index]) {
            marked.add(leaves[index].id)
          }
        })

        this.downloaded = marked
      } catch {
        // 查不到就不标。这条信息没有也能用，不值得为它在页面上弹个错
      }
    },

    /**
     * 列配置
     *
     * 与桌面版共用 `parse_list_column`，所以两边的列设置是一致的。
     * 配置里那一项坏掉（手改过、或旧版本写的）时退回默认列 —— 表头空掉比列错更难用
     */
    async loadColumns() {
      const settingsStore = useSettingsStore()

      await settingsStore.load()

      const raw = settingsStore.value('parse_list_column')

      if (!Array.isArray(raw)) {
        return
      }

      const columns = raw
        .filter(
          (entry): entry is Record<string, unknown> => Boolean(entry) && typeof entry === 'object',
        )
        .map((entry) => ({
          key: String(entry.attr_key ?? ''),
          width: Number(entry.width) || 120,
          show: entry.show !== false,
        }))
        .filter((column) => column.key)

      if (columns.length) {
        this.columns = columns
      }
    },

    /**
     * 点表头切换排序
     *
     * 与桌面版一样在升序、降序之间来回切，**没有「回到原始顺序」这一档** ——
     * Qt 的 `setSortingEnabled` 就是这个行为，重新解析一次才会回到后端给的顺序
     */
    toggleSort(key: string) {
      if (this.sortKey === key) {
        this.sortOrder = this.sortOrder === 'asc' ? 'desc' : 'asc'

        return
      }

      this.sortKey = key
      this.sortOrder = 'asc'
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

    async parse(url: string, keyword?: string) {
      if (!url.trim()) {
        return
      }

      this.loading = true
      this.error = ''

      try {
        this._load(await parseApi.url(url.trim(), 1, keyword))
      } catch (e) {
        this.error = e instanceof Error ? e.message : String(e)
      } finally {
        this.loading = false
      }
    },

    /**
     * 批量解析：逐条解析，结果累加到同一张列表上
     *
     * ## 为什么在前端循环，而不是给后端开一个批量接口
     *
     * 桌面版是把整批链接交给 `DynamicParser`，在一个后台线程里顺序解析并往同一棵树上
     * 追加节点。这里改成逐条调 `/api/parse`：那个接口已经在用、已经有测试，而**进度与
     * 中途停下在前端天然就有** —— 做成一个长请求的话，二十条链接要等几十秒，
     * 期间没有任何反馈，还容易撞上网关超时。
     *
     * 代价是每条链接各自成为一个顶层节点，不像桌面版那样收在一个动态节点下面。
     *
     * ## 两条之间要等一下
     *
     * 连着打 B 站接口会被风控挡下（412），整批就废了。间隔取共用配置的
     * `auto_parse_interval`（桌面版自动解析分页用的也是它），读不到时按 2 秒。
     *
     * `onEach` 在每条解析完之后调用，交给调用方做「自动加入下载列表」那一步 ——
     * 建任务是 store 之外的事，不该塞进来
     */
    async parseBatch(
      urls: string[],
      options: {
        interval?: number
        onEach?: (nodes: ParseNode[]) => Promise<void> | void
        shouldStop?: () => boolean
      } = {},
    ) {
      if (!urls.length) {
        return
      }

      const interval = Math.max(0, options.interval ?? 2) * 1000

      this.loading = true
      this.error = ''
      this.batch = { done: 0, total: urls.length, failed: 0 }

      // 从空列表开始重新攒。沿用上一次的结果会让「共 N 项」和实际内容对不上
      const collected: ParseNode[] = []

      let lastError = ''

      try {
        for (const [index, url] of urls.entries()) {
          if (options.shouldStop?.()) {
            break
          }

          try {
            const result = await parseApi.url(url)
            const nodes = result.tree?.children ?? []

            collected.push(...nodes)

            // 每条都立刻并进列表，用户能看着它一条条长出来
            this._load({
              ...result,
              tree: { ...result.tree, children: [...collected] },
            })

            await options.onEach?.(nodes)
          } catch (e) {
            this.batch.failed += 1

            lastError = e instanceof Error ? e.message : String(e)
          }

          this.batch.done = index + 1

          if (interval && index < urls.length - 1 && !options.shouldStop?.()) {
            await new Promise((resolve) => setTimeout(resolve, interval))
          }
        }

        // 全军覆没时把最后一条错误摆出来，否则用户只看到一张空列表
        if (this.batch.failed && !collected.length) {
          this.error = lastError
        }
      } finally {
        this.loading = false
        this.batch = null
      }
    },

    /**
     * 交给服务端搜索：把关键词写回链接重新解析
     *
     * 用的是**后端返回的那条链接**而不是输入框里的原文 —— 短链已经跳转过，
     * 而关键词参数要拼在跳转之后的地址上
     */
    async serverSearch(keywords: string) {
      await this.parse(this.url, keywords)
    },

    /**
     * 本地筛选：标出命中的行并把它们的祖先展开
     *
     * 只高亮不过滤，与桌面版一致 —— 过滤掉其余行会让用户失去上下文，
     * 也没法看出命中项在整张列表里的位置。返回命中数量，交给调用方提示
     */
    searchLocal(keywords: string): number {
      this.searchKeyword = keywords

      if (!keywords) {
        return 0
      }

      const needle = keywords.toLowerCase()
      const hits: string[] = []

      for (const [id, node] of this._nodes) {
        if ((node.title || '').toLowerCase().includes(needle)) {
          hits.push(id)
        }
      }

      // 命中项藏在折叠的分组里就等于没找到，逐级展开它的祖先
      for (const id of hits) {
        let parent = this._parents.get(id) ?? null

        while (parent) {
          this.expanded.add(parent)

          parent = this._parents.get(parent) ?? null
        }
      }

      return hits.length
    },

    /**
     * 按序号批量勾选
     *
     * 判据与桌面版 `batch_select` 一致：节点的 `number` 落在给定的序号表里就勾上。
     * **不清除已有的勾选** —— 那边也是只加不减，可以分几次把要的都挑齐
     */
    batchSelect(numbers: number[]): number {
      const wanted = new Set(numbers)

      let count = 0

      for (const [id, node] of this._nodes) {
        if (node.is_node) {
          continue
        }

        const value = Number(node.number)

        if (Number.isFinite(value) && wanted.has(value)) {
          this.setChecked(id, true)

          count += 1
        }
      }

      return count
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

    /**
     * 建完任务后重新标一遍
     *
     * 不在本地直接把勾选项标成已下载：实际建出来的可能比勾选的少（需要二次解析的
     * 会被后端拦掉），本地硬标会标出一批其实没进队列的。重问一次数据库最准，
     * 也就一次请求
     */
    async refreshDownloaded() {
      await this.checkDownloaded()
    },
  },
})
