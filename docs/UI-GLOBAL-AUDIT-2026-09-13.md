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
