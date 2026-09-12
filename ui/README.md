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

基础：页面背景、页面容器、Hero、页头、工具栏、卡片、指标、面板、分区。

导航：Tabs、分段控制、导航按钮、图标按钮。

操作：主按钮、普通按钮、危险按钮、幽灵链接、加载状态、禁用状态。

表单：文本、数字、搜索、选择、文本域、复选框、单选框、范围、开关、字段提示。

数据：表格、列表、状态胶囊、进度条、空状态、骨架、代码块、分页。

反馈：Toast、Modal、Popover、错误横幅、警告提示。

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
