# 系列接管页 · D3「主从 + 能力网格」详细设计规格

> **v2 修订（2026-09-14，已实施）**：本规格已按 `docs/TAKEOVER-UI-D3-SYNTHESIS.md` 的 **D3.1** 修订并落地到 `webui/app.js` / `webui/style.css`：
> ① 能力卡由两行 56px → **三行 76px**（状态徽标 + 能力名 + `设置 ›` / 描述 / 元信息）；
> ② 新增 `capabilityBadge()` / `capabilityMetaText()` / `sortCapabilities()`（异常优先）；
> ③ "来源 N 个模块" → `N 项可调` / `N 个模块共同提供 · M 项可调` / `在模块里设置` / `核自带`；
> ④ 模式条增加 `待处理 N` 与状态图例；
> ⑤ 响应式：≤1120px 域列表转横向 chips；≤620px 能力单列。
> 验收见综合报告 §5，放行门槛为"复测无评审低于 24 分"。

> 版本：v1（2026-09-14）｜目标：替换核 WebUI「系列接管」的一级视图｜配套：`docs/SERIES-CAPABILITY-PLAN-2026-09-14.md`
> 现状数据源已就绪：`core/capability_catalog.py`（7 域 / 40 能力）、`state.control.capabilities`、`capabilityStatus()`、能力详情（provider 分区 + 能力级字段过滤）

---

## 1. 设计目标

1. **一屏完成"看域 → 看能力 → 进设置"**：域列表与能力列表同屏，不跳页即可切换域。
2. **异常前置**：状态点贯穿域行与能力卡；支持"异常优先"排序。
3. **不臃肿**：域行 34px、能力卡约 56px，首屏可容纳 7 域 + 8–10 能力卡。
4. **移动端成立**：窄屏把域列表降级为横向 chips，能力网格降为单列。
5. **与无障碍兼容**：roving tabindex + `aria-selected` + focus-visible。

---

## 2. 布局规格

### 2.1 桌面（≥ 1200px）

```
┌ 侧栏 212 ─┬─ 内容区 ────────────────────────────────────────────┐
│           │ 模式条（统一接管 · 7 域 · 40 能力 · 版本号 8）      │
│           │ ┌ 域列表 200px ─┐ ┌ 能力网格（2 列）─────────────┐ │
│           │ │ ● 对话与消息 10│ │ ● 沉默判断   来源 1 模块      │ │
│           │ │ ● 记忆与知识  7│ │ ● 智能分段   来源 1 模块      │ │
│           │ │ ● 关系与身份  7│ │ ● 插话合并   来源 1 模块      │ │
│           │ │ …             │ │ …                            │ │
│           │ └───────────────┘ └──────────────────────────────┘ │
└───────────┴──────────────────────────────────────────────────────┘
```

- 内容区最大宽 1500px（沿用 `.content` 既有约束）
- 主从栅格：`grid-template-columns: 200px minmax(0, 1fr); gap: 12px; align-items: start`
- 能力网格：`grid-template-columns: repeat(2, minmax(220px, 1fr)); gap: 8px`
- 域列表吸附：`position: sticky; top: 12px`（内容长时域列表保持可见）

### 2.2 中等宽度（900–1200px）

- 域列表收窄到 170px；能力网格 `repeat(auto-fill, minmax(210px, 1fr))`（多数为 2 列，少数 1 列）

### 2.3 窄屏（< 900px，含移动端）

- 主从降级为上下结构：
  - 域切换变为**横向滚动 chips**：`display:flex; overflow-x:auto; gap:6px`，每 chip = 状态点 + 域名 + 数量
  - 能力网格单列：`grid-template-columns: 1fr`
- 域 chips 保持 sticky（顶部 0），避免滚动后失去上下文

---

## 3. 组件规格

### 3.1 域列表项（`.domain-item`）

| 属性 | 规格 |
|---|---|
| 结构 | `按钮`：状态点(8px) + 域名(13px/600) + 数量(11px，右对齐) |
| 内边距 | 9px 10px；圆角 8px；行高 ≈ 34px |
| 默认 | 透明背景，文字 `#475569` |
| 选中 | `background: var(--si-primary-soft); color: var(--si-primary-strong); font-weight:700` |
| 悬停 | 背景 `#f6f8fd` |
| 键盘 | 容器 `role="tablist"`、项 `role="tab"` + `aria-selected`；↑/↓ 移动、Home/End 首尾；roving tabindex（仅选中项 `tabindex=0`） |
| 状态点 | 颜色：ready 绿 / degraded+unavailable 琥珀 / disabled+unknown 灰 / stale 蓝；`title` 显示完整状态文本 |

### 3.2 能力卡（`.capability-card`）

| 属性 | 规格 |
|---|---|
| 结构 | 第一行：状态点(8px) + 能力名(12.5px/600)；第二行：`来源 N 个模块`(11px，muted) |
| 内边距 | 10px 12px；圆角 10px；边框 `1px solid var(--line)` |
| 悬停 | 边框加深 + 轻微阴影 `0 6px 18px rgba(79,70,229,.06)` |
| 点击 | 整卡可点（`button`），打开能力详情 |
| 多提供者 | `来源 N 个模块`；N≥2 时名称前缀加 `⇄` 视觉提示（文案仍是"来源 N 个模块"） |
| 无提供者（核内置） | 显示"核内置能力"，点击跳对应治理视图 |
| 异常态 | 状态点变琥珀 + 卡片左侧 2px 色条（仅异常项），保证异常在网格中可扫 |
| 键盘 | `tabindex=0`，Enter/Space 打开；focus-visible 外环 |

### 3.3 模式条（沿用）

`统一接管 · 7 个功能域 · 40 项能力 · 版本号 8`，右上角放"异常优先/全部"分段控件（仅影响能力网格排序，与是否过滤无关）。

### 3.4 能力详情（复用已实现）

点击能力卡 → 现有 `capabilityDetail()`：
- 每个 provider 一个分区（模块名 + 更多设置提示 + [模块详情]）
- 字段按能力过滤（`controlFieldsTab(schema, snapshot, {fields, capabilityTitle})`）
- 面板/生命周期仍通过[模块详情]进入

---

## 4. 状态与排序规则

| 状态 | 颜色 | 文案（能力级） | 文案（域级） |
|---|---|---|---|
| ready | 绿 | 正常 | 统一接管 |
| degraded | 琥珀 | 降级 | 部分不可用 |
| unavailable | 琥珀/红 | 不可用 | 部分不可用 |
| disabled | 灰 | 已关闭 | 独立配置 |
| stale | 蓝 | 数据陈旧 | 部分陈旧 |
| unknown | 灰 | 未知 | 待检查 |

- **异常优先排序**（默认开启）：`unavailable > degraded > stale > unknown > disabled > ready`，同级按能力名排序。
- 域级状态 = 域内能力状态的"最差"聚合（沿用 `domainStatus()`）。
- 状态新鲜度：> 3 分钟未刷新（`link_health.STALE_AFTER_SECONDS`）视为 stale。

---

## 5. 交互流程

1. 进入页面 → 默认选中第一个域（或保留本次会话上次选择，仅内存）。
2. 点击域行 → 右侧立即切换能力网格（不刷新页面数据）。
3. 点击能力卡 → 能力详情；返回按钮回到**原域**（保存 `state.selectedDomain`）。
4. "异常优先/全部"切换 → 仅重排当前域能力。
5. 域行/能力卡的 `设置` 入口始终指向"该能力的字段集合"，不展示其它能力的字段。

---

## 6. 实现改动点

| 文件 | 改动 |
|---|---|
| `webui/app.js` | `controlView()` 改为 `master-detail`；新增 `domainList()`、`capabilityGrid()`、`capabilityCard()`；`state.domainSort = "attention" \| "all"`；事件绑定 `data-domain-select`、`data-domain-sort`、`data-capability-open`（后两者已存在） |
| `webui/style.css` | 新增 `.master-detail`、`.domain-list`、`.domain-item`、`.capability-grid`、`.capability-card`、`.mode-sort`；三个断点（1200 / 900 上下） |
| 测试 | `tests/test_pages_ui.py` 增加：主从结构断言、域选择事件、能力卡来源文案、异常优先排序函数、移动端断点 CSS |
| 文档 | 本文件；UI 全局审计文档补一条 |

**不改**：`core/capability_catalog.py`（数据源）、`series.control`/`series.webui` 契约、任何插件侧代码。

---

## 7. 验收清单

- [ ] 1440×900：7 个域行 + ≥8 张能力卡同屏；无横向滚动
- [ ] 390×844：域 chips 可横向滚动；能力卡单列；点击可达能力详情
- [ ] 键盘：↑/↓ 切换域、Enter 打开能力、Esc 从能力详情返回
- [ ] 异常项在网格中可一眼定位（色条 + 状态点）
- [ ] "设置"只显示该能力的字段（不出现同插件其它字段）
- [ ] 空态：域无能力 / 全部正常 / 全部异常 三种文案
- [ ] 无原生 confirm/alert；加载失败显示内联错误
- [ ] `tests/test_pages_ui.py` 与核全量测试通过

---

## 8. 与 B3 的组合关系

- **D3**（本设计）= 域列表 + 能力网格；
- **B3** = 域瓦片（含能力预览）+ 点击进域。
- 若最终采用 D3：B3 的"能力预览"思想可保留在**域 chips 的 tooltip**（悬停显示前 3 个能力名）。
- 若最终采用 B3：D3 的能力网格可作为域详情的默认展示（二者不冲突，共用同一 `capabilityCard()` 组件）。
