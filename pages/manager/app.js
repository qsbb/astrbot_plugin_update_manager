const messages = {
  "zh-CN": {
    title: "凝心溯溪-焕 · 更新管理", heading: "凝心溯溪-焕", subtitle: "安全、串行、可回滚的插件更新控制台",
    refresh: "刷新", overview: "总览", config: "配置", catalog: "目录", loading: "加载中…",
    startupFailed: "页面启动失败",
    capabilities: "运行时能力", configTitle: "配置读取与保存", tokenHint: "敏感 token 仅显示是否已配置，留空不会覆盖。",
    save: "保存", catalogTitle: "插件目录", catalogHint: "展示当前 AstrBot 可见插件及更新资格。",
    enabled: "插件启用", automatic: "自动更新", busy: "执行状态", idle: "空闲", running: "执行中", nextRun: "下次运行",
    available: "可用", unavailable: "不可用", configured: "已配置", notConfigured: "未配置", writeOnly: "仅写入，不回显",
    eligible: "可规划", blocked: "已阻断", empty: "暂无插件", saved: "配置已保存", loadFailed: "加载失败", saveFailed: "保存失败"
  },
  "en-US": {
    title: "Update Manager", heading: "Update Manager", subtitle: "Safe, serial and rollback-ready plugin updates",
    refresh: "Refresh", overview: "Overview", config: "Configuration", catalog: "Catalog", loading: "Loading…",
    startupFailed: "Page startup failed",
    capabilities: "Runtime capabilities", configTitle: "Read and save configuration", tokenHint: "Sensitive tokens are write-only. Empty values keep the current secret.",
    save: "Save", catalogTitle: "Plugin catalog", catalogHint: "AstrBot plugins visible to the current runtime and update eligibility.",
    enabled: "Plugin enabled", automatic: "Automatic updates", busy: "Execution", idle: "Idle", running: "Running", nextRun: "Next run",
    available: "Available", unavailable: "Unavailable", configured: "Configured", notConfigured: "Not configured", writeOnly: "Write-only; never returned",
    eligible: "Eligible", blocked: "Blocked", empty: "No plugins", saved: "Configuration saved", loadFailed: "Load failed", saveFailed: "Save failed"
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
  config: null
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
  document.getElementById("catalog-list").innerHTML = items.length ? items.map((item) => `<article class="catalog-item"><div><strong>${escapeHtml(item.plugin_id)}</strong><span>${escapeHtml(item.version || "—")} · ${item.activated ? "active" : "inactive"}</span></div><span class="pill ${item.eligible ? "ok" : "off"}">${item.eligible ? t("eligible") : `${t("blocked")}: ${escapeHtml((item.reasons || []).join(", "))}`}</span></article>`).join("") : `<p>${t("empty")}</p>`;
}

async function refreshAll() {
  try { await Promise.all([loadOverview(), loadConfig(), loadCatalog()]); }
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
