const messages = {
  "zh-CN": {
    title: "凝心溯溪-核 · 更新管理", heading: "凝心溯溪-核", subtitle: "安全、串行、可回滚的插件更新控制台",
    refresh: "刷新", overview: "总览", recommendations: "系列推荐", config: "配置", catalog: "目录", loading: "加载中…",
    startupFailed: "页面启动失败",
    capabilities: "运行时能力", configTitle: "配置读取与保存", tokenHint: "敏感 token 仅显示是否已配置，留空不会覆盖。",
    save: "保存", catalogTitle: "插件目录", catalogHint: "合并展示运行时插件与已安装元数据；未加载插件不可更新。",
    recommendationsTitle: "凝心溯溪系列推荐", recommendationsHint: "仅允许操作固定可信清单；核禁止自更新和自停用。",
    install: "安装", installed: "已安装", update: "更新", enable: "启用", disable: "停用", operationDone: "操作完成", operationFailed: "操作失败", unavailableAction: "当前 AstrBot 不支持此操作",
    confirmTitle: "确认插件操作", confirmAction: "确认操作", cancel: "取消", confirmPrompt: "确定要{action}“{name}”吗？", installRunning: "正在安装…", updateRunning: "正在更新…", enableRunning: "正在启用…", disableRunning: "正在停用…",
    enabled: "插件启用", automatic: "自动更新", busy: "执行状态", idle: "空闲", running: "执行中", nextRun: "下次运行",
    available: "可用", unavailable: "不可用", configured: "已配置", notConfigured: "未配置", writeOnly: "仅写入，不回显",
    eligible: "可规划", blocked: "已阻断", loaded: "已加载", notLoaded: "未加载", active: "已启用", inactive: "未启用",
    empty: "暂无插件", emptyDiagnostics: "目录诊断", saved: "配置已保存", loadFailed: "加载失败", saveFailed: "保存失败"
  },
  "en-US": {
    title: "Update Manager", heading: "Update Manager", subtitle: "Safe, serial and rollback-ready plugin updates",
    refresh: "Refresh", overview: "Overview", recommendations: "Recommendations", config: "Configuration", catalog: "Catalog", loading: "Loading…",
    startupFailed: "Page startup failed",
    capabilities: "Runtime capabilities", configTitle: "Read and save configuration", tokenHint: "Sensitive tokens are write-only. Empty values keep the current secret.",
    save: "Save", catalogTitle: "Plugin catalog", catalogHint: "Runtime plugins and installed metadata are always merged; unloaded plugins cannot be updated.",
    recommendationsTitle: "Ningxin Suxi series", recommendationsHint: "Only the fixed trusted list can be managed. Core cannot update or disable itself.",
    install: "Install", installed: "Installed", update: "Update", enable: "Enable", disable: "Disable", operationDone: "Operation completed", operationFailed: "Operation failed", unavailableAction: "This action is unavailable on the current AstrBot runtime",
    confirmTitle: "Confirm plugin action", confirmAction: "Confirm", cancel: "Cancel", confirmPrompt: "Are you sure you want to {action} “{name}”?", installRunning: "Installing…", updateRunning: "Updating…", enableRunning: "Enabling…", disableRunning: "Disabling…",
    enabled: "Plugin enabled", automatic: "Automatic updates", busy: "Execution", idle: "Idle", running: "Running", nextRun: "Next run",
    available: "Available", unavailable: "Unavailable", configured: "Configured", notConfigured: "Not configured", writeOnly: "Write-only; never returned",
    eligible: "Eligible", blocked: "Blocked", loaded: "Loaded", notLoaded: "Not loaded", active: "Active", inactive: "Inactive",
    empty: "No plugins", emptyDiagnostics: "Catalog diagnostics", saved: "Configuration saved", loadFailed: "Load failed", saveFailed: "Save failed"
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

function parseJsonResponse(value) {
  const data = typeof value === "string" ? JSON.parse(value) : value;
  if (data?.success === false) {
    const detail = data.detail || data.error || "API_ERROR";
    throw new Error(detail);
  }
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
  document.getElementById("capabilities").innerHTML = Object.entries(data.runtime?.capabilities || {}).map(([key, value]) =>
    `<div><code>${escapeHtml(key)}</code><span class="pill ${value ? "ok" : "off"}">${value ? t("available") : t("unavailable")}</span></div>`
  ).join("");
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

async function loadCatalog() {
  const data = await apiGet("catalog");
  const items = data.items || [];
  const diagnostics = data.diagnostics?.messages || [];
  document.getElementById("catalog-list").innerHTML = items.length ? items.map((item) => `<article class="catalog-item"><div><strong>${escapeHtml(item.plugin_id)}</strong><span>${escapeHtml(item.version || "—")} · ${item.loaded ? t("loaded") : t("notLoaded")} · ${item.activated ? t("active") : t("inactive")}</span></div><span class="pill ${item.eligible ? "ok" : "off"}">${item.eligible ? t("eligible") : `${t("blocked")}: ${escapeHtml((item.reasons || []).join(", "))}`}</span></article>`).join("") : `<div class="catalog-empty"><strong>${t("empty")}</strong><span>${escapeHtml(t("emptyDiagnostics"))}: ${escapeHtml(diagnostics.join(", ") || "NO_DIAGNOSTIC")}</span></div>`;
}

function actionButton(item, action, label, enabled) {
  const disabled = enabled ? "" : "disabled";
  const hint = enabled ? "" : `title="${escapeHtml(t("unavailableAction"))}"`;
  return `<button type="button" data-recommendation-action="${action}" data-plugin-id="${escapeHtml(item.plugin_id)}" data-plugin-name="${escapeHtml(item.name)}" ${disabled} ${hint}>${escapeHtml(t(label))}</button>`;
}

async function loadRecommendations() {
  const data = await apiGet("recommendations");
  const items = data.items || [];
  const list = document.getElementById("recommendations-list");
  list.innerHTML = items.map((item) => {
    const actions = item.actions || {};
    const install = item.installed
      ? `<button type="button" disabled>${escapeHtml(t("installed"))}</button>`
      : actionButton(item, "install", "install", actions.install);
    const lifecycle = item.installed
      ? `${actionButton(item, "update", "update", actions.update)}${item.activated ? actionButton(item, "disable", "disable", actions.disable) : actionButton(item, "enable", "enable", actions.enable)}`
      : "";
    return `<article class="recommendation-item"><div class="recommendation-copy"><span class="series-key">${escapeHtml(item.key)}</span><div><strong>${escapeHtml(item.name)}</strong><p class="recommendation-description" lang="zh-CN">${escapeHtml(item.description_zh || "")}</p><code>${escapeHtml(item.plugin_id)}</code><span>${escapeHtml(item.version || "—")} · ${item.installed ? t("installed") : t("notLoaded")} · ${item.activated ? t("active") : t("inactive")}</span><a href="${escapeHtml(item.repo_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.repo_url)}</a></div></div><div class="recommendation-actions">${install}${lifecycle}</div></article>`;
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
  document.querySelectorAll("#recommendations-list button").forEach((item) => { item.disabled = true; });
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
  if (requiresConfirmation && !await confirmRecommendationAction(action, pluginName)) return;
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

async function refreshAll() {
  try { await Promise.all([loadOverview(), loadRecommendations(), loadConfig(), loadCatalog()]); }
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
  document.getElementById("recommendations-list").addEventListener("click", (event) => {
    const button = event.target.closest("[data-recommendation-action]");
    if (button) runRecommendationAction(button);
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
