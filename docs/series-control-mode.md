# 凝心溯溪系列统一接管模式设计

状态：设计稿，尚未实现

本文定义“核”独立 WebUI 直接统一管理凝心溯溪系列配置时的行为。目标是：打开核接管后，统一 WebUI 的覆盖配置生效；关闭核接管后，各插件立即恢复自身配置；核不读取插件私有字段，也不修改 AstrBot Core。

## 1. 目标与非目标

### 目标

- 由核独立 WebUI 统一展示和编辑已接入的系列插件配置。
- 支持全局接管开关和字段级“覆盖/继承”。
- 关闭接管后保持插件原有 Page、原生配置和运行行为不变。
- 配置写入由插件自身校验、持久化、热应用和回滚。
- 未接入、版本不兼容或运行异常时失败关闭，自动回退插件自身配置。
- 所有写操作有管理员权限、版本冲突保护和诊断记录。

### 非目标

- 不代理任意第三方插件。
- 不转发 AstrBot Dashboard JWT、Plugin Page Cookie 或插件私有 Web API。
- 不由核直接修改其他插件的配置文件。
- 不把所有插件改造成共享配置对象。
- 不修改 AstrBot Core。

## 2. 用户可见行为

核 WebUI 增加“系列接管”页面。页面顶部显示当前模式：

| 模式 | 行为 |
|---|---|
| `native`，插件自主管理 | 所有插件读取自己的配置；核保存的覆盖值不生效但保留 |
| `managed`，核统一接管 | 已接入插件按字段使用核覆盖值或插件自身值 |
| `managed_degraded`，接管降级 | 核仍开启，但某些插件/字段不可用；不可用项回退自身配置 |

每个插件和字段显示：

- 当前生效来源：`managed`、`plugin` 或 `default`；
- 核覆盖是否配置；
- 插件原生值是否配置；
- 当前值是否可用；
- 最近一次降级原因；
- 配置修订号和最后更新时间。

关闭接管只改变模式，不删除覆盖层。重新开启后，之前保存且仍通过校验的覆盖值可以继续生效。

插件自身 Page 在核接管时必须显示醒目标识：

> 此字段当前由“核”接管。修改本页的原生值不会改变当前生效值；关闭核接管后恢复生效。

未接入统一接口的插件继续使用自身 Page，不显示为可编辑的统一配置项。

## 3. 配置解析模型

统一解析顺序如下：

```text
mode=native
    -> 插件自身配置 -> 插件默认值

mode=managed 且字段 policy=override
    -> 核覆盖值 -> 插件自身配置 -> 插件默认值

mode=managed 且字段 policy=inherit
    -> 插件自身配置 -> 插件默认值

核或契约不可用
    -> 插件自身配置 -> 插件默认值
```

建议的核持久化结构：

```json
{
  "schema_version": 1,
  "mode": "native",
  "revision": 12,
  "members": {
    "astrbot_plugin_conversation_flow": {
      "policy": {
        "chunking_enabled": "inherit",
        "chunking_max_segments": "override"
      },
      "overrides": {
        "chunking_max_segments": 3
      },
      "revision": 4
    }
  }
}
```

约束：

- `mode` 只能是 `native` 或 `managed`；`managed_degraded` 是运行态，不持久化。
- `overrides` 只允许契约声明的字段，未知字段拒绝保存。
- `policy=inherit` 时可以保留历史覆盖值，但解析器不得使用它。
- 密钥、令牌、密码和原始账号标识不能进入核覆盖层的公开响应。
- 每次成功写入递增全局 `revision` 和插件局部 `revision`。
- 使用原子写入；写入失败时恢复旧快照和旧运行态。

## 4. 插件统一接口：`series.control@1.0`

每个自有插件通过实例方法声明能力。核只调用这些方法，不猜测私有字段和配置文件路径。

```python
def series_control_contract() -> dict[str, object]:
    return {
        "name": "series.control@1.0",
        "version": "1.0",
        "series_id": "ningxin_suxi",
        "plugin_id": "astrbot_plugin_example",
        "plugin_name": "例",
        "capabilities": (
            "read_schema",
            "read_snapshot",
            "validate_patch",
            "apply_patch",
            "reset_override",
        ),
        "read_only": False,
        "secrets_in_response": False,
        "max_patch_fields": 64,
    }

def series_control_schema() -> dict[str, object]: ...
def series_control_snapshot() -> dict[str, object]: ...
def validate_series_control_patch(
    patch: dict[str, object], *, expected_revision: int
) -> dict[str, object]: ...
def apply_series_control_patch(
    patch: dict[str, object], *, expected_revision: int
) -> dict[str, object]: ...
```

### 4.1 Schema 响应

字段必须显式标注：

```json
{
  "contract_name": "series.control@1.0",
  "contract_version": "1.0",
  "plugin_id": "astrbot_plugin_example",
  "revision": 4,
  "fields": {
    "chunking_enabled": {
      "type": "bool",
      "default": true,
      "control": "overrideable",
      "secret": false,
      "restart_required": false
    },
    "provider_key": {
      "type": "string",
      "control": "overrideable",
      "secret": true,
      "write_only": true
    }
  }
}
```

字段控制类型：

- `overrideable`：核可以覆盖；
- `read_only`：只能展示；
- `native_only`：始终由插件自身管理；
- `write_only`：只允许提交新值，不返回原值。

### 4.2 Snapshot 响应

```json
{
  "status": "ok",
  "revision": 4,
  "fields": {
    "chunking_enabled": {
      "native_configured": true,
      "managed_configured": false,
      "effective_source": "plugin",
      "effective_value": true
    },
    "provider_key": {
      "native_configured": true,
      "managed_configured": true,
      "effective_source": "managed",
      "effective_value": {"configured": true}
    }
  }
}
```

禁止返回：密钥原值、密码、JWT、Provider Key、Bridge Key、账号凭据、消息正文和插件内部路径。

### 4.3 写入语义

`validate_series_control_patch` 只做纯校验，不产生持久化和外部副作用；`apply_series_control_patch` 才执行提交。

提交必须满足：

1. `expected_revision` 与插件当前局部修订号一致，否则返回 `REVISION_CONFLICT`。
2. 所有字段通过 schema 类型、范围、枚举、长度和秘密字段校验。
3. 先写临时快照，再原子替换插件自己的覆盖存储。
4. 重新构建运行配置并做轻量健康检查。
5. 任何一步失败都恢复旧覆盖快照和旧运行态。
6. 返回新的 revision、字段来源和固定 reason code，不返回敏感值。

## 5. 核代理网关接口

独立 WebUI 只访问核自己的接口：

```text
GET   /api/series/control
POST  /api/series/control/mode
GET   /api/series/{plugin_id}/control/schema
GET   /api/series/{plugin_id}/control/snapshot
POST  /api/series/{plugin_id}/control/validate
POST  /api/series/{plugin_id}/control/apply
POST  /api/series/{plugin_id}/control/reset
GET   /api/series/{plugin_id}/control/diagnostics
```

所有接口都要求独立 WebUI 会话。写接口还需要角色：

| 操作 | viewer | admin | owner |
|---|---:|---:|---:|
| 查看模式、schema、snapshot | 是 | 是 | 是 |
| 修改普通覆盖字段 | 否 | 是 | 是 |
| 修改秘密字段 | 否 | 否 | 是 |
| 切换全局接管模式 | 否 | 否 | 是 |
| 重置插件覆盖 | 否 | 是 | 是 |
| 管理员和生命周期操作 | 否 | 否 | 是 |

核网关必须执行：

- 固定可信清单校验；
- `series_id`、`plugin_id` 和契约版本校验；
- 每个插件独立超时，建议 1 秒读取、3 秒校验、5 秒提交；
- 请求体字段白名单和最大长度限制；
- 不把 Dashboard Cookie/JWT 传给插件；
- 记录操作人角色、插件、字段名、结果、reason code、耗时和 revision，不记录值。

## 6. 生命周期与故障处理

### 启用接管

1. owner 在核 WebUI 确认启用。
2. 核读取可信成员契约并生成兼容报告。
3. 已接入成员进入 `managed`；未接入成员保持 `native`。
4. 核写入模式快照并通知已接入成员刷新运行配置。
5. 任一成员失败不回滚其他成员，页面显示逐项结果。

### 关闭接管

1. owner 确认关闭。
2. 核先把全局模式切为 `native`，再通知成员清除运行时覆盖。
3. 成员清理失败时仍不得继续使用核覆盖；记录 `NATIVE_MODE_RESTORE_PENDING`。
4. 插件自身配置立即成为有效来源。

### 热重载和重启

- 插件启动时先读取自身配置，再读取核覆盖快照。
- 核模式为 `native` 时不得应用覆盖值。
- 核不可用、快照损坏或契约不兼容时使用自身配置。
- 重启恢复以“最后一次原子提交的核快照”为准；正在提交的半成品不得被读取。

### 失败原因码

```text
CONTROL_DISABLED
CONTRACT_UNAVAILABLE
CONTRACT_VERSION_UNSUPPORTED
PLUGIN_NOT_LOADED
SCHEMA_INVALID
PATCH_INVALID
REVISION_CONFLICT
SECRET_WRITE_REJECTED
APPLY_TIMEOUT
APPLY_FAILED_ROLLED_BACK
NATIVE_MODE_RESTORE_PENDING
```

## 7. 与现有契约的关系

- `series.model_router@1.0` 保留，作为模型字段解析的专用契约；其来源增加 `managed`，但不改变现有插件 → 核 → AstrBot 的兼容回退语义。
- `series.diagnostics@1.0` 保留；统一接管操作写入核诊断事件，插件自身仍可提供业务诊断。
- `update_manager.series_runtime@1.0` 保留，只负责成员运行状态，不承担配置写入。
- 新增 `series.control@1.0` 后，旧插件没有该方法时一律按 `native` 处理。

## 8. 接入顺序

### 阶段一：核网关和只读能力

- 新增契约发现、schema/snapshot 聚合、角色校验和独立 WebUI 页面。
- 先接入知、言、声，验证字段来源显示和未接管回退。
- 不开放写入，先证明只读边界。

### 阶段二：普通字段写入

- 接入知、言、声的开关、数值、枚举字段。
- 增加 revision 冲突、原子保存、运行时恢复和失败回滚测试。

### 阶段三：序、情、境、临、枢

- 逐插件声明可接管字段。
- 身份、自然人、Quest、账号和权限相关字段默认 `native_only`。
- 临/Quest 只接入非秘密运行策略；Bridge Key、Provider Key、自然人值不得由核代理。

### 阶段四：秘密字段和生命周期动作

- 只由 owner 修改 write-only 字段。
- 对更新、回滚、启停继续复用核现有事务模块。
- 自定义动作必须列入契约能力白名单，不支持任意方法名调用。

## 9. 验收清单

- `native` 模式下，所有已接入插件行为与未接入前一致。
- `managed` 模式下，核覆盖字段生效，`inherit` 字段仍使用插件值。
- 关闭接管后无需重启即可恢复插件自身配置。
- 核 WebUI 重启后覆盖快照和模式正确恢复。
- 契约缺失、超时、版本不兼容、schema 错误均失败关闭。
- revision 冲突不会覆盖其他管理员的修改。
- 任何响应和日志不含密钥、JWT、Provider Key、Bridge Key、账号凭据或消息正文。
- 第三方插件不会因为仓库归属或同名字段进入统一接管页面。
- 每个插件的原生 Page 仍可用，并明确显示当前是否被核接管。
- 多插件批量应用出现部分失败时，页面能逐项显示结果，普通消息功能不被阻断。

## 10. 结论

“核”应成为统一配置的控制平面，而不是配置文件代理。核拥有模式、覆盖层、权限、审计和编排；插件拥有 schema、配置所有权、校验、持久化和运行时应用。两者通过 `series.control@1.0` 这个小接口连接，能够同时满足统一管理和关闭接管后完全恢复原生行为的要求。
