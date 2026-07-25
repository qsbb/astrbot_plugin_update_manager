# 更新日志

本项目遵循语义化版本（Semantic Versioning），版本号不带 `v` 前缀。

## 未发布

### 变更
- 版本检查改为有上限的并发执行：可信系列五个插件同时检查，`/aup plan`、`/aup dryrun` 与每日规则的候选解析同样并发，总耗时不再随插件数线性累加。
- `raw.githubusercontent.com` 版本探测使用独立短超时且不重试（实测该域单请求可达约 19 秒），超时立即回退 GitHub API，不再拖垮整批检查。
- 缓存仓库默认分支（含 API 查得的结果，有效期 24 小时）：已知默认分支时只探测该分支，省掉注定 404 的第二次 raw 请求。
- 单个插件版本检查新增墙钟上限，超时记为 `VERSION_CHECK_TIMEOUT` 并保留仓库上下文，其余插件照常返回版本，页面不再整体显示获取不到最新版。

### 配置
- 新增 `raw_timeout_seconds`（默认 `8.0`）：raw 域版本探测的独立超时。
- 新增 `version_check_concurrency`（默认 `5`）：版本检查并发上限，非法值回落到默认值。
- 新增 `version_check_timeout_seconds`（默认 `25`）：单个插件版本检查的墙钟上限，`0` 表示不额外限制。
- 三项均为新增字段并自带默认值，向后兼容，旧配置无需迁移。

## 0.1.0

凝心溯溪系列更新模块（凝心溯溪-核）首个发布版本。

### 变更
- 展示名统一为 `凝心溯溪-核`；稳定 ID `astrbot_plugin_update_manager`、目录、仓库与 `@register` 第一个参数保持不变。
- 新增知、言、序、声、核固定可信系列清单及推荐安装管理入口，按钮覆盖安装/已安装、更新、启用/停用并在操作后刷新状态。
- 适配 AstrBot `4.16-4.x` 的 `install_plugin`、`update_plugin`、`turn_on_plugin`、`turn_off_plugin`，所有变更操作统一串行并严格校验固定插件 ID。
- 禁止核自更新与自停用；修复 GitHub 仓库 URL 被误传为 `download_url`，仅真实归档 URL 可进入该参数。
- 新增 AstrBot Plugin Page 便捷设置页面，提供运行总览、系列推荐、常用配置修改与插件目录浏览。
- 补齐 `.astrbot-plugin/i18n/zh-CN.json` 的 `manager` 页面标题与描述元数据。
- Plugin Page API 采用能力探测；AstrBot 旧版本缺少页面注册接口时自动降级，不影响既有命令、事务与调度功能。
- `github_token` 按只写敏感配置处理，页面和 API 仅显示是否已配置，不回显原值；空值或占位符不会覆盖现有 token。
- `enabled=false` 时统一门禁全部 `/aup` 管理命令与每日调度，返回一致提示且不触碰事务边界。
- 补齐元数据契约：`metadata.yaml` 的 `name`、`version`、`author`、`repo` 与代码常量强一致，`repo` 不以 `.git` 结尾。
- 新增 README、LICENSE（MIT）、CHANGELOG 与 CI 工作流。

### 能力
- 可信来源候选发现、冻结不可变计划、经 AstrBot 核心串行更新。
- 更新前自动备份，更新后健康检查与失败自动回滚。
- 持久化每日规则、审计记录与备份清理策略。
