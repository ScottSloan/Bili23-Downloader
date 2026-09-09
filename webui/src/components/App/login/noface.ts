/**
 * 未登录时的默认头像
 *
 * 桌面版用的是打进资源里的 `:/bili23/image/noface.jpg`（`gui/component/profile.py`、
 * `main_window.py` 都引它）。Web 端直接用 B 站自己那张同名图 —— 为一张默认头像
 * 往前端包里塞一份二进制不划算，而这个地址与桌面版那张本来就是同一张。
 *
 * 引用它的 `<img>` 必须带 `referrerpolicy="no-referrer"`：B 站的图床对 Referer
 * 有校验，带着本站地址过去会被拒，表现是头像位置一片空白。
 *
 * 拿不到时（离线、图床抽风）浏览器会画一个碎图图标，比原先那个纯灰圆好认 ——
 * 至少能看出「这里本该有张头像」。
 */
export const NOFACE_URL = 'https://i0.hdslb.com/bfs/face/member/noface.jpg'
