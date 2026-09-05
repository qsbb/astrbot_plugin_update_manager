# 凝心溯溪系列插件开发规范

> **文档定位**：本文件是凝心溯溪系列的唯一现行技术规范，治理范围为 8 个插件（知、言、序、情、境、声、临、核）。规范正本只存于核仓库根目录（本文件），随核发布；其余仓库不再分发副本。
>
> - 取代 `docs/CONVENTIONS-公共规范快照.md`（核仓库内，2026-07-24 历史快照，仅作追溯，不再指导开发）。
> - 与《开发协作约定.md》（流程层：需求归属、开发流程、环境事实）互补——约定管"谁在什么流程下做什么"，本规范管"代码必须长什么样"。
> - 平台层依据：AstrBot `AGENTS.md` 工程规范与 AstrBot 源码事实（`astrbot.core.provider`、`ProviderManager`、dashboard provider API、`pyproject.toml`）。
> - 事实基线：以 2026-09-02 的实现为准；附录 A 记录现行状态快照，后续随实现演进更新。
> - **治理范围：8 个插件（知、言、序、情、境、声、临、核）。枢（`astrbot_plugin_orchestration_hub`）未接入系列治理，按 2026-09-02 决定忽略——不适用本规范、不纳入契约要求与开发范围。**

---

## 1. 总则（第一性原则）

1. **插件是宿主的租户**：系列插件运行在 AstrBot 进程内。不修改 AstrBot Core、不打猴子补丁、不触碰宿主私有对象；一切能力通过公开 API（`astrbot.api.*`）获得。
2. **插件之间是进程内邻居，不是依赖方**：跨插件协作只走第 5 节的版本化契约；禁止 import 其他插件的内部模块、禁止读写其他插件的数据文件。
3. **KISS / 最小有用变更**：先识别真实问题、需要的行为、最小可用改动，再写代码。不加投机性抽象、配置开关、依赖或兼容层。修 bug 不顺手重构。
4. **fail-closed**：契约校验失败、权限不足、provider 不可用时返回明确错误码并降级，绝不"大概行"地继续执行。
5. **可观测是功能**：诊断契约（5.1）是必选项。每个插件必须能回答"我刚才做了什么、为什么"。

---

## 2. 命名与不可变标识

### 2.1 系列与单字分配

系列名：**凝心溯溪**。展示名格式 `凝心溯溪-{单汉字}`，单字唯一、一经分配不变：

| 字 | plugin_id | 职责域 |
|----|-----------|--------|
| 知 | `astrbot_plugin_active_learner` | 可验证知识：多源检索学习、交叉验证、黑话、知识图谱、记忆注入；不存私人情节 |
| 言 | `astrbot_plugin_conversation_flow` | 对话调节：沉默判断、分段、插话衔接、群聊上下文、交付政策 |
| 序 | `astrbot_plugin_identity_guardian` | 身份与行动授权：关系感知、权限边界、群管工具、最终否决权 |
| 情 | `astrbot_plugin_relationship` | 关系状态：情绪、好感、四维信任、熟悉度、跨平台身份归属、表达建议 |
| 境 | `astrbot_plugin_environment_awareness` | 环境事实：时间、天气、空气质量、预警、地震；不做生活日程 |
| 声 | `astrbot_plugin_voice_hub` | 语音：双 TTS 后端、多音色、AI 语音导演、PCM 契约、可取消交付 |
| 临 | `astrbot_plugin_embodiment_bridge` | 具身桥接：VR/MR 设备 Protocol 1.0、SSE、STT/TTS、动作意图、空间感知 |
| 核 | `astrbot_plugin_update_manager` | 更新与治理：安全更新/回滚、每日规则、系列诊断、模型路由、配置接管 |

> 枢（`astrbot_plugin_orchestration_hub`）已忽略：不在治理范围内，本规范不约束它。其单字「枢」视为已分配，不得释放给其他插件复用；若未来重新接入，按第 12 章清单从零执行。

### 2.2 不可变标识（改动即破坏性变更）

- 目录名 = `metadata.yaml` 的 `name` = `@register` 第一个参数（如 `astrbot_plugin_relationship`），三者必须一致
- 命令前缀（见 2.3）
- 配置键名与配置文件名
- 契约方法名（第 5 节）

历史别名（如 临 的 `astrbot_plugin_quest_avatar_bridge`）只能在核的可信登记中以 `aliases` 形式兼容，不得产生第二个正式标识。

### 2.3 命令前缀（现行分配）

| 字 | 命令 | 形态 |
|----|------|------|
| 知 | `/memory` | `command_group` |
| 言 | `/convflow` | `command_group` |
| 序 | `/idg` | `command_group` |
| 情 | `/rel` | `command_group` |
| 境 | `/environment`（别名 `境`）、`/env_time` `/env_calendar` `/env_weather` `/env_air` `/env_alerts` | 平铺命令 + 中文别名 |
| 声 | 无聊天命令 | 通过 LLM 工具与配置触发 |
| 临 | 无聊天命令 | 通过协议/SSE 桥接触发 |
| 核 | `/aup` | `command_group`（管理员权限） |

- 新增前缀前必须查重（含别名）；命令名不含空格，多级语义用 `command_group`。
- 管理员命令统一挂 `@filter.permission_type(filter.PermissionType.ADMIN)`。

### 2.4 描述文案风格

- `desc` / `short_desc` 以「凝心溯溪系列 XX 模块」开头，冒号后列能力清单。
- 不用感叹号、不用营销话术，保持工程文档语气。

---

## 3. AstrBot 平台基座规范

> 本章合并 AstrBot `AGENTS.md` 工程标准与本系列运行事实，是全部插件的平台层硬性要求。

### 3.1 运行环境与版本下限

- AstrBot 核心当前要求 **Python ≥3.12**（核心 `pyproject.toml` `requires-python`）；系列插件以 3.12 为运行下限，禁止依赖更高版本特性。
- 跨平台兼容：Windows / macOS / Linux、ARM64 / x86；不写平台假设（路径分隔符、`os.replace` 语义、文件锁均按可移植写法）。
- `metadata.yaml` 的 `astrbot_version` 下界必须覆盖实际使用的 API：
  - 现行声明：知/言/情/境/声 `">=4.16,<5"`；序 `">=4.17,<5"`；临 `">=4.26,<5"`；核 `">=4.16,<5"`。
  - 参考下界：`on_llm_response` ≥4.16；`TextPart.mark_as_temp()` ≥4.24；Agent/tool 新钩子 >4.23.1。用了更新 API 必须同步抬下界。
- 第三方依赖写入 `requirements.txt`（无依赖也保留空文件）；约束用 `>=` 下界，不锁上限除非已知不兼容；网络请求一律异步客户端（`aiohttp`/`httpx`），禁止阻塞式 `requests`。

### 3.2 路径与数据

- 一律 `pathlib.Path`，不使用字符串路径。
- 持久化数据只放 AstrBot data 目录（`context.get_plugin_data_dir(PLUGIN_NAME)`），**永不写插件安装目录**——核的自更新会在运行中替换插件目录。
- JSON 落盘必须原子写：`tempfile.mkstemp` → `json.dump` → `flush` + `fsync` → `os.replace`（参考 情 `series_control.py` 的 `_write`）。
- 外部 IO 必须有超时上限；并发外呼用有界并发（参考 核 `core/concurrency.py` `bounded_gather`），单个慢源不得拖垮整批操作。

### 3.3 钩子语义

- 钩子必须显式声明 `priority`，不依赖默认值与加载顺序（分配见第 4 节）。
- `on_llm_request` / `on_llm_response` / `on_decorating_result` 内不 `yield` 消息；需要发送用 `await event.send(...)`。
- `event.stop_event()` 会截断整条链，调用前必须确认语义；只想拦截默认 LLM 流程时优先使用 extra 标记而非停止传播。
- `terminate()` 清理全部运行时资源：定时任务、文件句柄、网络连接、动态注册的 LLM 工具；模块级单例（如 `_current_instance`）必须置空。
- 不直接修改全局 `star_handlers_registry`；确需操作时以自身插件名为筛选条件并在 `terminate()` 中撤销。

### 3.4 配置 schema（`_conf_schema.json`）

- 只使用 AstrBot 内建类型（`bool` / `int` / `float` / `string` / `object` / `list` …）；**禁止自造类型**（0.13.2 教训：自定义类型导致宿主 schema 解析失败，改用原生 `object`）。
- 每个字段必带 `type` / `description` / `default`；`object` 字段补 `items` 定义（0.13.3 教训）。
- 敏感字段声明 `"secret": true`，读取接口侧转 `write_only: true`；**回显只给 `{configured: bool}`，永不回传明文**（"不回显"原则）。
- schema 变更向后兼容：新增字段必须提供默认值；删除或重命名字段必须在 CHANGELOG 写迁移说明。

### 3.5 Provider 与模型访问

- Provider 实例从 `context.provider_manager` 的分桶枚举：`provider_insts`（对话/LLM）、`embedding_provider_insts`、`stt_provider_insts`、`tts_provider_insts`、`rerank_provider_insts`；按 id 查实例用 `inst_map` 或 `get_provider_by_id()`。
- 实例的 `provider_config` 是配置 dict（含 `id` / `type` / `model` 等）；当前模型用 `get_model()`；id 首选 `provider_config["id"]`。
- **`get_models()` 可能发起远程请求**：设置页渲染、候选枚举、表单填充等路径禁止调用它（0.16.0 教训），只读已加载配置；确需在线模型清单时由用户显式触发。
- 跨插件选模型一律走核的 `series.model_router@1.0`（见 5.4），不自建 provider 探测逻辑。

### 3.6 日志

- 统一使用 `astrbot.api.logger`，消息前缀 `[plugin-short]`（如 `[update-manager]`）。
- 级别纪律：ERROR=需要人介入；WARNING=已降级但仍可用；INFO=状态变化；DEBUG=细节。
- 日志与审计中的错误文本必须先经 `redact()`（核 `core/adapters/storage.py`）脱敏；任何情况下不打印凭据。

---

## 4. 钩子优先级分配

区间规则：LLM 三钩子（`on_llm_request` / `on_llm_response` / `on_decorating_result`）使用 **200–800**，数值越大越先执行；消息监听类钩子使用 100–1000。

**现行槽位（已占用，新插件不得冲突）：**

| 钩子 | 槽位分配 |
|------|---------|
| `on_llm_request` | 序 800 · 知 700 · 情 600 · 境 550 · 言 500 · 声 300 · 临 250 |
| `on_llm_response` | 知 700 · 言 500 |
| `on_decorating_result` | 言 600 · 声 400 |
| 消息监听 | 言 1000（GROUP_MESSAGE）· 序 500（ALL） |

**硬顺序约束（架构上必须保持）：**

1. LLM 注入链：序(800) → 知(700) → 情(600) → 境(550) → 言(500)——身份与安全边界先于知识注入，知识先于对话收敛。
2. 交付链：言(600) 先完成分段，声(400) 后做语音合成——语音必须拿到最终分段结果。

**新插槽规则**：新插件在 200–800 内选择未占用槽位（当前空闲：200、450、650、750），同时在代码注释与本表登记。调整已占用槽位 = 破坏性变更，升主版本并全系列回归。

---

## 5. 跨插件契约体系

### 5.0 通用规则（所有契约共同遵守）

- `series_id` 一律 `ningxin_suxi`；契约四要素 `name` / `series_id` / `plugin_id` / `version`，任一缺失或不匹配即 fail-closed。
- 统一错误码：`PLUGIN_NOT_TRUSTED` / `PLUGIN_NOT_LOADED` / `CONTRACT_UNAVAILABLE` / `CONTRACT_VERSION_UNSUPPORTED` / `REVISION_CONFLICT` / `ROLE_REQUIRED` / `ROLE_FORBIDDEN`。
- 角色模型：viewer < admin < owner。读操作 viewer+；写操作 admin+；生命周期（安装/更新/启停）与回滚仅 owner。
- 写操作携带 revision 乐观锁；版本不符返回 `REVISION_CONFLICT`，调用方重新拉快照。
- 契约响应永不携带凭据（`secrets_in_response: false`）；密钥命中的字段在 schema/snapshot 双侧剔除。
- 可信登记：核 `core/trusted.py` 的 `TRUSTED_SERIES` 是唯一名单，仓库地址严格匹配 `https://github.com/qsbb/<plugin_id>`。新插件必须先登记，再被核治理。枢虽保留在登记中（历史安装兼容），但按忽略决定不对其发起契约调用与治理操作。
- 跨插件调用全部走 in-process 实例方法（`adapter.get_plugin_instance`），不经 HTTP、不依赖 dashboard 会话。

### 5.1 `series.diagnostics@1.0`（必选契约）

每个插件必须实现三个方法：

```python
def diagnostic_log_contract(self) -> dict: ...      # 声明
def diagnostic_events(self, after_seq=0, limit=200) -> dict: ...   # 游标续读
def diagnostic_clear(self) -> None: ...
```

- 声明内容：`{name: "series.diagnostics", version: "1.0", series_id, plugin_id, plugin_name, capabilities, storage: "memory_only", astrbot_log_propagation: False}`。
- 事件结构：`{seq, timestamp(UTC ISO), plugin_id, plugin_name, level, code(≤80), summary, details(dict)}`。
- 内存环形缓冲上限 1000 条；`limit ≤ 1000`；返回 `events + next_seq + dropped_before + stream_id`；`stream_id` 变化表示插件重启，调用方必须重置游标。
- **脱敏哲学**：保留排障数据（路径、URL、参数、账号标识、长数字、正文、错误文本、哈希），只隐藏凭据值——key 命中 `token / api_key / secret / password / authorization / cookie / jwt / private_key / ssh_key / provider_key / bridge_key` 时值替换为 `<已隐藏>`，结构保留。
- 级别仅 DEBUG / INFO / WARNING / ERROR；不向 AstrBot 核心日志传播。
- 核聚合端输出 `series.diagnostics.aggregate@1.0`，单成员读取超时 3 秒级；成员状态集：`ready / timeout / read_failed / invalid / unsupported / missing / incompatible / lookup_failed`。

### 5.2 `series.control@1.0`（配置接管）

插件侧方法面（7 个，全部显式实现，不做动态属性）：

```python
def series_control_contract(self) -> dict: ...
def series_control_schema(self) -> dict: ...
def series_control_snapshot(self) -> dict: ...
def validate_series_control_patch(self, patch, expected_revision) -> dict: ...
def apply_series_control_patch(self, patch, expected_revision) -> dict: ...
def reset_series_control_override(self, fields, expected_revision) -> dict: ...
def series_control_set_mode(self, mode) -> dict: ...   # native | managed
```

- schema 的 fields 描述：`{type, default, minimum/maximum, control: overrideable|read_only, secret, source, native_value, effective_value, managed_configured}`。
- 覆盖层存插件自己的 data 目录 `series-control.json`（原子写 + 自身 revision）；核另存全系列 overlay。
- `native`：插件自身配置生效；`managed`：核覆盖生效；关闭接管立即回退，无残留状态。
- capabilities 至少声明 `read_schema / read_snapshot / validate_patch / apply_patch / reset_override`。
- 校验失败拒绝整批 patch，不部分应用；apply 前必须先 validate。

### 5.3 `series.webui@1.0`（管理面板）

```python
def webui_panels_contract(self) -> dict: ...
def webui_panel_data(self, panel) -> dict: ...
def webui_panel_action(self, panel, action, payload) -> dict: ...
```

- 声明：`{name: "series.webui@1.0", plugin_id, series_id, panels: [{id, title, description}]}`。
- 面板与动作 id 规则 `^[a-z0-9_]{1,48}$`；未知 id 返回 `UNKNOWN_PANEL` / `UNKNOWN_ACTION`。
- 数据走**通用渲染契约**：`{success, title, description, columns: [{key, label}], rows: [...], actions: [...]}`——前端零定制即可统一接管。
- 动作可带 `confirm` 提示文本与 `payload_fields`（`name/label/type/required`）；执行要求 admin+ 角色（网关侧二次校验）；返回 `{success, message}`。
- **新插件需要管理界面时优先实现本契约**，由核 WebUI 统一接管，不再新建独立控制台（见第 9 节）。

### 5.4 `series.model_router@1.0`（只读模型路由）

- 核暴露 `resolve_model_route(kind, plugin_override=None)` 与 `model_routes_snapshot()`；契约只读、不修改 AstrBot 配置。
- 回退顺序：插件显式配置 → 核配置 → AstrBot 原生 → `unavailable`。
- kinds：`conversation / embedding / vision / stt / tts`；**voice 字段仅对 tts 有意义**（0.16.0 起保存与解析时静默丢弃其他 kind 的 voice）。
- 配套 `GET /api/model-options` 只读已加载 provider 配置与已配置模型清单，不触发远程模型探测。

### 5.5 `active_learner.knowledge@1.0`（知识桥接，知 → 序）

- 提供方（知）：`knowledge_contract()` 返回 `{name: "active_learner.knowledge", version: "1.0", plugin, capabilities: ("recall",)}`。
- 检索方法：`recall(query, scope="", top_k=5)`，async、**只读**（不写库、不计访问次数、不触发学习）。
- 每条证据字典含 `content / source / score / topic / verified / confidence`；消费方（序）侧 `top_k` 上限 10（`_BRIDGE_RECALL_MAX_TOP_K`）。
- scope 格式：`group:123` / `private:u1` / `global`；无法识别时回落 `global`（序的入群审核发生在成员进群前，没有可信上下文）。
- **版本校验是硬性要求（反 duck-typing）**：消费方在启动时通过插件服务发现获取对端实例，校验契约名与 major 版本——缺少契约方法 → 视为不支持，warning；major 不一致 → 停用桥接 + warning，不做兼容猜测；major 一致、minor 更高 → 允许，按已知字段读取。历史教训：0.x 时期靠 duck-typing 探测 `recall`，对端未实现时桥接静默失效，排查成本极高。
- 版本语义：major 递增 = 不兼容变更（消费方必须停用）；minor 递增 = 向后兼容新增。

### 5.6 `ningxin.request_context.v1`（统一请求上下文，6 插件）

- 载体：`event.set_extra` / `event.get_extra` 上键为 `ningxin.request_context.v1` 的**普通 dict**（契约名 `ningxin.request_context`，版本 `1.0`）。禁止放入插件实例、dataclass、自定义类对象——只允许 JSON 可表达的普通值；跨插件传对象会制造隐式依赖，热重载后出现「同名不同类」的 isinstance 失败。
- **字节一致副本分发**：同名模块 `request_context.py` 在 6 个仓库各存一份（知在根目录，言/序/情/声/核在 `core/`），修改时必须同步全部副本（2026-09-02 经 md5 校验一致）。副本一致性目前靠人工同步；模块 docstring 提及的 series 级一致性测试尚未落地，落地前每次改动后必须 md5 复核。
- 结构与写入纪律：
  - 任一插件可**惰性创建**（先到者建骨架，后到者复用），不依赖加载顺序；
  - **字段单写者**：`flags` / `artifacts` / `diagnostics` 按 owner 分区，每个插件只写自己的分区；`version` / `request_id` 创建后不可变；`phase` 是唯一多写者字段，只允许按 `PHASE_ORDER` 单调前进（created → message → command → llm_request → llm_response → decorating_result）；
  - 现行 owner 恰为 6 个：`active_learner / conversation_flow / identity_guardian / relationship / update_manager / voice_hub`（境不参与；临为只读消费者，无写者身份）。新增 owner 需同步全部副本的 `KNOWN_OWNERS`。
- 容量上限：每 owner 原因码 32 条、prompt 片段 16 条、单片段 24,000 字符（`prompt_fragments` 工件）；越界写入抛 `RequestContextError`。
- 现行用法：言将文本分段/交付计划写入自己分区（同时挂 event extra `conversation_flow.delivery_plan`）；声与临读取该交付计划决定语音合成前的最终文本（临的实现为 extra 优先、request_context 工件回退的双链读取）。
- 便捷入口：`note(event, owner, reason, phase)` 一行完成惰性建上下文 + 推进 phase + 记原因码。

### 5.7 契约实现状态（2026-09-02）

| 字 | diagnostics | control | webui panels | knowledge 桥 | request_ctx |
|----|-------------|---------|--------------|---------------|-------------|
| 知 | ✓ | ✓ | — | 提供 | ✓（owner） |
| 言 | ✓ | ✓ | — | — | ✓（owner） |
| 序 | ✓ | ✓ | — | 消费 | ✓（owner） |
| 情 | ✓ | ✓ | ✓ | — | ✓（owner） |
| 境 | ✓ | ✓ | — | — | — |
| 声 | ✓ | ✓ | — | — | ✓（owner） |
| 临 | ✓ | ✓ | — | — | 只读消费 |
| 核 | ✓（聚合方） | 网关 | 网关 | — | ✓（owner） |

---

## 6. 配置与持久化

- 运行态可写配置与 schema 分离：对外入口只允许写白名单键（参考 核 `WEBUI_SETTINGS_KEYS`），敏感键只在核 Page 维护。
- **保存链路单一内核**：Plugin Page 与独立入口共用同一保存内核（校验 → 原子持久化 → 运行时应用 → 调度重建，参考 核 `_save_config_core`），不允许两套平行实现。
- 数据文件带 `schema_version` 字段；读旧版本数据时兼容迁移，不静默丢弃。
- 时区一律 UTC 存储（`datetime.now(UTC)`），展示层再本地化。

---

## 7. 代码结构与工程质量

### 7.1 目录结构

```
astrbot_plugin_xxx/
├── main.py              # 入口；目标 ≤1000 行，只做装配与 AstrBot 接口层
├── metadata.yaml
├── _conf_schema.json
├── requirements.txt     # 无依赖也保留空文件
├── core/ 或按域拆分模块     # 业务逻辑
├── series_control.py    #（接入时）series.control 适配器，独立成文件
├── series_diagnostics.py# series.diagnostics 适配器，独立成文件
├── request_context.py   #（参与时）系列统一请求上下文字节一致副本（5.6）
├── pages/manager/       #（可选）Plugin Page
└── tests/test_*.py
```

### 7.2 工程标准（采纳自 AstrBot AGENTS.md）

- 提交前执行 `ruff format .` 与 `ruff check .`；CI 必须绿。
- Conventional commits：`feat:` / `fix:` / `docs:` / `chore:` + 中文描述（系列惯例；若直接向 AstrBot 核心仓库贡献，标题与描述全英文）。
- 复杂函数写 Google 风格 docstring（`Args:` / `Returns:` / `Raises:`）；非显而易见的逻辑必须注释（"Comment the complex"）。
- **Helper 政策（inline-first）**：逻辑能内联就内联；只有满足"同一逻辑 ≥3 处复用"或"内联使主函数超过约 50 行"才抽函数；不为"整洁"拆碎连续逻辑；修改既有代码时不顺手重构函数结构。
- 禁止提交：`.bak`、`__pycache__`、临时文件、报告类文件（如 `xxx_SUMMARY.md`）。
- **语言规则**：标识符、错误码、日志与 API 名一律英文；注释、文档、CHANGELOG、用户可见文案用中文（系列面向中文用户的既定惯例，与 AstrBot 核心"全英文"规则的差异在此显式豁免并记录）。

### 7.3 安全底线

- 不执行第三方代码；不 eval 远程内容；插件目录内容视为不可信输入。
- 凭据只进 `secret` 字段；不进日志、审计、契约响应、异常文本（`redact()` 兜底）。
- 写操作双重门控：会话角色 + 动作级 confirm；高危操作（更新/回滚/停用）仅 owner。
- 自更新禁止（核 `SELF_UPDATE_FORBIDDEN`）：更新一律走核的事务链路——备份 → 更新 → 健康检查 → 失败自动回滚。

---

## 8. 测试规范

- 测试位于 `tests/test_*.py`，不依赖运行中的 AstrBot 实例；框架对象用 stub（参考 核 `tests/test_plugin_entry.py` 的 `astrbot.api` stub 方案）。
- 必测路径：
  - 命令解析与权限门控
  - 配置加载、schema 校验、敏感字段不回显
  - 钩子入口逻辑
  - 契约方法：contract 声明形状、schema/snapshot、apply 的 revision 冲突与 fail-closed 分支
  - 脱敏不泄漏（序列化全文断言不含凭据样例）
- 运行方式（每插件目录内）：
  ```bash
  source /data/dsh/home/dsh/venv/bin/activate
  python -m pytest tests/ -x -q
  ```
- 全系列当前基线 2,156 例；已知环境相关失败 2 例（知 `test_retrieval_sources`、核 `test_transaction_coordinator` 的 symlink 项），非代码 bug，不阻塞合入，但不得新增失败。
- UI 结构断言：用 `test_pages_ui.py` 对前端源码做关键控件/接口存在性断言，防止界面回退。

---

## 9. 用户界面规范

- **Plugin Page**（`pages/manager/`）：运行在 dashboard iframe，经 bridge-sdk 接入，宿主 JWT 鉴权；必须带 zh-CN/en-US 双语 i18n；i18n 页面元数据（title/description）齐全。
- **核独立 WebUI**（仅核，`webui/`）：自有 aiohttp 服务与会话 Cookie；首屏永远是登录页；不提供注册入口；管理员账户只在核 Page 创建和维护。
- **边界规则**：新插件需要管理面时，实现 `series.webui@1.0` 面板交给核统一接管；不新建第二个独立控制台、不复制核的鉴权体系。
- 前端改动保持组件化、无重复代码（AstrBot WebUI 工程要求）。
- 若向 AstrBot dashboard 贡献：对话框标题基类 `text-h3 pa-4 pb-0 pl-6`，按钮 `variant="text"` / `variant="tonal"`；后端 API/schema 变更后执行 `pnpm generate:api` 重新生成前端客户端。

---

## 10. 版本与发布

- 语义化版本，三段式、无 `v` 前缀（`{主}.{次}.{修订}`）。
- `metadata.yaml` 的 `version` 是**唯一事实源**，必须同步 `main.py` 的 `__version__`（有测试断言二者一致）。
- 升版本判定：不兼容变更（命令改名、配置键删除、钩子顺序变更、契约破坏）→ 主版本；向下兼容新功能 → 次版本；向下兼容修复 → 修订号；纯文档/注释改动不升版本。
- 每次发布在 `CHANGELOG.md` 顶部写版本段（未发布内容积累在 `Unreleased`）。
- 核是系列唯一的更新通道：串行事务、备份、健康检查、自动回滚、审计。

---

## 11. 开发流程（摘要）

需求定位 → 判断目标插件（给理由）→ 实现与测试 → 升版本与 CHANGELOG → 全量自测 → conventional commit → push main。

完整流程、需求归属判断规则、不 push 的情形与远端部署边界见《开发协作约定.md》。若向 AstrBot 核心仓库贡献代码，额外遵循其 `AGENTS.md`：全英文、`uv sync` 环境版本同步（`pyproject.toml` 与 `astrbot/__init__.py`）、release 分支流程。

---

## 12. 新插件接入清单

- [ ] 单字命名 + 展示名 + desc 文案合规（2.1 / 2.4）
- [ ] 目录名 / metadata `name` / `@register` 首参一致；命令前缀查重（2.2 / 2.3）
- [ ] `_conf_schema.json`：内建类型 + 默认值齐全；敏感键 `secret`（3.4）
- [ ] 钩子显式 `priority`，选未占用槽位并登记（第 4 节）
- [ ] `series_diagnostics.py` 三方法 + 脱敏规则（5.1，**必选**）
- [ ] `series_control.py` 七方法（5.2，需要被核接管时）
- [ ] `webui_panels_contract` 面板三方法（5.3，需要管理面时）
- [ ] 需要跨插件请求上下文时：同步全部 6 份 `request_context.py` 副本（含 `KNOWN_OWNERS`）并 md5 复核一致（5.6）
- [ ] 在核 `core/trusted.py` 登记可信清单（plugin_id / display_name / repo_url）
- [ ] 测试套件（含契约与脱敏断言）+ CHANGELOG + README 更新
- [ ] 版本号与 `astrbot_version` 下界声明（第 10 节 / 3.1）

---

## 附录 A. 现行状态快照（2026-09-02）

| 字 | plugin_id | 版本 | astrbot_version |
|----|-----------|------|-----------------|
| 知 | astrbot_plugin_active_learner | 1.5.3 | >=4.16,<5 |
| 言 | astrbot_plugin_conversation_flow | 0.8.13 | >=4.16,<5 |
| 序 | astrbot_plugin_identity_guardian | 0.5.4 | >=4.17,<5 |
| 情 | astrbot_plugin_relationship | 0.9.6 | >=4.16,<5 |
| 境 | astrbot_plugin_environment_awareness | 0.3.1 | >=4.16,<5 |
| 声 | astrbot_plugin_voice_hub | 0.9.1 | >=4.16,<5 |
| 临 | astrbot_plugin_embodiment_bridge | 1.1.3 | >=4.26,<5 |
| 核 | astrbot_plugin_update_manager | 0.16.0 | >=4.16,<5 |

枢（astrbot_plugin_orchestration_hub 0.2.1）已忽略，不纳入治理范围，故不列于此表。

契约实现矩阵见 5.7；钩子槽位分配见第 4 节；命令前缀分配见 2.3。
