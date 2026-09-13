# 凝心溯溪 · Standalone 能力矩阵（8×5）

> 审计快照：2026-09-14 05:01 Asia/Shanghai。范围为 `/home/lingxi/project` 下 8 个仓库的当前工作树；当时多仓存在并发的未提交改动，本文行号按该快照记录。
>
> 前提：AstrBot 版本支持 Plugin Page、`register_web_api` 和 `/api/plugin/page/bridge-sdk.js`。若宿主本身不支持 Page，则全部 standalone Page 均不可用，这不是本矩阵要判定的插件依赖问题。
>
> 状态：`✅` 适用动作齐全；`⚠️` 核独立路径存在，但有动作全集或 Page 路由测试缺口；`❌` 当前场景没有可用的插件管理面。

## 1. 审计口径

- 8 个仓库都存在真实业务页，不是引导页：`pages/manager/{index.html,app.js}`、`pages/join_review/`、`pages/status/`、`pages/settings/`、`pages/operator/`。每页均加载宿主 bridge SDK，例如知 `pages/manager/index.html:809`、言 `:47`、序 `:245`、情 `:218`、境 `:282`、声 `:446`、临 `:704`、核 `:186`。
- 对 7 个业务插件全文检索 `astrbot_plugin_update_manager` 与 `/api/series/`，Page 与非测试 Python 源码均为 0 命中；页面只调用本插件相对 API。核的 `pages/manager` 同样只调用核自身 Page API。
- 所有页面均在插件初始化时注册自己的 API；各场景检查“配置读取、配置保存、上传/导入、预览、删除、启停、导出、其它管理动作”，不存在的业务能力按 `—` 处理。
- 8 个 Page 当前都有 `hasUnsavedChanges`、`window.SeriesUI.confirm` 和 `beforeunload` 守卫，且各自有 `tests/test_page_dirty_guard.py`；其中 `beforeunload` 在 sandbox iframe 中只能 best-effort。守卫“存在”不等于覆盖全部表单：知的基础设置、情的身份编辑器、临的非人格设置仍有覆盖缺口，见 G9-G11。
- 核的 `webui/` 不是“核未加载”时的 fallback：同一 `UpdateManagerPlugin` 在 `__init__` 注册 Page、创建 `WebUIServer`（`main.py:149-150,197`），在 `initialize` 启动 WebUI（`main.py:972-994`），在 `terminate` 停止它（`main.py:1510-1515`）。插件未加载时两个面都不存在。

## 2. 各 Page 的动作集基线

| 插件 | Page/API 入口与当前动作集 | 直接测试证据 |
|---|---|---|
| **知** | `pages/manager/`；读取/保存、text/md/zip/pdf/docx/txt 导入、详情预览、删除、启停、JSON 导出、批处理、黑话、日志。API：`web_api.py:45-246`；保存：`:1525-1601`。缺 managed 面板已有的撤销验证、结构化 JSON 导入、刷新访问时间动作（对照 `series_webui.py:51-59,563-586,680-683`）。 | Page 结构/脏状态有静态测试，配置、存储、Importer 有底层测试；`web_api.py` 的大多数 HTTP handler 没有直接路由级测试。 |
| **言** | `pages/manager/`；状态/配置读取、schema 驱动的全量配置保存。注册：`main.py:476-485`；保存：`:647-709`。插件无上传、删除、导出业务动作。 | `tests/test_pages_ui.py:92-119` 明确验证“无核可编辑保存”；`tests/test_page_settings_api.py:153-250` 直接验证 schema、保存、持久化和非法输入。 |
| **序** | `pages/join_review/`；全局设置、群配置/批处理、目标群增删/邀请、审批/驳回、模拟审核预览。注册：`core/join_review_api.py:72-97`；实现：`:327-495,630-686`。 | `tests/test_join_review_api.py:90-108` 验证完整路由，后续测试直接覆盖目标群、配置、审批、驳回、模拟和设置；`tests/test_join_review_page.py` 覆盖 Page 交互。 |
| **情** | `pages/manager/`；总览、配置读写、身份创建/更新/合并/解除、关系删除、关系性质。注册：`main.py:1428-1465`；实现：`:1869,2444,2666,2850,2919,2974`。缺 managed `accounts` 面板的显式原子账号迁移入口（对照 `series_webui.py:70-77,325-371,839-890`）。 | `tests/test_main_entry.py:1695+`、`:2905+`、`:3176+`、`:3291+` 直接覆盖多数 Page 动作；`_page_set_relationship_type` 与原子迁移没有同等直接测试。 |
| **境** | `pages/status/`；状态读取、全量配置保存/启停、地点校验、数据源实时 probe 预览。注册：`main.py:688-718`；保存：`:869-1000`；probe：`:1071+`。 | `tests/test_main_entry.py:31-99` 直接验证注册、状态/配置和保存；`tests/test_pages_ui.py:18-62` 验证配置可保存、危险开关说明和分组覆盖。 |
| **声** | `pages/settings/`；配置读写、音频上传、音色创建/更新/删除/启停、默认与情绪映射、试听预览、连接测试、旧插件迁移。注册：`pages_api.py:174-242`；保存/上传/CRUD/预览：`:273-306,405-590`。 | 配置保存、本地降级、连接测试和上传辅助有直接测试（`tests/test_config_persistence.py:186-324`、`tests/test_pages_upload_api.py:14-32`）；`create/update/delete/preview` 的 Page HTTP handler 缺少直接路由测试。 |
| **临** | `pages/operator/`；服务启停、配对创建/查询/撤销、端口/URL/模型/人格/诊断设置、人格转换预览、人格档案删除。注册：`transport/pairing.py:281-560`；Page 调用：`pages/operator/app.js:444-495,1081-1111,1866-2191,2358-2471,3168`。缺 managed 面板已有的“撤销全部待配对”和“仅断开全部会话”动作（对照 `series_webui.py:205-242,584-612`）。 | `tests/test_pairing_http.py` 直接覆盖多数配对 Page API；`tests/test_operator_page_ui.py` 覆盖前端动作绑定。 |
| **核** | `pages/manager/`；配置/规则/镜像、目录检查、安装/更新/启停、推荐、诊断读取/清空/导出、管理员 CRUD、从 Page 启动 WebUI。注册：`pages_api.py:227-315`；Page 实现见 `:1656,1781,2223,2432-2559,2904-3165,1480`。Page 缺 WebUI 的已提交事务列表和手工回滚（`core/webui_server.py:173-175`、`main.py:900-933`）。 | `tests/test_pages_api.py` 直接覆盖 Page 配置、目录、推荐、安装/更新/启停和诊断；WebUI 回滚只在 `tests/test_webui_capabilities.py`、`tests/test_pages_ui.py:886-905` 覆盖，Page 没有回滚路由。 |

## 3. 8×5 场景矩阵

| 插件 | ① 核未安装 | ② 核已装未加载/禁用 | ③ control 接管不可用（native） | ④ 核 WebUI 不可用 | ⑤ diagnostics 不可用 |
|---|---|---|---|---|---|
| **知** | ⚠️ Page/API 均在本地（`web_api.py:45-246`），但缺撤销验证/结构化 JSON 导入等动作（`app.js:257-259` 只给详情/验证/删除；另有基础设置 dirty 缺口 G9）。 | ⚠️ 注册发生在插件初始化，不经过核发现（`main.py:392-397`）；不影响控制流，但缺口同 G1/G9。 | ⚠️ native 下设置直接写本地 `ConfigManager` 并热应用（`web_api.py:1525-1601`），但缺口同 G1/G9。 | ⚠️ Page 只调相对 Page API，不依赖核 WebUI（`app.js:135-2704`）；缺口同 G1/G9。 | ⚠️ 日志和诊断读取本地缓冲区（`web_api.py:1862-1865`），不依赖核 diagnostics；缺口同 G1/G9。 |
| **言** | ✅ status/config/schema/save 全在本地注册（`main.py:476-485`），Page 无核或 WebUI 引用（`app.js:173-175,406`）。 | ✅ 注册在插件 `__init__` 直接执行（`main.py:405,476-485`），核未加载不改变页面。 | ✅ 保存直接更新本地配置并重建 runtime（`main.py:647-709`），native 模式就是完整路径。 | ✅ Page 只请求相对 endpoint，核 WebUI 有无不参与（`app.js:173-175,406`）。 | ✅ 页面动作不消费核 diagnostics 聚合，缺诊断不影响配置读取/保存。 |
| **序** | ✅ 14 个 Page 路由在插件本地注册（`core/join_review_api.py:72-97`），覆盖配置、目标群、审批、驳回、模拟预览。 | ✅ 页面 API 在插件构造时注册（`main.py:218-230`），不依赖核加载或 discovery。 | ✅ 群配置和全局设置直接写插件 store/config（`core/join_review_api.py:327-358,630-686`），native 不削减动作。 | ✅ Page 只调 `join-review/*` 相对 API（`app.js:176-190`），WebUI 缺席无影响。 | ✅ 审批、模拟和配置由本地 runtime/store 完成，diagnostics 不是前置；另有 `tests/test_page_dirty_guard.py` 覆盖未保存守卫。 |
| **情** | ⚠️ 配置/总览/身份 CRUD/合并删除/关系类型均本地注册（`main.py:1428-1465`），但缺显式原子账号迁移和身份编辑器 dirty 覆盖（G2/G10）。 | ⚠️ 初始化直接注册 Page API（`main.py:225`），核状态无关；缺口同 G2/G10。 | ⚠️ 配置先写 native 再落本地 overlay 并热应用（`main.py:2974-3060`），但缺口同 G2/G10。 | ⚠️ Page 只调相对 API（`app.js:177-187,692-745,1139-1385`），但缺口同 G2/G10。 | ⚠️ diagnostics 是独立本地契约（`main.py:331-351`），管理动作不依赖它；缺口同 G2/G10。 |
| **境** | ✅ 5 个 Page 路由本地注册（`main.py:688-718`），覆盖状态、配置、地点和 probe 预览。 | ✅ 注册在插件初始化中执行（`main.py:126-130`），不依赖核加载。 | ✅ native 配置直接经 schema 校验、`save_config` 和 runtime 热应用（`main.py:869-1000`）。 | ✅ Page 只调相对 API（`app.js:326,483,544,607,687`），无 WebUI 依赖。 | ✅ probe 与配置使用本插件 provider/service；diagnostics 缺失不影响页面动作。 |
| **声** | ⚠️ 配置/上传/CRUD/启停/试听/测试均在本地注册（`pages_api.py:174-242`），但 Page CRUD/预览缺少直接路由测试（G6）。 | ⚠️ 注册在插件 `__init__`（`main.py:173`），不依赖核；缺口为 G6 测试覆盖。 | ⚠️ native 保存写本地文件并回写原生 config，随后重建 runtime（`pages_api.py:273-306`、`main.py:292-322`）；功能完整，测试缺口同 G6。 | ⚠️ Page 只调相对 Page API（`app.js:807-1020`），但缺口为 G6。 | ⚠️ 试听/连接测试走本插件合成链路（`pages_api.py:516-590`），不依赖核 diagnostics；缺口为 G6。 |
| **临** | ⚠️ 配对/服务/模型/人格/诊断 Page API 本地注册（`transport/pairing.py:281-560`），但缺批量撤销、仅断开全部会话和非人格设置 dirty 覆盖（G3/G11）。 | ⚠️ 注册在插件构造末尾直接执行（`main.py:720-721`），核缺席无影响；缺口同 G3/G11。 | ⚠️ 服务启停与设置直接持久化/应用（`app.js:444-495`、`core/config_persistence.py:15-50`），但缺口同 G3/G11。 | ⚠️ Page 只调相对 pairing API（`app.js:3553-3564`），WebUI 缺席无影响；缺口同 G3/G11。 | ⚠️ 诊断面板读取本插件 `client_diagnostics`/diagnostic log（`app.js:3134-3168`），不依赖核聚合；缺口同 G3/G11。 |
| **核** | ❌ 核自身未安装就没有 Page、API 或 WebUI，谈不上单插件 fallback。 | ❌ 按“AstrBot 未加载/禁用”判定：`__init__` 不执行，Page 路由和 WebUI 均不存在（`main.py:197,972-994,1510-1515`）；若只是内部 `enabled=false` 但代码已加载，Page 已注册而 WebUI 自动启动被跳过，见下方注。 | ⚠️ native 只关闭 series managed 面板（`core/webui_server.py:400-452`），核自身 Page/WebUI 管理仍在；但 Page 缺事务恢复点/手工回滚（`pages_api.py:227-315` 对照 `core/webui_server.py:173-175`）。 | ⚠️ Page 仍可配置、查目录、安装/更新/启停、诊断、管理员和手动启动 WebUI（`pages_api.py:227-315,1480`），但无事务列表/回滚，未满足完整 standalone fallback。 | ⚠️ diagnostics 缺失只令成员日志显示 unavailable，更新主链路不回退失败（`tests/test_series_runtime_contract.py:82-115`）；Page 回滚缺口仍在。 |

注（核 ②）：若“禁用”仅指核内部配置 `enabled=false`，但插件代码已经加载，`__init__` 已注册 Page（`main.py:197`），`initialize` 仅跳过运行态初始化/WebUI 自动启动（`main.py:972-981`），此时 Page 仍可打开。若“禁用/未加载”指 AstrBot 没有加载插件，则本格是 `❌`。核 WebUI 无论哪种解释都不是独立替代面。

## 4. 缺口清单

| ID | 插件/场景 | 缺什么 | 建议怎么补 | 预估工作量 |
|---|---|---|---|---|
| **G1** | 知 / ①–⑤ | Page 动作不等于 managed 动作集：没有“撤销验证”、结构化 JSON 导入和刷新访问时间入口；`web_api.py:45-246` 也没有对应路由，而 managed 已声明/实现这些动作（`series_webui.py:51-59,563-586,680-683`）。 | 在 Page 菜单与 `web_api.py` 增加对应白名单端点，复用 `MemoryStore.set_verified/update_last_accessed` 和 Importer 的 JSON 路径；沿用现有确认框与错误码。 | 1–1.5 天（含单测） |
| **G2** | 情 / ①–⑤ | Page 没有 managed `accounts` 面板的显式原子账号迁移；只能通过全量身份保存/合并近似，不能保证“账号迁移 + 关系状态迁移”一次事务完成（`series_webui.py:70-77,325-371,839-890` 对照 `main.py:1428-1465`）。 | 增加账号行“迁移到自然人”入口和 Page API，直接调用已有 `_migrate_account_service`/revision 锁，禁止另写一套状态迁移逻辑。 | 0.5–1 天（含回滚/冲突测试） |
| **G3** | 临 / ①–⑤ | Page 只能逐个 `pairing/revoke` 或通过“停用服务”间接断开；缺 managed 的批量撤销待配对和仅断开全部会话（`series_webui.py:205-242,584-612` 对照 `transport/pairing.py:281-560`）。 | 增加两个 owner/admin 门控且有二次确认的 Page 端点，调用 `_revoke_all_pairings`/`_disconnect_all_sessions` 的同一业务服务；同步 UI 状态刷新。 | 0.5–1 天（含权限与幂等测试） |
| **G4** | 核 / ③–⑤（尤其 ④） | 核 Page 无已提交事务列表和手工回滚；只有独立 WebUI 有 `/api/updates/transactions`、`/api/updates/rollback`（`core/webui_server.py:173-175`、`main.py:900-933`）。WebUI 不可用时无法从单插件 Page 完成恢复点操作。 | 在 `pages_api.py` 增加 `updates/transactions`、`updates/rollback`，Page 增加恢复点视图/确认流程，直接复用 `_webui_transactions`、`_webui_rollback`/`transaction.manual_rollback`，保持 owner 门控与失败回滚。 | 1–2 天（含 Page API、UI、危险操作测试） |
| **G5** | 知 / ①–⑤ | `web_api.py:45-246` 的多数 Page HTTP handler 没有直接测试；现有 `tests/test_series_webui.py` 主要验证 managed adapter，不能证明 Page 路由、请求解析和响应形态。 | 增加 Page API 路由级测试，覆盖注册表、配置保存、导入、导出、删除、黑话和错误分支；复用 `tests/test_page_settings_api.py` 的 TestClient/request stub 模式。 | 0.5–1 天 |
| **G6** | 声 / ①–⑤ | `create/update/delete/preview` Page handler 只有业务层或 managed 动作测试，没有直接验证 `pages_api.py:405-540` 的 HTTP 合约。 | 增加 Page handler 路由测试，覆盖文件与 JSON 上传、更新/删除、默认/情绪映射、试听错误和 Secret 字段不回显。 | 0.5–1 天 |
| **G7** | 情 / ①–⑤ | `_page_set_relationship_type` 与原子迁移缺少 Page 层直接测试；现有测试主要集中在身份 CRUD、删除和配置。 | 增加 Page 方法测试：scope 校验、revision/写锁、成功/失败持久化、关系类型和迁移状态一致性。 | 0.25–0.5 天 |
| **G8** | 8 仓 / ①–⑤ | 目前只有各仓库的脏状态/i18n 契约测试，没有一个“Page 存在且非引导页 + 页面 endpoint 均有注册 + 无核/WebUI 引用 + 适用动作齐全”的共享矩阵测试。 | 增加参数化 standalone 审计测试，输入 8 个仓库/5 场景/动作清单；同时在 CI 中检查 `bridge-sdk` 加载、路由集合和禁用的核引用。 | 1–2 天 |
| **G9** | 知 / ①–⑤ | 未保存守卫只跟踪高级配置 `configState.dirty`（`pages/manager/app.js:19-21,1084-1085`）；基础设置 modal 的 LLM Provider、精炼开关等在 `:1119-1175,1337-1391` 保存，但未纳入 `hasUnsavedChanges`，关闭/切页可能静默丢失。 | 为基础设置建立表单基线/统一 dirty registry，并在关闭 modal、切换 tab、刷新和离开时复用 `SeriesUI.confirm`；补“编辑基础设置后离开”的浏览器/契约测试。 | 0.25–0.5 天 |
| **G10** | 情 / ①–⑤ | `hasUnsavedChanges` 只扫描 `#config-form`（`pages/manager/app.js:625-627`）；身份编辑器的字段编辑/移除账号在 `:1162` 才保存，但关闭弹层 `:940-942` 和切页 `:952-957` 不会检测身份草稿。 | 为身份编辑器增加表单 baseline，在关闭弹层、切换 tab、刷新和离开时触发确认；禁止把身份编辑误判为已保存。 | 0.25–0.5 天 |
| **G11** | 临 / ①–⑤ | `hasUnsavedChanges` 只覆盖人格 settings/editor/converter（`pages/operator/app.js:1250-1253`）；Public URL、Quest 链路、工具过滤、知识/环境、快速动作、STT/TTS/平台/诊断等有独立保存按钮（`:352,602,690,756,846,2640,2660,2693,3138`），切换设置组时只在离开 persona 组检查（`:1513-1518`）。 | 建立通用分区表单 baseline/dirty registry，所有设置组切换、刷新、离开都统一检查；保留 persona 草稿的特殊处理。 | 0.5–1 天 |
| **N1** | 核 / ①–② | 无代码层可修复的 fallback：审计对象本身未加载时，没有 Page API 或 WebUI listener 可调用；WebUI 不是外部服务。 | 不改代码伪造第二入口；在发布文档和告警中明确“核未加载不可从核管理”，恢复应依赖 AstrBot 自身的插件管理/重新启用流程。 | 0（设计约束） |

## 5. 结论与优先级

### 结论

1. **核依赖结论通过**：知的公开 Page 动作、言、序、情、境、声、临都没有硬编码 `astrbot_plugin_update_manager` 或 `/api/series/`；核未安装、未加载、native 接管、WebUI 不可用、diagnostics 不可用不会直接切断它们的 Page。核 WebUI 不可用也不会代理它们的原生 Page API。
2. **standalone 完整性尚未全绿**：`言`、`序`、`境`在当前实现和测试证据下可判为完整；`声`功能完整但 Page CRUD/预览的 HTTP 合约缺少直接测试；`知`缺动作全集，`情`缺原子账号迁移，`临`缺批量管理动作，`核`缺 Page 回滚。
3. **未保存守卫基础已补齐，但表单覆盖不全**：当前 8 个 Page 都有 `SeriesUI.confirm` + `beforeunload` + `hasUnsavedChanges`，并有各仓 `tests/test_page_dirty_guard.py`；知的 basic settings、情的身份编辑器、临的非人格设置未全部纳入 dirty 状态（G9-G11）。iframe sandbox 下仍是 best-effort，不应当把它当作强杀进程后的草稿持久化。
4. **核必须单独看**：`webui/` 的同进程依赖 `UpdateManagerPlugin` 加载和 `initialize()`；它只增强核自身管理，不是核未安装/未加载时的 fallback。核 Page 是唯一单插件 fallback，因此 G4 优先级高于普通测试补项。

### 优先级

| 优先级 | 工作项 | 理由 | 建议工期 |
|---|---|---|---|
| **P0** | G4：核 Page 事务列表 + 手工回滚 | 唯一涉及恢复/安全闭环的 standalone 缺口；WebUI 故障时不能把恢复动作留给命令行或外部入口。 | 1–2 天 |
| **P1** | G1：知撤销验证/JSON 导入/刷新动作 | managed 与 Page 动作不一致，直接违反“全部管理动作仍可通过 Plugin Page 完成”。 | 1–1.5 天 |
| **P1** | G3：临批量撤销/断开 | 单条撤销无法等价覆盖 managed 的批量管理语义。 | 0.5–1 天 |
| **P1** | G2：情原子账号迁移 | 现有全量保存可近似但不保证事务一致性和关系状态迁移语义。 | 0.5–1 天 |
| **P1** | G9-G11：知/情/临的表单 dirty 覆盖 | 现有测试只证明守卫函数存在，不能防止基础设置、身份草稿或临的多组设置被静默丢弃。 | 1–2 天 |
| **P2** | G5/G6/G7：知/声/情的 Page 路由直接测试 | 补足“代码看起来可用”与“接口被直接证明可用”的证据差。 | 1–2.5 天 |
| **P2** | G8：8 仓×5 场景共享审计测试 | 将本次人工矩阵固化为可重复 CI 证据，防止后续 Page/路由回退。 | 1–2 天 |

