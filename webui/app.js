const API_PREFIX = "/api";
let state = {
  authenticated: false,
  configured: false,
  session: null,
  modules: [],
  providers: [],
  routes: null,
  control: null,
  controlSchema: null,
  controlSnapshot: null,
  controlTab: "fields",
  panelsList: null,
  panelData: null,
  selectedPanel: "",
  selectedControlPlugin: "",
  logs: [],
  logMembers: [],
  logLevel: "",
  logAuto: false,
  logTimer: null,
  updatesCheck: null,
  transactions: null,
  settingsData: null,
  filter: "all",
  query: "",
  view: "modules",
  selectedModule: "",
};
const app = document.getElementById("app");

function parse(value) { return typeof value === "string" ? JSON.parse(value) : value; }
function esc(value) { return String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c])); }
async function get(name) { const response = await fetch(`${API_PREFIX}/${name}`, { credentials: "same-origin" }); const data = parse(await response.json()); if (!response.ok || data?.success === false) throw new Error(data.error || "请求失败"); return data; }
async function post(name, payload) { const response = await fetch(`${API_PREFIX}/${name}`, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload || {}) }); const data = parse(await response.json()); if (!response.ok || data?.success === false) throw new Error(data.error || "请求失败"); return data; }
function showToast(message, error = false) { const node = document.createElement("div"); node.className = `toast${error ? " error" : ""}`; node.textContent = message; document.body.appendChild(node); setTimeout(() => node.remove(), 2200); }
function loginView(message = "") {
  app.innerHTML = `<section class="login"><div class="login-side"><div class="brand"><span class="brand-mark">核</span><div><strong>凝心溯溪</strong><small>模块运营中心</small></div></div><div class="login-copy"><h1>把每个模块，放进同一张工作台。</h1><p>管理员账户由“核” Page 创建和维护。WebUI 只负责安全登录，不提供注册入口。</p></div><small>Dashboard Page 二次认证 · 管理员会话受服务端控制</small></div><div class="login-main"><form class="login-card" id="login-form"><h2>登录模块运营中心</h2><p>${state.configured ? "请输入在“核” Page 中配置的管理员账户。" : "当前还没有可用管理员，请先回到“核” Page 设置管理员。"}</p><div class="field"><label for="username">管理员账户</label><input id="username" name="username" autocomplete="username" required ${state.configured ? "" : "disabled"}></div><div class="field"><label for="password">密码</label><input id="password" name="password" type="password" autocomplete="current-password" required ${state.configured ? "" : "disabled"}></div><div class="error" role="alert">${esc(message)}</div><button class="btn primary" type="submit" ${state.configured ? "" : "disabled"}>安全登录</button><div class="note">WebUI 不在浏览器保存账户、密码或会话令牌。请在“核” Page 管理多个管理员、角色和禁用状态。</div></form></div></section>`;
  document.getElementById("login-form")?.addEventListener("submit", async event => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    try { const result = await post("login", { username: data.get("username"), password: data.get("password") }); state.authenticated = true; state.session = result.session; await loadDashboard(); }
    catch (error) { loginView(error.message); }
  });
}
function filtered() { return state.modules.filter(item => (state.filter === "all" || (state.filter === "normal" && item.status === "normal") || (state.filter === "offline" && item.status !== "normal")) && (!state.query || `${item.display_name} ${item.plugin_id}`.toLowerCase().includes(state.query.toLowerCase()))); }
function color(id) { const colors = ["#3b82b9", "#7653a6", "#cb4d48", "#db7d27", "#2c927c", "#3975aa", "#414a55", "#be385c"]; let sum = 0; for (const char of id) sum += char.charCodeAt(0); return colors[sum % colors.length]; }
function moduleRows() {
  const list = filtered();
  return list.length ? list.map(item => `<tr><td><button class="module module-button" data-module="${esc(item.plugin_id)}"><span class="mark" style="--color:${color(item.plugin_id)}">${esc(item.display_name.slice(-1))}</span><span><b>${esc(item.display_name)}</b><small>${esc(item.plugin_id)}</small></span></button></td><td><span class="status ${item.status === "normal" ? "" : "off"}">${item.status === "normal" ? "正常" : "已停用/未加载"}</span></td><td><span class="pill">${item.contracts} 条契约</span></td><td><code>v${esc(item.version || "未知")}</code></td><td>${item.version_status === "not_checked" ? `<span class="pill">未检查</span>` : item.update_available ? `<span class="pill managed">有更新</span>` : `<span class="pill native">最新</span>`}</td><td><button class="link" data-diagnostic="${esc(item.plugin_id)}">诊断</button></td></tr>`).join("") : `<tr><td colspan="6" style="padding:40px;text-align:center;color:#667085">没有匹配的可信模块。</td></tr>`;
}
function selectedDetail() {
  const item = state.modules.find(value => value.plugin_id === state.selectedModule);
  if (!item) return "";
  return `<section class="workspace module-detail"><div class="workspace-head"><div class="section-title"><h2>${esc(item.display_name)}</h2><button class="btn" id="close-module-detail">返回列表</button></div><p class="detail-copy">${esc(item.plugin_id)} · v${esc(item.version || "未知")} · ${item.status === "normal" ? "运行正常" : "需要关注"}</p><div class="detail-grid"><div><span>加载</span><strong>${item.loaded ? "是" : "否"}</strong></div><div><span>激活</span><strong>${item.activated ? "是" : "否"}</strong></div><div><span>契约</span><strong>${item.contracts}</strong></div><div><span>管理来源</span><strong>可信登记</strong></div></div><p class="detail-note">字段接管、专属面板与生命周期操作在「系列接管」管理台完成；此处展示运行状态与诊断入口。</p><button class="btn primary" data-control-open="${esc(item.plugin_id)}">打开管理台</button></div></section>`;
}
function modulesView() {
  const normal = state.modules.filter(x => x.status === "normal").length;
  const offline = state.modules.length - normal;
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 生产状态</div><h1>模块运营中心</h1><p>统一查看可信自有模块的运行状态、版本、契约与诊断入口。</p></div><div class="actions"><button class="btn" id="export">导出摘要</button><button class="btn primary" id="check">检查更新</button></div></div><div class="stats"><div class="stat"><label>可信模块</label><strong>${state.modules.length}</strong><small>来自可信登记</small></div><div class="stat"><label>运行正常</label><strong>${normal}</strong><small>核心链路可用</small></div><div class="stat"><label>需关注</label><strong>${offline}</strong><small>非阻断状态</small></div><div class="stat"><label>契约发现</label><strong>已接入</strong><small>版本化能力</small></div><div class="stat"><label>管理边界</label><strong>安全</strong><small>高危操作仍需确认</small></div></div><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>系列模块</h2><span>${filtered().length} 个匹配当前视图</span></div><div class="filters"><label class="search">⌕<input id="query" placeholder="搜索模块名称或 ID" value="${esc(state.query)}"></label><div class="seg"><button data-filter="all" class="${state.filter === "all" ? "active" : ""}">全部</button><button data-filter="normal" class="${state.filter === "normal" ? "active" : ""}">正常</button><button data-filter="offline" class="${state.filter === "offline" ? "active" : ""}">需关注</button></div><span class="grow"></span><button class="btn" id="reload">刷新状态</button></div></div><div class="table-wrap"><table class="table"><thead><tr><th>模块</th><th>运行状态</th><th>契约</th><th>版本</th><th>更新</th><th>操作</th></tr></thead><tbody>${moduleRows()}</tbody></table></div><div class="footer"><span>只纳管可信登记中的凝心溯溪系列插件。</span><span>${state.modules.length} 个模块</span></div></section>${selectedDetail()}`;
}
function diagnosticsView() {
  const rows = state.providers.length ? state.providers.map(item => `<tr><td>${esc(item.display_name)}</td><td><code>${esc(item.plugin_id)}</code></td><td><span class="status">${esc(item.status)}</span></td></tr>`).join("") : `<tr><td colspan="3" class="empty-cell">暂无诊断提供方</td></tr>`;
  const members = (state.logMembers || []).map(item => `<span class="pill">${esc(item.display_name || item.plugin_id)} · ${esc(item.status)} · seq ${esc(item.next_seq ?? 0)}${item.gap ? " · 有断层" : ""}</span>`).join(" ");
  const events = (state.logs || []).filter(item => !state.logLevel || item.level === state.logLevel).slice(-400).reverse();
  const logRows = events.map(item => `<tr class="log-${esc(item.level.toLowerCase())}"><td><code>${esc(item.timestamp || "")}</code></td><td>${esc(item.plugin_name || item.plugin_id)}</td><td><span class="pill ${item.level === "ERROR" ? "managed" : item.level === "WARNING" ? "warn" : ""}">${esc(item.level)}</span></td><td><code>${esc(item.code || "-")}</code></td><td>${esc(item.summary || "")}</td><td class="log-details">${esc(item.details && Object.keys(item.details).length ? JSON.stringify(item.details) : "")}</td></tr>`).join("") || `<tr><td colspan="6" class="empty-cell">暂无日志，点击「加载日志」拉取。</td></tr>`;
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 可观测性</div><h1>运行诊断</h1><p>按 series.diagnostics 契约逐模块读取日志：游标续读、级别过滤、断层提示。</p></div><div class="actions"><label class="switch"><input type="checkbox" id="log-auto" ${state.logAuto ? "checked" : ""} /><span>5 秒自动刷新</span></label><button class="btn" id="refresh-logs">加载日志</button><button class="btn danger" id="clear-logs" ${state.session?.role === "owner" || state.session?.role === "admin" ? "" : "disabled"}>清空日志</button></div></div><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>诊断提供方</h2><span>${state.providers.length} 个</span></div></div><div class="table-wrap"><table class="table"><thead><tr><th>模块</th><th>插件 ID</th><th>状态</th></tr></thead><tbody>${rows}</tbody></table></div></section><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>诊断日志</h2><span>${members || "未加载"}</span></div><div class="filters"><select id="log-level" class="select"><option value="">全部级别</option>${["ERROR", "WARNING", "INFO", "DEBUG"].map(level => `<option value="${level}" ${state.logLevel === level ? "selected" : ""}>${level}</option>`).join("")}</select></div></div><div class="table-wrap log-table"><table class="table"><thead><tr><th>时间</th><th>模块</th><th>级别</th><th>代码</th><th>摘要</th><th>详情</th></tr></thead><tbody>${logRows}</tbody></table></div></section>`;
}
function updatesView() {
  const checkedAt = state.modules.find(item => item.versions_checked_at)?.versions_checked_at || "";
  const rows = state.modules.map(item => {
    const status = item.version_status === "not_checked" ? `<span class="pill">未检查</span>` : item.update_available ? `<span class="pill managed">有更新</span>` : item.version_status === "up_to_date" ? `<span class="pill native">已是最新</span>` : `<span class="pill">${esc(item.version_status)}</span>`;
    const self = item.plugin_id === "astrbot_plugin_update_manager";
    return `<tr><td>${esc(item.display_name)}</td><td><code>v${esc(item.version || "?")}</code></td><td><code>${item.latest_version ? "v" + esc(item.latest_version) : "—"}</code></td><td>${status}</td><td>${self ? `<span class="pill">核自更新走 Page</span>` : `<button class="link" data-control-open="${esc(item.plugin_id)}">前往接管台</button>`}</td></tr>`;
  }).join("");
  const txRows = (state.transactions || []).map(tx => `<tr><td><code>${esc(String(tx.tx_id).slice(0, 12))}…</code></td><td>${esc(tx.plugin_id)}</td><td><code>v${esc(tx.from_version || "?")} → v${esc(tx.to_version || "?")}</code></td><td>${esc(tx.started_at || "")}</td><td><button class="link" data-rollback="${esc(tx.tx_id)}">回滚</button></td></tr>`).join("") || `<tr><td colspan="5" class="empty-cell">暂无可回滚的更新事务（每次更新完成都会留一个恢复点）</td></tr>`;
  const isOwner = state.session?.role === "owner";
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 生命周期</div><h1>更新与回滚</h1><p>检查更新对比 GitHub 最新版本；回滚按事务恢复点恢复更新前版本（仅 owner）。</p></div><div class="actions"><button class="btn" id="reload-transactions">刷新恢复点</button><button class="btn primary" id="check-updates" ${state.session?.role === "owner" || state.session?.role === "admin" ? "" : "disabled"}>检查更新</button></div></div><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>版本状态</h2><span>${checkedAt ? `上次检查：${esc(checkedAt)}` : "尚未检查"}</span></div></div><div class="table-wrap"><table class="table"><thead><tr><th>模块</th><th>当前版本</th><th>最新版本</th><th>状态</th><th>操作</th></tr></thead><tbody>${rows}</tbody></table></div></section><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>回滚恢复点</h2><span>来自核事务记录，只接受核生成的备份</span></div></div><div class="table-wrap"><table class="table"><thead><tr><th>事务</th><th>模块</th><th>版本变化</th><th>时间</th><th>操作</th></tr></thead><tbody>${txRows}</tbody></table></div><p class="form-hint">${isOwner ? "回滚会覆盖当前代码并热重载，执行前需确认。" : "回滚仅 owner 可执行。"}</p></section>`;
}
function settingsView() {
  const s = state.settingsData?.settings || {};
  const route = s.model_routing || {};
  const canWrite = state.session?.role === "owner" || state.session?.role === "admin";
  const labels = [["conversation", "对话 / LLM"], ["embedding", "向量 / Embedding"], ["vision", "识图 / 视觉"], ["stt", "语音识别 / STT"], ["tts", "语音合成 / TTS"]];
  const routeRows = labels.map(([kind, label]) => { const item = route[kind] || {}; return `<tr><td><b>${label}</b></td>${[["provider_id", "Provider ID"], ["model", "模型名"], ["voice", "音色（TTS/STT）"]].map(([field, ph]) => `<td><input type="text" list="provider-options" data-setting-route="${kind}.${field}" value="${esc(item[field] || "")}" placeholder="${ph}" ${canWrite ? "" : "disabled"} /></td>`).join("")}</tr>`; }).join("");
  const resolvedRows = Object.entries(state.routes?.routes || {}).map(([kind, item]) => { const label = (labels.find(entry => entry[0] === kind) || [kind, kind])[1]; return `<tr><td>${esc(label)}</td><td><code>${esc(item.provider_id || "未配置")}</code></td><td>${esc(item.model || "自动")}</td><td>${esc(item.source || "unavailable")}</td><td><span class="status ${item.available ? "" : "off"}">${item.available ? "可用" : "不可用"}</span></td></tr>`; }).join("");
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 模型策略</div><h1>全局设置</h1><p>统一模型路由与运行项可直接在此编辑；密钥类配置仍在核 Page 维护。WebUI 连接项保存后需重启生效。</p></div><div class="actions"><button class="btn" id="settings-reload">重读</button><button class="btn primary" id="save-settings" ${canWrite ? "" : "disabled"}>保存设置</button></div></div><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>统一模型路由</h2><span>留空 = 回退 AstrBot 原生 Provider</span></div></div><datalist id="provider-options">${(state.settingsData?.providers || []).map(item => `<option value="${esc(item.provider_id)}">`).join("")}</datalist><div class="table-wrap"><table class="table"><thead><tr><th>能力</th><th>Provider</th><th>模型</th><th>音色</th></tr></thead><tbody>${routeRows}</tbody></table></div></section><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>运行项</h2><span>保存后即时生效</span></div></div><div class="form-grid"><div class="form-row"><label><code>auto_update_enabled</code><small>bool · 到期自动检查并更新系列插件</small></label><div class="form-input"><label class="switch"><input type="checkbox" id="setting-auto-update" ${s.auto_update_enabled ? "checked" : ""} ${canWrite ? "" : "disabled"} /><span>启用自动更新</span></label></div><div class="form-meta"></div></div><div class="form-row"><label><code>log_level</code><small>str · 核自身日志级别</small></label><div class="form-input"><select id="setting-log-level" class="select" ${canWrite ? "" : "disabled"}>${["DEBUG", "INFO", "WARNING", "ERROR"].map(level => `<option value="${level}" ${String(s.log_level || "INFO").toUpperCase() === level ? "selected" : ""}>${level}</option>`).join("")}</select></div><div class="form-meta"></div></div><div class="form-row"><label><code>webui_host</code><small>str · WebUI 绑定地址（重启生效）</small></label><div class="form-input"><input type="text" id="setting-webui-host" value="${esc(s.webui_host || "")}" ${canWrite ? "" : "disabled"} /></div><div class="form-meta"></div></div><div class="form-row"><label><code>webui_port</code><small>int · WebUI 端口（重启生效）</small></label><div class="form-input"><input type="number" id="setting-webui-port" min="1" max="65535" value="${esc(s.webui_port ?? "")}" ${canWrite ? "" : "disabled"} /></div><div class="form-meta"></div></div><div class="form-row"><label><code>webui_public_url</code><small>str · 对外展示地址（重启生效）</small></label><div class="form-input"><input type="text" id="setting-webui-url" value="${esc(s.webui_public_url || "")}" ${canWrite ? "" : "disabled"} /></div><div class="form-meta"></div></div></div></section><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>当前路由解析快照</h2><span>series.model_router@1.0</span></div></div><div class="table-wrap"><table class="table"><thead><tr><th>能力</th><th>Provider</th><th>模型</th><th>来源</th><th>状态</th></tr></thead><tbody>${resolvedRows}</tbody></table></div><div class="footer"><span>插件显式配置 &gt; 核路由 &gt; AstrBot 原生 Provider。</span><span>只接受安全字段，不回显密钥。</span></div></section>`;
}
function controlView() {
  const control = state.control || { mode: "native", members: [], revision: 0 };
  const rows = (control.members || []).map(item => `<tr><td><b>${esc(item.display_name)}</b><small>${esc(item.plugin_id)}</small></td><td><span class="status ${item.status === "managed" ? "" : "off"}">${esc(item.status)}</span></td><td>${esc(item.reason || "-")}</td><td><button class="link" data-control-plugin="${esc(item.plugin_id)}">打开管理台</button></td></tr>`).join("") || `<tr><td colspan="4" class="empty-cell">暂无可信插件控制契约</td></tr>`;
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 统一接管</div><h1>系列接管</h1><p>核只保存覆盖层；关闭接管后插件自身配置立即恢复生效。字段接管、插件面板与生命周期操作全部在本控制台完成。</p></div><div class="actions"><button class="btn" id="refresh-control">刷新</button>${state.session?.role === "owner" ? `<button class="btn primary" id="toggle-control">${control.mode === "managed" ? "关闭统一接管" : "启用统一接管"}</button>` : ""}</div></div><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>当前模式：${esc(control.mode)}</h2><span>revision ${esc(control.revision)}</span></div></div><div class="table-wrap"><table class="table"><thead><tr><th>模块</th><th>运行来源</th><th>状态原因</th><th>操作</th></tr></thead><tbody>${rows}</tbody></table></div></section>${controlDetail()}`;
}
function controlDetail() {
  const schema = state.controlSchema;
  if (!schema || !state.selectedControlPlugin) return "";
  const member = (state.control?.members || []).find(item => item.plugin_id === schema.plugin_id);
  const displayName = member?.display_name || schema.plugin_id;
  const snapshot = state.controlSnapshot || { snapshot: { fields: {} } };
  const tabs = [["fields", "字段接管"], ["panels", "插件面板"], ["lifecycle", "生命周期"]];
  const strip = `<div class="tab-strip">${tabs.map(([id, label]) => `<button class="${state.controlTab === id ? "active" : ""}" data-control-tab="${id}">${label}</button>`).join("")}</div>`;
  let body = "";
  if (state.controlTab === "panels") body = controlPanelsTab();
  else if (state.controlTab === "lifecycle") body = controlLifecycleTab();
  else body = controlFieldsTab(schema, snapshot);
  return `<section class="workspace"><div class="workspace-head"><div class="section-title"><h2>${esc(displayName)} 管理台</h2><span>${esc(state.selectedControlPlugin)} · revision ${esc(schema.revision)}</span></div><button class="btn" id="close-control-detail">返回列表</button></div>${strip}<div class="control-body">${body}</div></section>`;
}
function controlFieldsTab(schema, snapshot) {
  const fields = schema?.schema?.fields || {};
  const values = snapshot?.snapshot?.fields || {};
  const canWrite = state.session?.role === "owner" || state.session?.role === "admin";
  const rowsHtml = Object.entries(fields).map(([name, def]) => {
    const value = values[name] || {};
    const current = value.effective_value ?? def.default ?? "";
    const managed = !!value.managed_configured;
    const source = managed ? `<span class="pill managed">核覆盖</span>` : `<span class="pill native">插件</span>`;
    let input = "";
    if (def.secret) input = `<input type="password" data-control-field="${esc(name)}" placeholder="${current ? "已配置（不回显）" : "未配置"}" ${canWrite ? "" : "disabled"}>`;
    else if (def.type === "bool") input = `<label class="switch"><input type="checkbox" data-control-field="${esc(name)}" ${current === true ? "checked" : ""} ${canWrite ? "" : "disabled"} /><span>${esc(def.description || "")}</span></label>`;
    else if (def.type === "int" || def.type === "float") input = `<input type="number" step="${def.type === "float" ? "any" : "1"}" min="${esc(def.minimum ?? "")}" max="${esc(def.maximum ?? "")}" value="${esc(current === null ? "" : current)}" data-control-field="${esc(name)}" ${canWrite ? "" : "disabled"}>`;
    else input = `<input type="text" value="${esc(current === null ? "" : current)}" data-control-field="${esc(name)}" ${canWrite ? "" : "disabled"}>`;
    const note = def.control === "read_only" ? `<span class="pill">只读</span>` : "";
    return `<div class="form-row"><label><code>${esc(name)}</code><small>${esc(def.type || "")}${def.description ? " · " + esc(def.description) : ""}</small></label><div class="form-input">${input}</div><div class="form-meta">${source}${note}</div></div>`;
  }).join("") || `<p class="empty-cell">该插件未声明可管理字段。</p>`;
  return `<div class="form-hint">${canWrite ? "修改后点击「应用修改」：先校验再写入覆盖层，带 revision 乐观锁。" : "当前角色为 viewer，仅可查看字段。"}</div><div class="form-grid">${rowsHtml}</div><div class="form-actions"><button class="btn primary" id="control-apply" ${canWrite ? "" : "disabled"}>应用修改</button><button class="btn" id="control-reset" ${canWrite ? "" : "disabled"}>重置全部覆盖</button><button class="btn" id="control-refresh-fields">刷新字段</button></div>`;
}
function controlPanelsTab() {
  const pluginId = state.selectedControlPlugin;
  if (!state.panelsList) return `<p class="empty-cell">尚未加载面板。${`<button class="btn primary" id="panel-load">加载该插件面板</button>`}</p><p class="form-hint">面板来自插件的 series.webui@1.0 契约，未实现契约的插件此区为空。</p>`;
  const panels = state.panelsList.panels || [];
  if (!panels.length) return `<p class="empty-cell">该插件未提供管理面板（未实现 series.webui@1.0 契约）。</p>`;
  const buttons = panels.map(panel => `<button class="btn ${state.selectedPanel === panel.id ? "primary" : ""}" data-panel-select="${esc(panel.id)}">${esc(panel.title)}</button>`).join("");
  let content = "";
  if (state.panelData && state.selectedPanel) content = panelContent(state.panelData);
  return `<div class="panel-nav">${buttons}</div><div class="panel-body">${content || `<p class="empty-cell">选择一个面板查看。</p>`}</div>`;
}
function panelContent(data) {
  const columns = data.columns || [];
  const rows = data.rows || [];
  const table = columns.length ? `<div class="table-wrap"><table class="table"><thead><tr>${columns.map(col => `<th>${esc(col.label || col.key)}</th>`).join("")}</tr></thead><tbody>${rows.length ? rows.map(row => `<tr>${columns.map(col => `<td>${esc(row[col.key] ?? "—")}</td>`).join("")}</tr>`).join("") : `<tr><td colspan="${columns.length}" class="empty-cell">暂无数据</td></tr>`}</tbody></table></div>` : "";
  const actions = (data.actions || []).map(action => {
    const fields = (action.payload_fields || []).map(field => field.type === "select"
      ? `<label><span>${esc(field.label || field.name)}</span><select data-panel-field="${esc(field.name)}">${(field.options || []).map(opt => `<option value="${esc(opt[0])}">${esc(opt[1])}</option>`).join("")}</select></label>`
      : `<label><span>${esc(field.label || field.name)}</span><input type="${field.type === "number" ? "number" : "text"}" data-panel-field="${esc(field.name)}" placeholder="${esc(field.hint || "")}" /></label>`).join("");
    return `<div class="panel-action">${fields ? `<div class="panel-action-form">${fields}</div>` : ""}<button class="btn ${action.danger ? "danger" : "primary"}" data-panel-action="${esc(action.id)}">${esc(action.label || action.id)}</button></div>`;
  }).join("");
  return `${data.title ? `<div class="section-title"><h3>${esc(data.title)}</h3>${data.description ? `<span>${esc(data.description)}</span>` : ""}</div>` : ""}${table}${actions ? `<div class="panel-actions">${actions}</div>` : ""}${data.footer ? `<p class="form-hint">${esc(data.footer)}</p>` : ""}`;
}
function controlLifecycleTab() {
  const pluginId = state.selectedControlPlugin;
  const module = state.modules.find(item => item.plugin_id === pluginId);
  const isOwner = state.session?.role === "owner";
  const status = module ? `<span class="status ${module.status === "normal" ? "" : "off"}">${module.status === "normal" ? "运行正常" : "已停用/未加载"}</span>` : `<span class="pill">未安装</span>`;
  return `<div class="detail-grid"><div><span>当前状态</span><strong>${status}</strong></div><div><span>当前版本</span><strong><code>v${esc(module?.version || "未知")}</code></strong></div><div><span>更新检查</span><strong>${module?.update_available ? "有更新" : "未检查/当前"}</strong></div></div><p class="form-hint">${isOwner ? "操作走核的事务路径（串行、可回滚、热重载），执行前需确认；仅 owner 可执行。" : "生命周期操作仅 owner 可执行。"}</p><div class="form-actions"><label class="switch"><input type="checkbox" id="lifecycle-force" /><span>强制更新（覆盖本地）</span></label><button class="btn primary" data-lifecycle="update" ${isOwner && module ? "" : "disabled"}>更新</button><button class="btn" data-lifecycle="enable" ${isOwner && module ? "" : "disabled"}>启用</button><button class="btn danger" data-lifecycle="disable" ${isOwner && module ? "" : "disabled"}>停用</button><button class="btn" data-lifecycle="install" ${isOwner && !module ? "" : "disabled"}>安装</button></div>`;
}
function securityView() {
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 访问控制</div><h1>安全与账户</h1><p>当前会话由核 WebUI 服务端 Cookie 管理。</p></div></div><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>当前管理员会话</h2><span>不会在浏览器持久化密码或令牌</span></div></div><div class="detail-grid account-grid"><div><span>用户名</span><strong>${esc(state.session?.username || "管理员")}</strong></div><div><span>角色</span><strong>${esc(state.session?.role || "admin")}</strong></div><div><span>会话状态</span><strong>已认证</strong></div></div><div class="footer"><span>管理员创建、禁用和重置密码请在核 Page 完成。</span><button class="btn danger" id="security-logout">退出登录</button></div></section>`;
}
function viewContent() { if (state.view === "diagnostics") return diagnosticsView(); if (state.view === "updates") return updatesView(); if (state.view === "settings") return settingsView(); if (state.view === "control") return controlView(); if (state.view === "security") return securityView(); return modulesView(); }
function rail() {
  const links = [["modules", "▦", "模块总览"], ["control", "◈", "系列接管"], ["diagnostics", "⌁", "运行诊断"], ["updates", "↻", "更新与回滚"], ["settings", "⚙", "全局设置"], ["security", "◇", "安全与账户"]];
  return `<aside class="rail"><div class="brand"><span class="brand-mark">核</span><div><strong>凝心溯溪</strong><small>模块运营中心</small></div></div><div class="nav-label">工作区</div><nav class="nav">${links.map(([view, icon, label]) => `<button class="${state.view === view ? "active" : ""}" data-view="${view}">${icon}　${label}</button>`).join("")}</nav><div class="spacer"></div><div class="health"><b>系列健康度</b><p>${state.modules.length} 个可信模块已纳管。模块发现不执行任意第三方代码。</p><div class="bar"><i></i></div></div><div class="user"><span class="avatar">管</span><span>${esc(state.session?.username || "管理员")}</span><button class="logout" id="rail-logout">↪</button></div></aside>`;
}
function dashboard() {
  const titles = { modules: "模块运营中心", control: "系列接管", diagnostics: "运行诊断", updates: "更新与回滚", settings: "全局设置", security: "安全与账户" };
  app.innerHTML = `<div class="shell">${rail()}<main class="main"><header class="topbar"><div class="crumb">凝心溯溪 / <b>核 · ${titles[state.view]}</b></div><div class="top-actions"><button class="btn" id="refresh">刷新</button><button class="btn" id="logout">退出登录</button></div></header><div class="content">${viewContent()}</div></main><nav class="mobile-nav"><button data-view="modules"><span>▦</span>模块</button><button data-view="diagnostics"><span>⌁</span>诊断</button><button data-view="settings"><span>⚙</span>设置</button><button id="mobile-logout"><span>⇥</span>退出</button></nav></div>`;
  bindDashboard();
}
function bindDashboard() {
  document.getElementById("logout")?.addEventListener("click", logout); document.getElementById("rail-logout")?.addEventListener("click", logout); document.getElementById("mobile-logout")?.addEventListener("click", logout);
  document.getElementById("refresh")?.addEventListener("click", loadDashboard); document.getElementById("reload")?.addEventListener("click", loadDashboard); document.getElementById("check")?.addEventListener("click", () => checkUpdates()); document.getElementById("export")?.addEventListener("click", exportSummary);
  document.getElementById("refresh-diagnostics")?.addEventListener("click", () => loadDiagnostics()); document.getElementById("refresh-logs")?.addEventListener("click", () => loadDiagnosticLogs(true)); document.getElementById("clear-logs")?.addEventListener("click", () => clearDiagnosticLogs()); document.getElementById("log-auto")?.addEventListener("change", () => toggleLogAuto()); document.getElementById("log-level")?.addEventListener("change", event => { state.logLevel = event.target.value || ""; dashboard(); }); document.getElementById("refresh-routes")?.addEventListener("click", () => loadSettings()); document.getElementById("settings-reload")?.addEventListener("click", () => loadSettings()); document.getElementById("save-settings")?.addEventListener("click", () => saveSettings()); document.getElementById("refresh-control")?.addEventListener("click", () => loadControl()); document.getElementById("toggle-control")?.addEventListener("click", toggleControl); document.getElementById("security-logout")?.addEventListener("click", logout);
  document.getElementById("check-updates")?.addEventListener("click", () => checkUpdates()); document.getElementById("reload-transactions")?.addEventListener("click", () => loadTransactions()); document.querySelectorAll("[data-rollback]").forEach(node => node.addEventListener("click", () => rollbackUpdate(node.dataset.rollback)));
  document.querySelectorAll("[data-view]").forEach(node => node.addEventListener("click", () => { state.view = node.dataset.view || "modules"; state.selectedModule = node.dataset.module || ""; if (state.view === "diagnostics") loadDiagnostics(); else if (state.view === "settings") loadSettings(); else if (state.view === "updates") { dashboard(); loadTransactions(); } else if (state.view === "control") loadControl(); else dashboard(); }));
  document.querySelectorAll("[data-diagnostic]").forEach(node => node.addEventListener("click", () => loadDiagnostics())); document.querySelectorAll("[data-module]").forEach(node => node.addEventListener("click", () => { state.view = "modules"; state.selectedModule = node.dataset.module || ""; dashboard(); })); document.getElementById("close-module-detail")?.addEventListener("click", () => { state.selectedModule = ""; dashboard(); });
  document.querySelectorAll("[data-filter]").forEach(node => node.addEventListener("click", () => { state.filter = node.dataset.filter; dashboard(); })); const query = document.getElementById("query"); query?.addEventListener("input", () => { state.query = query.value; dashboard(); requestAnimationFrame(() => { const next = document.getElementById("query"); next?.focus(); next?.setSelectionRange(state.query.length, state.query.length); }); });
  document.querySelectorAll("[data-control-plugin]").forEach(node => node.addEventListener("click", () => loadControlPlugin(node.dataset.controlPlugin)));
  document.getElementById("close-control-detail")?.addEventListener("click", () => { state.selectedControlPlugin = ""; state.controlSchema = null; state.controlSnapshot = null; state.panelsList = null; state.panelData = null; state.selectedPanel = ""; dashboard(); });
  document.querySelectorAll("[data-control-tab]").forEach(node => node.addEventListener("click", () => { state.controlTab = node.dataset.controlTab || "fields"; dashboard(); }));
  document.getElementById("control-apply")?.addEventListener("click", () => applyControlPatch());
  document.getElementById("control-reset")?.addEventListener("click", () => resetControlFields());
  document.getElementById("control-refresh-fields")?.addEventListener("click", () => refreshControlFields());
  document.getElementById("panel-load")?.addEventListener("click", () => loadPanelsList());
  document.querySelectorAll("[data-panel-select]").forEach(node => node.addEventListener("click", () => loadPanelData(node.dataset.panelSelect)));
  document.querySelectorAll("[data-panel-action]").forEach(node => node.addEventListener("click", () => runPanelAction(node.dataset.panelAction)));
  document.querySelectorAll("[data-lifecycle]").forEach(node => node.addEventListener("click", () => runLifecycle(node.dataset.lifecycle)));
  document.querySelectorAll("[data-control-open]").forEach(node => node.addEventListener("click", async () => { state.view = "control"; await loadControl(); await loadControlPlugin(node.dataset.controlOpen); }));
}
async function loadDiagnostics() { try { const result = await post("diagnostics", {}); state.providers = result.providers || []; state.view = "diagnostics"; dashboard(); await loadDiagnosticLogs(true); } catch (error) { showToast(error.message, true); } }
function logCursors() { const cursors = {}; const streams = {}; (state.logMembers || []).forEach(item => { cursors[item.plugin_id] = item.reset ? 0 : (item.next_seq || 0); streams[item.plugin_id] = item.stream_id || ""; }); return { cursors, streams }; }
async function loadDiagnosticLogs(reset = false) {
  try {
    if (reset) { state.logs = []; state.logMembers = []; }
    const { cursors, streams } = logCursors();
    const result = await post("diagnostics/logs", { cursors, streams, limit: 500 });
    state.logMembers = result.members || [];
    state.logs = [...state.logs, ...(result.events || [])];
    if (state.logs.length > 3000) state.logs = state.logs.slice(-3000);
    dashboard();
  } catch (error) { showToast(error.message, true); }
}
async function clearDiagnosticLogs() {
  if (!confirm("清空所有模块的诊断日志？该操作不可恢复。")) return;
  try { await post("diagnostics/clear", { confirm: true }); state.logs = []; state.logMembers = []; showToast("诊断日志已清空"); await loadDiagnostics(); } catch (error) { showToast(error.message, true); }
}
function toggleLogAuto() {
  state.logAuto = !state.logAuto;
  if (state.logTimer) { clearInterval(state.logTimer); state.logTimer = null; }
  if (state.logAuto) state.logTimer = setInterval(() => { if (state.view === "diagnostics") loadDiagnosticLogs(); }, 5000);
  dashboard();
}
async function checkUpdates() {
  try { showToast("正在检查更新…"); state.updatesCheck = await post("updates/check", {}); showToast("检查完成"); await loadDashboard(); if (state.view === "updates") await loadTransactions(); } catch (error) { showToast(error.message, true); }
}
async function loadTransactions() {
  try { state.transactions = (await get("updates/transactions")).transactions || []; if (state.view === "updates") dashboard(); } catch (error) { showToast(error.message, true); }
}
async function rollbackUpdate(txId) {
  if (!confirm("确定回滚该次更新？插件将恢复到更新前版本并热重载。")) return;
  try { const result = await post("updates/rollback", { tx_id: txId }); showToast(`已回滚 ${result.plugin_id || ""} → v${result.from_version || "?"}`); await Promise.all([loadDashboard(), loadTransactions()]); } catch (error) { showToast(error.message, true); }
}
async function loadSettings() {
  try {
    state.settingsData = await get("settings");
    try { state.routes = await get("model-routing"); } catch (error) { state.routes = null; }
    if (state.view === "settings") dashboard();
  } catch (error) { showToast(error.message, true); }
}
async function saveSettings() {
  if (!(state.session?.role === "owner" || state.session?.role === "admin")) { showToast("设置修改仅 admin 及以上可执行", true); return; }
  const routes = {};
  document.querySelectorAll("[data-setting-route]").forEach(node => { const [kind, field] = String(node.dataset.settingRoute).split("."); const value = node.value.trim(); if (!value) return; routes[kind] = routes[kind] || {}; routes[kind][field] = value; });
  const payload = { model_routing: routes, auto_update_enabled: !!document.getElementById("setting-auto-update")?.checked, log_level: document.getElementById("setting-log-level")?.value || "INFO" };
  const host = document.getElementById("setting-webui-host")?.value.trim() || "";
  const portRaw = document.getElementById("setting-webui-port")?.value.trim() || "";
  const publicUrl = document.getElementById("setting-webui-url")?.value.trim() || "";
  if (portRaw) { const port = parseInt(portRaw, 10); if (!(port >= 1 && port <= 65535)) { showToast("WebUI 端口必须是 1-65535", true); return; } payload.webui_port = port; }
  if (host) payload.webui_host = host;
  if (publicUrl) payload.webui_public_url = publicUrl;
  try { const result = await post("settings", payload); showToast("设置已保存并生效（连接项重启后生效）"); await Promise.all([loadSettings(), loadDashboard()]); } catch (error) { showToast(error.message, true); }
}
async function loadModelRouting() { try { state.routes = await get("model-routing"); state.view = "settings"; dashboard(); } catch (error) { showToast(error.message, true); } }
async function loadControl() { try { state.control = await get("series/control"); state.view = "control"; dashboard(); } catch (error) { showToast(error.message, true); } }
async function loadControlPlugin(pluginId) {
  try {
    state.selectedControlPlugin = pluginId;
    state.controlTab = "fields";
    state.panelsList = null;
    state.panelData = null;
    state.selectedPanel = "";
    state.controlSchema = await get(`series/${encodeURIComponent(pluginId)}/control/schema`);
    state.controlSnapshot = await get(`series/${encodeURIComponent(pluginId)}/control/snapshot`);
    state.view = "control"; dashboard();
  } catch (error) { showToast(error.message, true); }
}
function controlFieldInputs() { return [...document.querySelectorAll("[data-control-field]")]; }
function collectControlPatch(schema, snapshot) {
  const fields = schema?.schema?.fields || {};
  const values = snapshot?.snapshot?.fields || {};
  const patch = {};
  controlFieldInputs().forEach(node => {
    const name = node.dataset.controlField;
    const def = fields[name];
    if (!def || def.control === "read_only" || node.disabled) return;
    const value = values[name] || {};
    let next;
    if (def.type === "bool") next = !!node.checked;
    else if (def.type === "int") next = parseInt(node.value, 10);
    else if (def.type === "float") next = parseFloat(node.value);
    else if (def.secret) { next = node.value ? String(node.value) : null; }
    else next = node.value;
    if (next === null || next === "") { if (value.managed_configured) patch[name] = null; return; }
    if (def.secret) { patch[name] = next; return; }
    if (next !== (value.effective_value ?? def.default)) patch[name] = next;
  });
  return patch;
}
async function applyControlPatch() {
  const pluginId = state.selectedControlPlugin;
  const schema = state.controlSchema;
  const snapshot = state.controlSnapshot;
  if (!pluginId || !schema) return;
  const patch = collectControlPatch(schema, snapshot);
  if (!Object.keys(patch).length) { showToast("没有修改需要应用"); return; }
  try {
    const revision = schema.revision;
    await post(`series/${encodeURIComponent(pluginId)}/control/validate`, { patch, expected_revision: revision });
    await post(`series/${encodeURIComponent(pluginId)}/control/apply`, { patch, expected_revision: revision });
    showToast("覆盖已应用");
    await loadControlPlugin(pluginId);
    await loadControl();
  } catch (error) {
    showToast(error.message, true);
    if (String(error.message).includes("REVISION")) await loadControlPlugin(pluginId);
  }
}
async function resetControlFields() {
  const pluginId = state.selectedControlPlugin;
  if (!pluginId) return;
  if (!confirm("重置该插件的全部核覆盖字段？插件自身配置将立即恢复生效。")) return;
  try {
    await post(`series/${encodeURIComponent(pluginId)}/control/reset`, { fields: null });
    showToast("已恢复插件自身配置");
    await loadControlPlugin(pluginId);
    await loadControl();
  } catch (error) { showToast(error.message, true); }
}
async function refreshControlFields() {
  if (state.selectedControlPlugin) await loadControlPlugin(state.selectedControlPlugin);
}
async function loadPanelsList() {
  const pluginId = state.selectedControlPlugin;
  if (!pluginId) return;
  try {
    state.panelsList = await get(`series/${encodeURIComponent(pluginId)}/panels`);
    state.panelData = null;
    state.selectedPanel = "";
    dashboard();
  } catch (error) { showToast(error.message, true); }
}
async function loadPanelData(panelId) {
  const pluginId = state.selectedControlPlugin;
  if (!pluginId || !panelId) return;
  try {
    state.selectedPanel = panelId;
    state.panelData = await get(`series/${encodeURIComponent(pluginId)}/panels/${encodeURIComponent(panelId)}`);
    dashboard();
  } catch (error) { showToast(error.message, true); }
}
async function runPanelAction(actionId) {
  const pluginId = state.selectedControlPlugin;
  const panelId = state.selectedPanel;
  const action = (state.panelData?.actions || []).find(item => item.id === actionId);
  if (!pluginId || !panelId || !action) return;
  const payload = {};
  let missing = false;
  (action.payload_fields || []).forEach(field => {
    const node = document.querySelector(`[data-panel-field="${CSS.escape(field.name)}"]`);
    const value = node ? node.value : "";
    if (field.required && !value) missing = true;
    payload[field.name] = field.type === "number" ? (value === "" ? null : Number(value)) : value;
  });
  if (missing) { showToast("请填写动作所需的必填字段", true); return; }
  if (action.confirm && !confirm(action.confirm)) return;
  try {
    const result = await post(`series/${encodeURIComponent(pluginId)}/panels/${encodeURIComponent(panelId)}/actions/${encodeURIComponent(actionId)}`, payload);
    showToast(result.message || "操作完成");
    await loadPanelData(panelId);
  } catch (error) { showToast(error.message, true); }
}
async function runLifecycle(action) {
  const pluginId = state.selectedControlPlugin;
  if (!pluginId) return;
  if (state.session?.role !== "owner") { showToast("生命周期操作仅 owner 可执行", true); return; }
  const labels = { install: "安装", update: "更新", enable: "启用", disable: "停用" };
  const forceNode = document.getElementById("lifecycle-force");
  const force = action === "update" && forceNode && forceNode.checked;
  const confirmText = force ? `确定强制更新「${pluginId}」？远端版本将覆盖本地代码。` : `确定对「${pluginId}」执行${labels[action] || action}？`;
  if (!confirm(confirmText)) return;
  try {
    const result = await post(`series/${encodeURIComponent(pluginId)}/lifecycle/${action}`, { force });
    showToast(`${labels[action] || action}完成${result.version ? ` · v${result.version}` : ""}`);
    await loadDashboard();
    await loadControl();
    if (state.selectedControlPlugin) await loadControlPlugin(state.selectedControlPlugin);
  } catch (error) { showToast(error.message, true); }
}
async function toggleControl() { try { const next = state.control?.mode === "managed" ? "native" : "managed"; await post("series/control/mode", { mode: next }); await loadControl(); showToast(next === "managed" ? "统一接管已启用" : "已恢复插件自身配置"); } catch (error) { showToast(error.message, true); } }
function exportSummary() { const payload = { generated_at: new Date().toISOString(), modules: state.modules.map(item => ({ plugin_id: item.plugin_id, version: item.version, status: item.status, contracts: item.contracts })) }; const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" }); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = "series-control-summary.json"; link.hidden = true; document.body.appendChild(link); link.click(); window.setTimeout(() => { link.remove(); URL.revokeObjectURL(url); }, 1000); showToast("已生成脱敏诊断摘要"); }
async function loadDashboard() { try { const session = await get("session"); state.configured = !!session.configured; if (!session.authenticated) { state.authenticated = false; loginView(); return; } state.authenticated = true; state.session = session.session; const modules = await get("modules"); state.modules = modules.modules || []; if (state.view === "settings") await loadSettings(); else if (state.view === "diagnostics") await loadDiagnostics(); else if (state.view === "updates") { dashboard(); await loadTransactions(); } else if (state.view === "control") await loadControl(); else dashboard(); } catch (error) { loginView(error.message); } }
async function logout() { try { await post("logout", {}); } finally { state.authenticated = false; state.session = null; loginView(); } }
async function start() { try { await loadDashboard(); } catch (error) { loginView(error.message); } }
start();
