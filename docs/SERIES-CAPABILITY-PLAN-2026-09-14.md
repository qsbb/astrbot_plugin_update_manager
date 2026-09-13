# 凝心溯溪 · 能力中心与治理体系完整方案

> 版本：v1（2026-09-14）｜范围：知 / 言 / 序 / 情 / 境 / 声 / 临 / 核 ｜状态：设计定稿，未实施
> 依据：CONVENTIONS.md（唯一规范）、private_companion 参考解剖、四轮子代理分析（解剖 / 设计 / 事实核验 / 对抗复审）

---

## 0. 一页摘要（TL;DR）

1. **"系列接管"要从"按插件分类"改成"按功能分类"**：现状 `FEATURE_DOMAINS` 是 8 条 1:1 插件映射（icon 就是插件代号），本质仍是插件目录。目标：**功能域 → 能力 → 提供者（多对多）**，插件身份只在排障视图出现。
2. **能力有 7 个域**：消息与对话 / 记忆与知识 / 关系与身份 / 环境与感知 / 语音与表达 / 设备与联动 / 治理与更新；一个能力可由多个插件提供，一个插件贡献多个域。
3. **状态真相单源**：新增 `series.diagnostics@1.1` 可选能力 `read_state`（`diagnostic_state()`）返回当前 link 状态；事件流只做历史，**heartbeat 不进事件流**，重启/溢出显示 `unknown/stale`（对抗复审结论，纯事件推导方案已否决）。
4. **standalone 优先**：不做"非核插件独立 WebUI"；把 8 个 Page 的"无核完整可用"做成验证矩阵（5 场景 × 动作清单）并补缺口。
5. **字段级 i18n**：schema 中文兜底 + `en-US` 覆盖 + `zh-CN` 页面元数据；自定义 Page 必须走 `bridge.t()/getI18n()`（数组 labels 用 getI18n 路径解析，`t()` 会把数组 String 化）。
6. **未保存守卫**：页内统一 `SeriesUI.confirm`，`beforeunload` 仅 best-effort（iframe sandbox 无 `allow-modals`，原生 confirm/localStorage 不可靠；硬拦截需上游 bridge 扩展）。
7. **明确不做**：自建独立 WebUI / heartbeat 洪泛 / 事件推导权威状态 / 猴子补丁 asset token TTL / 原生 confirm / 全页面大爆炸翻译。

---

## 1. 现状与问题（事实基线）

### 1.1 已完成（本批）
- 言 0.12.5：独立 Page 恢复 + schema 驱动设置中心（89 项全可编辑）
- 境 0.6.4：独立 Page 恢复（总览/配置/实时检查）
- 状态驱动插话合并（言 0.12.4）、诊断窗口 P0 修复、核检查更新重构（0.19.3）

### 1.2 六个问题（含证据）
| # | 问题 | 证据 |
|---|---|---|
| 1 | 系列接管=插件目录（按插件分类） | `webui/app.js:381-460` FEATURE_DOMAINS 1:1 插件；卡 icon=插件代号；管理按钮绑单个 plugin_id |
| 2 | 没有能力级状态 | 状态来自 `member.status`（插件级），无法表达"分段正常但插话降级" |
| 3 | 联动降级不可见 | 各适配器的 degraded 只写普通日志；核侧仅有安装/加载/健康快照 |
| 4 | standalone 完整性未验证 | 8 页 × 5 场景无矩阵；序/核等页 dirty 守卫缺失 |
| 5 | i18n 覆盖不足 | 只有 4/8 页有页面元数据 i18n；`config.*` 字段级翻译为 0；合计 438 description / 352 hint / 29 个带 options 字段（82 选项） |
| 6 | 代码债 | `series.webui@2.0` 命名漂移（网关文件/常量仍写 1.0）；`series.control.reset` 重复调用 |

---

## 2. 设计原则（P0 冻结，不可违背）

1. **能力优先**：用户界面按 功能域 → 能力 组织；插件身份仅在排障视图与详情"来源"小字出现。
2. **standalone 优先**（CONVENTIONS §9）：没核时每个插件 Page 必须完成全部配置/上传/预览/管理动作；managed 是增强不是替代。
3. **状态真相单源**：当前状态只能来自 `diagnostic_state()` / `series_control_snapshot` 等**纯读接口**；事件流只做历史与时间线。
4. **渐进披露**：入口层只回答"去哪"；细节放内容层与详情页（借鉴 private_companion：section-head + `<details>` + `data-jump-tab`）。
5. **契约只增不改**：新能力一律"可选 + 缺失降级"，不改变现有方法语义；major 不兼容才 fail-closed。
6. **不做第二控制台**：不新增插件侧 HTTP 服务/鉴权体系；一切管理面收敛到 Plugin Page 与核 WebUI。
7. **失败可解释**：任何降级必须有 `state/reason_code/peer/version/missing` 可读字段，禁止"看起来已接管"。

---

## 3. 目标信息架构：能力中心（Capability-first）

### 3.1 三层模型

```
功能域 Domain（7 个）
  └── 能力 Capability（约 30 个）
        └── 提供者 Provider（1..n 个插件：字段 / 面板 / 动作）
```

- **多对多**：能力可跨插件（如"语音表达"= 声 TTS + 言 分段节奏 + 情 语气）；插件可跨域（知的记忆同时服务"消息与对话"和"记忆与知识"）。
- **状态在能力级**：能力状态 = 提供者状态聚合并（任一异常→黄，全部正常→绿，无提供者→灰）。
- **模块身份不可见**：模块名只出现在能力详情的"来源（可折叠）"与排障视图。

### 3.2 七个功能域与能力清单（草案）

| 功能域 | 能力（来源插件） |
|---|---|
| **消息与对话** | 沉默判断（言）· 智能分段（言）· 插话合并（言）· 上下文承接与预算（言）· 群聊语境与读空气（言）· 收尾方式（言）· 场景感知（言）· 回复格式与引用（言）· 图片意图（言）· 智能拦截（言）· 语气与表达建议（情）· 记忆注入（知）· 语音交付（声） |
| **记忆与知识** | 记忆库与生命周期（知）· 学习与交叉验证（知）· 检索与向量（知）· 导入导出与内置知识库（知）· 群黑话（知）· URL 来源与爬取（知）· 关系档案与四维信任（情）· 环境事实缓存（境）· 联动回忆（序→知） |
| **关系与身份** | 关系层级与性质（情）· 账号归属（情）· 白名单与边界（情）· 身份识别与授权（序）· 入群审核（序）· 群管理与处罚（序）· 欢迎与通知（序）· 安全防护（序） |
| **环境与感知** | 天气/空气/日历/预警/地震（境）· 地点与校验（境）· 主动环境关心（境）· 位置与设备状态（临） |
| **语音与表达** | TTS 后端与音色（声）· 情绪路由与 AI 导演（声）· 音频交付与失败回退（声）· 试听（声）· 说话节奏/分段延迟（言）· 语气风格（情）· 语音识别适配（临） |
| **设备与联动** | 设备配对与监听器（临）· 平台实例（临）· 会话桥接与角色动作（临）· 人格转换（临）· 外部语音接口（声）· 自然工具调用（言） |
| **治理与更新** | 更新与回滚（核）· 系列推荐（核）· 每日规则（核）· 镜像加速（核）· 模型角色（核）· 全局设置（核）· 账号安全（核）· 运行诊断（核） |

> 完整字段映射见附录 A；实施时先冻结本目录，再写代码。

### 3.3 能力目录条目结构（Phase 1：核侧静态目录）

```jsonc
{
  "id": "chunking",
  "domain": "message",
  "title": "智能分段",
  "description": "把长回复按语义拆成多条发送，避免一次性刷屏",
  "providers": [
    {
      "plugin_id": "astrbot_plugin_conversation_flow",
      "fields": ["chunking_enabled", "chunking_min_length", "chunking_max_segments",
                 "chunking_preserve_paragraphs", "chunking_long_paragraph_threshold",
                 "chunking_protect_code_block", "chunking_llm_assist*"],
      "field_prefixes": ["chunking_delay_"],
      "panels": []
    }
  ],
  "status_rule": "worst_of_providers",
  "fallback": "未装该模块时隐藏本能力"
}
```

- 数据源全部复用现状：`series.control` 字段、`series.webui` 面板、member 状态、`series.diagnostics`。
- Phase 2 改为插件在契约里声明 `capabilities[]`，核自动聚合；静态目录降级为兼容兜底。

### 3.4 状态模型

| 层级 | 取值 | 来源 |
|---|---|---|
| 能力状态 | 正常 / 部分不可用 / 未接管 / 未加载 / 待检查 | 提供者 member.status 聚合并 |
| 提供者状态 | managed / native / not_loaded / contract 异常 | `series.control` member + `diagnostic_state()` link |
| 域状态 | 最差能力 | 派生 |
| 模块身份 | 仅排障视图展示 | member.plugin_id |

`unknown/stale`：无状态、超期（> 2× 心跳间隔）、gap/reset 后一律显示未知，不沿用旧绿色。

### 3.5 页面结构（借鉴 private_companion 的布局语言）

**页头（folio 式）**：标题"系列接管" + 一行运行摘要（统一接管 · 7 域 · N 能力 · 已接管 x/y） + 主操作（启用/关闭接管）。

**一级分类（已实施）**：按"控制中心要做的五件事"重划，9 项平铺 → **5 个一级入口 / 2 组**：

| 组 | 一级入口 | 内容 |
|---|---|---|
| 工作台 | 总览 | 模块状态、版本、待办（原"模块总览"） |
| 工作台 | 系列接管 | 7 功能域 / 40 能力（能力优先） |
| 运维 | 更新与安装 | 套件子页签：更新与回滚 · 系列推荐 · 每日规则 · 镜像加速 |
| 运维 | 诊断与日志 | 事件流、问题聚合（后续接入联动健康） |
| 运维 | 设置与安全 | 内部页签：模型路由 · 运行项 · 完整配置 · 解析快照 · 账户与安全 |

**程序结构（已实施）**：`VIEWS` 视图注册表作为单一事实源（icon/label/group/suite/inSuite/tabLabel/hidden），
`NAV_GROUPS` 定义分组，`railItemsForGroup()` 渲染侧栏，`suiteTabStrip()` 渲染套件子页签，
`VIEW_RENDERERS`/`VIEW_ENTERS` + `enterView()` 统一渲染与进入逻辑——新增视图只需改注册表一处，
不再分别维护导航、标题、渲染、加载四份 if 链。
**系列接管主视图**：
- 7 张域卡：`域标题 + 一句话 + N 项能力 + 聚合状态点 + 箭头`（**不出现插件名、不出现功能 chips**）
- 分段筛选：全部 / 统一接管 / 独立配置 / 待检查
**能力详情（点域进入）**：
- 能力行：`能力名 · 状态点 · 来源 N 个模块（可折叠）· [设置] [面板]`
- 设置按**能力分组**渲染（分段的 8+5 字段、沉默的 6 字段…），不按插件分组
- 面板挂到对应能力（境"实时检查"→环境能力；言 status→对话能力）
**排障视图（次级）**："按模块查看"保留插件维度：版本、契约、加载状态、诊断事件、更新回滚。

---

## 4. 支撑体系

### 4.1 standalone 能力矩阵（替代"救援 WebUI"）

**结论：不做插件侧独立 WebUI**（违反 §9、救不了进程未启动、SSH+CLI 更轻）。改为验证矩阵：

维度：8 个 Page × 5 场景（核不存在 / 核未加载 / control 不可用 / webui 不可用 / diagnostics 不可用）× 动作（配置保存、上传、预览、删除、启停、导出）。
产出：`docs/STANDALONE-MATRIX.md`（每格 ✅/❌+修复项）。缺口按 §9 补 Page，不碰核鉴权。

### 4.2 联动状态契约 series.diagnostics@1.1（可选能力）

- 新增可选 `read_state` → `diagnostic_state()`：**只读本地缓存、无网络、无副作用**，返回：
```jsonc
{
  "contract": "series.diagnostics@1.1",
  "plugin_id": "...", "stream_id": "...", "observed_at": "...",
  "links": {
    "orderflow->knowledge.recall": {
      "state": "ready|degraded|unavailable|disabled|unknown",
      "since": "...", "last_attempt_at": "...", "last_success_at": "...",
      "reason_code": "CONTRACT_VERSION_UNSUPPORTED",
      "contract": "active_learner.knowledge", "contract_version": "1.x",
      "method": "recall", "peer_plugin_id": "...",
      "consecutive_failures": 3, "fallback": "保持待审"
    }
  }
}
```
- 事件只记**状态迁移**（ready/unavailable/version_unsupported/method_missing/invoke_failed/recovered）+ 采样的重复失败；**heartbeat 不进事件流**。
- 每条 link 唯一 writer（调用方记录）；字段白名单（禁止 endpoint/header/token/正文）；去重键 = `link_id+direction+code+reason+contract@version+method`；恢复事件绕过限流；读取路径纯读（测试：连续读 N 次 seq 不增长）。
- 核侧新增 `core/link_health.py`（聚合）+ 日志页"联动健康"卡 + 排障明细中文化。

### 4.3 字段级 i18n

- 结构：`.astrbot-plugin/i18n/{zh-CN,en-US}.json` → `config.<组>.<字段>.{description,hint,labels}` + `pages.<page>.{title,description}`。
- 策略：**schema 中文为兜底**；en-US 只放覆盖；zh-CN 只放页面元数据（避免双份中文漂移）。
- 页面消费：`await bridge.ready()` 后用 `bridge.getLocale()/getI18n()/t(key, fallback)`；**数组 labels 必须用 getI18n 路径解析**（`t()` 会 String 化）；语言切换重渲染需保留草稿与焦点。
- 校验：核 `series_audit` 增加 i18n 审计（路径存在、labels 长度=options、禁止覆盖 options/default、单文件 <1MB）。
- 分批：① 8 页元数据齐全 ② 29 个 options 字段的 labels ③ 高频字段 description/hint ④ 全量（UI 冻结后）。

### 4.4 未保存守卫

- iframe sandbox 无 `allow-modals/allow-same-origin` → **不用原生 confirm/alert/localStorage**。
- 页内守卫（tab/二级页/返回）统一 `SeriesUI.confirm`；`beforeunload` 仅 best-effort 兜底。
- 覆盖：知/言/情/境/声/临/序/核（**复审纠正：序与核也要覆盖**；临的 personaConversionDraftToken 不算通用 dirty）。
- 硬拦截宿主路由需上游 bridge 扩展（`setDirty()` / 宿主 onBeforeRouteLeave）——写入上游提案，不在插件侧造轮子。

### 4.5 能力目录契约 series.webui@2.1（Phase 2）

在 `webui_panels_contract()` 增加可选 `capabilities[]`（id/domain/title/description/fields/panels）；核优先用声明，缺失回退 Phase 1 静态目录；旧核忽略该字段。同步清理 `series.webui` 命名债（网关文件/常量统一 2.0）。

---

## 5. 契约与接口变更清单

| 对象 | 变更 | 兼容策略 |
|---|---|---|
| `series.diagnostics@1.1` | 新增可选 `read_state`/`diagnostic_state()` | 旧核忽略；旧插件 → unknown；不破坏 1.0 |
| `series.webui@2.1` | 新增可选 `capabilities[]` | 旧核忽略；无声明回退静态目录 |
| `series.control@1.0` | **不变**（仅核侧目录引用字段） | — |
| 核 WebUI | FEATURE_DOMAINS → 能力目录渲染；新增排障"按模块查看" | 视图层变更，无 API 破坏 |
| 核审计 | 新增 i18n 审计、capability 覆盖检查 | check 命令输出 warning，不 fail 默认 |
| 8 仓 Page | 补 i18n 元数据 / dirty 守卫 / standalone 缺口 | 逐仓独立发布 |

**不变量**：owner 权限、revision 乐观锁、幂等键、危险操作确认、密钥不回显、Page fallback、TAKEOVER_DISABLED 语义全部保持。

---

## 6. 分阶段实施计划

| 批次 | 内容 | 工期 | 依赖 | 验收 |
|---|---|---|---|---|
| **P0-1** | 能力目录冻结（7 域/约 30 能力/字段面板映射）+ `core/capability_catalog.py` | 1-1.5 天 | — | 目录通过评审；单测覆盖映射完整性（字段/面板存在性） |
| **P0-2** | 系列接管页重构（能力优先 UI） | 1.5-2 天 | P0-1 | 页面不出现插件名（排障除外）；截图对比；无回归 |
| **P0-3** | standalone 矩阵验证 + 缺口清单 | 1-2 天 | — | 8 页 × 5 场景逐格 ✅/❌，缺口建单 |
| **P0-4** | `series.diagnostics@1.1` 冻结 + 单链路垂直切片 + 联动健康卡 | 3-4 天 | P0-1 | 溢出/重启/递归/脱敏测试全绿；读 N 次无新事件 |
| **P1-1** | i18n：8 页元数据 + 29 个 options labels | 1-2 天 | — | 双语切换正确；缺 en 回落中文 |
| **P1-2** | dirty 守卫（8 页） | 4-8 天 | — | 切页/关闭有确认；草稿不丢；全部 SeriesUI |
| **P1-3** | 高频字段 description/hint en 覆盖 | 3-5 天 | P1-1 | 审计通过 |
| **P2-1** | Phase 2 契约声明 `capabilities[]` + 命名债清理 + `reset` 重复调用修复 | 4-6 天 | P0-4 | 旧插件回退静态目录；审计通过 |
| **P2-2** | 全页面双语（分批） | 20-40 人日 | UI 冻结 | 逐批验收 |
| **P2-3** | 上游提案（asset token 重签、宿主导航拦截） | 提案 | — | issue/PR 追踪 |

可并行：P0-3 / P1-1 / P1-2 互不依赖；P0-4 依赖 P0-1 目录。

**最小可交付切片（建议第一步）**：P0-1 + P0-2（能力目录 + 系列接管页重构），因为它是用户直接看到的价值。

---

## 7. 测试与验收总纲

- **单元**：能力目录映射（字段/面板存在）、状态聚合规则、diagnostic_state 纯读、i18n 审计、dirty 状态计算。
- **集成**：`series_ui sync/check`、8 仓全量 pytest、`git diff --check`。
- **浏览器**：系列接管页 1440/390（无插件名、7 域、能力行、筛选、详情按能力分组）；8 页 dirty 守卫；i18n 双语切换。
- **对抗**：一个能力跨 2 个插件且其一未加载；一个插件贡献 2 个域；诊断溢出/重启显示 stale；连续读 10 次无新事件。

---

## 8. 风险与不做清单

**风险**
- 能力目录是策展映射，插件加字段后可能漏挂 → 审计（每个 control 字段必须被至少一个能力覆盖）
- 诊断 1.1 需要 8 仓同步升级副本 → 分批发布，旧版本安全降级
- i18n 翻译成本被低估 → 只承诺 schema 层，页面文案分批
- dirty 守卫在 iframe 下无硬保证 → 明确 best-effort，上游提案

**不做**
- 插件侧独立 WebUI / 救援服务器
- heartbeat 写入事件流 / 用事件推导权威当前状态
- 猴子补丁 AstrBot 内部（asset token TTL 等）
- 原生 confirm/alert、localStorage 依赖
- 全页面一次性翻译、巨石式重构

---

## 附录 A：能力目录·字段映射草案（按插件）

| 插件 | 主要分组（schema） | 归入能力 |
|---|---|---|
| 言（89 字段） | 沉默判断6 / 智能分段8 / 分段延迟5 / 插话中断11 / 私聊上下文3 / 动态上下文3 / 跨会话近期感知5 / 群聊上下文7 / 读空气4 / 收尾方式3 / 场景感知5 / 拟人化情绪11 / 引用消息2 / 引用回复3 / 话题上下文2 / 上下文预算3 / 智能拦截2 / 回复格式1 / 图片处理1 / 关系保护1 / 工具调用1 / 通用2 | 沉默、分段、插话合并、上下文承接、群聊语境、收尾、场景、格式与引用、图片意图、智能拦截、说话节奏（分段延迟→语音域） |
| 知（46 字段） | 页面设置中心 6 组（LLM/学习/搜索/URL来源/其它/全部配置） | 记忆库、学习与验证、检索与向量、导入导出、群黑话、URL 来源 |
| 序（39 字段） | 基础1/身份1/机器人控制1/邀请2/兼容3/关系1/安全7/互动2/处罚3/审核5/入群4/联动2/通知1/欢迎2/高级3 | 身份与授权、入群审核、群管理与处罚、欢迎通知、安全防护、联动回忆 |
| 情（53 字段） | 关系/信任/归属/白名单/边界/情绪 | 关系档案、账号归属、边界、语气建议、关系记忆 |
| 境（40 字段） | 地点/日历/预警/空气/地震/机会缓存/主动关心 | 天气空气日历预警地震、地点、主动关心、环境事实缓存 |
| 声（45 字段） | TTS 后端/音色/情绪路由/AI 导演/API/访问控制 | TTS 后端与音色、情绪路由、音频交付、试听、外部接口 |
| 临（92 字段） | 监听器/配对/TLS/平台/人格/STT/TTS/任务 | 设备配对、平台实例、会话桥接、人格转换、语音识别适配 |
| 核（25 字段） | 更新/自动更新/镜像/网络/数据目录 | 更新回滚、推荐、每日规则、镜像、模型角色、全局设置、账号、诊断 |

> 逐字段映射表（capability → fields/panels）在 P0-1 交付物中冻结，并写入 `core/capability_catalog.py`。

## 附录 B：private_companion 参考取舍（已核验）

**值得借鉴**：编号/分组导航、section-head + section-desc 统一内容模式、`<details>` 渐进披露、`data-jump-tab` 跳转、hidden 功能门控、asset guard（我们页面小，暂不做）、字段级 i18n 约定、降级状态 DTO、"预检→尝试→确认→结算"状态机、前端 API 字面量与路由表对账测试。

**不借鉴**：3 万行 page_api + 4 万行 app.js 巨石、插件自带 Quart 第二服务器、宿主猴子补丁、私有方法 monkey patch、调用栈扫描、双目录镜像、共享 token 单身份、`method_count` 当接管完整度、多 endpoint 猜测兼容、生产保留 `?debug_http=1`。

