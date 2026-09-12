# 凝心 UI 1.0（Glass Aurora）

这是凝心溯溪系列所有 Plugin Page 的唯一 UI 组件库。规范正本仍只在
`astrbot_plugin_update_manager/CONVENTIONS.md`；本目录是组件实现和设计约束，不是第二份开发规范。

## 使用方式

每个 Page 必须按以下顺序加载：

```html
<link rel="stylesheet" href="./style.css" />
<link rel="stylesheet" href="./series-ui.css" />
<script src="/api/plugin/page/bridge-sdk.js"></script>
<script src="./series-ui.js"></script>
<script type="module" src="./app.js"></script>
<body data-series-ui="1">
```

`series-ui.css` 提供全部基础控件和 Glass 视觉；`style.css` 只允许写页面专属布局和
业务组件，不再重复定义按钮、输入框、下拉框、卡片、表格、弹窗、Toast、状态胶囊等通用样式。
`series-ui.js` 暴露 `window.SeriesUI`：

- `SeriesUI.toast(message, type, duration)`
- `SeriesUI.confirm(options)`
- `SeriesUI.prompt(options)`
- `SeriesUI.modal(options)`
- `SeriesUI.copy(text)`
- `SeriesUI.setBusy(button, busy, label)`
- `SeriesUI.setTheme("glass" | "dark")`

## 组件清单

稳定类名（新增页面优先使用）：

- 容器：`.si-surface`、`.si-card`、`.si-empty`
- 导航：`.si-tabs`、`.si-tab`
- 操作：`.si-button`（可与 `.primary` / `.danger` 组合）
- 表单：`.si-input`、`.si-select`、`.si-textarea`
- 数据：`.si-table`、`.si-badge`
- 交互：必须通过 `window.SeriesUI.toast/confirm/prompt/modal/setBusy/copy`

兼容类名（旧页面迁移期）：`.card`、`.panel`、`.metric`、`.tabs`、`.tab-btn`、`.pill`、`.toast`、`.modal-card`。新页面不要继续扩散这些旧类名，优先使用 `.si-*`。

## 禁止事项

- 不在页面 CSS 中重新定义 `button`、`input`、`select`、`textarea`、`table`、`.card`、`.panel`、`.modal`、`.toast`、`.pill` 的通用视觉。
- 不新增一套颜色、圆角、阴影或字体；使用 `--si-*` token。
- 不在页面 JS 中实现第二套 Toast/Modal；使用 `window.SeriesUI`。
- 不直接修改 vendor 副本；只修改 `astrbot_plugin_update_manager/ui/`，然后运行同步器。

## 版本与同步

正本：

```text
astrbot_plugin_update_manager/ui/series-ui.css
astrbot_plugin_update_manager/ui/series-ui.js
```

同步到所有 Page：

```bash
python -m astrbot_plugin_update_manager.core.series_ui sync
```

只检查漂移：

```bash
python -m astrbot_plugin_update_manager.core.series_ui check
```

新增组件时，先在正本增加组件和预览状态，再同步到全部 Page。系列审计会拒绝缺失引用或哈希不一致。
