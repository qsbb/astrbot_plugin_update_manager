# 凝心溯溪 UI 全局诊断（2026-09-13）

## 范围

知、言、序、情、境、声、临、核 8 个在维仓库的 Plugin Page，以及核独立 WebUI。
本轮不包含通和枢；服务器只读，截图中的线上状态不代表本地已发布代码。

## 结论

- 8 个在维 Page 已统一接入 `series.ui@1.0` Glass Aurora。
- 核独立 WebUI 的旧资源路径 `./series-ui.css` 已修正为 `/static/series-ui.css`，这是线上仍显示旧视觉的直接原因。
- 临的线上截图仍是 1.4.0 深色旧界面；本地源码已到 1.7.0，使用 Glass 控件，属于未部署/未更新，不是本地漏改。
- 系列接管已从“插件清单”改为“功能域分类”，不再直接展示插件 ID 或模块名称。

## 必须保留

- owner 才能执行的更新、回滚、停用、人格转换、账号删除。
- revision 乐观锁、二次确认、幂等 request id、失败回滚。
- 凭据/令牌/密钥只显示配置状态，不回显值。
- 诊断日志、来源依据、执行结果、恢复点和状态原因。
- 每个插件的 standalone Page，核缺失或接管关闭时继续可用。

## 可以精简

- 把 `契约发现` 与 `管理边界` 两个固定指标合并为状态条，不占用统计卡。
- 表格中的 UID、完整会话标识、内部人格 ID 默认显示短名，完整值放 `title`。
- 时间统一显示 `MM-DD HH:mm`，完整时间放悬停提示。
- 诊断成员不再为每个插件重复显示“可读取”，改为 `正常/未就绪/有断层` 汇总。
- 配置页按“模型、网络、运行、监听”分组；监听类配置的 5 个字段折叠为一个分组。
- 管理页不再展示插件 ID；调试需要时放入详情或导出摘要。

## 当前缺失/遗漏

- 长表格缺少“列宽策略”和“详情展开”的通用规范。
- 设置页缺少统一的未保存修改提示。
- 长 ID/来源缺少通用截断组件，当前已先在知和情页面局部修复。
- 插件页与独立 WebUI 之间缺少统一返回入口。
- 核独立 WebUI 的线上静态资源部署缓存仍需部署后验证。

## 页面诊断

| 页面 | 已发现 | 处理 |
|---|---|---|
| 知 | 更新时间换行、来源显示完整 UMO、操作列拥挤 | 时间压缩到单行，来源显示“会话”，完整值保留 title；移动端列宽已收敛 |
| 言 | 原页面信息量偏少，统计与功能状态缺少层次 | 统计卡、状态标签、移动端两列布局已统一 |
| 序 | 旧按钮、输入框、表格视觉分散 | 统一切换到共享控件；状态色保留语义色 |
| 情 | 关系人格显示完整自动 ID | 显示“默认人格”或“自动 · 末4位”，完整值放 title |
| 境 | “使用当前设备位置 / 保存并校验”折成两行 | 文案改为“使用当前位置 / 保存校验”，按钮禁止拆词 |
| 声 | 音色卡片、上传区、波形、设置区视觉分裂 | 统一玻璃面板和控件，保留专用波形与试听结构 |
| 临 | 线上仍是旧深色页面，控件不统一 | 本地版已用共享控件、CSS hash 校验通过；需要部署新版本才能线上生效 |
| 核 | 系列接管按插件列出、日志能力标签重复、资源路径错误 | 系列接管改为八个功能域；诊断摘要改为汇总状态；静态资源路径改为 `/static/` |

## 功能域分类

- 对话与消息：沉默、分段、防抖、插话、话题承接、上下文预算、群聊语境。
- 身份与权限：身份识别、行动授权、群管理、入群审核、权限否决。
- 关系与情绪：好感、信任、熟悉度、关系性质、情绪建议、账号归属。
- 知识与记忆：检索、验证、图谱、记忆管理、导入导出。
- 环境与时间：时间、天气、空气质量、日历、预警、主动关心。
- 语音与表达：语音合成、音色、情绪映射、语音导演、音频试听。
- 具身与设备：设备配对、会话桥接、角色动作、人格模式、实时诊断。
- 更新与治理：每日规则、镜像、推荐、更新回滚、模型角色、全局设置。

## 截图索引

- 前后对比：`/home/lingxi/.codex/visualizations/2026/09/12/01a095b4-bc18-7f22-adc8-639e15437c73/glass-ui/ui-diagnostic-before-after.png`
- 全部 Page 汇总：`/home/lingxi/.codex/visualizations/2026/09/12/01a095b4-bc18-7f22-adc8-639e15437c73/glass-ui/all-pages-glass-overview.png`
- 功能域接管：`/home/lingxi/.codex/visualizations/2026/09/12/01a095b4-bc18-7f22-adc8-639e15437c73/glass-ui/series-takeover-functional-groups.png`

## 修复批次（2026-09-13，未提交 / 未推送）

本节记录在只读审查之后落地的第一批修复。所有仓库仍保留未提交工作树，未提交、未推送、未部署。

### P0 已修复并完成浏览器验证

- 共享静态弹窗：`ui/series-ui.css` 将 `.modal-backdrop` 降为 `position:absolute; z-index:0`，`.modal-card` 提升为 `position:relative; z-index:1`，并补齐 header/body/footer 的 flex 滚动结构。知页设置弹窗真实点击命中 `.modal-card`。
- 情页关系明细：`pages/manager/app.js` 将不存在的 `escapeHtmlAttr()` 改为已定义的 `escapeHtml()`；非空关系列表可正常渲染，删除/编辑入口恢复。
- 临快速绑定：`pages/operator/index.html` 将 `#quick-pairing-modal` 与 `#toast` 移出 `<main class="shell">`；390px 首屏可见弹窗且命中 `.qp-dialog`。
- `SeriesUI.confirm()` 的多行消息已启用 `white-space: pre-line`。

### P1 已修复

- 知：URL 来源表单改为单列，来源项改为四列网格；黑话表不再继承 960px 最小宽度；移动端主记忆表恢复作用域/来源/更新时间并使用卡片 meta 行；详情弹窗桌面改为双列布局。
- 言：补齐 17 项运行统计，按“响应决策 / 输出节奏 / 上下文预算”分组；新增版本、更新时间与刷新失败后的旧数据提示；hero 恢复 flex 布局，steering 改为中文说明。
- 序：群表删除 11 列旧宽度并改为当前 5 列模型；780px 媒体查询调整到 560px 之前；新增“待审申请 / 群配置 / 目标群聊 / 设置与诊断”四个顶层 tab；移除目标群改用 `SeriesUI.confirm`。
- 情：多人格删除确认改为整行插入，避免 1440px 下操作列越界。
- 境：390px 下短指标卡恢复 2 列，不再全部单列。
- 声：推荐流程默认折叠；hero 状态卡改为 2×2 并显示真实音色/提供商数量；手填 provider ID 收入折叠项；复制地址跟随监听 host；9 个无标签控件补齐 `aria-label`；新增分区锚点导航和移动端 sticky 保存/诊断快捷栏。
- 临：快速绑定和 toast 已提升到 body 层；原生 `confirm/prompt` 迁移到 `SeriesUI.confirm/prompt/copy/toast`；对话与模型页新增二级锚点导航。
- 核独立 WebUI：移动端导航改为可横向滚动的 9 个入口，并新增 `aria-current`；导航数据提升为模块级 `NAV_ITEMS`，避免 `links` 作用域回归。
- 核 Plugin Page：旧 dark 通用层改为浅色兼容别名，按钮/卡片/胶囊/镜像/开关等深色硬编码改为玻璃色；原生 prompt/confirm 迁入统一确认组件；诊断终端样式保留。
- 共享交互：`SeriesUI` 正本修改后已通过同步器写入 8 个 Page 与核 WebUI，`series.ui 1.0.0: ok`。

### 仍待处理

- 序：当待审申请或群数量很大时，活动 tab 仍需要分页或“显示更多”。
- 声：AI 导演、外部 API、访问控制三块在 390px 下仍很长；已加锚点导航和 sticky 快捷栏，仍可进一步做折叠。波形保持为播放状态指示，不引入 WebAudio。
- 临：“对话与模型”已加二级锚点导航，但仍可继续做真正的子 tabs/折叠；快速绑定弹窗的 Escape、焦点陷阱、焦点归还仍可继续完善。
- 知：设置与配置仍有信息架构重叠；高级 JSON 配置可增加分组/搜索；`summary` 内嵌按钮的语义问题仍待修。
- 言：已补当前配置摘要；loading/skeleton 仍可继续完善。
- 核 Plugin Page：旧业务规则已转为浅色兼容层，但尚未完全物理删除；后续应保留诊断终端，其余通用规则继续下沉到 `series-ui`。
- 审计工具：`core/series_ui.py` 仍只校验资源哈希与加载顺序，尚未静态禁止原生 `alert/confirm/prompt` 或页面自建 toast。

### 验证基线

- 浏览器 P0 回归：知弹窗真实点击、情非空关系渲染、临移动端快速绑定首屏可见，全部通过。
- 浏览器 P1 回归：核独立 WebUI 390px 九个导航入口逐项可达；序 1440/390px 四个 tab 逐项可达且无 pageerror。
- 全量测试：核 318、知 703（3 skipped）、言 453 + 384 subtests、序 468、情 297 + 26 subtests、境 132、声 193 + 6 subtests、临 600（8 skipped），全部通过。
- `series.ui 1.0.0: ok`；8 个 Page 与核 WebUI 的 vendored `series-ui.css/js` 仍与正本逐字节一致。
- 本轮未提交、未推送、未部署；`CONVENTIONS.md` 仅在核仓库保留，其他插件仓库没有副本；`orchestration_hub` 本地不存在，本轮未访问、未修改。

## 第二批：完整开发（2026-09-13，未提交 / 未推送 / 未升版本）

### 共享 UI 与交互

- `SeriesUI.dialog(options)` 已落地：支持标题、可移动 body、异步 actions、busy 状态、Escape、点击遮罩关闭、Tab 焦点陷阱、关闭后焦点归还和背景 inert。
- `SeriesUI.confirm/prompt` 已复用同一 dialog 内核；现有调用保持兼容。
- 8 个 Page 与核 WebUI 的反馈统一走 `SeriesUI.toast`；页面自定义 `toast/showToast` 实现和静态 `#toast` 节点已移除，SeriesUI 缺失时仅保留内联错误横幅降级。
- `series-ui` 正本修改后已同步到 8 个 Page 与核 WebUI；本轮不升版本号。

### 知

- “设置”和“全部配置”已合并为一个设置中心：`LLM / 学习 / 搜索与领域 / URL 来源 / 其它 / 全部配置`。
- 全部配置保留 46 项 `_conf_schema.json` 字段，并按“记忆与检索 / 向量与图谱 / LLM 与性能 / 搜索与来源 / 主动学习 / 黑话与学习 / 其它”分组；新增按 key/description 搜索。
- 日志折叠面板的按钮/checkbox 已移出 `summary`，消除嵌套交互元素。

### 序

- 待审申请、群配置、目标群聊改为客户端渐进显示，每批 20 条，支持“显示更多 / 收起”。
- 刷新重置到 20 条，切换 tab 保留当前批次数；全选继续作用于完整结果集并在摘要中明确提示。
- 后端 join-review API 未修改。

### 声

- AI 风格导演、外部 TTS API、访问控制三块新增 `mobile-fold`：390px 默认折叠，桌面端始终展开。
- 分区锚点导航与 sticky 保存/诊断快捷栏保留；折叠不会隐藏保存状态、错误、授权或诊断结果。
- 波形继续保持播放状态指示，不引入 WebAudio。

### 临

- “对话与模型”锚点导航升级为三个真实二级 tab：模型与决策、语音、平台与集成；保留全部原有 DOM id 和保存接口。
- 快速绑定迁移到 `SeriesUI.dialog`，保留二维码、6 位配对码、倒计时、复制、撤销、重新生成和关闭；补齐 Escape、焦点陷阱、背景 inert 和关闭后焦点归还。
- 页面架构文案已统一为“普通对话走临专属链路、不进入 AstrBot EventBus”，消除旧 EventBus 表述冲突。

### 言

- 首屏统计、能力状态、配置摘要新增 skeleton；`.shell` 使用 `aria-busy`，成功后清除。
- 刷新失败保留旧数据并显示 stale 提示；首次失败显示明确空状态；skeleton 尊重 `prefers-reduced-motion`。

### 核 Plugin Page / WebUI

- 核 Page 旧 `:root`、全局 body/button/input/select、页面级 dialog/#toast、全局 button hover/transition 规则已物理删除；剩余业务样式改用 `--si-*`。
- 原生 `#confirmation-dialog` 和原生 confirm/prompt 回退已移除，统一使用 `SeriesUI.confirm/prompt`。
- 诊断终端样式保留并局部化；核 Page / WebUI 1440、390 截图回归通过。

### 静态交互审计

- `core/series_ui.py` 新增 `audit_interactions(root)`。
- 硬错误：原生 `alert/confirm/prompt`、页面自定义 `toast/showToast`、静态 `#toast`。
- 警告：仍由页面持有的静态业务 modal；当前仅有知的业务弹窗产生 warning，无硬错误。
- `check` 继续校验资源哈希与加载顺序，并打印 warning、对硬错误返回失败；`sync/check` 参数保持兼容。

### 最终验证

- 全量测试：核 322、知 705（3 skipped）、言 454 + 384 subtests、序 469、情 297 + 26 subtests、境 132、声 194 + 6 subtests、临 601（8 skipped），全部通过。
- 浏览器回归：
  - `SeriesUI.dialog`、confirm、prompt、Escape、焦点进入/归还全部通过。
  - 知设置中心两个入口、全部配置分组搜索、footer 切换通过。
  - 序 45 条数据验证 20 → 40 → 45、收起、tab 切换通过。
  - 声 390px 折叠默认关闭、手动展开、1440px 始终展开通过。
  - 临二级 tab 键盘切换、配对弹窗复制/撤销/关闭、Escape 和焦点归还通过。
  - 言 skeleton、aria-busy、stale 提示通过。
  - 核 WebUI 390px 九个导航入口逐项可达；核 Page/WebUI 1440、390 无 pageerror。
- `series.ui 1.0.0: ok`；交互审计无硬错误。
- 本轮未提交、未推送、未部署；`orchestration_hub` 未访问、未修改；`CONVENTIONS.md` 仍只在核仓库保留。

## 第三批：对抗性复核修复（2026-09-13，未提交 / 未推送）

两个只读子智能体复核后，发现并修复了共享 dialog、toast、页面时序和竞态问题：

### 共享 UI

- 嵌套 dialog：新 dialog 打开时，下层 dialog card 自动 `inert` / `aria-hidden`；关闭后恢复新的顶层。
- Escape：最上层 dialog 消费事件后调用 `stopPropagation()`，不再连带关闭页面底层静态弹窗。
- confirm：默认焦点回到“确认”按钮，回车不会再触发取消；confirm/prompt 显式 `closeOnBackdrop:false`，保持旧交互兼容。
- prompt：输入框仍保持初始焦点。
- dialog 增加 `aria-labelledby`、标题唯一 id、focusin 兜底和 `onClose` 异常保护。
- toast 层提升到 dialog 之上（z-index 1400），打开 dialog 时不再被 inert / aria-hidden，屏幕阅读器可继续播报。
- 核 WebUI 旧 `.toast` 覆盖已删除；连续两个 toast 现在会垂直堆叠而不是重叠。

### 页面状态与竞态

- 知：搜索前先 `syncConfigFormState()`，不再丢失未保存编辑；其它 tab 保存后会让高级配置缓存失效并在下一次打开时重载；`escapeHtmlAttr()` 现在正确转义属性值。
- 言：仅首次加载显示 skeleton；刷新时保留旧数据，失败只显示 stale；Bridge 缺失时清除 `aria-busy` 并显示错误空态。
- 声：`bindMobileFolds()` 移到 `await resolveBridge()` 之前，Bridge 延迟时首屏仍会正确折叠；新增 `data-toast-fallback` 并删除死 `#toast` CSS。
- 序：`showStatus()` / `showPageError()` 优先走 `SeriesUI.toast`，`.toast-stack` 仅保留为共享 UI 缺失时的降级。
- 临：快速绑定增加 `qpCreateToken` 代次；关闭弹窗后，在途的 `pairing/create` 响应不会再设置状态或启动轮询。
- 情、声、核 WebUI 的页面级 toast 残留清理完成；知、情、声、核 WebUI 增加内联 toast 降级节点。

### 审计加固

- `audit_interactions()` 现在识别 `window?.confirm`、`globalThis.prompt`、`self.confirm`、`const toast =` 等变体。
- 新增页面 CSS 的 `#toast` 硬错误和页面级 `.toast` 覆盖 warning。
- 新增“`notify()` 但无内联降级节点”warning。
- 当前审计结果仍只有知的静态业务 modal warning，无硬错误。

### 最终验证（更新）

- 全量测试：核 322、知 706（3 skipped）、言 454 + 384 subtests、序 470、情 297 + 26 subtests、境 132、声 194 + 6 subtests、临 601（8 skipped），全部通过。
- 新增浏览器回归：
  - dialog 嵌套 inert、Escape 不冒泡、confirm 默认焦点、toast 不被 inert 全部通过。
  - 知编辑后搜索保留 777、综合设置保存后高级配置重新请求 schema 通过。
  - 言刷新失败保留旧数据且 skeleton 为 0 通过。
  - 声 Bridge 延迟 1.2s 时首屏仍为折叠通过。
  - 临生成请求中关闭弹窗后 `pairing/status` 调用数为 0 通过。
  - 核 WebUI 连续两个 toast 垂直堆叠通过。
- `series.ui 1.0.0: ok`；`git diff --check` clean。
- 本轮仍未提交、未推送、未部署；`orchestration_hub` 未访问、未修改。

## 第四批：任务优先 UI 结构改造（2026-09-13，未提交 / 未推送）

### 已完成

- **共享组件**：新增 `si-summary-strip`、`si-metric-row`、`si-tabbar`、`si-subnav`、`si-disclosure`、`si-actionbar`、`si-master-detail`、`si-filter-bar`、`si-data-list`、`si-problem-list`、`si-source-status`、`si-skeleton`、`si-empty`、`si-mobile-more-sheet` 和 `SeriesUI.bindTabs()`；正本同步到 8 个 Page 与核 WebUI。
- **核 WebUI**：移动端导航移出 `.shell`，改为“3 个主入口 + 更多”sheet；排除 `#app` 的共享 shell `backdrop-filter`，底栏现在固定在 390×844 视口底部。
- **临**：修复 `.dialogue-tabs` / `.dialogue-panel` 在双列 grid 中的错位；主导航上移到服务摘要之前并 sticky，390px 首屏可见。
- **知**：日志和验证详情移到记忆表之后；移动端每页 10 条；统计卡移动端保持 2 列；高级配置保存栏 sticky；首条记忆进入 390px 首屏。
- **声**：后端选择上移到工作台状态之前；移动端隐藏 Hero 状态面板；分区导航 sticky；后端选择在移动端首屏可见。
- **核 Page**：默认 tab 从日志改为总览，总览排到第一位。
- **境**：实时检查新增数据源错误、组件错误、官方预警不可用原因和重试提示。
- **情**：新增独立“关系明细”tab；增加搜索筛选；桌面 20 条、移动端 10 条渐进显示；关系总览不再直接承载全部明细。
- **序**：待审申请增加状态/群/关键词筛选；移动端每批 10 条；申请卡移动端压缩；修复长群名横向溢出。

### 尚未完成（后续批次）

- 情：账号归属移动端全屏 sheet、设置折叠分组和 sticky 保存、总览策略与逻辑合并。
- 序：群配置筛选和 sticky 批量栏、全部关闭影响确认、目标群表单折叠、模拟申请默认折叠。
- 声：4 个任务 tab、状态去重、音色+试听 master-detail、访问控制规则表和编辑抽屉。
- 临：绑定 stepper、诊断二级 tab、人格主从布局与 sticky 操作、模型文案统一。
- 核 Page：推荐与目录合并、设置子 tab、诊断问题聚合。
- 核 WebUI：版本信息去重、设置子导航、诊断影响范围与建议动作、安全账户移动卡片。
- P2：图表点击筛选、键盘快速审批、自动刷新、长 ID 复制、技术词 tooltip、排序等。

### 本批验证

- 全量测试保持全绿：核 322、知 706（3 skipped）、言 454 + 384 subtests、序 470、情 297 + 26 subtests、境 132、声 194 + 6 subtests、临 601（8 skipped）。
- 浏览器回归通过：核 WebUI 底栏视口可见且 3+6 入口可达；临主导航首屏可见且二级 tab 全宽；知首条记忆进入 390px 首屏；声后端选择进入首屏；序 10 条批量和筛选可用；情 10/20 条渐进与搜索可用；境错误源与重试提示可见；核 Page 默认总览。
- `series.ui 1.0.0: ok`；`git diff --check` clean。
- 本轮仍未提交、未推送、未部署；`orchestration_hub` 未访问、未修改。

## 发布批次（2026-09-13，补丁版本）

- 知 `1.8.1`
- 言 `0.12.1`
- 序 `0.8.1`
- 情 `0.12.1`
- 境 `0.6.1`
- 声 `0.12.1`
- 临 `1.7.1`
- 核 `0.19.1`

本次发布包含任务优先 UI 结构改造、共享布局组件、P0 阻断修复和对应 CHANGELOG 记录。发布后仍需继续处理第四批“尚未完成”中的 P1/P2 项。

## 第五批：任务优先 UI 续做（2026-09-13，未升版本、未提交）

本批在发布批次之后继续，未提升任何版本号（知 1.8.1 / 言 0.12.1 / 序 0.8.1 / 情 0.12.1 / 境 0.6.1 / 声 0.12.1 / 临 1.7.1 / 核 0.19.1 保持不变）。

### 声（astrbot_plugin_voice_hub）

- 新增四个真实任务 tab：`总览 / 后端与音色 / 对话与交付 / 接口与权限`；移除与真实 tab 冲突的锚点 `.section-nav`。
- 语音后端选择改为**常驻作用域切换器**：不属于任何 tab 面板，移动端 390×844 首屏完整可见；`applyPanelVisibility()` 把“任务 tab 显隐”和“后端 scope 显隐”相乘，解决两者互相覆盖导致空面板的问题。
- 移动端 Hero 收紧：说明文字两行截断、动作按钮两列；后端选项在移动端只保留标题，后果由实时说明承担。
- 音色库 + 试听改为 master-detail；访问控制改为规则表（管理员/群白/群黑/私白/私黑）+ 编辑抽屉，计数随输入实时更新。
- 页面 CSS 不引入 `backdrop-filter`（保持既有约束）。

### 情（astrbot_plugin_relationship）

- 设置中心新增搜索（名称 / key / 说明）、只看已修改、未保存计数 chip（含无效数字提示），与既有 sticky 保存栏同区。
- 配置分组改为 `si-disclosure`，默认只展开“情绪追踪”；筛选时空分组自动隐藏并给出空态。
- 账号归属：≤900px 点击新建/编辑改为 `SeriesUI.dialog` 全屏 sheet，关闭后编辑器归还原位（Escape/焦点归还可验证）。
- 总览“关系逻辑”并入“关系策略”卡内的折叠区，视觉网格改单列。

### 序（astrbot_plugin_identity_guardian）

- 待审申请、群配置、目标群三块都支持筛选；本批补齐目标群状态 + 关键词筛选、过滤计数提示与空态。
- 完整加载时筛选条件连同输入框一起复位（此前只复位变量不复位 DOM）。
- 登记目标群 / 邀请成员 / 模拟申请折叠；批量栏 sticky；“全部关闭”二次确认显示影响群数。

### 临（astrbot_plugin_embodiment_bridge）

- 页头状态压缩为一个 chip；能力健康折叠为一行摘要（健康显示“8 项全部可用”，异常自动展开并显示“N 项不可用”，用户手动收起后不再强开）。
- “运行”分区升级为真实二级 tab：`服务 / 集成 / 诊断`；诊断根因出现或变化时一次性自动定位到诊断分区，用户手动选过 tab 后不再抢焦点。
- 新增“设备绑定四步”stepper（服务地址 → 平台实例 → 基础身份 → 快速绑定），显示已完成/待补充、4 步进度摘要，并可一键跳到对应 tab 与字段（含焦点）。
- 人格编辑器的转换/保存/启用统一为共享 `si-actionbar`；`.persona-panel` 不再 `overflow:hidden`，sticky 才能吸附到视口。

### 核 Page（astrbot_plugin_update_manager/pages/manager）

- “系列推荐”和“目录”合并为单一“推荐与目录”tab：范围筛选（全部 / 系列推荐 / 其他目录 / 有更新）+ 搜索 + 计数摘要 + 跳转“更新与回滚”。
- 系列推荐里已出现的模块不再在目录列表重复渲染，消除同一插件两套版本信息。
- 诊断新增问题聚合：按模块 + 错误码分组 ERROR/WARNING，展示影响范围与建议动作，点击一组可按模块与错误码筛选下方事件流；事件流与详情折叠保持原样。

### 核 WebUI（astrbot_plugin_update_manager/webui）

- 模块总览去掉“更新”列，改为“有更新 N 个 + 查看更新与回滚”入口；版本详情只在“更新与回滚”呈现。
- 系列推荐把“最新版本”并入状态药丸（`可更新 → vX`），不再单开一列。
- 设置页新增四段子导航（模型路由 / 运行项 / 完整配置 / 解析快照），tab 状态跨整页重绘保留。
- 诊断问题项补齐影响范围与按错误码推导的建议动作（纯前端派生，不新增后端字段）。
- 安全与账户的管理员列表由表格改为账户卡片，移动端 390px 无横向溢出。

### 本批验证

- 全量测试：核 323、知 706（3 skipped）、言 454 + 384 subtests、序 471、情 297 + 26 subtests、境 132、声 196 + 6 subtests、临 604（8 skipped），全部通过。
- 浏览器回归：声 4 tab × 后端 scope 组合、计数实时更新、无横向溢出；情 设置搜索/只看已修改/脏计数/sheet 打开与 Escape 归还；序 目标群筛选与折叠；临 能力折叠、运行二级 tab、根因自动定位、四步绑定与跳转聚焦；核 Page 推荐与目录合并、范围筛选、诊断问题聚合与点击筛选；核 WebUI 版本去重、设置子导航、诊断影响与建议、安全账户卡片。
- `series_ui check`：`series.ui 1.0.0: ok`（保留既有 warning：知页面静态业务弹层为页面自有例外）；8 仓 `git diff --check` 均 clean。
- 本轮仍未提交、未推送、未部署；`orchestration_hub` 未访问、未修改；未在任何其他仓库创建 `CONVENTIONS.md` 副本。

### 仍未完成

- 核 Page：设置区子导航（运行配置 / 自动更新 / 控制中心账户 / 镜像与网络），需要保持单一 `#config-form` 提交语义。
- P2：图表点击跳转筛选、键盘快速审批、自动刷新开关、长 ID 短显示 + 复制、技术词 tooltip、按最后互动排序。

## 第六批：剩余 P1/P2 收尾（2026-09-13，未升版本、未提交）

沿用 0.0.1 补丁版本号（知 1.8.1 / 言 0.12.1 / 序 0.8.1 / 情 0.12.1 / 境 0.6.1 / 声 0.12.1 / 临 1.7.1 / 核 0.19.1），只补齐 UI/交互。

### 核 Page（设置区子导航）

- 顶部 6 个 tab 收敛为 5 个：`总览 / 推荐与目录 / 设置 / 日志` 中的“设置”合并原“配置”和“镜像加速”。
- 设置区内新增 `si-subnav` 四个真实子分区：**运行配置 / 自动更新 / 控制中心账户 / 镜像与网络**；面板承载改为 `div[data-si-panel]`，保留 `#config-form`、`#rule-form`、`#webui-admins`、`#mirror-list`、`#mirror-add-form` 等全部原有 id 与保存接口。
- `sectionLoaders` 合并为 `settings: loadSettingsPanel`（config + rule + mirrors 并行加载）；首次进入设置 tab 若加载失败会补拉，并保留 `#config`/`#mirrors` 锚点以便深链。

### 知（长 ID 短显示 + 复制）

- 新增 `shortId()` / `idChip()` / `scopeCell()`：记忆表、纠错表、详情弹窗、调试作用域列表里的作用域 ID 一律显示“首尾 + 省略号”，点击通过 `SeriesUI.copy` 复制完整值并 toast 反馈。
- 作用域下拉改用 `option.dataset.scopeType / scopeId` 传值，修掉原来 `split(":", 2)` 会把含冒号的 UMO 截断的问题（现在带冒号的 scope_type 也能正确筛选）。

### 言（首屏比率 + 完整配置）

- 首屏新增“关键比率”组：沉默率 / 分段率 / 插话合并率 / 上下文拦截率，按“命中数 ÷ 总请求”计算，总请求为 0 时显示 `—`；加载骨架同步为“比率组 + 3 个统计组”的最终结构。
- 配置摘要从 4 项扩展到后端返回的全部 8 项；布尔显示“开启/关闭”，缺失值显示 `—`。

### 序（键盘快速审批 + 顶部状态条）

- 待审申请支持键盘操作：`J/K` 选择、`A` 批准、`D` 驳回（走原有行内原因流程）；焦点在输入控件内或面板不可见时不拦截按键，重绘后保持选中态，卡片有选中描边，筛选栏给出快捷键提示。
- 560px 以下顶部三个指标由纵向堆叠改为一行状态条（3 列、字号收紧），首屏高度从约 200px 降到 87px。

### 情（图表跳转 + 筛选排序 + 自动刷新 + 长 ID）

- 关系总览的分层图改为可点击按钮：点击某一层直接切到“关系明细”并按该层级筛选。
- 关系明细新增“关系层级”筛选与排序（默认 / 好感 / 信任 / 熟悉度 / 互动次数 / 最后互动）。
- 页头新增数据新鲜度（秒/分钟前更新，超过 2 分钟标黄）与“自动刷新”开关（60 秒，页面隐藏时不请求）。
- 关系明细与账号归属里的自然人 ID 改为短显示 + 一键复制；账号归属新增搜索（名称 / 自然人 ID / 账号 / UMO / 记忆人格）。
- 账号归属编辑器把「内部 ID / 关系人格 / 初始关系」收进高级折叠，新建时默认收起、编辑已有自然人时自动展开，常用字段与保存按钮保持常显。

### 境（配置 sticky + 危险开关说明）

- 配置卡头部改为 sticky，保存按钮与“N 项待保存”计数始终可见；输入变化实时更新计数，保存/重置后归零。
- 6 个会影响对外行为或数据新鲜度的开关补充后果说明：主动发送、暂停主动、官方预警、候选缓存、节假日感知、强天气风险（危险级用红色、警示级用琥珀色）。

### 声（情绪路由并入风格导演）

- 删除独立的“情绪路由”卡片，将其并入“AI 风格导演”卡片，形成“先定情绪，再定风格”的单一任务域；补充分工说明，`#emotion-routing-enabled` 与 `#emotion-defaults` 行为不变。

### 临（技术词中文解释）

- 能力条的 8 个技术词（对话模型 / 临专属链路 / 身份配置 / STT / TTS / 角色动作 / 交互决策 / 直连回退）各补一句中文解释，折叠展开时可见，桌面 6 列与移动 2 列布局不变。

### 本批验证

- 全量测试：核 324、知 707（3 skipped）、言 455 + 384 subtests、序 473、情 299 + 26 subtests、境 134、声 196 + 6 subtests、临 604（8 skipped），全部通过。
- 浏览器回归（1440/390 双视口）：核 Page 推荐与目录合并 + 设置四分区切换与键盘导航 + 诊断问题聚合点击筛选；核 WebUI 版本去重、设置子导航、诊断建议、账户卡片；知长 ID 复制（真实剪贴板）与作用域筛选；言比率与 8 项配置；序键盘审批与顶部状态条；情图表跳转、筛选排序、自动刷新、账号归属搜索；境 sticky 保存与脏计数；声 4 tab × 后端 scope 与合并后的风格卡；临能力解释、运行二级 tab、根因自动定位、四步绑定；均无 pageerror、无横向溢出。
- `series_ui check`：`series.ui 1.0.0: ok`（保留既有 warning：知页面静态业务弹层为页面自有例外）；8 仓 `git diff --check` clean。
- 本轮仍未提交、未推送、未部署；`orchestration_hub` 未访问、未修改；未在任何其他仓库创建 `CONVENTIONS.md` 副本。

### 计划内剩余

- 知：导入向导（现有“导入记忆”弹层已按 文本 / 文件 / ZIP / PDF 分 tab，可视为向导形态；如需严格分步向导仍可再迭代）。
- 其余 P2 体验项（图表联动到具体记忆、更多排序维度）属于可选优化，不影响当前验收项。

## 第七批：全系列旧版本残留审计与清理（2026-09-13，未升版本、未提交）

### 审计维度

1. 版本一致性（metadata / CHANGELOG / 页面资源 `?v=` / i18n / 页脚版本）
2. 旧主题与旧结构（暗色 token、已删除元素的选择器、旧导航、旧 toast、原生弹窗）
3. 死引用与死代码（JS 引用的元素 id、未被引用的函数、未使用的 i18n 键、未使用的 CSS class / keyframes / 变量）
4. 废弃与临时文件（备份、快照、缓存、孤儿资源）
5. 共享 UI 库漂移与规范副本（`series_ui check` + `series_audit`）

### 审计结论（干净项）

- 8 仓 `metadata.yaml` 版本与各自 `CHANGELOG.md` 首条、页面资源 `?v=` 一致，无跨版本号残留；README 中的少量版本号均为“功能引入版本/框架兼容版本/迁移来源”说明。
- 无暗色主题残留（`color-scheme: dark`、`#07111d`、`#0d1b2a` 全仓为 0）；无页面级 `showToast`、静态 `#toast`、原生 `alert/confirm/prompt`。
- 无备份/快照/临时跟踪文件；仅有 `.pytest_cache`、`.ruff_cache` 等被忽略的本地缓存。
- `series_ui check`：`series.ui 1.0.0: ok`；20 份 vendored `series-ui.css/js` sha256 完全一致，无漂移。
- `series_audit`：`errors: []`、`warnings: []`、`conventions_copies_outside_kernel: []`、`request_context.consistent: true`。
- 页面目录与 `main.py` 注册一致，无废弃页面目录；8 仓页面资源无孤儿文件。

### 已清理的残留

**核 Page**
- 标题/副标题自指文案对齐新定位（“更新管理” → “模块运营中心”），中英同步。
- 移除合并 tab 后成为孤儿的导航 i18n 键 `recommendations` / `config` / `mirrors`；新增的 `modulesHint` / `settingsHint` 落地到页面（不再有死键）。
- “更新管理器”自指错误文案统一为“核”；`main.py` 初始化 / 卸载诊断文案同步。

**核 WebUI**
- 删除死引用 `refresh-diagnostics` / `refresh-routes`、死函数 `loadModelRouting`。
- 删除旧日志抽屉样式 `.log` / `.log-head` / `.log-body` / `.log-table` / `.log-error` / `.log-warning` / `.log-details` 与失效的 `.status.warning`。

**其他仓**
- 声：删除已并入“AI 风格导演”的 `.routing-card` 选择器。
- 言：删除页面不再使用的 `.cards` 规则（含媒体查询分支）。
- 知：删除 `.feature:hover` 死选择器。
- 临：删除无 `wave-bars` 的 reduced-motion 规则（改为绑定步骤与滚动真实生效的降动效规则）、删除未被引用的 `qpClose` / `qpSetBusy`；`_conf_schema.json` 中“「更新管理」（update_manager）”改为“「核」（update_manager）”。

**文档同步**
- 核 README：页面入口与页签说明改为“总览 / 推荐与目录 / 设置（运行配置·自动更新·控制中心账户·镜像与网络）/ 日志”。
- 声 README：主题描述由“深色低干扰”更正为浅色玻璃（Glass Aurora），补充四个任务页签与“情绪路由并入风格导演”。
- 情 README：补充关系明细独立页签、筛选排序、长 ID 短显示 + 复制、账号归属搜索与高级折叠、数据新鲜度与自动刷新。
- 临 README：补充四步绑定向导、能力健康折叠、运行区二级页签与根因自动定位。

### 缓存破坏参数

8 仓页面与核 WebUI 的 `style.css` / `series-ui.css` / `series-ui.js` / `app.js` 现已全部带 `?v=<版本>-2`，避免“新版 HTML + 旧版 CSS/JS”混用；后续同版本内再次改动请递增后缀。

### 有意保留（附理由）

- 共享库 `.routing-card` / `.logic-card` 别名：属 `series-ui` 公共类名，8 仓已无页面使用，但库外插件可能引用，保留不删。
- 系列 README 清单中 核 的“职能”列写作“更新管理”：这是职责描述（安全检查、计划、串行更新与回滚），非页面名，保持与描述一致。
- 知页面的自有 detail / settings 弹层：`series_ui check` 的既有 warning，属业务弹层，明确例外。
- 声 README 中的 `astrbot_plugin_mimo_tts_clone`：迁移来源与致谢，属历史事实，不是残留。
- `docs/CONVENTIONS-公共规范快照.md`：已废弃但按约定只保留在核仓作历史参考，未在其他仓复制。

### 服务器侧说明（只读判断）

192.168.5.88 上运行的核 Page 仍是 **0.16.3 ~ 0.17.0 之间**的旧版本：页签顺序为“日志 / 系列推荐 / 配置 / 镜像加速 / 目录 / 总览”，样式为 `color-scheme: dark`，且未加载 `series-ui.css`。这与本仓库（0.19.1 + 未提交改造）不一致；本机 SSH 仅允许密码认证，未做任何服务器改动，需推送并更新插件后才会显示新版。

### 本批验证

- 8 仓全量测试：核 324、知 707（3 skipped）、言 455 + 384 subtests、序 473、情 300 + 26 subtests、境 134、声 196 + 6 subtests、临 604（8 skipped），全部通过。
- 浏览器回归 9 个脚本全部 PASS（含核 Page 新增提示位的落地校验、声/临/言/知/情/境页面结构校验）。
- `series_ui check` ok；`series_audit` errors/warnings 空；8 仓 `git diff --check` clean。
- 本轮仍未提交、未推送、未部署；`orchestration_hub` 未访问、未修改。

## 第八批：视觉与可读性修复发布（2026-09-13，补丁 +0.0.1）

- 知 `1.8.2` / 言 `0.12.2` / 序 `0.8.2` / 情 `0.12.2` / 境 `0.6.2` / 声 `0.12.2` / 临 `1.7.2` / 核 `0.19.2`
- 共享库 `series.ui 1.0.1`：通用控件选择器按分片 `:where()` 降权，页面自身样式不再被静默覆盖（一次性解决 8 仓同类问题）。
- 核 Page 诊断日志/报错条旧深色清理（对比度 1.24:1 → 14.9:1）；WebUI 侧栏浅色化、字段接管 2 列等高、字段中文名 + 一句用途说明。
- 临「对话与模型」两张卡片桌面并排等高、按钮不再整行拉伸；运行区页签独占整行；服务卡补齐内边距。
- 声试听栏修复（输入框 31px → 整行）；知移动卡片内边距与行高统一；言骨架顺序与移动端两列；序批量栏 sticky 重叠修复；情账号归属顺序与 sticky 头压缩；境 sticky 头压缩与 AQI/UV 中文等级。
- 校验：8 仓全量测试 707/455(+384 sub)/473/300(+26 sub)/134/196(+6 sub)/604/324 全绿；浏览器回归 9/9 通过；9 页渲染扫描大间隙 0、空洞 0、横向溢出 0、裸方法名 0。

## 第九批：统一滑块开关与能力卡直出主开关（2026-09-14，未升版本）

- 正本新增统一滑块开关：`input[type="checkbox"].si-toggle` / `.switch` 容器 / `.si-switch` 容器三选一即渲染 40×22 滑块；`series-ui.js` 自动补 `role="switch"` 与 `aria-checked`（动态渲染同样生效）。radio 与列表勾选不匹配该选择器，保持原生语义。
- 能力目录 `core/capability_catalog.py` 新增 `providers[].switch_field`（17 项能力声明主开关），`validate_catalog()` 校验其必须属于 `fields`。
- 核 WebUI 系列接管：卡片拆为「标题行（`cap-card-head`：`cap-card-open` + 右侧主开关）／描述行／`cap-card-meta` 设置行」，主开关按方案 A 贴在标题行右侧（文字在左、轨道在右）；切换走 `control/validate → control/apply`（带 `expected_revision`），失败回滚；提示带「撤销」（共享 `SeriesUI.toast(..., action)`），5.2 秒内可用最新 revision 恢复原值；详情页布尔字段改用 `label.si-switch`。
- 卡片链接式按钮显式 `min-height:0` 并归零 hover 位移/阴影，避免继承共享按钮的 38px 高度（卡片 110px → 80px）。
- 8 仓页面布尔开关统一：知（13）、言（1）、序（2）、情（4）、境（1）、声（11）、临（11）改用共享开关；核沿用 `label.switch` 容器契约。知/序页面自绘滑块样式物理删除，情/境/言/声/临/核页面不再写死勾选框尺寸。
- 有意保留原生：知导入/文档勾选、序全选与行选择、核目标模块多选与镜像单选、声 TTS 后端与触发模式单选。
- 验证：8 仓全量测试全绿（知 716/言 479+384sub/序 484/情 315+26sub/境 148/声 208+6sub/临 614+8skip/核 377）；`series_ui check` ok；浏览器回归 1440/390 各 10 卡 8 开关、0 pageerror，开关点击实发 validate/apply。
- 仍未提交、未推送、未部署；`orchestration_hub` 未访问、未修改。
