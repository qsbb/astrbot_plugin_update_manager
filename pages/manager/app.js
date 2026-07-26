const messages = {
  "zh-CN": {
    title: "凝心溯溪-核 · 更新管理", heading: "凝心溯溪-核", subtitle: "安全、串行、可回滚的插件更新控制台",
    refresh: "刷新", overview: "总览", recommendations: "系列推荐", config: "配置", catalog: "目录", mirrors: "镜像加速", loading: "加载中…",
    startupFailed: "页面启动失败",
    capabilities: "运行时能力", configTitle: "配置读取与保存", tokenHint: "敏感 token 仅显示是否已配置，留空不会覆盖。",
    save: "保存", catalogTitle: "插件目录", catalogHint: "合并展示运行时插件与已安装元数据；未加载插件不可更新。",
    recommendationsTitle: "凝心溯溪系列推荐", recommendationsHint: "官方安装会直接加载；更新和启用由 AstrBot 内部热重载，页面不会额外重复重载。核禁止自更新和自停用。",
    checkLatest: "检查最新版本", checkingLatest: "正在检查…", autoCheckingLatest: "正在自动检查版本…", latestChecked: "版本检查完成", currentVersion: "当前", latestVersion: "最新", checkFailed: "检查失败",
    applyAll: "一键全部安装/更新", applyingAll: "正在全部安装/更新…", applyAllConfirm: "确定要安装或更新全部可用的推荐插件吗？", applyAllDone: "全部操作完成", applyAllPartial: "部分操作失败",
    updateAvailable: "有新版本", upToDate: "已是最新版", localNewer: "本地版本更新", notInstalled: "未安装", unknown: "未知",
    selfUpdateNotice: "更新管理器有新版本：当前 {current}，最新 {latest}。自身更新已禁用，请前往仓库更新。", goToRepository: "前往仓库更新",
    install: "安装", installed: "已安装", update: "更新", enable: "启用", disable: "停用", operationDone: "操作完成", operationFailed: "操作失败", unavailableAction: "仅检测到新版本且运行时支持时可更新", catalogUnavailable: "此插件不可启停", errorUnknown: "请求失败，请稍后重试", error404: "远端未发布 Release 或标签", errorNetwork: "网络连接失败", errorTimeout: "请求超时", errorRateLimit: "GitHub 请求受限，请稍后重试", errorCode: "错误代码", errorHttpStatus: "HTTP 状态", errorRepository: "仓库", errorBranch: "分支",
    errorRetryAfter: "可重试时间", errorTokenHint: "可在配置中填写 GitHub Token 提升额度", rateLimitBanner: "GitHub 配额已用尽，{retry}后可再次检查。", rateLimitRemaining: "剩余配额",
    confirmTitle: "确认插件操作", confirmAction: "确认操作", cancel: "取消", confirmPrompt: "确定要{action}“{name}”吗？", installRunning: "正在安装…", updateRunning: "正在更新…", enableRunning: "正在启用…", disableRunning: "正在停用…",
    enabled: "插件启用", automatic: "自动更新", busy: "执行状态", idle: "空闲", running: "执行中", nextRun: "下次运行",
    available: "可用", unavailable: "不可用", configured: "已配置", notConfigured: "未配置", writeOnly: "仅写入，不回显",
    eligible: "可规划", blocked: "已阻断", loaded: "已加载", notLoaded: "未加载", active: "已启用", inactive: "未启用",
    empty: "暂无插件", emptyDiagnostics: "目录诊断", saved: "配置已保存", loadFailed: "加载失败", saveFailed: "保存失败",
    checkUpdates: "检查更新", checkingUpdates: "正在检查更新…", updatesChecked: "更新检查完成", notChecked: "未检查", catalogUpdateHint: "点击「检查更新」后才会显示版本状态",
    mirrorsTitle: "GitHub 镜像加速", mirrorsHint: "加速站只做前缀代理；镜像不可用会自动回退直连，不会导致检查失败。", mirrorDirect: "直连 GitHub（不使用加速站）", mirrorBuiltin: "内置", mirrorCustom: "自定义",
    mirrorBenchmark: "一键测速", mirrorBenchmarking: "正在测速…", mirrorBenchmarkDone: "测速完成", mirrorLatency: "延迟", mirrorUnreachable: "不可用", mirrorUntested: "未测速",
    mirrorApply: "使用该加速站", mirrorApplied: "加速站已切换", mirrorAddTitle: "添加自定义加速站", mirrorAddPlaceholder: "https://your-mirror.example.com", mirrorAdd: "添加", mirrorAdded: "自定义加速站已添加", mirrorInvalid: "加速站必须是合法的 https 前缀", mirrorDuplicate: "该加速站已在列表中", mirrorRemove: "移除", mirrorRemoved: "自定义加速站已移除", mirrorProbeHint: "测速探针",
    ruleTitle: "每日自动更新", saveRule: "保存规则", ruleEnabled: "启用每日规则", autoUpdateGate: "允许自动更新总闸", autoUpdateGateHint: "关闭时任何每日规则都不会执行自动更新。", ruleTime: "运行时间", ruleTimezone: "时区", rulePolicy: "更新策略", failurePolicy: "失败策略", jitter: "抖动（分钟）", minimumAge: "最小发布年龄（小时）", prerelease: "允许预发行版本", selectPlugins: "选择插件", ruleSaved: "每日规则与总闸已保存", checkOnlyNote: "check_only 仅检查并记录，绝不会更新插件。", gateReady: "总闸已开启，启用规则后将注册每日任务。", gateClosed: "自动更新总闸已关闭。", pluginDisabled: "插件当前未启用，规则不会执行。", policyCheckOnly: "仅检查（check_only）", policyPatch: "仅补丁版本（patch）", policyMinor: "允许次版本（minor）", policyStable: "最新稳定版（stable）", failureRollbackContinue: "回滚后继续（rollback_continue）", failureRollbackStop: "回滚并停止（rollback_stop）"
  },
  "en-US": {
    title: "Update Manager", heading: "Update Manager", subtitle: "Safe, serial and rollback-ready plugin updates",
    refresh: "Refresh", overview: "Overview", recommendations: "Recommendations", config: "Configuration", catalog: "Catalog", mirrors: "Mirror acceleration", loading: "Loading…",
    startupFailed: "Page startup failed",
    capabilities: "Runtime capabilities", configTitle: "Read and save configuration", tokenHint: "Sensitive tokens are write-only. Empty values keep the current secret.",
    save: "Save", catalogTitle: "Plugin catalog", catalogHint: "Runtime plugins and installed metadata are always merged; unloaded plugins cannot be updated.",
    recommendationsTitle: "Ningxin Suxi series", recommendationsHint: "Official installation loads directly. Update and enable use AstrBot's internal hot reload; this page never triggers a duplicate reload. Core cannot update or disable itself.",
    checkLatest: "Check latest versions", checkingLatest: "Checking…", autoCheckingLatest: "Checking versions automatically…", latestChecked: "Version check completed", currentVersion: "Current", latestVersion: "Latest", checkFailed: "Check failed",
    applyAll: "Install/update all", applyingAll: "Installing/updating all…", applyAllConfirm: "Install or update all available recommended plugins?", applyAllDone: "All operations completed", applyAllPartial: "Some operations failed",
    updateAvailable: "New version available", upToDate: "Up to date", localNewer: "Local version is newer", notInstalled: "Not installed", unknown: "Unknown",
    selfUpdateNotice: "A newer update manager is available: current {current}, latest {latest}. Self-update is disabled; update it from the repository.", goToRepository: "Open repository",
    install: "Install", installed: "Installed", update: "Update", enable: "Enable", disable: "Disable", operationDone: "Operation completed", operationFailed: "Operation failed", unavailableAction: "Update is enabled only when a newer version is detected and supported", catalogUnavailable: "This plugin cannot be toggled", errorUnknown: "Request failed; try again later", error404: "No release or tag was found", errorNetwork: "Network connection failed", errorTimeout: "Request timed out", errorRateLimit: "GitHub request limit reached; try again later", errorCode: "Error code", errorHttpStatus: "HTTP status", errorRepository: "Repository", errorBranch: "Branch",
    errorRetryAfter: "Retry after", errorTokenHint: "Set a GitHub Token in configuration to raise the quota", rateLimitBanner: "The GitHub quota is exhausted; you can check again in {retry}.", rateLimitRemaining: "Remaining quota",
    confirmTitle: "Confirm plugin action", confirmAction: "Confirm", cancel: "Cancel", confirmPrompt: "Are you sure you want to {action} “{name}”?", installRunning: "Installing…", updateRunning: "Updating…", enableRunning: "Enabling…", disableRunning: "Disabling…",
    enabled: "Plugin enabled", automatic: "Automatic updates", busy: "Execution", idle: "Idle", running: "Running", nextRun: "Next run",
    available: "Available", unavailable: "Unavailable", configured: "Configured", notConfigured: "Not configured", writeOnly: "Write-only; never returned",
    eligible: "Eligible", blocked: "Blocked", loaded: "Loaded", notLoaded: "Not loaded", active: "Active", inactive: "Inactive",
    empty: "No plugins", emptyDiagnostics: "Catalog diagnostics", saved: "Configuration saved", loadFailed: "Load failed", saveFailed: "Save failed",
    checkUpdates: "Check for updates", checkingUpdates: "Checking for updates…", updatesChecked: "Update check completed", notChecked: "Not checked", catalogUpdateHint: "Version status appears after you run a check",
    mirrorsTitle: "GitHub mirror acceleration", mirrorsHint: "Mirrors only proxy by prefix. An unavailable mirror falls back to a direct connection and never fails the check.", mirrorDirect: "Direct GitHub connection (no mirror)", mirrorBuiltin: "Built-in", mirrorCustom: "Custom",
    mirrorBenchmark: "Run benchmark", mirrorBenchmarking: "Benchmarking…", mirrorBenchmarkDone: "Benchmark completed", mirrorLatency: "Latency", mirrorUnreachable: "Unavailable", mirrorUntested: "Not tested",
    mirrorApply: "Use this mirror", mirrorApplied: "Mirror switched", mirrorAddTitle: "Add a custom mirror", mirrorAddPlaceholder: "https://your-mirror.example.com", mirrorAdd: "Add", mirrorAdded: "Custom mirror added", mirrorInvalid: "A mirror must be a valid https prefix", mirrorDuplicate: "This mirror is already listed", mirrorRemove: "Remove", mirrorRemoved: "Custom mirror removed", mirrorProbeHint: "Benchmark probe",
    ruleTitle: "Daily automatic updates", saveRule: "Save rule", ruleEnabled: "Enable daily rule", autoUpdateGate: "Allow automatic updates — master switch", autoUpdateGateHint: "When off, no daily rule can perform automatic updates.", ruleTime: "Run time", ruleTimezone: "Timezone", rulePolicy: "Update policy", failurePolicy: "Failure policy", jitter: "Jitter (minutes)", minimumAge: "Minimum release age (hours)", prerelease: "Allow prereleases", selectPlugins: "Select plugins", ruleSaved: "Daily rule and master switch saved", checkOnlyNote: "check_only checks and records only; it never updates plugins.", gateReady: "The automatic-update master switch is on; enabling the rule registers the daily job.", gateClosed: "The automatic-update master switch is off.", pluginDisabled: "The plugin is disabled, so the rule will not run.", policyCheckOnly: "Check only (check_only)", policyPatch: "Patch releases only (patch)", policyMinor: "Allow minor releases (minor)", policyStable: "Latest stable release (stable)", failureRollbackContinue: "Roll back and continue (rollback_continue)", failureRollbackStop: "Roll back and stop (rollback_stop)"
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
  catalogDiagnostics: []
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

// AstrBot 插件页常嵌在 iframe/沙箱里，裸 <a target="_blank"> 可能被拦截且无反馈。
// 统一走显式打开：先尝试新窗口，失败再顶层/本页跳转。
function openInternalRoute(route) {
  const target = String(route || "").trim();
  if (!target || !target.startsWith("#/")) return false;
  try {
    if (window.top && window.top !== window) {
      window.top.location.assign(target);
      return true;
    }
  } catch (error) {
    console.warn("Top-level route navigation blocked", error);
  }
  try {
    window.location.assign(target);
    return true;
  } catch (error) {
    console.warn("Unable to navigate to internal route", error);
    return false;
  }
}

function openExternalUrl(url) {
  const href = String(url || "").trim();
  if (!href || href === "#" || href.toLowerCase().startsWith("javascript:")) return false;
  try {
    const opened = window.open(href, "_blank", "noopener,noreferrer");
    if (opened) {
      try {
        opened.opener = null;
      } catch (error) {
        console.warn("Unable to clear opener for external link", error);
      }
      return true;
    }
  } catch (error) {
    console.warn("window.open blocked for external link", error);
  }
  try {
    if (window.top && window.top !== window) {
      window.top.location.assign(href);
      return true;
    }
  } catch (error) {
    console.warn("top-level navigation blocked for external link", error);
  }
  try {
    window.location.assign(href);
    return true;
  } catch (error) {
    console.warn("Unable to navigate to external link", error);
    return false;
  }
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

async function saveRule(event) {
  event.preventDefault();
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
    await Promise.all([loadConfig(), loadRule(), loadOverview()]);
  }
}

async function saveConfig(event) {
  event.preventDefault();
  const payload = {};
  for (const [key, field] of Object.entries(state.config?.schema || {})) {
    const input = event.currentTarget.elements.namedItem(key);
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
    await Promise.all([loadConfig(), loadOverview()]);
  } catch (error) { toast(`${t("saveFailed")}: ${error.message}`, true); }
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
  const enabled = Boolean(item.update_lifecycle?.operable) && Boolean(view?.update_available);
  const reason = item.update_lifecycle?.operable
    ? t("unavailableAction")
    : errorReason(item.update_lifecycle?.reason);
  const hint = enabled ? "" : `title="${escapeHtml(reason)}"`;
  return `<button type="button" data-catalog-update="${escapeHtml(item.plugin_id)}" data-plugin-name="${escapeHtml(item.display_name || item.plugin_id)}" ${enabled ? "" : "disabled"} ${hint}>${escapeHtml(t("update"))}</button>`;
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
  if (!pluginId || button.disabled || state.catalogBusy || state.catalogCheckBusy) return;
  if (!await confirmRecommendationAction("update", pluginName)) return;
  state.catalogBusy = pluginId;
  document.querySelectorAll("#catalog-list button, #catalog-list input[role='switch']").forEach((node) => { node.disabled = true; });
  const status = document.getElementById("recommendation-status");
  status.textContent = `${pluginName}：${t("updateRunning")}`;
  status.hidden = false;
  try {
    await apiPost("catalog/update", { plugin_id: pluginId, confirm: true });
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
  return `<span class="version-error">${escapeHtml(reason)} · ${escapeHtml(details.join(" · "))}</span>`;
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
  const repoUrl = String(selfUpdate.repo_url || "").trim();
  const installedRoute = "#/extension#installed";
  const strong = document.createElement("strong");
  strong.textContent = message;
  const link = document.createElement("a");
  link.href = repoUrl || "#";
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = t("goToRepository");
  link.dataset.externalUrl = repoUrl;
  link.dataset.internalRoute = installedRoute;
  if (!repoUrl) {
    link.setAttribute("aria-disabled", "true");
    link.classList.add("is-disabled");
  }
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
      ? `${actionButton(item, "update", "update", actions.update)}${lifecycleSwitch(item, actions)}`
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
  if (!action || !pluginId || button.disabled || state.recommendationBusy) return;
  const requiresConfirmation = ["install", "update", "disable"].includes(action);
  if (requiresConfirmation && !await confirmRecommendationAction(action, pluginName)) {
    await loadRecommendations();
    return;
  }
  setRecommendationBusy(action, pluginName);
  try {
    const payload = requiresConfirmation
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

async function refreshAll() {
  try { await Promise.all([loadOverview(), loadRecommendations(), loadConfig(), loadRule(), loadMirrors(), loadCatalog()]); }
  catch (error) { toast(`${t("loadFailed")}: ${error.message}`, true); }
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
  document.querySelectorAll("[data-tab]").forEach((button) => button.addEventListener("click", () => {
    document.querySelectorAll("[data-tab], .panel").forEach((node) => node.classList.remove("active"));
    button.classList.add("active");
    document.getElementById(button.dataset.tab).classList.add("active");
    if (button.dataset.tab === "recommendations") {
      autoCheckRecommendations().catch((error) => {
        console.warn("Automatic recommendation version check failed", error);
      });
    }
  }));
  // 自更新提示与推荐卡片里的仓库链接共用显式打开，避免 iframe 拦截 target=_blank。
  document.addEventListener("click", (event) => {
    const link = event.target.closest("a[data-external-url]");
    if (!link || !document.contains(link)) return;
    const route = link.dataset.internalRoute || "";
    if (route) {
      event.preventDefault();
      if (!openInternalRoute(route)) toast(t("operationFailed"), true);
      return;
    }
    const url = link.dataset.externalUrl || link.getAttribute("href") || "";
    if (!url || url === "#") {
      event.preventDefault();
      return;
    }
    event.preventDefault();
    if (!openExternalUrl(url)) toast(t("operationFailed"), true);
  });
  document.getElementById("config-form").addEventListener("submit", saveConfig);
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
  document.getElementById("refresh").addEventListener("click", refreshAll);
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
  await refreshAll();
}

init().catch(showStartupError);
