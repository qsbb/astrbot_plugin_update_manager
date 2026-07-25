const messages = {
  "zh-CN": {
    title: "凝心溯溪-核 · 更新管理", heading: "凝心溯溪-核", subtitle: "安全、串行、可回滚的插件更新控制台",
    refresh: "刷新", overview: "总览", recommendations: "系列推荐", config: "配置", catalog: "目录", loading: "加载中…",
    startupFailed: "页面启动失败",
    capabilities: "运行时能力", configTitle: "配置读取与保存", tokenHint: "敏感 token 仅显示是否已配置，留空不会覆盖。",
    save: "保存", catalogTitle: "插件目录", catalogHint: "合并展示运行时插件与已安装元数据；未加载插件不可更新。",
    recommendationsTitle: "凝心溯溪系列推荐", recommendationsHint: "官方安装会直接加载；更新和启用由 AstrBot 内部热重载，页面不会额外重复重载。核禁止自更新和自停用。",
    checkLatest: "检查最新版本", checkingLatest: "正在检查…", latestChecked: "版本检查完成", currentVersion: "当前", latestVersion: "最新", checkFailed: "检查失败",
    updateAvailable: "有新版本", upToDate: "已是最新版", localNewer: "本地版本更新", notInstalled: "未安装", unknown: "未知",
    selfUpdateNotice: "更新管理器有新版本：当前 {current}，最新 {latest}。自身更新已禁用，请前往仓库更新。", goToRepository: "前往仓库更新",
    install: "安装", installed: "已安装", update: "更新", enable: "启用", disable: "停用", operationDone: "操作完成", operationFailed: "操作失败", unavailableAction: "仅检测到新版本且运行时支持时可更新", catalogUnavailable: "此插件不可启停", errorUnknown: "请求失败，请稍后重试", error404: "远端未发布 Release 或标签", errorNetwork: "网络连接失败", errorTimeout: "请求超时", errorRateLimit: "GitHub 请求受限，请稍后重试", errorCode: "错误代码", errorHttpStatus: "HTTP 状态", errorRepository: "仓库", errorBranch: "分支",
    confirmTitle: "确认插件操作", confirmAction: "确认操作", cancel: "取消", confirmPrompt: "确定要{action}“{name}”吗？", installRunning: "正在安装…", updateRunning: "正在更新…", enableRunning: "正在启用…", disableRunning: "正在停用…",
    enabled: "插件启用", automatic: "自动更新", busy: "执行状态", idle: "空闲", running: "执行中", nextRun: "下次运行",
    available: "可用", unavailable: "不可用", configured: "已配置", notConfigured: "未配置", writeOnly: "仅写入，不回显",
    eligible: "可规划", blocked: "已阻断", loaded: "已加载", notLoaded: "未加载", active: "已启用", inactive: "未启用",
    empty: "暂无插件", emptyDiagnostics: "目录诊断", saved: "配置已保存", loadFailed: "加载失败", saveFailed: "保存失败",
    ruleTitle: "每日自动更新", saveRule: "保存规则", ruleEnabled: "启用每日规则", autoUpdateGate: "允许自动更新总闸", autoUpdateGateHint: "关闭时任何每日规则都不会执行自动更新。", ruleTime: "运行时间", ruleTimezone: "时区", rulePolicy: "更新策略", failurePolicy: "失败策略", jitter: "抖动（分钟）", minimumAge: "最小发布年龄（小时）", prerelease: "允许预发行版本", selectPlugins: "选择插件", ruleSaved: "每日规则与总闸已保存", checkOnlyNote: "check_only 仅检查并记录，绝不会更新插件。", gateReady: "总闸已开启，启用规则后将注册每日任务。", gateClosed: "自动更新总闸已关闭。", pluginDisabled: "插件当前未启用，规则不会执行。", policyCheckOnly: "仅检查（check_only）", policyPatch: "仅补丁版本（patch）", policyMinor: "允许次版本（minor）", policyStable: "最新稳定版（stable）", failureRollbackContinue: "回滚后继续（rollback_continue）", failureRollbackStop: "回滚并停止（rollback_stop）"
  },
  "en-US": {
    title: "Update Manager", heading: "Update Manager", subtitle: "Safe, serial and rollback-ready plugin updates",
    refresh: "Refresh", overview: "Overview", recommendations: "Recommendations", config: "Configuration", catalog: "Catalog", loading: "Loading…",
    startupFailed: "Page startup failed",
    capabilities: "Runtime capabilities", configTitle: "Read and save configuration", tokenHint: "Sensitive tokens are write-only. Empty values keep the current secret.",
    save: "Save", catalogTitle: "Plugin catalog", catalogHint: "Runtime plugins and installed metadata are always merged; unloaded plugins cannot be updated.",
    recommendationsTitle: "Ningxin Suxi series", recommendationsHint: "Official installation loads directly. Update and enable use AstrBot's internal hot reload; this page never triggers a duplicate reload. Core cannot update or disable itself.",
    checkLatest: "Check latest versions", checkingLatest: "Checking…", latestChecked: "Version check completed", currentVersion: "Current", latestVersion: "Latest", checkFailed: "Check failed",
    updateAvailable: "New version available", upToDate: "Up to date", localNewer: "Local version is newer", notInstalled: "Not installed", unknown: "Unknown",
    selfUpdateNotice: "A newer update manager is available: current {current}, latest {latest}. Self-update is disabled; update it from the repository.", goToRepository: "Open repository",
    install: "Install", installed: "Installed", update: "Update", enable: "Enable", disable: "Disable", operationDone: "Operation completed", operationFailed: "Operation failed", unavailableAction: "Update is enabled only when a newer version is detected and supported", catalogUnavailable: "This plugin cannot be toggled", errorUnknown: "Request failed; try again later", error404: "No release or tag was found", errorNetwork: "Network connection failed", errorTimeout: "Request timed out", errorRateLimit: "GitHub request limit reached; try again later", errorCode: "Error code", errorHttpStatus: "HTTP status", errorRepository: "Repository", errorBranch: "Branch",
    confirmTitle: "Confirm plugin action", confirmAction: "Confirm", cancel: "Cancel", confirmPrompt: "Are you sure you want to {action} “{name}”?", installRunning: "Installing…", updateRunning: "Updating…", enableRunning: "Enabling…", disableRunning: "Disabling…",
    enabled: "Plugin enabled", automatic: "Automatic updates", busy: "Execution", idle: "Idle", running: "Running", nextRun: "Next run",
    available: "Available", unavailable: "Unavailable", configured: "Configured", notConfigured: "Not configured", writeOnly: "Write-only; never returned",
    eligible: "Eligible", blocked: "Blocked", loaded: "Loaded", notLoaded: "Not loaded", active: "Active", inactive: "Inactive",
    empty: "No plugins", emptyDiagnostics: "Catalog diagnostics", saved: "Configuration saved", loadFailed: "Load failed", saveFailed: "Save failed",
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
  recommendationBusy: null
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
  if (value === "REGISTRY_TIMEOUT") return t("errorTimeout");
  if (value === "REGISTRY_NETWORK_ERROR") return t("errorNetwork");
  if (["REGISTRY_HTTP_403", "REGISTRY_HTTP_429"].includes(value)) return t("errorRateLimit");
  const known = {
    CONFIRMATION_REQUIRED: "停用前必须明确确认",
    SELF_LIFECYCLE_BLOCKED: "更新管理器不能操作自身启停",
    RESERVED_PLUGIN: "AstrBot 保留插件不可操作",
    PLUGIN_NOT_LOADED: "插件尚未加载",
    PLUGIN_NOT_FOUND: "未找到该插件",
    PLUGIN_STATE_UNCHANGED: "插件已经处于目标状态",
    LIFECYCLE_CAPABILITY_UNAVAILABLE: "当前 AstrBot 不支持此启停操作",
    ACTIVATION_RESULT_MISMATCH: "操作后插件状态校验失败"
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

function catalogSwitch(item) {
  const action = item.activated ? "disable" : "enable";
  const operable = Boolean(item.lifecycle?.operable);
  const reason = operable ? "" : (item.lifecycle?.reason || t("catalogUnavailable"));
  return `<label class="lifecycle-switch" title="${escapeHtml(reason)}"><span class="sr-only">${escapeHtml(`${item.name || item.plugin_id} ${t(action)}`)}</span><input type="checkbox" role="switch" aria-checked="${item.activated ? "true" : "false"}" data-catalog-action="${action}" data-plugin-id="${escapeHtml(item.plugin_id)}" data-plugin-name="${escapeHtml(item.name || item.plugin_id)}" ${item.activated ? "checked" : ""} ${operable ? "" : "disabled"}/><span class="switch-track" aria-hidden="true"><span class="switch-thumb"></span></span><span class="switch-label">${escapeHtml(t(action))}</span></label>`;
}

async function loadCatalog() {
  const data = await apiGet("catalog");
  const items = data.items || [];
  const diagnostics = data.diagnostics?.messages || [];
  document.getElementById("catalog-list").innerHTML = items.length ? items.map((item) => `<article class="catalog-item"><div><strong>${escapeHtml(item.display_name || item.plugin_id)}</strong><code>${escapeHtml(item.plugin_id)}</code><span>${escapeHtml(item.version || "—")} · ${item.loaded ? t("loaded") : t("notLoaded")} · ${item.activated ? t("active") : t("inactive")}</span></div><div class="catalog-actions"><span class="pill ${item.eligible ? "ok" : "off"}">${item.eligible ? t("eligible") : `${t("blocked")}: ${escapeHtml((item.reasons || []).join(", "))}`}</span>${catalogSwitch(item)}</div></article>`).join("") : `<div class="catalog-empty"><strong>${t("empty")}</strong><span>${escapeHtml(t("emptyDiagnostics"))}: ${escapeHtml(diagnostics.join(", ") || "NO_DIAGNOSTIC")}</span></div>`;
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

function recommendationError(item) {
  if (item.version_status !== "check_failed") return "";
  const context = item.error_context || {};
  const details = [
    `${t("errorCode")}: ${item.error || "UNKNOWN"}`,
    context.http_status ? `${t("errorHttpStatus")}: ${context.http_status}` : "",
    context.repo ? `${t("errorRepository")}: ${context.repo}` : "",
    context.default_branch ? `${t("errorBranch")}: ${context.default_branch}` : ""
  ].filter(Boolean);
  const reason = errorReason(item.error || item.error_detail);
  return `<span class="version-error">${escapeHtml(reason)} · ${escapeHtml(details.join(" · "))}</span>`;
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
  notice.innerHTML = `<strong>${escapeHtml(message)}</strong><a href="${escapeHtml(selfUpdate.repo_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(t("goToRepository"))}</a>`;
  notice.hidden = false;
}

async function loadRecommendations(force = false) {
  const data = force ? await apiPost("recommendations/check-latest", {}) : await apiGet("recommendations");
  const items = data.items || [];
  renderSelfUpdateNotice(data.self_update);
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
    return `<article class="recommendation-item"><div class="recommendation-copy"><span class="series-key">${escapeHtml(item.key)}</span><div><strong>${escapeHtml(item.name)}</strong><p class="recommendation-description" lang="zh-CN">${escapeHtml(item.description_zh || "")}</p><code>${escapeHtml(item.plugin_id)}</code><span class="version-line">${versionStatusBadge(item)}<span>${versionDetail} · ${item.installed ? t("installed") : t("notLoaded")} · ${item.activated ? t("active") : t("inactive")}</span></span>${recommendationError(item)}<a href="${escapeHtml(item.repo_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.repo_url)}</a></div></div><div class="recommendation-actions">${install}${lifecycle}</div></article>`;
  }).join("");
}

function confirmRecommendationAction(action, pluginName) {
  const dialog = document.getElementById("confirmation-dialog");
  const message = t("confirmPrompt")
    .replace("{action}", t(action))
    .replace("{name}", pluginName);
  document.getElementById("confirmation-message").textContent = message;
  return new Promise((resolve) => {
    dialog.addEventListener("close", () => resolve(dialog.returnValue === "confirm"), { once: true });
    dialog.showModal();
  });
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
  try { await Promise.all([loadOverview(), loadRecommendations(), loadConfig(), loadRule(), loadCatalog()]); }
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
  }));
  document.getElementById("config-form").addEventListener("submit", saveConfig);
  document.getElementById("rule-form").addEventListener("submit", saveRule);
  document.getElementById("rule-policy").addEventListener("change", (event) => {
    document.getElementById("check-only-note").hidden = event.target.value !== "check_only";
  });
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
  document.getElementById("check-latest").addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    button.textContent = t("checkingLatest");
    try {
      await loadRecommendations(true);
      toast(t("latestChecked"));
    } catch (error) {
      toast(`${t("loadFailed")}: ${error.message}`, true);
    } finally {
      button.disabled = false;
      button.textContent = t("checkLatest");
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
