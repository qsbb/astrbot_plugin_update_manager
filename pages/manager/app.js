const messages = {
  "zh-CN": {
    title: "凝心溯溪-核 · 更新管理", heading: "凝心溯溪-核", subtitle: "安全、串行、可回滚的插件更新控制台",
    refresh: "刷新", controlCenter: "模块运营中心", overview: "总览", recommendations: "系列推荐", config: "配置", catalog: "目录", mirrors: "镜像加速", logs: "日志", loading: "加载中…", webuiAdminsTitle: "控制中心管理员", webuiAdminsHint: "管理员只能在这个已鉴权的 Page 中创建、修改和禁用；WebUI 不提供注册入口。", refreshAdmins: "刷新管理员", adminUsername: "用户名", adminPassword: "初始密码", adminRole: "角色", createAdmin: "创建管理员", adminCreated: "管理员已创建", adminUpdated: "管理员已更新", adminDisabled: "管理员已禁用", adminEnable: "启用", adminDisable: "禁用", adminResetPassword: "重置密码", adminNewPassword: "新密码", adminConfirmDisable: "确认禁用该管理员？",
    openWebUi: "打开独立 WebUI", copyWebUiLink: "复制链接", copiedWebUiLink: "WebUI 链接已复制", copyWebUiPrompt: "请复制独立 WebUI 地址", webuiActionsLabel: "独立 WebUI 操作", startupFailed: "页面启动失败", webuiAddressLoading: "独立 WebUI 地址加载中…", webuiAddressUnavailable: "独立 WebUI 地址不可用", webuiAddressRunning: "运行中", webuiAddressStopped: "未启动，点击按钮启动", webuiAddressDisabled: "已关闭，请在配置中启用", webuiAddressLabel: "地址", portLabel: "端口", eyebrow: "AstrBot 插件管理页", languageLabel: "语言", managerSectionsLabel: "管理页分区", diagnosticStatusLabel: "插件诊断状态",
    retry: "重试", sectionLoadFailed: "本区域加载失败", saving: "保存中…",
    capabilities: "运行时能力", configTitle: "配置读取与保存", tokenHint: "敏感 token 仅显示是否已配置，留空不会覆盖。",
    save: "保存", catalogTitle: "插件目录", catalogHint: "合并展示运行时插件与已安装元数据；未加载插件不可更新。",
    recommendationsTitle: "凝心溯溪系列推荐", recommendationsHint: "官方安装会直接加载；更新和启用由 AstrBot 内部热重载，页面不会额外重复重载。核禁止自更新和自停用。",
    checkLatest: "检查最新版本", checkingLatest: "正在检查…", autoCheckingLatest: "正在自动检查版本…", latestChecked: "版本检查完成", currentVersion: "当前", latestVersion: "最新", checkFailed: "检查失败",
    applyAll: "一键全部安装/更新", applyingAll: "正在全部安装/更新…", applyAllConfirm: "确定要安装或更新全部可用的推荐插件吗？", applyAllDone: "全部操作完成", applyAllPartial: "部分操作失败",
    updateAvailable: "有新版本", upToDate: "已是最新版", localNewer: "本地版本更新", notInstalled: "未安装", unknown: "未知",
    selfUpdateNotice: "更新管理器有新版本：当前 {current}，最新 {latest}。自身更新已禁用，请前往已安装插件页更新。", goToInstalledPlugins: "前往已安装插件页", installedPageUrlLabel: "更新页地址", installedPageUrlCopied: "宿主阻止自动跳转，更新页地址已复制", copyInstalledPageUrl: "请复制更新页地址后在浏览器中打开：",
    install: "安装", installed: "已安装", update: "更新", forceUpdate: "强制更新", enable: "启用", disable: "停用", operationDone: "操作完成", operationFailed: "操作失败", unavailableAction: "仅检测到新版本且运行时支持时可更新", forceUpdateUnavailable: "强制更新仅支持有新版本、已是最新版或本地版本更新的插件", catalogUnavailable: "此插件不可启停", errorUnknown: "请求失败，请稍后重试", error404: "远端未发布 Release 或标签", errorNetwork: "网络连接失败", errorTimeout: "请求超时", errorRateLimit: "GitHub 请求受限，请稍后重试", errorCode: "错误代码", errorHttpStatus: "HTTP 状态", errorRepository: "仓库", errorBranch: "分支",
    errorRetryAfter: "可重试时间", errorTokenHint: "可在配置中填写 GitHub Token 提升额度", rateLimitBanner: "GitHub 配额已用尽，{retry}后可再次检查。", rateLimitRemaining: "剩余配额",
    confirmTitle: "确认插件操作", confirmAction: "确认操作", cancel: "取消", confirmPrompt: "确定要{action}“{name}”吗？", forceUpdateConfirm: "确定要强制更新“{name}”吗？即使已是最新版或远端版本更旧，也会用远端版本覆盖本地代码。", installRunning: "正在安装…", updateRunning: "正在更新…", forceUpdateRunning: "正在强制更新…", enableRunning: "正在启用…", disableRunning: "正在停用…",
    enabled: "插件启用", automatic: "自动更新", busy: "执行状态", idle: "空闲", running: "执行中", nextRun: "下次运行",
    available: "可用", unavailable: "不可用", configured: "已配置", notConfigured: "未配置", writeOnly: "仅写入，不回显",
    eligible: "可规划", blocked: "已阻断", loaded: "已加载", notLoaded: "未加载", active: "已启用", inactive: "未启用",
    empty: "暂无插件", emptyDiagnostics: "目录诊断", saved: "配置已保存", loadFailed: "加载失败", saveFailed: "保存失败",
    checkUpdates: "检查更新", checkingUpdates: "正在检查更新…", updatesChecked: "更新检查完成", notChecked: "未检查", catalogUpdateHint: "点击「检查更新」后才会显示版本状态",
    mirrorsTitle: "GitHub 镜像加速", mirrorsHint: "加速站只做前缀代理；镜像不可用会自动回退直连，不会导致检查失败。", mirrorDirect: "直连 GitHub（不使用加速站）", mirrorBuiltin: "内置", mirrorCustom: "自定义",
    mirrorBenchmark: "一键测速", mirrorBenchmarking: "正在测速…", mirrorBenchmarkDone: "测速完成", mirrorLatency: "延迟", mirrorUnreachable: "不可用", mirrorUntested: "未测速",
    mirrorApply: "使用该加速站", mirrorApplied: "加速站已切换", mirrorAddTitle: "添加自定义加速站", mirrorAddPlaceholder: "https://your-mirror.example.com", mirrorAdd: "添加", mirrorAdded: "自定义加速站已添加", mirrorInvalid: "加速站必须是合法的 https 前缀", mirrorDuplicate: "该加速站已在列表中", mirrorRemove: "移除", mirrorRemoved: "自定义加速站已移除", mirrorProbeHint: "测速探针",
    ruleTitle: "每日自动更新", saveRule: "保存规则", ruleEnabled: "启用每日规则", autoUpdateGate: "允许自动更新总闸", autoUpdateGateHint: "关闭时任何每日规则都不会执行自动更新。", ruleTime: "运行时间", ruleTimezone: "时区", rulePolicy: "更新策略", failurePolicy: "失败策略", jitter: "抖动（分钟）", minimumAge: "最小发布年龄（小时）", prerelease: "允许预发行版本", selectPlugins: "选择插件", ruleSaved: "每日规则与总闸已保存", checkOnlyNote: "check_only 仅检查并记录，绝不会更新插件。", gateReady: "总闸已开启，启用规则后将注册每日任务。", gateClosed: "自动更新总闸已关闭。", pluginDisabled: "插件当前未启用，规则不会执行。", policyCheckOnly: "仅检查（check_only）", policyPatch: "仅补丁版本（patch）", policyMinor: "允许次版本（minor）", policyStable: "最新稳定版（stable）", failureRollbackContinue: "回滚后继续（rollback_continue）", failureRollbackStop: "回滚并停止（rollback_stop）",
    diagnosticTitle: "系列诊断日志", pauseLogs: "暂停", resumeLogs: "继续", refreshLogs: "刷新日志", clearLogs: "清空", pluginFilter: "插件", levelFilter: "级别", searchLogs: "搜索", searchLogsPlaceholder: "事件码、摘要或详情", allPlugins: "全部插件", allLevels: "全部级别", diagnosticReady: "可读取", diagnosticMissing: "未加载", diagnosticDisabled: "已关闭", diagnosticUnavailable: "不可用", diagnosticUnsupported: "暂不支持", diagnosticFailed: "读取失败", diagnosticCount: "显示 {shown} 条，共缓存 {total} 条", diagnosticPaused: "已暂停", diagnosticEmpty: "暂无符合条件的日志", diagnosticNoDetails: "暂无更多详细信息", clearDiagnosticsConfirm: "清空所有系列插件的内存诊断日志？", diagnosticsCleared: "诊断日志已清空", diagnosticGap: "部分较早日志已被环形缓冲覆盖"
  },
  "en-US": {
    title: "Update Manager", heading: "Update Manager", subtitle: "Safe, serial and rollback-ready plugin updates",
    refresh: "Refresh", controlCenter: "Module operations", overview: "Overview", recommendations: "Recommendations", config: "Configuration", catalog: "Catalog", mirrors: "Mirror acceleration", logs: "Logs", loading: "Loading…", webuiAdminsTitle: "Control center administrators", webuiAdminsHint: "Administrators are created, changed, and disabled only from this authenticated Page. The WebUI has no registration screen.", refreshAdmins: "Refresh administrators", adminUsername: "Username", adminPassword: "Initial password", adminRole: "Role", createAdmin: "Create administrator", adminCreated: "Administrator created", adminUpdated: "Administrator updated", adminDisabled: "Administrator disabled", adminEnable: "Enable", adminDisable: "Disable", adminResetPassword: "Reset password", adminNewPassword: "New password", adminConfirmDisable: "Disable this administrator?",
    openWebUi: "Open standalone WebUI", copyWebUiLink: "Copy link", copiedWebUiLink: "WebUI link copied", copyWebUiPrompt: "Copy the standalone WebUI address", webuiActionsLabel: "Standalone WebUI actions", startupFailed: "Page startup failed", webuiAddressLoading: "Loading standalone WebUI address…", webuiAddressUnavailable: "Standalone WebUI address unavailable", webuiAddressRunning: "Running", webuiAddressStopped: "Stopped; click the button to start", webuiAddressDisabled: "Disabled; enable it in configuration", webuiAddressLabel: "Address", portLabel: "Port", eyebrow: "AstrBot plugin management", languageLabel: "Language", managerSectionsLabel: "Manager sections", diagnosticStatusLabel: "Plugin diagnostic status",
    retry: "Retry", sectionLoadFailed: "This section failed to load", saving: "Saving…",
    capabilities: "Runtime capabilities", configTitle: "Read and save configuration", tokenHint: "Sensitive tokens are write-only. Empty values keep the current secret.",
    save: "Save", catalogTitle: "Plugin catalog", catalogHint: "Runtime plugins and installed metadata are always merged; unloaded plugins cannot be updated.",
    recommendationsTitle: "Ningxin Suxi series", recommendationsHint: "Official installation loads directly. Update and enable use AstrBot's internal hot reload; this page never triggers a duplicate reload. Core cannot update or disable itself.",
    checkLatest: "Check latest versions", checkingLatest: "Checking…", autoCheckingLatest: "Checking versions automatically…", latestChecked: "Version check completed", currentVersion: "Current", latestVersion: "Latest", checkFailed: "Check failed",
    applyAll: "Install/update all", applyingAll: "Installing/updating all…", applyAllConfirm: "Install or update all available recommended plugins?", applyAllDone: "All operations completed", applyAllPartial: "Some operations failed",
    updateAvailable: "New version available", upToDate: "Up to date", localNewer: "Local version is newer", notInstalled: "Not installed", unknown: "Unknown",
    selfUpdateNotice: "A newer update manager is available: current {current}, latest {latest}. Self-update is disabled; update it from the installed plugins page.", goToInstalledPlugins: "Open installed plugins", installedPageUrlLabel: "Update page URL", installedPageUrlCopied: "The host blocked automatic navigation. The update page URL was copied.", copyInstalledPageUrl: "Copy this update page URL and open it in a browser:",
    install: "Install", installed: "Installed", update: "Update", forceUpdate: "Force update", enable: "Enable", disable: "Disable", operationDone: "Operation completed", operationFailed: "Operation failed", unavailableAction: "Update is enabled only when a newer version is detected and supported", forceUpdateUnavailable: "Force update requires an available, up-to-date, or locally newer version state", catalogUnavailable: "This plugin cannot be toggled", errorUnknown: "Request failed; try again later", error404: "No release or tag was found", errorNetwork: "Network connection failed", errorTimeout: "Request timed out", errorRateLimit: "GitHub request limit reached; try again later", errorCode: "Error code", errorHttpStatus: "HTTP status", errorRepository: "Repository", errorBranch: "Branch",
    errorRetryAfter: "Retry after", errorTokenHint: "Set a GitHub Token in configuration to raise the quota", rateLimitBanner: "The GitHub quota is exhausted; you can check again in {retry}.", rateLimitRemaining: "Remaining quota",
    confirmTitle: "Confirm plugin action", confirmAction: "Confirm", cancel: "Cancel", confirmPrompt: "Are you sure you want to {action} “{name}”?", forceUpdateConfirm: "Force update “{name}”? The remote version will overwrite local code even when it is the same version or older.", installRunning: "Installing…", updateRunning: "Updating…", forceUpdateRunning: "Force updating…", enableRunning: "Enabling…", disableRunning: "Disabling…",
    enabled: "Plugin enabled", automatic: "Automatic updates", busy: "Execution", idle: "Idle", running: "Running", nextRun: "Next run",
    available: "Available", unavailable: "Unavailable", configured: "Configured", notConfigured: "Not configured", writeOnly: "Write-only; never returned",
    eligible: "Eligible", blocked: "Blocked", loaded: "Loaded", notLoaded: "Not loaded", active: "Active", inactive: "Inactive",
    empty: "No plugins", emptyDiagnostics: "Catalog diagnostics", saved: "Configuration saved", loadFailed: "Load failed", saveFailed: "Save failed",
    checkUpdates: "Check for updates", checkingUpdates: "Checking for updates…", updatesChecked: "Update check completed", notChecked: "Not checked", catalogUpdateHint: "Version status appears after you run a check",
    mirrorsTitle: "GitHub mirror acceleration", mirrorsHint: "Mirrors only proxy by prefix. An unavailable mirror falls back to a direct connection and never fails the check.", mirrorDirect: "Direct GitHub connection (no mirror)", mirrorBuiltin: "Built-in", mirrorCustom: "Custom",
    mirrorBenchmark: "Run benchmark", mirrorBenchmarking: "Benchmarking…", mirrorBenchmarkDone: "Benchmark completed", mirrorLatency: "Latency", mirrorUnreachable: "Unavailable", mirrorUntested: "Not tested",
    mirrorApply: "Use this mirror", mirrorApplied: "Mirror switched", mirrorAddTitle: "Add a custom mirror", mirrorAddPlaceholder: "https://your-mirror.example.com", mirrorAdd: "Add", mirrorAdded: "Custom mirror added", mirrorInvalid: "A mirror must be a valid https prefix", mirrorDuplicate: "This mirror is already listed", mirrorRemove: "Remove", mirrorRemoved: "Custom mirror removed", mirrorProbeHint: "Benchmark probe",
    ruleTitle: "Daily automatic updates", saveRule: "Save rule", ruleEnabled: "Enable daily rule", autoUpdateGate: "Allow automatic updates — master switch", autoUpdateGateHint: "When off, no daily rule can perform automatic updates.", ruleTime: "Run time", ruleTimezone: "Timezone", rulePolicy: "Update policy", failurePolicy: "Failure policy", jitter: "Jitter (minutes)", minimumAge: "Minimum release age (hours)", prerelease: "Allow prereleases", selectPlugins: "Select plugins", ruleSaved: "Daily rule and master switch saved", checkOnlyNote: "check_only checks and records only; it never updates plugins.", gateReady: "The automatic-update master switch is on; enabling the rule registers the daily job.", gateClosed: "The automatic-update master switch is off.", pluginDisabled: "The plugin is disabled, so the rule will not run.", policyCheckOnly: "Check only (check_only)", policyPatch: "Patch releases only (patch)", policyMinor: "Allow minor releases (minor)", policyStable: "Latest stable release (stable)", failureRollbackContinue: "Roll back and continue (rollback_continue)", failureRollbackStop: "Roll back and stop (rollback_stop)",
    diagnosticTitle: "Series diagnostic logs", pauseLogs: "Pause", resumeLogs: "Resume", refreshLogs: "Refresh logs", clearLogs: "Clear", pluginFilter: "Plugin", levelFilter: "Level", searchLogs: "Search", searchLogsPlaceholder: "Event code, summary, or details", allPlugins: "All plugins", allLevels: "All levels", diagnosticReady: "Ready", diagnosticMissing: "Not loaded", diagnosticDisabled: "Disabled", diagnosticUnavailable: "Unavailable", diagnosticUnsupported: "Unsupported", diagnosticFailed: "Read failed", diagnosticCount: "Showing {shown} of {total} cached events", diagnosticPaused: "Paused", diagnosticEmpty: "No matching events", diagnosticNoDetails: "No additional details", clearDiagnosticsConfirm: "Clear all in-memory series diagnostic logs?", diagnosticsCleared: "Diagnostic logs cleared", diagnosticGap: "Some older events were overwritten by the ring buffer"
  }
};

let bridge = null;

function readStoredLocale() {
  try {
    return window.localStorage.getItem("update-manager-locale");
  } catch (error) {
    console.warn("Unable to read update manager locale from localStorage", error);
    return null;
  }
}

function storeLocale(locale) {
  try {
    window.localStorage.setItem("update-manager-locale", locale);
  } catch (error) {
    console.warn("Unable to save update manager locale to localStorage", error);
  }
}

const storedLocale = readStoredLocale();
const state = {
  locale: Object.prototype.hasOwnProperty.call(messages, storedLocale) ? storedLocale : "zh-CN",
  config: null,
  rule: null,
  mirrors: null,
  // 测速结果按加速站 URL 缓存，切换语言或重载列表都不用重新测速。
  mirrorLatency: {},
  mirrorBusy: false,
  recommendationBusy: null,
  // 版本检查互斥：自动检查与手动检查共享同一把锁，避免并发请求触发限流。
  versionCheckBusy: false,
  // 每次会话只自动检查一次；刷新页面才会重新自动检查。
  autoVersionCheckDone: false,
  // 目录版本结果按 plugin_id 缓存。目录不做自动检查（全量插件探测会拖慢首屏并
  // 快速耗尽 GitHub 匿名配额），所以刷新目录列表时必须保留已有结果，否则用户
  // 点过的检查会因为一次启停操作而白跑。
  catalogVersions: {},
  catalogCheckBusy: false,
  catalogBusy: null,
  catalogItems: [],
  catalogDiagnostics: [],
  diagnosticEvents: [],
  diagnosticMembers: [],
  diagnosticCursors: {},
  diagnosticStreams: {},
  diagnosticLoaded: false,
  diagnosticBusy: false,
  diagnosticGeneration: 0,
  diagnosticRefreshPending: false,
  diagnosticPaused: false,
  diagnosticExpanded: new Set(),
  diagnosticTimer: null,
  diagnosticSearchTimer: null
};
const t = (key) => messages[state.locale][key] || key;

async function resolveBridge(timeout = 3000) {
  if (window.AstrBotPluginPage) return window.AstrBotPluginPage;
  if (typeof window.waitForAstrBotBridge === "function") return window.waitForAstrBotBridge(timeout);
  const started = Date.now();
  while (Date.now() - started < timeout) {
    await new Promise((resolve) => setTimeout(resolve, 50));
    if (window.AstrBotPluginPage) return window.AstrBotPluginPage;
  }
  throw new Error("请在 AstrBot 插件管理页中打开 / Open from AstrBot plugin manager");
}

async function apiGet(name) {
  if (!bridge) throw new Error("Bridge is not initialized");
  return parseJsonResponse(await bridge.apiGet(name));
}

async function apiPost(name, payload) {
  if (!bridge) throw new Error("Bridge is not initialized");
  return parseJsonResponse(await bridge.apiPost(name, payload));
}

function errorReason(code) {
  const value = String(code || "");
  if (value === "REGISTRY_HTTP_404" || value === "GITHUB_TAG_SCHEMA_INVALID") return t("error404");
  if (value === "REGISTRY_TIMEOUT" || value === "VERSION_CHECK_TIMEOUT") return t("errorTimeout");
  if (value === "REGISTRY_NETWORK_ERROR") return t("errorNetwork");
  if (["REGISTRY_RATE_LIMITED", "REGISTRY_HTTP_403", "REGISTRY_HTTP_429"].includes(value)) return t("errorRateLimit");
  const known = {
    CONFIRMATION_REQUIRED: "停用前必须明确确认",
    SELF_LIFECYCLE_BLOCKED: "更新管理器不能操作自身启停",
    RESERVED_PLUGIN: "AstrBot 保留插件不可操作",
    PLUGIN_NOT_LOADED: "插件尚未加载",
    PLUGIN_NOT_FOUND: "未找到该插件",
    PLUGIN_STATE_UNCHANGED: "插件已经处于目标状态",
    LIFECYCLE_CAPABILITY_UNAVAILABLE: "当前 AstrBot 不支持此启停操作",
    ACTIVATION_RESULT_MISMATCH: "操作后插件状态校验失败",
    SELF_UPDATE_BLOCKED: "更新管理器不能更新自身",
    SOURCE_REQUIRED: "无法识别 GitHub 来源，不能更新",
    NO_UPDATE_AVAILABLE: "当前已是最新版本",
    UPDATE_CAPABILITY_UNAVAILABLE: "当前 AstrBot 不支持插件更新"
  };
  return known[value] || (state.locale === "zh-CN" ? t("errorUnknown") : value || t("errorUnknown"));
}

function parseJsonResponse(value) {
  const data = typeof value === "string" ? JSON.parse(value) : value;
  if (data?.success === false) throw new Error(errorReason(data.error || data.detail));
  return data;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[char]);
}

// 移动端 Plugin Page 常嵌在受限 iframe 中。宿主 bridge 能明确接管导航时才算成功；
// 不再用 iframe 自身的 location/hash 兜底，以免页面看似成功但用户仍停在原处。
async function invokeBridgeNavigation(method, target) {
  if (!bridge || typeof bridge[method] !== "function") return false;
  try {
    const result = await bridge[method](target);
    return result !== false;
  } catch (error) {
    console.warn(`Bridge ${method} failed`, error);
    return false;
  }
}

function internalRouteUrl(route) {
  const target = String(route || "").trim();
  if (!target || !target.startsWith("/") || target.startsWith("//")) return "";
  return new URL(`/#${target}`, window.location.origin).href;
}

async function openInternalRoute(route) {
  const target = String(route || "").trim();
  const targetUrl = internalRouteUrl(target);
  if (!targetUrl) return false;
  if (await invokeBridgeNavigation("navigate", target)) return true;

  // bridge 已提供但调用失败时，尝试直接驱动顶层 Dashboard；受限 sandbox 会抛错。
  try {
    const topWindow = window.top || window;
    if (topWindow.location && typeof topWindow.location.assign === "function") {
      topWindow.location.assign(targetUrl);
      return true;
    }
  } catch (error) {
    console.warn("Top-level Dashboard navigation blocked", error);
  }

  // 兼容允许弹出窗口但不允许直接改写顶层 location 的旧版宿主。
  try {
    const opened = window.open(targetUrl, "_top");
    return Boolean(opened);
  } catch (error) {
    console.warn("Top-level Dashboard navigation blocked", error);
    return false;
  }
}

async function openExternalUrl(url) {
  const href = String(url || "").trim();
  if (!href || href === "#" || href.toLowerCase().startsWith("javascript:")) return false;
  if (await invokeBridgeNavigation("openExternal", href)) return true;
  try {
    const opened = window.open(href, "_blank", "noopener,noreferrer");
    if (!opened) return false;
    try {
      opened.opener = null;
    } catch (error) {
      console.warn("Unable to clear opener for external link", error);
    }
    return true;
  } catch (error) {
    console.warn("window.open blocked for external link", error);
    return false;
  }
}

function revealInstalledPageUrl(link, url) {
  const notice = link.closest(".self-update-notice");
  if (!notice) return;
  let fallback = notice.querySelector(".installed-page-url-fallback");
  if (!fallback) {
    fallback = document.createElement("p");
    fallback.className = "installed-page-url-fallback";
    notice.append(fallback);
  }
  fallback.textContent = `${t("installedPageUrlLabel")}：${url}`;
}

async function copyInstalledPageUrl(link, url) {
  revealInstalledPageUrl(link, url);
  try {
    if (!navigator.clipboard || typeof navigator.clipboard.writeText !== "function") throw new Error("Clipboard API unavailable");
    await navigator.clipboard.writeText(url);
    toast(t("installedPageUrlCopied"));
  } catch (error) {
    console.warn("Unable to copy installed plugins page URL", error);
    window.prompt(t("copyInstalledPageUrl"), url);
  }
}

async function openSelfUpdateTarget(link, route) {
  if (await openInternalRoute(route)) return true;
  await copyInstalledPageUrl(link, internalRouteUrl(route));
  return false;
}

function toast(message, error = false) {
  const node = document.getElementById("toast");
  node.textContent = message;
  node.classList.toggle("error", error);
  node.classList.add("visible");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => node.classList.remove("visible"), 2600);
}

function applyI18n() {
  document.documentElement.lang = state.locale;
  document.title = t("title");
  document.querySelectorAll("[data-i18n]").forEach((node) => { node.textContent = t(node.dataset.i18n); });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((node) => { node.setAttribute("aria-label", t(node.dataset.i18nAriaLabel)); });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => { node.placeholder = t(node.dataset.i18nPlaceholder); });
  document.getElementById("locale").value = state.locale;
}

async function loadOverview() {
  const data = await apiGet("overview");
  const plugin = data.plugin || {};
  const rule = data.rule || {};
  document.getElementById("summary").innerHTML = [
    [t("enabled"), plugin.enabled ? t("available") : t("unavailable")],
    [t("automatic"), plugin.auto_update_enabled ? t("available") : t("unavailable")],
    [t("busy"), plugin.busy ? t("running") : t("idle")],
    [t("nextRun"), rule.next_run || "—"]
  ].map(([label, value]) => `<article class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></article>`).join("");
  document.getElementById("capabilities").innerHTML = (data.runtime?.capabilities || []).map((item) => {
    const label = item.label?.[state.locale] || item.code;
    const comment = item.comment?.[state.locale] || "";
    return `<div><span class="capability-copy"><strong>${escapeHtml(label)}</strong><code>${escapeHtml(item.code)}</code><small>${escapeHtml(comment)}</small></span><span class="pill ${item.available ? "ok" : "off"}">${item.available ? t("available") : t("unavailable")}</span></div>`;
  }).join("");
}

function makeField(key, field, value) {
  const label = escapeHtml(field.description || key);
  if (field.write_only) {
    const configured = Boolean(value?.configured);
    return `<label><span>${label}</span><input name="${key}" type="password" autocomplete="new-password" placeholder="${configured ? t("configured") : t("notConfigured")}" /><small>${t("writeOnly")}</small></label>`;
  }
  if (field.type === "bool") return `<label class="switch"><input name="${key}" type="checkbox" ${value ? "checked" : ""}/><span>${label}</span></label>`;
  if (field.type === "model_routing") {
    const routes = value && typeof value === "object" ? value : {};
    const kinds = Object.entries(field.kinds || {});
    return `<fieldset class="model-routing-field"><legend>${label}</legend><p class="field-hint">插件显式配置优先，其次使用核，最后回退 AstrBot 原生配置。</p>${kinds.map(([kind, kindLabel]) => { const route = routes[kind] || {}; return `<div class="model-route-row"><strong>${escapeHtml(kindLabel)}</strong><input data-model-kind="${escapeHtml(kind)}" data-model-field="provider_id" placeholder="Provider ID" value="${escapeHtml(route.provider_id || "")}"/><input data-model-kind="${escapeHtml(kind)}" data-model-field="model" placeholder="模型名" value="${escapeHtml(route.model || "")}"/><input data-model-kind="${escapeHtml(kind)}" data-model-field="voice" placeholder="音色（可选）" value="${escapeHtml(route.voice || "")}"/></div>`; }).join("")}</fieldset>`;
  }
  if (field.options) return `<label><span>${label}</span><select name="${key}">${field.options.map((option) => `<option ${option === value ? "selected" : ""}>${escapeHtml(option)}</option>`).join("")}</select></label>`;
  const type = field.type === "int" || field.type === "float" ? "number" : "text";
  const step = field.type === "float" ? "any" : "1";
  const disabled = ["data_dir", "plugin_root"].includes(key) ? "disabled" : "";
  return `<label><span>${label}</span><input name="${key}" type="${type}" step="${step}" value="${escapeHtml(value)}" ${disabled}/></label>`;
}

async function loadConfig() {
  const data = await apiGet("config");
  state.config = data;
  document.getElementById("config-fields").innerHTML = Object.entries(data.schema || {}).map(([key, field]) => makeField(key, field, data.config?.[key])).join("");
  await loadWebUiAddress();
  try { await loadWebUiAdmins(); } catch (error) { renderSectionLoadError("config", error); }
}

function renderWebUiAddress(data) {
  const node = document.getElementById("webui-address");
  if (!node) return;
  if (!data?.url) {
    node.textContent = t("webuiAddressUnavailable");
    return;
  }
  const stateText = data.ready
    ? t("webuiAddressRunning")
    : data.configured_enabled === false
      ? t("webuiAddressDisabled")
      : t("webuiAddressStopped");
  node.textContent = `${t("webuiAddressLabel")}: ${data.url} · ${t("portLabel")}: ${data.port} · ${stateText}`;
  node.title = data.url;
}

async function loadWebUiAddress() {
  try {
    renderWebUiAddress(await apiGet("webui/url"));
  } catch (error) {
    renderWebUiAddress(null);
    console.warn("Unable to read standalone WebUI address", error);
  }
}

async function openStandaloneWebUi() {
  // Reserve the popup synchronously while the click still counts as a user gesture.
  const popup = window.open("about:blank", "_blank");
  try {
    let data = await apiGet("webui/url");
    if (!data.enabled || !data.ready || !data.url) data = await apiPost("webui/start", {});
    if (!data.enabled || !data.ready || !data.url) throw new Error("独立 WebUI 启动后仍不可用");
    renderWebUiAddress(data);
    if (popup && !popup.closed) {
      try { popup.opener = null; } catch (_) { /* Optional hardening. */ }
      popup.location.replace(data.url);
    } else {
      if (!await openExternalUrl(data.url)) window.prompt("请复制独立 WebUI 地址", data.url);
    }
  } catch (error) {
    if (popup && !popup.closed) popup.close();
    toast(`${t("operationFailed")}: ${error.message}`, true);
  }
}

async function copyStandaloneWebUiLink() {
  let data;
  try {
    data = await apiGet("webui/url");
    if (!data.enabled || !data.ready || !data.url) data = await apiPost("webui/start", {});
    if (!data.enabled || !data.ready || !data.url) throw new Error("独立 WebUI 启动后仍不可用");
    renderWebUiAddress(data);
    if (!navigator.clipboard || typeof navigator.clipboard.writeText !== "function") throw new Error("Clipboard API unavailable");
    await navigator.clipboard.writeText(data.url);
    toast(t("copiedWebUiLink"));
  } catch (error) {
    if (data?.url) {
      renderWebUiAddress(data);
      window.prompt(t("copyWebUiPrompt"), data.url);
      return;
    }
    toast(`${t("operationFailed")}: ${error.message}`, true);
  }
}

function renderWebUiAdmins(admins) {
  const node = document.getElementById("webui-admin-list");
  if (!node) return;
  if (!admins.length) {
    node.innerHTML = `<p>${escapeHtml(t("notConfigured"))}</p>`;
    return;
  }
  node.innerHTML = admins.map((admin) => {
    const action = admin.enabled ? "adminDisable" : "adminEnable";
    const label = admin.enabled ? t("adminDisable") : t("adminEnable");
    return `<div class="admin-row"><strong>${escapeHtml(admin.username)}</strong><span>${escapeHtml(admin.role)}</span><small>${admin.enabled ? escapeHtml(t("active")) : escapeHtml(t("inactive"))}</small><div class="admin-actions"><button type="button" data-admin-action="password" data-admin-id="${escapeHtml(admin.id)}">${escapeHtml(t("adminResetPassword"))}</button><button type="button" data-admin-action="${action === "adminDisable" ? "disable" : "enable"}" data-admin-id="${escapeHtml(admin.id)}">${escapeHtml(label)}</button></div></div>`;
  }).join("");
}

async function loadWebUiAdmins() {
  const data = await apiGet("webui/admins");
  renderWebUiAdmins(data.admins || []);
}

async function createWebUiAdmin(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const username = document.getElementById("webui-admin-username").value;
  const password = document.getElementById("webui-admin-password").value;
  const role = document.getElementById("webui-admin-role").value;
  const button = form.querySelector("button[type=submit]");
  button.disabled = true;
  try {
    await apiPost("webui/admins/create", { username, password, role });
    form.reset();
    toast(t("adminCreated"));
    await loadWebUiAdmins();
  } catch (error) { toast(`${t("operationFailed")}: ${error.message}`, true); }
  finally { button.disabled = false; }
}

async function updateWebUiAdmin(adminId, action) {
  if (action === "password") {
    const password = window.prompt(t("adminNewPassword"));
    if (password === null) return;
    await apiPost("webui/admins/update", { admin_id: adminId, password });
    toast(t("adminUpdated"));
  } else {
    if (action === "disable" && !window.confirm(t("adminConfirmDisable"))) return;
    await apiPost("webui/admins/update", { admin_id: adminId, enabled: action === "enable" });
    toast(action === "enable" ? t("adminEnable") : t("adminDisabled"));
  }
  await loadWebUiAdmins();
}

async function loadRule() {
  const data = await apiGet("rule");
  state.rule = data;
  const rule = data.rule || {};
  document.getElementById("rule-auto-update-enabled").checked = Boolean(data.global?.auto_update_enabled);
  document.getElementById("rule-enabled").checked = Boolean(rule.enabled);
  document.getElementById("rule-time").value = rule.local_time || "04:30";
  document.getElementById("rule-timezone").value = rule.timezone || "Asia/Shanghai";
  document.getElementById("rule-policy").value = rule.policy || "check_only";
  document.getElementById("rule-failure").value = rule.on_failure || "rollback_continue";
  document.getElementById("rule-jitter").value = rule.jitter_minutes ?? 10;
  document.getElementById("rule-minimum-age").value = rule.minimum_release_age_hours ?? 24;
  document.getElementById("rule-prerelease").checked = Boolean(rule.prerelease);
  document.getElementById("rule-next-run").textContent = data.next_run || "—";
  document.getElementById("rule-gate-hint").textContent = !data.global?.enabled
    ? t("pluginDisabled")
    : data.global?.auto_update_enabled ? t("gateReady") : t("gateClosed");
  document.getElementById("check-only-note").hidden = rule.policy !== "check_only";
  const selected = new Set(rule.plugin_ids || []);
  document.getElementById("rule-plugins").innerHTML = (data.catalog || []).map((item) => `<label class="plugin-option"><input type="checkbox" value="${escapeHtml(item.plugin_id)}" ${selected.has(item.plugin_id) ? "checked" : ""}/><span><strong>${escapeHtml(item.display_name || item.plugin_id)}</strong><code>${escapeHtml(item.plugin_id)}</code></span></label>`).join("") || `<span>${escapeHtml(t("empty"))}</span>`;
}

function setFormBusy(form, busy) {
  const button = form.querySelector('button[type="submit"]');
  if (!button) return;
  button.disabled = busy;
  button.setAttribute("aria-busy", busy ? "true" : "false");
  button.textContent = busy ? t("saving") : t(button.dataset.i18n);
}

async function saveRule(event) {
  event.preventDefault();
  const form = event.currentTarget;
  setFormBusy(form, true);
  const autoUpdateEnabled = document.getElementById("rule-auto-update-enabled").checked;
  const pluginIds = [...document.querySelectorAll("#rule-plugins input:checked")].map((input) => input.value);
  const payload = {
    expected_revision: state.rule?.rule?.revision,
    enabled: document.getElementById("rule-enabled").checked,
    plugin_ids: pluginIds,
    local_time: document.getElementById("rule-time").value,
    timezone: document.getElementById("rule-timezone").value,
    policy: document.getElementById("rule-policy").value,
    on_failure: document.getElementById("rule-failure").value,
    jitter_minutes: Number.parseInt(document.getElementById("rule-jitter").value, 10),
    minimum_release_age_hours: Number.parseInt(document.getElementById("rule-minimum-age").value, 10),
    prerelease: document.getElementById("rule-prerelease").checked
  };
  try {
    if (!autoUpdateEnabled) {
      await apiPost("config", { auto_update_enabled: false });
      await apiPost("rule", payload);
    } else {
      await apiPost("rule", payload);
      await apiPost("config", { auto_update_enabled: true });
    }
    toast(t("ruleSaved"));
  } catch (error) {
    try {
      await apiPost("config", { auto_update_enabled: false });
    } catch (safetyError) {
      console.error("Failed to close automatic-update master switch", safetyError);
    }
    toast(`${t("saveFailed")}: ${error.message}`, true);
  } finally {
    await Promise.allSettled([loadConfig(), loadRule(), loadOverview()]);
    setFormBusy(form, false);
  }
}

async function saveConfig(event) {
  event.preventDefault();
  const form = event.currentTarget;
  setFormBusy(form, true);
  const payload = {};
  for (const [key, field] of Object.entries(state.config?.schema || {})) {
    const input = event.currentTarget.elements.namedItem(key);
    if (field.type === "model_routing") {
      const routes = {};
      form.querySelectorAll(`[data-model-kind][data-model-field]`).forEach((node) => { const kind = node.dataset.modelKind; const fieldName = node.dataset.modelField; const text = String(node.value || "").trim(); if (text) (routes[kind] ||= {})[fieldName] = text; });
      payload[key] = routes;
      continue;
    }
    if (!input || input.disabled) continue;
    if (field.write_only && !input.value) continue;
    if (field.type === "bool") payload[key] = input.checked;
    else if (field.type === "int") payload[key] = Number.parseInt(input.value, 10);
    else if (field.type === "float") payload[key] = Number.parseFloat(input.value);
    else payload[key] = input.value;
  }
  try {
    await apiPost("config", payload);
    toast(t("saved"));
    await Promise.allSettled([loadConfig(), loadOverview()]);
  } catch (error) { toast(`${t("saveFailed")}: ${error.message}`, true); }
  finally {
    setFormBusy(form, false);
  }
}

function isValidMirror(value) {
  // 与后端 normalize_mirror 保持同一条底线：必须 https、必须有主机、不带凭据。
  try {
    const url = new URL(String(value).trim());
    return url.protocol === "https:" && Boolean(url.hostname) && !url.username && !url.password && !url.search && !url.hash;
  } catch (error) {
    console.warn("Invalid mirror prefix", error);
    return false;
  }
}

function normalizeMirrorInput(value) {
  return String(value ?? "").trim().replace(/\/+$/, "");
}

function mirrorLatencyLabel(url) {
  const result = state.mirrorLatency[url];
  if (!result) return t("mirrorUntested");
  if (!result.available) return `${t("mirrorUnreachable")}${result.error ? ` · ${result.error}` : ""}`;
  return `${t("mirrorLatency")} ${result.latency_ms} ms`;
}

function mirrorRow(url, selected, builtin) {
  const result = state.mirrorLatency[url];
  const tone = !result ? "" : result.available ? "ok" : "off";
  const remove = builtin
    ? ""
    : `<button type="button" data-mirror-remove="${escapeHtml(url)}">${escapeHtml(t("mirrorRemove"))}</button>`;
  return `<label class="mirror-item" title="${escapeHtml(t("mirrorApply"))}"><input type="radio" name="mirror-choice" value="${escapeHtml(url)}" ${selected ? "checked" : ""}/><span class="mirror-copy"><strong>${escapeHtml(url || t("mirrorDirect"))}</strong><small>${escapeHtml(builtin ? t("mirrorBuiltin") : t("mirrorCustom"))}</small></span><span class="mirror-meta"><span class="pill ${tone}">${escapeHtml(mirrorLatencyLabel(url))}</span>${remove}</span></label>`;
}

function renderMirrors() {
  const data = state.mirrors;
  if (!data) return;
  const direct = `<label class="mirror-item"><input type="radio" name="mirror-choice" value="" ${data.direct ? "checked" : ""}/><span class="mirror-copy"><strong>${escapeHtml(t("mirrorDirect"))}</strong></span><span class="mirror-meta"></span></label>`;
  document.getElementById("mirror-list").innerHTML = direct + (data.candidates || [])
    .map((item) => mirrorRow(item.url, Boolean(item.selected), Boolean(item.builtin)))
    .join("");
  document.getElementById("mirror-probe").textContent = `${t("mirrorProbeHint")}: ${data.probe_url || ""}`;
  const button = document.getElementById("mirror-benchmark");
  button.disabled = state.mirrorBusy;
  button.textContent = state.mirrorBusy ? t("mirrorBenchmarking") : t("mirrorBenchmark");
}

async function loadMirrors() {
  state.mirrors = await apiGet("mirrors");
  renderMirrors();
}

async function benchmarkMirrors() {
  if (state.mirrorBusy) return;
  state.mirrorBusy = true;
  renderMirrors();
  try {
    const data = await apiPost("mirrors/benchmark", {});
    for (const result of data.results || []) state.mirrorLatency[result.url] = result;
    toast(t("mirrorBenchmarkDone"));
  } catch (error) {
    toast(`${t("loadFailed")}: ${error.message}`, true);
  } finally {
    state.mirrorBusy = false;
    renderMirrors();
  }
}

async function selectMirror(value) {
  const mirror = normalizeMirrorInput(value);
  if (mirror && !isValidMirror(mirror)) {
    toast(t("mirrorInvalid"), true);
    await loadMirrors();
    return;
  }
  try {
    await apiPost("config", { github_mirror: mirror });
    toast(t("mirrorApplied"));
  } catch (error) {
    toast(`${t("saveFailed")}: ${error.message}`, true);
  } finally {
    await Promise.all([loadMirrors(), loadConfig()]);
  }
}

async function saveMirrorCandidates(candidates, successKey) {
  try {
    await apiPost("config", { github_mirror_candidates: candidates.join("\n") });
    toast(t(successKey));
  } catch (error) {
    toast(`${t("saveFailed")}: ${error.message}`, true);
  } finally {
    await Promise.all([loadMirrors(), loadConfig()]);
  }
}

async function addCustomMirror(event) {
  event.preventDefault();
  const input = document.getElementById("mirror-add-input");
  const mirror = normalizeMirrorInput(input.value);
  if (!isValidMirror(mirror)) {
    toast(t("mirrorInvalid"), true);
    return;
  }
  const custom = state.mirrors?.custom || [];
  const known = (state.mirrors?.candidates || []).map((item) => item.url);
  if (known.includes(mirror)) {
    toast(t("mirrorDuplicate"), true);
    return;
  }
  input.value = "";
  await saveMirrorCandidates([...custom, mirror], "mirrorAdded");
}

async function removeCustomMirror(mirror) {
  const custom = (state.mirrors?.custom || []).filter((item) => item !== mirror);
  // 移除正在使用的加速站时同步回到直连，避免配置指向一个已不存在的候选。
  if (state.mirrors?.selected === mirror) await selectMirror("");
  await saveMirrorCandidates(custom, "mirrorRemoved");
}

function catalogSwitch(item) {
  const action = item.activated ? "disable" : "enable";
  const operable = Boolean(item.lifecycle?.operable);
  const reason = operable ? "" : (item.lifecycle?.reason || t("catalogUnavailable"));
  return `<label class="lifecycle-switch" title="${escapeHtml(reason)}"><span class="sr-only">${escapeHtml(`${item.name || item.plugin_id} ${t(action)}`)}</span><input type="checkbox" role="switch" aria-checked="${item.activated ? "true" : "false"}" data-catalog-action="${action}" data-plugin-id="${escapeHtml(item.plugin_id)}" data-plugin-name="${escapeHtml(item.name || item.plugin_id)}" ${item.activated ? "checked" : ""} ${operable ? "" : "disabled"}/><span class="switch-track" aria-hidden="true"><span class="switch-thumb"></span></span><span class="switch-label">${escapeHtml(t(action))}</span></label>`;
}

// 把目录项与本地缓存的版本结果合并成推荐区同构的形状，直接复用
// versionStatusBadge / versionError，避免两套状态文案漂移。
function catalogVersionView(item) {
  const result = state.catalogVersions[item.plugin_id];
  if (!result) return null;
  return {
    version_status: result.version_status,
    error: result.error,
    error_detail: result.error_detail,
    error_context: result.error_context,
    latest_version: result.latest_version,
    update_available: Boolean(result.update_available)
  };
}

function catalogVersionLine(item) {
  const view = catalogVersionView(item);
  const base = `${escapeHtml(item.version || "—")} · ${item.loaded ? t("loaded") : t("notLoaded")} · ${item.activated ? t("active") : t("inactive")}`;
  if (!view) {
    // 没检查过就明确写"未检查"，不能让空白被误读成"已是最新"。
    const hint = item.update_lifecycle?.checkable ? `<span class="version-badge unknown">${escapeHtml(t("notChecked"))}</span>` : "";
    return `<span class="version-line">${hint}<span>${base}</span></span>`;
  }
  const detail = `${t("latestVersion")}: ${escapeHtml(view.latest_version || "—")}`;
  return `<span class="version-line">${versionStatusBadge(view)}<span>${base} · ${detail}</span></span>${versionError(view)}`;
}

function catalogUpdateButton(item) {
  // 来源不可回溯到 GitHub 的插件根本没有更新通道，直接不渲染按钮。
  if (!item.update_lifecycle?.checkable) return "";
  const view = catalogVersionView(item);
  const operable = Boolean(item.update_lifecycle?.operable);
  const updateEnabled = operable && Boolean(view?.update_available);
  const forceEnabled = operable && ["update_available", "up_to_date", "local_newer"].includes(view?.version_status);
  const lifecycleReason = errorReason(item.update_lifecycle?.reason);
  const updateHint = updateEnabled ? "" : `title="${escapeHtml(operable ? t("unavailableAction") : lifecycleReason)}"`;
  const forceHint = forceEnabled ? "" : `title="${escapeHtml(operable ? t("forceUpdateUnavailable") : lifecycleReason)}"`;
  const attributes = `data-catalog-update="${escapeHtml(item.plugin_id)}" data-plugin-name="${escapeHtml(item.display_name || item.plugin_id)}"`;
  return `<button type="button" ${attributes} ${updateEnabled ? "" : "disabled"} ${updateHint}>${escapeHtml(t("update"))}</button><button type="button" ${attributes} data-force-update="true" ${forceEnabled ? "" : "disabled"} ${forceHint}>${escapeHtml(t("forceUpdate"))}</button>`;
}

function renderCatalog() {
  const items = state.catalogItems || [];
  const diagnostics = state.catalogDiagnostics || [];
  document.getElementById("catalog-list").innerHTML = items.length
    ? items.map((item) => `<article class="catalog-item"><div><strong>${escapeHtml(item.display_name || item.plugin_id)}</strong><code>${escapeHtml(item.plugin_id)}</code>${catalogVersionLine(item)}</div><div class="catalog-actions"><span class="pill ${item.eligible ? "ok" : "off"}">${item.eligible ? t("eligible") : `${t("blocked")}: ${escapeHtml((item.reasons || []).join(", "))}`}</span>${catalogUpdateButton(item)}${catalogSwitch(item)}</div></article>`).join("")
    : `<div class="catalog-empty"><strong>${t("empty")}</strong><span>${escapeHtml(t("emptyDiagnostics"))}: ${escapeHtml(diagnostics.join(", ") || "NO_DIAGNOSTIC")}</span></div>`;
  const button = document.getElementById("catalog-check-updates");
  if (button) {
    button.disabled = state.catalogCheckBusy || Boolean(state.catalogBusy);
    button.textContent = state.catalogCheckBusy ? t("checkingUpdates") : t("checkUpdates");
  }
}

async function loadCatalog() {
  const data = await apiGet("catalog");
  state.catalogItems = data.items || [];
  state.catalogDiagnostics = data.diagnostics?.messages || [];
  // 目录被卸载或改名后残留的版本结果会一直显示旧数据，这里按最新目录裁剪。
  const known = new Set(state.catalogItems.map((item) => item.plugin_id));
  for (const pluginId of Object.keys(state.catalogVersions)) {
    if (!known.has(pluginId)) delete state.catalogVersions[pluginId];
  }
  renderCatalog();
}

// 只在用户点击时调用；进入页面和切到目录标签都不会自动触发。
// pluginIds 为空表示全量检查，传入时只复查指定插件（更新成功后单项刷新）。
async function checkCatalogUpdates(pluginIds = null) {
  const payload = { force_refresh: true };
  if (pluginIds?.length) payload.plugin_ids = pluginIds;
  const data = await apiPost("catalog/check-updates", payload);
  for (const result of data.items || []) state.catalogVersions[result.plugin_id] = result;
  renderRateLimitNotice(data.rate_limit, "catalog-rate-limit-notice");
  renderCatalog();
}

async function runCatalogCheck() {
  if (state.catalogCheckBusy || state.catalogBusy) return;
  state.catalogCheckBusy = true;
  renderCatalog();
  try {
    await checkCatalogUpdates();
    toast(t("updatesChecked"));
  } catch (error) {
    toast(`${t("checkFailed")}: ${error.message}`, true);
  } finally {
    state.catalogCheckBusy = false;
    renderCatalog();
  }
}

async function runCatalogUpdate(button) {
  const pluginId = button.dataset.catalogUpdate;
  const pluginName = button.dataset.pluginName || pluginId;
  const force = button.dataset.forceUpdate === "true";
  if (!pluginId || button.disabled || state.catalogBusy || state.catalogCheckBusy) return;
  const confirmed = force
    ? await showConfirmation(t("forceUpdateConfirm").replace("{name}", pluginName))
    : await confirmRecommendationAction("update", pluginName);
  if (!confirmed) return;
  state.catalogBusy = pluginId;
  document.querySelectorAll("#catalog-list button, #catalog-list input[role='switch']").forEach((node) => { node.disabled = true; });
  const status = document.getElementById("recommendation-status");
  status.textContent = `${pluginName}：${t(force ? "forceUpdateRunning" : "updateRunning")}`;
  status.hidden = false;
  try {
    const payload = force
      ? { plugin_id: pluginId, confirm: true, force: true }
      : { plugin_id: pluginId, confirm: true };
    await apiPost("catalog/update", payload);
    toast(t("operationDone"));
    // 更新成功后该行的版本结果已过期，只复查这一个插件而不是全量重扫。
    delete state.catalogVersions[pluginId];
  } catch (error) {
    toast(`${t("operationFailed")}: ${error.message}`, true);
  } finally {
    state.catalogBusy = null;
    status.hidden = true;
    await Promise.all([loadCatalog(), loadOverview(), loadRecommendations()]);
    try {
      await checkCatalogUpdates([pluginId]);
    } catch (error) {
      console.warn("Unable to re-check catalog plugin version", error);
    }
  }
}

function actionButton(item, action, label, enabled) {
  const disabled = enabled ? "" : "disabled";
  const hint = enabled ? "" : `title="${escapeHtml(t("unavailableAction"))}"`;
  return `<button type="button" data-recommendation-action="${action}" data-plugin-id="${escapeHtml(item.plugin_id)}" data-plugin-name="${escapeHtml(item.name)}" ${disabled} ${hint}>${escapeHtml(t(label))}</button>`;
}

function forceUpdateButton(item, enabled) {
  const disabled = enabled ? "" : "disabled";
  const hint = enabled ? "" : `title="${escapeHtml(t("forceUpdateUnavailable"))}"`;
  return `<button type="button" data-recommendation-action="update" data-force-update="true" data-plugin-id="${escapeHtml(item.plugin_id)}" data-plugin-name="${escapeHtml(item.name)}" ${disabled} ${hint}>${escapeHtml(t("forceUpdate"))}</button>`;
}

function lifecycleSwitch(item, actions) {
  const action = item.activated ? "disable" : "enable";
  const enabled = Boolean(actions[action]);
  const disabled = enabled ? "" : "disabled";
  const checked = item.activated ? "checked" : "";
  return `<label class="lifecycle-switch" title="${enabled ? "" : escapeHtml(t("unavailableAction"))}"><span class="sr-only">${escapeHtml(`${item.name} ${t(action)}`)}</span><input type="checkbox" role="switch" aria-checked="${item.activated ? "true" : "false"}" data-recommendation-action="${action}" data-plugin-id="${escapeHtml(item.plugin_id)}" data-plugin-name="${escapeHtml(item.name)}" ${checked} ${disabled}/><span class="switch-track" aria-hidden="true"><span class="switch-thumb"></span></span><span class="switch-label">${escapeHtml(t(action))}</span></label>`;
}

function formatRetryDelay(seconds) {
  const total = Number(seconds);
  if (!Number.isFinite(total) || total <= 0) return "";
  const minutes = Math.ceil(total / 60);
  if (minutes < 60) return state.locale === "zh-CN" ? `${minutes} 分钟` : `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return state.locale === "zh-CN"
    ? `${hours} 小时${rest ? ` ${rest} 分钟` : ""}`
    : `${hours} h${rest ? ` ${rest} min` : ""}`;
}

function retryHint(context) {
  const retry = formatRetryDelay(context.retry_after_seconds);
  const at = context.reset_at ? new Date(context.reset_at) : null;
  const readable = at && !Number.isNaN(at.getTime()) ? at.toLocaleString(state.locale) : "";
  if (!retry && !readable) return "";
  return `${t("errorRetryAfter")}: ${[retry, readable].filter(Boolean).join(" / ")}`;
}

// 推荐区与目录区共用同一份错误明细渲染：两侧的 check_failed 结构完全一致。
function versionError(item) {
  if (item.version_status !== "check_failed") return "";
  const context = item.error_context || {};
  const details = [
    `${t("errorCode")}: ${item.error || "UNKNOWN"}`,
    context.http_status ? `${t("errorHttpStatus")}: ${context.http_status}` : "",
    context.repo ? `${t("errorRepository")}: ${context.repo}` : "",
    context.default_branch ? `${t("errorBranch")}: ${context.default_branch}` : "",
    context.rate_limited ? retryHint(context) : "",
    context.token_hint_required ? t("errorTokenHint") : ""
  ].filter(Boolean);
  const reason = errorReason(item.error || item.error_detail);
  const message = [reason, ...details].filter(Boolean).join(" · ");
  return `<span class="version-error">${escapeHtml(message)}</span>`;
}

function renderRateLimitNotice(rateLimit, nodeId = "rate-limit-notice") {
  const notice = document.getElementById(nodeId);
  if (!notice) return;
  if (!rateLimit?.limited) {
    notice.hidden = true;
    notice.replaceChildren();
    return;
  }
  const parts = [
    t("rateLimitBanner").replace("{retry}", formatRetryDelay(rateLimit.retry_after_seconds) || "—"),
    retryHint({ retry_after_seconds: rateLimit.retry_after_seconds, reset_at: rateLimit.reset_at }),
    rateLimit.remaining === null || rateLimit.remaining === undefined
      ? ""
      : `${t("rateLimitRemaining")}: ${rateLimit.remaining}${rateLimit.limit ? `/${rateLimit.limit}` : ""}`,
    rateLimit.token_configured ? "" : t("errorTokenHint")
  ].filter(Boolean);
  notice.innerHTML = `<strong>${escapeHtml(parts[0])}</strong><span>${escapeHtml(parts.slice(1).join(" · "))}</span>`;
  notice.hidden = false;
}

function versionStatusBadge(item) {
  const status = ["update_available", "up_to_date", "local_newer", "not_installed", "check_failed"].includes(item.version_status)
    ? item.version_status
    : "unknown";
  const labels = {
    update_available: "updateAvailable",
    up_to_date: "upToDate",
    local_newer: "localNewer",
    not_installed: "notInstalled",
    check_failed: "checkFailed",
    unknown: "unknown"
  };
  return `<span class="version-badge ${status}">${escapeHtml(t(labels[status]))}</span>`;
}

function renderSelfUpdateNotice(selfUpdate) {
  const notice = document.getElementById("self-update-notice");
  if (!selfUpdate?.update_available) {
    notice.hidden = true;
    notice.replaceChildren();
    return;
  }
  const message = t("selfUpdateNotice")
    .replace("{current}", selfUpdate.current_version || "—")
    .replace("{latest}", selfUpdate.latest_version || "—");
  const installedRoute = "/extension#installed";
  const strong = document.createElement("strong");
  strong.textContent = message;
  const link = document.createElement("a");
  link.href = internalRouteUrl(installedRoute) || "#";
  link.target = "_top";
  link.rel = "noopener noreferrer";
  link.textContent = t("goToInstalledPlugins");
  link.dataset.internalRoute = installedRoute;
  notice.replaceChildren(strong, link);
  notice.hidden = false;
}

// check 为真时走 recommendations/check-latest；forceRefresh 为假时复用后端缓存，避免触发 GitHub 限流。
async function loadRecommendations(check = false, forceRefresh = true) {
  const data = check
    ? await apiPost("recommendations/check-latest", { force_refresh: forceRefresh })
    : await apiGet("recommendations");
  const items = data.items || [];
  renderSelfUpdateNotice(data.self_update);
  renderRateLimitNotice(data.rate_limit);
  const list = document.getElementById("recommendations-list");
  list.innerHTML = items.map((item) => {
    const actions = item.actions || {};
    const install = item.installed
      ? `<button type="button" disabled>${escapeHtml(t("installed"))}</button>`
      : actionButton(item, "install", "install", actions.install);
    const lifecycle = item.installed
      ? `${actionButton(item, "update", "update", actions.update)}${forceUpdateButton(item, actions.force_update)}${lifecycleSwitch(item, actions)}`
      : "";
    const versionDetail = `${t("currentVersion")}: ${escapeHtml(item.version || "—")} · ${t("latestVersion")}: ${escapeHtml(item.latest_version || "—")}`;
    return `<article class="recommendation-item"><div class="recommendation-copy"><span class="series-key">${escapeHtml(item.key)}</span><div><strong>${escapeHtml(item.name)}</strong><p class="recommendation-description" lang="zh-CN">${escapeHtml(item.description_zh || "")}</p><code>${escapeHtml(item.plugin_id)}</code><span class="version-line">${versionStatusBadge(item)}<span>${versionDetail} · ${item.installed ? t("installed") : t("notLoaded")} · ${item.activated ? t("active") : t("inactive")}</span></span>${versionError(item)}<a href="${escapeHtml(item.repo_url)}" target="_blank" rel="noopener noreferrer" data-external-url="${escapeHtml(item.repo_url)}">${escapeHtml(item.repo_url)}</a></div></div><div class="recommendation-actions">${install}${lifecycle}</div></article>`;
  }).join("");
}

function setVersionCheckBusy(labelKey) {
  state.versionCheckBusy = true;
  const button = document.getElementById("check-latest");
  if (button) {
    button.disabled = true;
    button.textContent = t("checkingLatest");
  }
  const status = document.getElementById("recommendation-status");
  if (status) {
    status.textContent = t(labelKey);
    status.hidden = false;
  }
}

function clearVersionCheckBusy() {
  state.versionCheckBusy = false;
  const button = document.getElementById("check-latest");
  if (button) {
    button.disabled = false;
    button.textContent = t("checkLatest");
  }
  // 推荐操作（安装/更新/启停）自己拥有状态条，不能被版本检查提前隐藏。
  const status = document.getElementById("recommendation-status");
  if (status && !state.recommendationBusy) status.hidden = true;
}

// 首次切到"系列推荐"时自动检查一次仓库版本；使用缓存、不强制刷新，失败也不阻塞列表渲染。
async function autoCheckRecommendations() {
  if (state.autoVersionCheckDone || state.versionCheckBusy || state.recommendationBusy) return;
  state.autoVersionCheckDone = true;
  setVersionCheckBusy("autoCheckingLatest");
  try {
    await loadRecommendations(true, false);
  } catch (error) {
    toast(`${t("checkFailed")}: ${error.message}`, true);
    try {
      await loadRecommendations();
    } catch (fallbackError) {
      console.warn("Unable to render cached recommendations", fallbackError);
    }
  } finally {
    clearVersionCheckBusy();
  }
}

function showConfirmation(message) {
  const dialog = document.getElementById("confirmation-dialog");
  document.getElementById("confirmation-message").textContent = message;
  return new Promise((resolve) => {
    dialog.addEventListener("close", () => resolve(dialog.returnValue === "confirm"), { once: true });
    dialog.showModal();
  });
}

function confirmRecommendationAction(action, pluginName) {
  const message = t("confirmPrompt")
    .replace("{action}", t(action))
    .replace("{name}", pluginName);
  return showConfirmation(message);
}

function setRecommendationBusy(action, pluginName) {
  state.recommendationBusy = action;
  document.querySelectorAll("#recommendations-list button, #recommendations-list input[role='switch']").forEach((item) => { item.disabled = true; });
  const status = document.getElementById("recommendation-status");
  status.textContent = `${pluginName}：${t(`${action}Running`)}`;
  status.hidden = false;
}

function clearRecommendationBusy() {
  state.recommendationBusy = null;
  document.getElementById("recommendation-status").hidden = true;
}

async function runApplyAllRecommendations() {
  const button = document.getElementById("apply-all-recommendations");
  if (!button || button.disabled || state.recommendationBusy || state.versionCheckBusy) return;
  if (!await showConfirmation(t("applyAllConfirm"))) return;

  state.recommendationBusy = "applyAll";
  button.disabled = true;
  document.getElementById("check-latest").disabled = true;
  document.querySelectorAll("#recommendations-list button, #recommendations-list input[role='switch']").forEach((item) => { item.disabled = true; });
  const status = document.getElementById("recommendation-status");
  status.textContent = t("applyingAll");
  status.hidden = false;
  try {
    const result = await apiPost("recommendations/apply-all", { confirm: true });
    const message = `${result.all_succeeded ? t("applyAllDone") : t("applyAllPartial")}：${result.succeeded}/${result.total}`;
    toast(message, !result.all_succeeded);
  } catch (error) {
    toast(`${t("operationFailed")}: ${error.message}`, true);
  } finally {
    clearRecommendationBusy();
    button.disabled = false;
    document.getElementById("check-latest").disabled = false;
    await Promise.all([loadRecommendations(), loadOverview(), loadCatalog()]);
  }
}

async function runRecommendationAction(button) {
  const action = button.dataset.recommendationAction;
  const pluginId = button.dataset.pluginId;
  const pluginName = button.dataset.pluginName || pluginId;
  const force = action === "update" && button.dataset.forceUpdate === "true";
  if (!action || !pluginId || button.disabled || state.recommendationBusy) return;
  const requiresConfirmation = ["install", "update", "disable"].includes(action);
  const confirmed = !requiresConfirmation
    || (force
      ? await showConfirmation(t("forceUpdateConfirm").replace("{name}", pluginName))
      : await confirmRecommendationAction(action, pluginName));
  if (!confirmed) {
    await loadRecommendations();
    return;
  }
  setRecommendationBusy(force ? "forceUpdate" : action, pluginName);
  try {
    const payload = force
      ? { plugin_id: pluginId, confirm: true, force: true }
      : requiresConfirmation
        ? { plugin_id: pluginId, confirm: true }
        : { plugin_id: pluginId };
    await apiPost(action, payload);
    toast(t("operationDone"));
  } catch (error) {
    toast(`${t("operationFailed")}: ${error.message}`, true);
  } finally {
    clearRecommendationBusy();
    await Promise.all([loadRecommendations(), loadOverview(), loadCatalog()]);
  }
}

async function runCatalogAction(input) {
  const action = input.dataset.catalogAction;
  const pluginId = input.dataset.pluginId;
  const pluginName = input.dataset.pluginName || pluginId;
  if (!action || !pluginId || input.disabled) return;
  // 更新与启停都会走热重载，必须串行，否则两个流程会互相打断。
  if (state.catalogBusy || state.catalogCheckBusy) {
    await loadCatalog();
    return;
  }
  if (action === "disable" && !await confirmRecommendationAction(action, pluginName)) {
    await loadCatalog();
    return;
  }
  input.disabled = true;
  try {
    const payload = action === "disable"
      ? { plugin_id: pluginId, confirm: true }
      : { plugin_id: pluginId };
    await apiPost(`catalog/${action}`, payload);
    toast(t("operationDone"));
  } catch (error) {
    toast(`${t("operationFailed")}: ${error.message}`, true);
  } finally {
    await Promise.all([loadCatalog(), loadOverview(), loadRule(), loadRecommendations()]);
  }
}

function diagnosticStatusKey(status) {
  if (status === "ready") return "diagnosticReady";
  if (status === "missing") return "diagnosticMissing";
  if (status === "disabled") return "diagnosticDisabled";
  if (status === "unavailable") return "diagnosticUnavailable";
  if (status === "unsupported" || status === "incompatible") return "diagnosticUnsupported";
  return "diagnosticFailed";
}

function diagnosticStatusClass(status) {
  if (status === "ready") return "ok";
  if (status === "missing" || status === "disabled" || status === "unsupported") return "off";
  return "warn";
}

function syncDiagnosticPluginFilter() {
  const select = document.getElementById("diagnostic-plugin-filter");
  const selected = select.value;
  select.innerHTML = `<option value="">${escapeHtml(t("allPlugins"))}</option>` + state.diagnosticMembers.map((member) => (
    `<option value="${escapeHtml(member.plugin_id)}">${escapeHtml(member.plugin_name)} · ${escapeHtml(member.display_name)}</option>`
  )).join("");
  if ([...select.options].some((option) => option.value === selected)) select.value = selected;
}

function diagnosticValue(value) {
  if (value && typeof value === "object") {
    try {
      return JSON.stringify(value, null, 2);
    } catch (_) {
      return String(value);
    }
  }
  return String(value ?? "");
}

function diagnosticDetails(details) {
  const data = details && typeof details === "object" ? details : {};
  const logDetail = typeof data.log_detail === "string" ? data.log_detail : "";
  const entries = Object.entries(data).filter(([key]) => key !== "log_detail");
  if (!logDetail && !entries.length) {
    return `<p class="diagnostic-detail-empty">${escapeHtml(t("diagnosticNoDetails"))}</p>`;
  }
  return `<div class="diagnostic-details">`
    + (logDetail ? `<pre class="diagnostic-log-detail">${escapeHtml(logDetail)}</pre>` : "")
    + (entries.length ? `<div class="diagnostic-detail-fields">${entries.map(([key, value]) => (
      `<span><code>${escapeHtml(key)}</code><pre>${escapeHtml(diagnosticValue(value))}</pre></span>`
    )).join("")}</div>` : "")
    + `</div>`;
}

function diagnosticTime(value) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return String(value || "—");
  return parsed.toLocaleString(state.locale, { hour12: false });
}

function filteredDiagnosticEvents() {
  const pluginId = document.getElementById("diagnostic-plugin-filter").value;
  const level = document.getElementById("diagnostic-level-filter").value;
  const query = document.getElementById("diagnostic-search").value.trim().toLocaleLowerCase();
  return state.diagnosticEvents.filter((event) => {
    if (pluginId && event.plugin_id !== pluginId) return false;
    if (level && event.level !== level) return false;
    if (!query) return true;
    return `${event.plugin_name} ${event.code} ${event.summary} ${JSON.stringify(event.details || {})}`.toLocaleLowerCase().includes(query);
  });
}

function renderDiagnostics() {
  syncDiagnosticPluginFilter();
  const memberNode = document.getElementById("diagnostic-members");
  memberNode.innerHTML = state.diagnosticMembers.map((member) => (
    `<span class="diagnostic-member ${diagnosticStatusClass(member.status)}" title="${escapeHtml(member.reason || "")}"><strong>${escapeHtml(member.plugin_name)}</strong>${escapeHtml(t(diagnosticStatusKey(member.status)))}</span>`
  )).join("");
  const list = document.getElementById("diagnostic-log-list");
  const shouldStick = list.scrollHeight - list.scrollTop - list.clientHeight < 48;
  const matchingEvents = filteredDiagnosticEvents();
  const events = matchingEvents.slice(-500);
  list.innerHTML = events.length ? events.map((event) => {
    const eventKey = `${event.plugin_id}:${event.seq}`;
    const open = state.diagnosticExpanded.has(eventKey) ? " open" : "";
    return `<details class="diagnostic-event level-${escapeHtml(event.level.toLowerCase())}" data-diagnostic-key="${escapeHtml(eventKey)}"${open}>`
      + `<summary class="diagnostic-event-summary">`
      + `<span class="diagnostic-meta"><span class="diagnostic-plugin">${escapeHtml(event.plugin_name)}</span><time>${escapeHtml(diagnosticTime(event.timestamp))}</time><span class="diagnostic-level">${escapeHtml(event.level)}</span><code>${escapeHtml(event.code || "event")}</code></span>`
      + `<span class="diagnostic-event-summary-text">${escapeHtml(event.summary || "—")}</span>`
      + `</summary><div class="diagnostic-event-body">${diagnosticDetails(event.details)}</div></details>`;
  }).join("") : `<p class="diagnostic-empty">${escapeHtml(t("diagnosticEmpty"))}</p>`;
  list.querySelectorAll("details.diagnostic-event").forEach((node) => {
    node.addEventListener("toggle", () => {
      const eventKey = node.dataset.diagnosticKey;
      if (!eventKey) return;
      if (node.open) state.diagnosticExpanded.add(eventKey);
      else state.diagnosticExpanded.delete(eventKey);
    });
  });
  if (shouldStick) list.scrollTop = list.scrollHeight;
  const hasGap = state.diagnosticMembers.some((member) => member.gap);
  const summary = t("diagnosticCount")
    .replace("{shown}", String(events.length))
    .replace("{total}", String(state.diagnosticEvents.length));
  document.getElementById("diagnostic-summary").textContent = [summary, state.diagnosticPaused ? t("diagnosticPaused") : "", hasGap ? t("diagnosticGap") : ""].filter(Boolean).join(" · ");
  document.getElementById("diagnostic-pause").textContent = t(state.diagnosticPaused ? "resumeLogs" : "pauseLogs");
}

async function loadDiagnostics(reset = false) {
  if (state.diagnosticBusy) {
    if (reset) {
      state.diagnosticGeneration += 1;
      state.diagnosticRefreshPending = true;
    }
    return;
  }
  if (reset) state.diagnosticGeneration += 1;
  const generation = state.diagnosticGeneration;
  state.diagnosticBusy = true;
  if (reset) {
    state.diagnosticEvents = [];
    state.diagnosticCursors = {};
    state.diagnosticStreams = {};
    state.diagnosticExpanded.clear();
  }
  try {
    const data = await apiPost("diagnostics/logs", {
      cursors: state.diagnosticCursors,
      streams: state.diagnosticStreams,
      limit: 1000
    });
    if (generation !== state.diagnosticGeneration) return;
    const nextMembers = data.members || [];
    const membersChanged = JSON.stringify(state.diagnosticMembers) !== JSON.stringify(nextMembers);
    state.diagnosticMembers = nextMembers;
    const activePluginIds = new Set(nextMembers.map((member) => member.plugin_id));
    const removedPluginIds = new Set(
      state.diagnosticEvents
        .map((event) => event.plugin_id)
        .filter((pluginId) => !activePluginIds.has(pluginId))
    );
    const resetPluginIds = new Set(
      state.diagnosticMembers.filter((member) => member.reset).map((member) => member.plugin_id)
    );
    let eventsChanged = reset || resetPluginIds.size > 0 || removedPluginIds.size > 0;
    if (resetPluginIds.size || removedPluginIds.size) {
      state.diagnosticEvents = state.diagnosticEvents.filter(
        (event) => !resetPluginIds.has(event.plugin_id) && !removedPluginIds.has(event.plugin_id)
      );
    }
    Object.keys(state.diagnosticCursors).forEach((pluginId) => {
      if (!activePluginIds.has(pluginId)) delete state.diagnosticCursors[pluginId];
    });
    Object.keys(state.diagnosticStreams).forEach((pluginId) => {
      if (!activePluginIds.has(pluginId)) delete state.diagnosticStreams[pluginId];
    });
    state.diagnosticMembers.forEach((member) => {
      if (member.status === "ready") {
        state.diagnosticCursors[member.plugin_id] = member.next_seq || 0;
        if (member.stream_id) {
          state.diagnosticStreams[member.plugin_id] = member.stream_id;
        } else {
          delete state.diagnosticStreams[member.plugin_id];
        }
      }
    });
    const seen = new Set(state.diagnosticEvents.map((event) => `${event.plugin_id}:${event.seq}`));
    (data.events || []).forEach((event) => {
      const key = `${event.plugin_id}:${event.seq}`;
      if (!seen.has(key)) {
        seen.add(key);
        state.diagnosticEvents.push(event);
        eventsChanged = true;
      }
    });
    state.diagnosticEvents.sort((left, right) => String(left.timestamp).localeCompare(String(right.timestamp)) || left.plugin_id.localeCompare(right.plugin_id) || left.seq - right.seq);
    if (state.diagnosticEvents.length > 10000) {
      state.diagnosticEvents.splice(0, state.diagnosticEvents.length - 10000);
      eventsChanged = true;
    }
    state.diagnosticLoaded = true;
    if (membersChanged || eventsChanged) renderDiagnostics();
  } finally {
    state.diagnosticBusy = false;
    if (state.diagnosticRefreshPending) {
      state.diagnosticRefreshPending = false;
      await loadDiagnostics(true);
    }
  }
}

function stopDiagnosticPolling() {
  if (state.diagnosticTimer !== null) window.clearInterval(state.diagnosticTimer);
  state.diagnosticTimer = null;
}

function startDiagnosticPolling() {
  stopDiagnosticPolling();
  if (state.diagnosticPaused) return;
  state.diagnosticTimer = window.setInterval(() => {
    if (document.getElementById("logs").classList.contains("active")) {
      loadDiagnostics().catch((error) => toast(`${t("loadFailed")}: ${error.message}`, true));
    }
  }, 2000);
}

async function clearDiagnostics() {
  if (!await showConfirmation(t("clearDiagnosticsConfirm"))) return;
  state.diagnosticGeneration += 1;
  await apiPost("diagnostics/clear", { confirm: true });
  state.diagnosticEvents = [];
  state.diagnosticMembers = [];
  state.diagnosticCursors = {};
  state.diagnosticStreams = {};
  state.diagnosticExpanded.clear();
  state.diagnosticLoaded = true;
  renderDiagnostics();
  await loadDiagnostics(true);
  toast(t("diagnosticsCleared"));
}


const sectionLoaders = {
  overview: { targetId: "summary", labelKey: "overview", load: loadOverview },
  recommendations: { targetId: "recommendations-list", labelKey: "recommendations", load: loadRecommendations },
  config: { targetId: "config-fields", labelKey: "config", load: loadConfig },
  rule: { targetId: "rule-plugins", labelKey: "ruleTitle", load: loadRule },
  mirrors: { targetId: "mirror-list", labelKey: "mirrors", load: loadMirrors },
  catalog: { targetId: "catalog-list", labelKey: "catalog", load: loadCatalog },
  diagnostics: { targetId: "diagnostic-log-list", labelKey: "diagnosticTitle", load: () => loadDiagnostics(true) }
};

function renderSectionLoadError(name, error) {
  const section = sectionLoaders[name];
  const node = section ? document.getElementById(section.targetId) : null;
  if (!node) return;
  const label = t(section.labelKey);
  const detail = error?.message || String(error || t("errorUnknown"));
  node.innerHTML = `<div class="section-load-error" role="alert"><strong>${escapeHtml(`${label}：${t("sectionLoadFailed")}`)}</strong><span>${escapeHtml(detail)}</span><button type="button" data-retry-section="${escapeHtml(name)}">${escapeHtml(t("retry"))}</button></div>`;
}

async function retrySection(name, button = null) {
  const section = sectionLoaders[name];
  if (!section) return;
  if (button) {
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
  }
  try {
    await section.load();
  } catch (error) {
    renderSectionLoadError(name, error);
  }
}

async function refreshPage(button) {
  if (button.disabled) return;
  const idleText = button.textContent;
  button.disabled = true;
  button.setAttribute("aria-busy", "true");
  button.textContent = t("loading");
  try {
    await refreshAll();
  } finally {
    button.disabled = false;
    button.setAttribute("aria-busy", "false");
    button.textContent = idleText;
  }
}

async function refreshAll(includeDiagnostics = true) {
  const entries = Object.entries(sectionLoaders).filter(([name]) => (
    name !== "diagnostics" || (includeDiagnostics && state.diagnosticLoaded)
  ));
  const results = await Promise.allSettled(entries.map(([, section]) => section.load()));
  let failed = 0;
  results.forEach((result, index) => {
    if (result.status === "fulfilled") return;
    failed += 1;
    renderSectionLoadError(entries[index][0], result.reason);
  });
  if (failed) toast(`${t("loadFailed")}：${failed}`, true);
}

function activateTab(button, focus = false) {
  document.querySelectorAll("[data-tab]").forEach((tab) => {
    const active = tab === button;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", active ? "true" : "false");
    tab.tabIndex = active ? 0 : -1;
  });
  document.querySelectorAll(".panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === button.dataset.tab);
  });
  if (focus) button.focus();
  if (button.dataset.tab !== "logs") stopDiagnosticPolling();
  if (button.dataset.tab === "recommendations") {
    autoCheckRecommendations().catch((error) => {
      console.warn("Automatic recommendation version check failed", error);
    });
  }
  if (button.dataset.tab === "logs") {
    loadDiagnostics(!state.diagnosticLoaded).catch((error) => renderSectionLoadError("diagnostics", error));
    startDiagnosticPolling();
  }
}

function showStartupError(error) {
  const message = `${t("startupFailed")}: ${error?.message || error}`;
  const node = document.getElementById("startup-error");
  if (node) {
    node.textContent = message;
    node.hidden = false;
  }
  toast(message, true);
}

function bindEvents() {
  const tabs = [...document.querySelectorAll("[data-tab]")];
  tabs.forEach((button) => button.addEventListener("click", () => activateTab(button)));
  document.querySelector(".tabs").addEventListener("keydown", (event) => {
    const current = tabs.indexOf(event.target.closest("[data-tab]"));
    if (current < 0) return;
    let next = null;
    if (event.key === "ArrowRight") next = (current + 1) % tabs.length;
    if (event.key === "ArrowLeft") next = (current - 1 + tabs.length) % tabs.length;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = tabs.length - 1;
    if (next === null) return;
    event.preventDefault();
    activateTab(tabs[next], true);
  });
  // 自更新提示与推荐卡片里的仓库链接共用显式打开，避免 iframe 拦截 target=_blank。
  document.addEventListener("click", async (event) => {
    const retryButton = event.target.closest("[data-retry-section]");
    if (retryButton) {
      event.preventDefault();
      await retrySection(retryButton.dataset.retrySection, retryButton);
      return;
    }
    const link = event.target.closest("a[data-external-url], a[data-internal-route]");
    if (!link || !document.contains(link)) return;
    const route = link.dataset.internalRoute || "";
    if (route) {
      // 没有导航 bridge 时保留 <a target="_top"> 的原生行为，
      // 让用户手势直接完成跨 iframe 的 Dashboard 跳转。
      if (!bridge || typeof bridge.navigate !== "function") return;
      event.preventDefault();
      await openSelfUpdateTarget(link, route);
      return;
    }
    const url = link.dataset.externalUrl || link.getAttribute("href") || "";
    if (!url || url === "#") {
      event.preventDefault();
      return;
    }
    event.preventDefault();
    if (!await openExternalUrl(url)) toast(t("operationFailed"), true);
  });
  document.getElementById("config-form").addEventListener("submit", saveConfig);
  document.getElementById("webui-admin-create-form")?.addEventListener("submit", createWebUiAdmin);
  document.getElementById("open-webui")?.addEventListener("click", openStandaloneWebUi);
  document.getElementById("open-webui-direct")?.addEventListener("click", openStandaloneWebUi);
  document.getElementById("copy-webui")?.addEventListener("click", copyStandaloneWebUiLink);
  document.getElementById("open-webui-config")?.addEventListener("click", openStandaloneWebUi);
  document.getElementById("webui-admins-refresh")?.addEventListener("click", () => loadWebUiAdmins().catch((error) => toast(`${t("loadFailed")}: ${error.message}`, true)));
  document.getElementById("webui-admin-list")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-admin-action]");
    if (!button) return;
    button.disabled = true;
    updateWebUiAdmin(button.dataset.adminId, button.dataset.adminAction)
      .catch((error) => toast(`${t("operationFailed")}: ${error.message}`, true))
      .finally(() => { button.disabled = false; });
  });
  document.getElementById("rule-form").addEventListener("submit", saveRule);
  document.getElementById("rule-policy").addEventListener("change", (event) => {
    document.getElementById("check-only-note").hidden = event.target.value !== "check_only";
  });
  document.getElementById("apply-all-recommendations").addEventListener("click", runApplyAllRecommendations);
  document.getElementById("recommendations-list").addEventListener("click", (event) => {
    const button = event.target.closest("[data-recommendation-action]");
    if (button) {
      event.preventDefault();
      runRecommendationAction(button);
    }
  });
  document.getElementById("catalog-list").addEventListener("change", (event) => {
    const input = event.target.closest("[data-catalog-action]");
    if (input) runCatalogAction(input);
  });
  document.getElementById("catalog-list").addEventListener("click", (event) => {
    const button = event.target.closest("[data-catalog-update]");
    if (button) {
      event.preventDefault();
      runCatalogUpdate(button);
    }
  });
  document.getElementById("catalog-check-updates").addEventListener("click", runCatalogCheck);
  document.getElementById("mirror-benchmark").addEventListener("click", benchmarkMirrors);
  document.getElementById("mirror-add-form").addEventListener("submit", addCustomMirror);
  document.getElementById("mirror-list").addEventListener("change", (event) => {
    const input = event.target.closest("input[name='mirror-choice']");
    if (input) selectMirror(input.value);
  });
  document.getElementById("mirror-list").addEventListener("click", (event) => {
    const button = event.target.closest("[data-mirror-remove]");
    if (button) {
      event.preventDefault();
      removeCustomMirror(button.dataset.mirrorRemove);
    }
  });
  document.getElementById("diagnostic-pause").addEventListener("click", () => {
    state.diagnosticPaused = !state.diagnosticPaused;
    if (state.diagnosticPaused) stopDiagnosticPolling();
    else startDiagnosticPolling();
    renderDiagnostics();
  });
  document.getElementById("diagnostic-refresh").addEventListener("click", () => {
    loadDiagnostics(true).catch((error) => toast(`${t("loadFailed")}: ${error.message}`, true));
  });
  document.getElementById("diagnostic-clear").addEventListener("click", () => {
    clearDiagnostics().catch((error) => toast(`${t("operationFailed")}: ${error.message}`, true));
  });
  document.getElementById("diagnostic-plugin-filter").addEventListener("change", renderDiagnostics);
  document.getElementById("diagnostic-level-filter").addEventListener("change", renderDiagnostics);
  document.getElementById("diagnostic-search").addEventListener("input", () => {
    window.clearTimeout(state.diagnosticSearchTimer);
    state.diagnosticSearchTimer = window.setTimeout(renderDiagnostics, 200);
  });
  document.getElementById("check-latest").addEventListener("click", async () => {
    // 与自动检查共享同一把锁：任一方在跑时忽略新的手动点击。
    if (state.versionCheckBusy) return;
    // 手动检查是明确的用户意图，跳过自动检查以免重复请求。
    state.autoVersionCheckDone = true;
    setVersionCheckBusy("checkingLatest");
    try {
      await loadRecommendations(true);
      toast(t("latestChecked"));
    } catch (error) {
      toast(`${t("loadFailed")}: ${error.message}`, true);
    } finally {
      clearVersionCheckBusy();
    }
  });
  document.getElementById("refresh").addEventListener("click", (event) => refreshPage(event.currentTarget));
  document.getElementById("locale").addEventListener("change", async (event) => {
    state.locale = event.target.value;
    storeLocale(state.locale);
    applyI18n();
    await refreshAll();
  });
}

async function init() {
  bridge = await resolveBridge();
  if (typeof bridge.ready !== "function") throw new Error("Bridge ready() is unavailable");
  await bridge.ready();
  bindEvents();
  applyI18n();
  const initialDiagnostics = loadDiagnostics(true);
  const initialPageData = refreshAll(false);
  try {
    await initialDiagnostics;
  } catch (error) {
    renderSectionLoadError("diagnostics", error);
  }
  startDiagnosticPolling();
  await initialPageData;
}

init().catch(showStartupError);
