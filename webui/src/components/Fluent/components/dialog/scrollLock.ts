// 对话框打开时锁住页面滚动
//
// ## 为什么要计数
//
// 对话框里还能再开对话框（下载选项里的优先级编辑器、弹幕样式、说明框）。
// 各自「开的时候设 hidden、关的时候清空」的话，内层一关就把外层的锁也解了 ——
// 外层还开着，背后的页面却已经能滚，滚一下对话框下面的内容就跑掉了。
//
// ## 为什么单独一个文件，而不是写在 FluentDialog.vue 里
//
// **`<script setup>` 里没有模块作用域**：那里面的顶层声明会被编译进 setup 函数，
// 于是每个组件实例各拿一份自己的计数器 —— 计数当场失效，而且看起来完全正常
// （两个对话框各数各的，都是 1，内层关掉时它那份归零就清了 overflow）。
// 我写出来过一次，靠实测「开说明框再关掉，外层的滚动锁没了」才发现。
//
// 放进普通的 .ts 模块，才是真正全局唯一的一份。

let count = 0

function apply() {
  if (typeof document === 'undefined') {
    return
  }

  document.body.style.overflow = count > 0 ? 'hidden' : ''
}

/** 加一把锁。调用方负责配对调用 release() */
export function acquire() {
  count += 1

  apply()
}

/** 解一把锁。多解不会把计数减成负数 —— 那会让之后真开一个对话框也锁不住 */
export function release() {
  count = Math.max(0, count - 1)

  apply()
}

/** 当前有几把锁。给测试与排查用 */
export function lockCount() {
  return count
}
