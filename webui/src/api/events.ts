// 增量事件的 WebSocket 客户端（对应后端 S3-9）
//
// ## 顺序不能反
//
// **先拉快照拿到 cursor，再带着它连 WebSocket**（`?since=cursor`）。反过来的话，
// 连上之后到快照返回之间的那些事件会被当成「快照已包含」而丢掉。
// 这条缝只在状态恰好落在两步之间时出现 —— 平时测不出来，上线后表现为
// 「进度条偶尔卡住，刷新一下就好了」。
//
// ## 三种要重新拉快照的情况
//
// 1. 服务端回 `resync`（缓冲区滚过去了、后端重启导致编号回退、这个连接积压太多）
// 2. 收到的 `seq` 不连续 —— 说明中间漏了
// 3. 断线重连后补不上
//
// 都归到同一个回调上，调用方只要实现「重新拉一次快照」这一件事。

/** 服务端推来的一条事件 */
export interface ServerEvent {
  seq: number
  type: string
  data: unknown
}

export interface EventStreamOptions {
  /** 收到一条正常事件 */
  onEvent: (event: ServerEvent) => void
  /** 需要重新拉快照。参数是服务端当前的编号（可能没有） */
  onResync: (seq?: number) => void
  onOpen?: () => void
  onClose?: () => void
}

// 重连退避：首次 0.5 秒，每次翻倍，封顶 10 秒。与后端 aria2 客户端的策略一致
const INITIAL_DELAY = 500
const MAX_DELAY = 10_000

export class EventStream {
  private socket: WebSocket | null = null
  private timer: number | null = null
  private delay = INITIAL_DELAY
  private cursor = 0
  private closed = false

  constructor(private options: EventStreamOptions) {}

  /** cursor 来自快照的返回值 */
  connect(cursor: number) {
    this.cursor = cursor
    this.closed = false

    this.open()
  }

  close() {
    this.closed = true

    if (this.timer !== null) {
      window.clearTimeout(this.timer)

      this.timer = null
    }

    // 先摘掉 onclose 再关：否则关闭会触发重连，而我们正是要停下来
    if (this.socket) {
      this.socket.onclose = null
      this.socket.close()
      this.socket = null
    }
  }

  private url(): string {
    // 同源 + 相对路径：开发时由 vite 代理转发（要开 ws: true），部署时直接同源。
    // 写死 host 的话反向代理下就连不上了
    const scheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:'

    return `${scheme}//${window.location.host}/api/ws?since=${this.cursor}`
  }

  private open() {
    if (this.closed) {
      return
    }

    let socket: WebSocket

    try {
      socket = new WebSocket(this.url())
    } catch {
      this.scheduleReconnect()

      return
    }

    this.socket = socket

    socket.onopen = () => {
      // 连上了才把退避重置。放在 onclose 里重置会让「连上就断」变成死循环重试
      this.delay = INITIAL_DELAY

      this.options.onOpen?.()
    }

    socket.onmessage = (event) => this.dispatch(event.data)

    socket.onclose = () => {
      this.socket = null

      this.options.onClose?.()

      this.scheduleReconnect()
    }

    // onerror 之后必定跟一个 onclose，重连交给那里做，这里不重复
    socket.onerror = () => {}
  }

  private dispatch(raw: unknown) {
    if (typeof raw !== 'string') {
      return
    }

    let message: ServerEvent

    try {
      message = JSON.parse(raw)
    } catch {
      return
    }

    if (message.type === 'resync') {
      // 服务端补不上了。它给的 seq 是当前编号，重新拉快照时会拿到更新的，
      // 所以这里不急着更新 cursor —— 由快照的返回值来更新
      this.options.onResync(message.seq)

      return
    }

    if (typeof message.seq !== 'number') {
      return
    }

    // 编号不连续说明中间漏了。**不能装作没看见**：漏掉的可能正是「任务完成」那一条，
    // 界面会永远停在 99%
    if (this.cursor && message.seq !== this.cursor + 1) {
      this.options.onResync(message.seq)

      return
    }

    this.cursor = message.seq

    this.options.onEvent(message)
  }

  /** 重新拉过快照之后，用新的游标接着收 */
  resume(cursor: number) {
    this.cursor = cursor
  }

  private scheduleReconnect() {
    if (this.closed || this.timer !== null) {
      return
    }

    const delay = this.delay

    this.delay = Math.min(this.delay * 2, MAX_DELAY)

    this.timer = window.setTimeout(() => {
      this.timer = null

      // 断线期间的事件多半已经滚出服务端的缓冲区，重连后先当作要重新同步 ——
      // 服务端补得上的话会照常发增量，补不上会回 resync，两种都对
      this.open()
    }, delay)
  }
}
