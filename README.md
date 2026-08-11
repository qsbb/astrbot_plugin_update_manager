# 凝心溯溪-核（astrbot_plugin_update_manager）

凝心溯溪系列更新模块：安全、串行、可回滚的 AstrBot 插件更新管理器。发现可信来源候选，冻结不可变计划，通过 AstrBot 核心串行更新，并提供备份、健康检查、自动回滚、审计、持久化每日规则与清理能力。

## 当前实现信息

- 版本号以 `metadata.yaml` 为唯一事实源；AstrBot 兼容范围：`>=4.16,<5`。
- 当前版本请以 `metadata.yaml` 中的 `version` 字段为准。
- 版本口径：README 只描述当前实现；CHANGELOG 下方版本号与日期均为真实历史记录，不因当前文档整改而改写。
- 命令入口：`/aup` 命令组，支持探测、目录、计划、执行、规则、预演、回滚、取消、状态和套件诊断（`/aup diag`）。
- 页面入口：AstrBot Plugin Page 的“更新管理”页面；实现目录为 `pages/manager/`，页面能力不可用时命令与调度仍可用。
- 当前展示名：`凝心溯溪-核`；旧文档中的“焕”仅是历史称呼，不再作为现行名称。

## 特性

- 可信来源候选发现，条件请求与缓存，支持代理与可选 GitHub token。
- 兼容 AstrBot 4.27.1 的 `repository` 安装来源标识：只有严格校验为 `https://github.com/<owner>/<repo>` 的仓库才归一为 `github`；来源类型缺失时可从同样受校验的插件 `repo` 元数据推断。保留插件和核自身仍禁止更新。
- 可选 GitHub 镜像加速：内置 gh-proxy 系加速站并支持自定义，版本探测与归档兜底走镜像优先、直连兜底，镜像挂掉不会导致检查失败。
- 冻结不可变计划（TTL 有效期内），避免执行与预览漂移。
- 经 AstrBot 核心串行更新，单事务加文件租约锁，杜绝并发。
- 并发/串行边界：版本检查是有上限的并发只读操作；检查任务之间按并发上限执行，单项检查有独立超时。任何会改变插件状态的安装、更新、启停、重载和回滚仍统一进入同一更新协调器，按事务边界串行执行，并发检查不会与更新写操作并行穿透。
- 更新前自动备份，更新后执行加载/版本/启用状态检查；声明 `plugin.health@1.0` 的插件还会执行业务健康检查，失败自动回滚。
- 持久化每日规则、审计记录与备份清理策略（按数量、天数、容量）。
- 提供 AstrBot Plugin Page 便捷设置页面，可查看总览、修改常用配置、浏览插件目录并管理固定可信系列推荐。
- 固定可信系列清单仅包含 qsbb GitHub 仓库：知 `active_learner`、言 `conversation_flow`、序 `identity_guardian`、情 `relationship`、境 `environment_awareness`、声 `voice_hub`、临 `embodiment_bridge`、核 `update_manager`；核禁止自更新和自停用。
- Plugin Page API 采用运行时能力探测；旧版 AstrBot 不支持页面能力时自动降级，不影响命令与调度功能。
- `github_token` 等敏感配置按只写方式处理：只显示“是否已配置”，敏感 token 不回显到页面、接口响应或审计。
- 新增“日志”页，统一读取知、言、序、情、境、声、临、核以及自动发现的官方系列插件所声明的 `series.diagnostics@1.0` 内存诊断；只在打开该页时增量轮询，不依赖 AstrBot 主日志。
- 日志按插件、级别和关键词筛选，可暂停、刷新或清空；清空操作需要页面和接口双重确认。每个插件独立保留有限条目，并对账号标识、URL 参数和敏感字段再次脱敏。
- `enabled=false` 时统一门禁全部命令与调度。

## 版本与发布边界

- 核只读取各插件 `metadata.yaml` 的版本并比较远端，不替插件作者生成或改写版本号。
- 普通更新要求远端版本更高；强制更新只改变安装动作的许可，不改变语义化版本判断，也不会替本地代码升版。
- 版本选择遵循语义化版本：兼容新增功能升次版本，兼容缺陷修复升修订号，不兼容公开接口或配置迁移升主版本。
- 发布前应先完成实现、README、CHANGELOG、配置说明和测试，再由发布者确认具体版本号；同一发布提交中同步 metadata 与代码版本常量。

## 安装

将本插件目录放入 AstrBot 的 `plugins/` 目录，或通过插件市场安装。要求 AstrBot `>=4.16,<5`。

## 命令

所有命令使用 `/aup` 前缀（需管理员权限）：

| 命令 | 说明 |
|------|------|
| `/aup probe` | 探测当前运行环境的更新能力 |
| `/aup catalog` | 列出已安装插件目录 |
| `/aup plan <ids>` | 为指定插件冻结更新计划 |
| `/aup run <plan_id>` | 执行已冻结的计划 |
| `/aup rule <show\|...>` | 查看或配置每日更新规则 |
| `/aup dryrun <ids>` | 预演更新流程，不落地变更 |
| `/aup rollback <tx_id>` | 人工回滚满足前置条件的已提交事务 |
| `/aup cancel` | 在当前事务边界后停止批次 |
| `/aup status` | 查看运行状态 |

## 便捷设置页面

在支持 Plugin Page 的 AstrBot 版本中，可从插件详情进入“更新管理”页面：

- **总览**：查看插件状态、AstrBot 版本、更新能力探测结果与每日规则。
- **系列推荐**：查看知、言、序、情、境、声、临、核固定可信清单；按运行时能力显示“安装/已安装”“更新”“强制更新”“启用/停用”，并提供“一键全部安装/更新”。普通更新仅在远端版本更高时可用；强制更新可用远端版本覆盖同版本或本地更高版本，并有独立二次警告；境与其他非核插件使用完全相同的安装、更新和安全门禁。批量操作仍只执行普通更新，会先检查最新状态，再串行安装未安装项、更新确有新版本的已安装项；核始终跳过自更新。完成后汇总成功/失败并刷新推荐状态、总览和目录。核有新版本时，“前往已安装插件页”优先使用宿主 bridge 跳到 `/extension#installed`；bridge 不支持时保留链接的原生 `target="_top"` 跳转，只有宿主仍不允许顶层导航时才会显示并复制更新页 URL，复制失败则弹出 URL 供手动复制。
- **设置**：修改常用配置并即时应用；配置仍会持久化到 AstrBot `data` 目录。
- **镜像加速**：列出内置与自定义 GitHub 加速站，单选启用、一键并发测速查看毫秒延迟、添加或移除自定义站点，保存即热应用。
- **插件目录**：查看已安装插件、当前版本、来源与自动更新资格；右上角「检查更新」按需探测全部有 GitHub 来源的插件。普通「更新」仅在检测到远端新版本时可用；「强制更新」支持以远端版本覆盖本地版本，可用于同版本重装、恢复已回退插件，或将本地更高版本覆盖为远端版本，并使用独立二次确认。进入页面或切到该 tab 都不会自动检查，避免全量探测拖慢首屏并耗尽 GitHub 匿名配额。

推荐操作通过 AstrBot 核心 `install_plugin`、`update_plugin`、`turn_on_plugin`、`turn_off_plugin` 执行，适配 AstrBot `4.16-4.x` 的签名差异并统一串行。请求仅接受固定清单中的正式插件 ID 或明确声明的旧部署兼容别名；响应统一返回正式 ID。核禁止自更新和自停用。仓库页面 URL 仅用于安装来源，绝不会误传为 `update_plugin.download_url`；只有已解析的归档 URL 才会传给该参数。

“临”从旧 ID 迁移时，核会优先识别正式 ID；只有旧部署存在时，仍以旧运行时 ID 调用 AstrBot 更新接口，但下载源固定为新仓库。AstrBot 4.27.1 的插件配置文件按安装目录命名，因此这种就地更新会继续复用旧配置文件，且不会把旧、新身份同时安装。它是滚动升级兼容路径，不等同于物理目录改名；AstrBot 当前没有公开的跨插件配置原子迁移 API，核不会读取私有配置字段或复制其中的秘密。需要彻底改名时，应先通过 AstrBot 备份导出建立恢复点，再执行单独、可回滚的迁移流程。

为兼容旧版 AstrBot，插件会在运行时探测 Plugin Page 注册接口。若当前 AstrBot 不提供该接口，插件仅跳过页面与管理 API 注册，原有 `/aup` 命令、更新事务和调度能力继续按运行时可用能力工作，无需额外配置。

`github_token` 是只写敏感项：页面和 API 仅返回是否已配置，敏感 token 不回显原值；保存空值或占位符不会清除现有 token。如需替换 token，请输入新值后保存。

### 跨插件系列运行态契约

核为具身桥接插件等明确消费方提供纯只读契约 `update_manager.series_runtime@1.0`。消费方应先按插件 ID `astrbot_plugin_update_manager` 取得实例，再直接调用 `series_runtime_contract()`；只接受契约名完全一致且主版本为 `1`、能力包含 `read_runtime_snapshot` 的声明，不得通过猜测方法名或读取核的私有字段降级接入。

声明中的调用方法固定为 `get_series_runtime_snapshot`。请求只允许一个可选关键字参数：

```json
{
  "timeout_seconds": 2.0
}
```

`timeout_seconds` 必须是 `0.05` 到 `5.0` 秒的数值，默认 `2.0`；未知参数不属于 1.0 契约。建议仅在 Bridge 启动、会话建立时的兼容检查或显式健康检查中调用，不要每轮对话调用。

响应固定包含以下顶层字段：

```json
{
  "contract_name": "update_manager.series_runtime",
  "contract_version": "1.0",
  "capability": "read_runtime_snapshot",
  "status": "ok",
  "reason": "HEALTHY",
  "members": [
    {
      "plugin_id": "astrbot_plugin_active_learner",
      "label": "知",
      "installed": true,
      "loaded": true,
      "activated": true,
      "version": "1.4.0",
      "health_status": "ok",
      "reason": "HEALTHY"
    }
  ],
  "healthy": 7,
  "total": 7
}
```

`members` 始终按知、言、序、情、境、声、临、核排列。成员 `health_status` 可为 `ok`、`compatible`、`degraded`、`unhealthy` 或 `missing`；`compatible` 表示旧插件未声明 `plugin.health@1.0`，只能确认基础运行态。顶层状态及降级语义如下：

成员状态与原因码是固定组合：`ok/HEALTHY`、`compatible/L0_ONLY`、`degraded/PLUGIN_NOT_ACTIVATED`、`missing/PLUGIN_NOT_FOUND`；`unhealthy` 对应 `PLUGIN_NOT_LOADED`、`HEALTH_CONTRACT_INCOMPATIBLE`、`HEALTH_CONTRACT_INVALID`、`HEALTH_PROBE_FAILED`、`HEALTH_VERSION_MISMATCH` 或 `BUSINESS_HEALTH_UNHEALTHY`。出现未声明组合时整个响应返回 `error/DIAGNOSTIC_INVALID`，消费方不得使用部分成员数据。

| `status` | `reason` | 含义与消费方处理 |
|---|---|---|
| `ok` | `HEALTHY` | 全部成员健康或处于 L0 兼容模式，可读取各成员结果 |
| `degraded` | `MEMBERS_DEGRADED` | 至少一个成员缺失、未加载、未激活、契约不兼容或健康失败；仍可读取其余成员 |
| `unavailable` | `ADAPTER_UNAVAILABLE` | 核已终止或运行时 adapter 不可用；`members` 为空，消费方跳过诊断 |
| `unavailable` | `DIAGNOSTIC_TIMEOUT` | 只读诊断超过请求时限；`members` 为空，消费方跳过诊断并可稍后重试 |
| `error` | `INVALID_REQUEST` | 请求参数不符合 1.0 schema；消费方修正调用，不重试同一载荷 |
| `error` | `DIAGNOSTIC_FAILED` | AstrBot 运行态读取异常；消费方跳过诊断，不阻断自身基础功能 |
| `error` | `DIAGNOSTIC_INVALID` | 内部结果未通过严格 schema 校验；按不兼容处理，不消费部分数据 |

该契约只封装现有 `diagnose_series(adapter)`：读取本地安装/加载/激活状态并调用各插件公开的 `plugin.health@1.0` 探针。它不访问 GitHub 或镜像，不检查新版本，不创建计划，不安装、更新、启停或重载插件，也不写数据库或配置。契约不可用或核未安装时，具身桥接插件应继续隔离运行，只把系列诊断标记为不可用。

### 系列诊断日志

- “日志”标签位于首位并作为页面默认视图。页面打开后会立即读取日志，并与总览、推荐、配置、镜像和目录数据并行加载，不再等待其他标签全部完成。诊断会捕获本系列插件自有 logger 的 `DEBUG` 到 `CRITICAL` 事件；每个插件最多保留 1000 条，页面单次读取最多 1000 条、浏览器最多暂存 10000 条。列表每行先显示插件中文名，再显示时间、级别和事件；大量折叠日志由浏览器延迟布局，但不会因此丢失缓存事件。
- 页面一次最多渲染最近 500 条匹配日志，完整的 10000 条浏览器缓存仍可用于筛选；搜索输入会短暂防抖，轮询没有新增事件时不会重建整张日志列表。
- “核”自身除生命周期外，还记录初始化、候选解析、计划命令、执行命令、定时检查、批次开始/逐项/完成、事务状态、健康检查结果、自动或人工回滚、备份清理及 Page 操作。结构化详情包含 `component`、`operation`、`outcome`、`duration_ms`，同一次操作通过 12 字符 `operation_ref` 关联；批次和事务只展示短引用，不暴露完整内部标识。
- Page 的只读 GET 成功事件记为 `DEBUG`，写操作记录开始与完成，4xx 记为 `WARNING`，未处理异常和 5xx 记为 `ERROR`。事件只保留路由名、方法、状态和耗时，不保存请求正文；`diagnostics/logs` 轮询端点明确不记录，避免日志读取不断制造新日志并挤掉真正故障。
- 所有详细日志继续使用 1000 条有界内存缓冲，不写磁盘、不传播到 AstrBot 主日志。异常只保留类型和稳定原因码，不保存异常正文、密钥、URL、路径或用户内容。
- 总览、推荐、配置、规则、镜像、目录或日志任一区域加载失败时，只在对应区域显示中文错误和“重试”按钮，其余区域继续可用；刷新和保存期间按钮会显示忙碌状态并阻止重复操作。
- 页签支持键盘左右方向键、Home 和 End 切换，并同步 `aria-selected`，便于键盘和读屏用户定位当前区域。
“日志”页始终保留知、言、序、情、境、声、临、核八个可信成员，并动态发现其他官方系列提供方。动态提供方必须同时满足：已加载；`metadata.yaml` 的仓库是与插件 ID 完全对应的 `https://github.com/qsbb/<plugin_id>`；契约声明 `series_id=ningxin_suxi`、自身插件 ID、中文简称、内存存储、禁止传播到 AstrBot 日志，以及读取和清空能力。第三方仓库、仓库名不匹配、畸形或伪造系列声明不会进入聚合。自动发现只授予诊断读取权，不会把插件加入推荐、更新、启停或重载清单；各插件也不会为了诊断额外读取聊天消息。`astrbot_plugin_quest_avatar_bridge` 仅作为“临”的旧部署兼容别名，聚合输出与推荐链接统一使用正式 ID `astrbot_plugin_embodiment_bridge`。日志只存在内存中，清空、热重载或 AstrBot 重启后自动消失。

新增插件接入时无需修改“核”，只需公开以下稳定方法；旧成员原有简版声明在迁移期继续兼容：

```python
def diagnostic_log_contract():
    return {
        "name": "series.diagnostics",
        "version": "1.0",
        "series_id": "ningxin_suxi",
        "plugin_id": "astrbot_plugin_example",
        "plugin_name": "例",
        "capabilities": ("read_events", "clear_events"),
        "storage": "memory_only",
        "astrbot_log_propagation": False,
    }

def diagnostic_events(after_seq: int = 0, limit: int = 200) -> dict: ...
def diagnostic_clear() -> None: ...
```

“核”最多缓存动态成员发现结果 10 秒；插件安装或热重载后无需重载“核”，稍后刷新日志页即可出现。每个契约和读取调用仍有独立 1 秒超时，单个提供方异常不会拖住其他插件。

每条事件都可以点击展开，查看模块、函数、行号、异常类型和最长 2000 字符的脱敏日志正文。“核”在汇总时会再次脱敏；令牌、账号标识、邮箱、长数字和过长内容不会原样显示。搜索同时覆盖事件码、摘要和详情。

如果某个插件尚未安装、版本较旧或诊断接口暂不可用，页面会单独显示该插件状态；“临”的独立诊断日志关闭时显示“已关闭”，写入失败后显示“不可用”，不会拖住其他插件。热重载导致日志序号从头开始时，核会只重置该插件的页面游标并重新读取，不影响其他插件。

核会从 AstrBot 4.x 的 `StarMetadata.star_cls` 读取真实插件实例，并兼容旧包装字段；因此已加载且声明诊断契约的系列插件会显示“可读取”，不会因包装对象本身没有诊断方法而误报“未加载”。

核同时核对流标识和序号，清空或热重载时只重置对应插件的页面缓存；任一插件读取超过 1 秒只标记该插件超时。清空会让正在返回的旧请求失效，并在旧轮询结束后自动补一次全量刷新。

## 配置

配置项定义于 `_conf_schema.json`，关键项：

| 键 | 类型 | 默认 | 说明 |
|----|------|------|------|
| `enabled` | bool | true | 启用管理命令与调度服务 |
| `auto_update_enabled` | bool | false | 允许每日规则执行更新 |
| `network_timeout_seconds` | int | 15 | 候选查询总超时 |
| `cache_ttl_seconds` | int | 300 | 候选与条件请求缓存时长 |
| `version_check_concurrency` | int | 8 | 版本检查并发上限；默认允许八个可信仓库同时探测 |
| `github_mirror` | string | "" | GitHub 加速站前缀（留空直连；镜像失败自动回退直连，不会导致检查失败） |
| `github_mirror_candidates` | string | "" | 自定义加速站列表（换行或逗号分隔，必须 https，非法项忽略） |
| `mirror_benchmark_timeout_seconds` | float | 5.0 | 单个加速站测速超时；仅用于诊断，超时判为不可用 |
| `github_token` | string | "" | 可选 GitHub token（按秘密保存，仅显示是否已配置，不在页面、API 或审计中回显） |
| `health_stability_seconds` | float | 2.0 | 更新重载后的健康稳定观察窗口 |
| `backup_capacity_mb` | int | 2048 | 备份总容量上限，永不删除唯一恢复点 |

持久化数据存放在 AstrBot `data` 目录下，不写入插件目录。

## 测试

在 `astrbot/plugin/` 目录下运行：

```
python -m pytest astrbot_plugin_update_manager/tests -q
python -m ruff check astrbot_plugin_update_manager
node --check astrbot_plugin_update_manager/pages/manager/app.js
```

系列功能变更还应从 `astrbot/plugin/` 运行公共契约测试，确认包含境在内的钩子优先级和现有六份统一请求上下文没有漂移。

## 维护约定

任何可观察功能、配置项或安全边界的增删改，必须在同一批变更中同步 README、CHANGELOG 的
`Unreleased`、配置 schema 与回归测试。版本号在实现、文档和验证完成后由发布者确认。

## 许可证

[MIT](LICENSE)。作者：凌溪；英文版权署名：`qsbb`。
