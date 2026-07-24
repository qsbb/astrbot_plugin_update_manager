# 凝心溯溪-焕（astrbot_plugin_update_manager）

凝心溯溪系列更新模块：安全、串行、可回滚的 AstrBot 插件更新管理器。发现可信来源候选，冻结不可变计划，通过 AstrBot 核心串行更新，并提供备份、健康检查、自动回滚、审计、持久化每日规则与清理能力。

## 特性

- 可信来源候选发现，条件请求与缓存，支持代理与可选 GitHub token。
- 冻结不可变计划（TTL 有效期内），避免执行与预览漂移。
- 经 AstrBot 核心串行更新，单事务加文件租约锁，杜绝并发。
- 更新前自动备份，更新后健康稳定观察窗口，失败自动回滚。
- 持久化每日规则、审计记录与备份清理策略（按数量、天数、容量）。
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

## 配置

配置项定义于 `_conf_schema.json`，关键项：

| 键 | 类型 | 默认 | 说明 |
|----|------|------|------|
| `enabled` | bool | true | 启用管理命令与调度服务 |
| `auto_update_enabled` | bool | false | 允许每日规则执行更新 |
| `network_timeout_seconds` | int | 15 | 候选查询总超时 |
| `cache_ttl_seconds` | int | 300 | 候选与条件请求缓存时长 |
| `github_token` | string | "" | 可选 GitHub token（按秘密保存，永不写入审计） |
| `health_stability_seconds` | float | 2.0 | 更新重载后的健康稳定观察窗口 |
| `backup_capacity_mb` | int | 2048 | 备份总容量上限，永不删除唯一恢复点 |

持久化数据存放在 AstrBot `data` 目录下，不写入插件目录。

## 测试

在 `astrbot/plugin/` 目录下运行：

```
python -m pytest astrbot_plugin_update_manager/tests -q
```

## 许可证

[MIT](LICENSE) © 2026 Justice-ocr
