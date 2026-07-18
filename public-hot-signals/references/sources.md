# Public Source Notes

The collector normalizes all providers into one artifact. Each signal retains `platform`, `source`, `title`, `url`, `rank`, `hot_value`, `snippet`, and `collected_at`.

| ID | Intended use | Caveat |
|---|---|---|
| `baidu` | General Chinese current-event signal | Parses the public realtime board HTML; markup can change. |
| `toutiao` | General Chinese current-event signal | Reads a public hot-board endpoint; availability can vary. |
| `douyin`, `zhihu`, `bilibili`, `ithome`, `juejin` | Platform-specific signal | Uses a public aggregation endpoint. Treat it as a convenience feed, not an authoritative platform API. |
| `36kr` | Technology/business signal | Uses a public aggregation endpoint. |
| `github` | Developer/open-source signal | Parses GitHub Trending and falls back to GitHub Search for recently created, highly starred repositories. |

Choose sources according to the current request. For example, a consumer topic may use `baidu,toutiao,zhihu,bilibili`; a developer topic may use `github,juejin,ithome`.

Collection metadata is evidence of attention, not evidence that a title's factual content is true. Verify claims separately before publishing.
