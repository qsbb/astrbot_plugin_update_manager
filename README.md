# 凝心溯溪-核（astrbot_plugin_update_manager）

凝心溯溪系列更新模块：安全、串行、可回滚的 AstrBot 插件更新管理器。发现可信来源候选，冻结不可变计划，通过 AstrBot 核心串行更新，并提供备份、健康检查、自动回滚、审计、持久化每日规则与清理能力。

## 特性

- 可信来源候选发现，条件请求与缓存，支持代理与可选 GitHub token。
- 可选 GitHub 镜像加速：内置 gh-proxy 系加速站并支持自定义，版本探测与归档兜底走镜像优先、直连兜底，镜像挂掉不会导致检查失败。
- 冻结不可变计划（TTL 有效期内），避免执行与预览漂移。
- 经 AstrBot 核心串行更新，单事务加文件租约锁，杜绝并发。
- 更新前自动备份，更新后健康稳定观察窗口，失败自动回滚。
- 持久化每日规则、审计记录与备份清理策略（按数量、天数、容量）。
- 提供 AstrBot Plugin Page 便捷设置页面，可查看总览、修改常用配置、浏览插件目录并管理固定可信系列推荐。
- 固定可信系列清单仅包含 qsbb GitHub 仓库：知 `active_learner`、言 `conversation_flow`、序 `identity_guardian`、声 `voice_hub`、核 `update_manager`；核禁止自更新和自停用。
- Plugin Page API 采用运行时能力探测；旧版 AstrBot 不支持页面能力时自动降级，不影响命令与调度功能。
- `github_token` 等敏感配置按只写方式处理：只显示“是否已配置”，敏感 token 不回显到页面、接口响应或审计。
- `enabled=false` 时统一门禁全部命令与调度。

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
- **系列推荐**：查看知、言、序、声、核固定可信清单；按运行时能力显示“安装/已安装”“更新”“启用/停用”，操作完成后刷新推荐状态、总览和目录。
- **设置**：修改常用配置并即时应用；配置仍会持久化到 AstrBot `data` 目录。
- **镜像加速**：列出内置与自定义 GitHub 加速站，单选启用、一键并发测速查看毫秒延迟、添加或移除自定义站点，保存即热应用。
- **插件目录**：查看已安装插件、当前版本、来源与自动更新资格。

推荐操作通过 AstrBot 核心 `install_plugin`、`update_plugin`、`turn_on_plugin`、`turn_off_plugin` 执行，适配 AstrBot `4.16-4.x` 的签名差异并统一串行。请求仅接受固定清单中的插件 ID；核禁止自更新和自停用。仓库页面 URL 仅用于安装来源，绝不会误传为 `update_plugin.download_url`；只有已解析的归档 URL 才会传给该参数。

为兼容旧版 AstrBot，插件会在运行时探测 Plugin Page 注册接口。若当前 AstrBot 不提供该接口，插件仅跳过页面与管理 API 注册，原有 `/aup` 命令、更新事务和调度能力继续按运行时可用能力工作，无需额外配置。

`github_token` 是只写敏感项：页面和 API 仅返回是否已配置，敏感 token 不回显原值；保存空值或占位符不会清除现有 token。如需替换 token，请输入新值后保存。

## 配置

配置项定义于 `_conf_schema.json`，关键项：

| 键 | 类型 | 默认 | 说明 |
|----|------|------|------|
| `enabled` | bool | true | 启用管理命令与调度服务 |
| `auto_update_enabled` | bool | false | 允许每日规则执行更新 |
| `network_timeout_seconds` | int | 15 | 候选查询总超时 |
| `cache_ttl_seconds` | int | 300 | 候选与条件请求缓存时长 |
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

## 许可证

[MIT](LICENSE) © 2026 Justice-ocr
