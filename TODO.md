# TODO

## 下个版本

### 解析内容的筛选与排序

个人空间、收藏夹、历史记录、稍后再看的接口除关键词外，还支持分区、排序等筛选条件，目前链接中携带的这些参数一律被忽略，接口参数使用的都是默认值。

各接口现有的相关参数（见对应 parser 中已拼好的 `params`）：

| 内容 | 文件 | 参数 |
| --- | --- | --- |
| 个人空间 | `src/util/parse/parser/space.py` | `tid`（分区）、`order`（排序） |
| 收藏夹 | `src/util/parse/parser/favlist.py` | `tid`（分区）、`order`（排序）、`type` |
| 历史记录 | `src/util/parse/parser/history.py` | `business`（类型）、`add_time_start` / `add_time_end`（时间范围）、`arc_min_duration` / `arc_max_duration`（时长范围） |
| 稍后再看 | `src/util/parse/parser/watch_later.py` | `viewed`（是否已观看）、`asc`（排序方向） |

具体可选值需对照 B 站接口确认后再实现。

实现方式可沿用 2.14.0 的关键词搜索：筛选条件同样随链接传递，由 `src/util/parse/search_url.py` 统一负责与链接的互转，这样翻页、自动解析分页、解析历史都无需额外改动即可保持筛选状态。界面入口可考虑与搜索对话框合并，或另做筛选面板。
