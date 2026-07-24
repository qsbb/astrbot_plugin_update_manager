# 更新日志

本项目遵循语义化版本（Semantic Versioning），版本号不带 `v` 前缀。

## 0.1.0

凝心溯溪系列更新模块（凝心溯溪-焕）首个发布版本。

### 变更
- 插件标识确立为 `astrbot_plugin_update_manager`，展示名 `凝心溯溪-焕`，内部标识、目录名、仓库名、`@register` 名称统一对齐。
- 新增 AstrBot Plugin Page 便捷设置页面，提供运行总览、常用配置修改与插件目录浏览。
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
