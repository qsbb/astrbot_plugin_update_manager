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
  return list.length ? list.map(item => `<tr><td><button class="module module-button" data-module="${esc(item.plugin_id)}"><span class="mark" style="--color:${color(item.plugin_id)}">${esc(item.display_name.slice(-1))}</span><span><b>${esc(item.display_name)}</b><small>${esc(item.plugin_id)}</small></span></button></td><td><span class="status ${item.status === "normal" ? "" : "off"}">${item.status === "normal" ? "正常" : "已停用/未加载"}</span></td><td><span class="pill">${item.contracts} 条契约</span></td><td><code>v${esc(item.version || "未知")}</code></td><td>${item.update_available ? "有更新" : "当前"}</td><td><button class="link" data-diagnostic="${esc(item.plugin_id)}">诊断</button></td></tr>`).join("") : `<tr><td colspan="6" style="padding:40px;text-align:center;color:#667085">没有匹配的可信模块。</td></tr>`;
}
function selectedDetail() {
  const item = state.modules.find(value => value.plugin_id === state.selectedModule);
  if (!item) return "";
  return `<section class="workspace module-detail"><div class="workspace-head"><div class="section-title"><h2>${esc(item.display_name)}</h2><button class="btn" id="close-module-detail">返回列表</button></div><p class="detail-copy">${esc(item.plugin_id)} · v${esc(item.version || "未知")} · ${item.status === "normal" ? "运行正常" : "需要关注"}</p><div class="detail-grid"><div><span>加载</span><strong>${item.loaded ? "是" : "否"}</strong></div><div><span>激活</span><strong>${item.activated ? "是" : "否"}</strong></div><div><span>契约</span><strong>${item.contracts}</strong></div><div><span>管理来源</span><strong>可信登记</strong></div></div><p class="detail-note">插件专属配置仍由“核” Page 的插件配置区管理；这里展示运行状态和诊断入口，避免独立 WebUI 绕过宿主权限。</p><button class="btn primary" data-diagnostic="${esc(item.plugin_id)}">查看该模块诊断</button></div></section>`;
}
function modulesView() {
  const normal = state.modules.filter(x => x.status === "normal").length;
  const offline = state.modules.length - normal;
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 生产状态</div><h1>模块运营中心</h1><p>统一查看可信自有模块的运行状态、版本、契约与诊断入口。</p></div><div class="actions"><button class="btn" id="export">导出摘要</button><button class="btn primary" id="check">运行全量检查</button></div></div><div class="stats"><div class="stat"><label>可信模块</label><strong>${state.modules.length}</strong><small>来自可信登记</small></div><div class="stat"><label>运行正常</label><strong>${normal}</strong><small>核心链路可用</small></div><div class="stat"><label>需关注</label><strong>${offline}</strong><small>非阻断状态</small></div><div class="stat"><label>契约发现</label><strong>已接入</strong><small>版本化能力</small></div><div class="stat"><label>管理边界</label><strong>安全</strong><small>高危操作仍需确认</small></div></div><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>系列模块</h2><span>${filtered().length} 个匹配当前视图</span></div><div class="filters"><label class="search">⌕<input id="query" placeholder="搜索模块名称或 ID" value="${esc(state.query)}"></label><div class="seg"><button data-filter="all" class="${state.filter === "all" ? "active" : ""}">全部</button><button data-filter="normal" class="${state.filter === "normal" ? "active" : ""}">正常</button><button data-filter="offline" class="${state.filter === "offline" ? "active" : ""}">需关注</button></div><span class="grow"></span><button class="btn" id="reload">刷新状态</button></div></div><div class="table-wrap"><table class="table"><thead><tr><th>模块</th><th>运行状态</th><th>契约</th><th>版本</th><th>更新</th><th>操作</th></tr></thead><tbody>${moduleRows()}</tbody></table></div><div class="footer"><span>只纳管可信登记中的凝心溯溪系列插件。</span><span>${state.modules.length} 个模块</span></div></section>${selectedDetail()}`;
}
function diagnosticsView() {
  const rows = state.providers.length ? state.providers.map(item => `<tr><td>${esc(item.display_name)}</td><td><code>${esc(item.plugin_id)}</code></td><td><span class="status">${esc(item.status)}</span></td></tr>`).join("") : `<tr><td colspan="3" class="empty-cell">暂无诊断提供方</td></tr>`;
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 可观测性</div><h1>运行诊断</h1><p>只读取已声明的系列诊断契约，不执行第三方模块代码。</p></div><div class="actions"><button class="btn primary" id="refresh-diagnostics">刷新诊断</button></div></div><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>诊断提供方</h2><span>${state.providers.length} 个</span></div></div><div class="table-wrap"><table class="table"><thead><tr><th>模块</th><th>插件 ID</th><th>状态</th></tr></thead><tbody>${rows}</tbody></table></div></section>`;
}
function updatesView() {
  const rows = state.modules.map(item => `<tr><td>${esc(item.display_name)}</td><td><code>v${esc(item.version || "未知")}</code></td><td>${item.update_available ? "有更新" : "未检查"}</td><td><button class="link" data-view="modules" data-module="${esc(item.plugin_id)}">查看模块</button></td></tr>`).join("");
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 生命周期</div><h1>更新与回滚</h1><p>版本检查、更新、启停和回滚继续通过核 Page 的二次确认流程执行。</p></div><div class="actions"><button class="btn" data-view="modules">返回模块</button></div></div><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>当前纳管版本</h2><span>独立 WebUI 不绕过 Page 鉴权</span></div></div><div class="table-wrap"><table class="table"><thead><tr><th>模块</th><th>当前版本</th><th>状态</th><th>操作</th></tr></thead><tbody>${rows}</tbody></table></div></section>`;
}
function settingsView() {
  const routes = state.routes?.routes || {};
  const labels = { conversation: "对话 / LLM", embedding: "向量 / Embedding", vision: "识图 / 视觉", stt: "语音识别 / STT", tts: "语音合成 / TTS" };
  const rows = Object.entries(labels).map(([kind, label]) => { const route = routes[kind] || {}; return `<tr><td>${label}</td><td><code>${esc(route.provider_id || "未配置")}</code></td><td>${esc(route.model || "自动")}</td><td>${esc(route.source || "unavailable")}</td><td><span class="status ${route.available ? "" : "off"}">${route.available ? "可用" : "不可用"}</span></td></tr>`; }).join("");
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 模型策略</div><h1>全局设置</h1><p>插件显式配置优先，其次使用核，最后回退 AstrBot 原生 Provider。</p></div><div class="actions"><button class="btn primary" id="refresh-routes">刷新路由</button></div></div><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>统一模型路由</h2><span>series.model_router@1.0</span></div></div><div class="table-wrap"><table class="table"><thead><tr><th>能力</th><th>Provider</th><th>模型</th><th>来源</th><th>状态</th></tr></thead><tbody>${rows}</tbody></table></div><div class="footer"><span>编辑入口：核 Page → 配置 → 统一模型路由。</span><span>只接受安全字段，不回显密钥。</span></div></section>`;
}
function controlView() {
  const control = state.control || { mode: "native", members: [], revision: 0 };
  const rows = (control.members || []).map(item => `<tr><td><b>${esc(item.display_name)}</b><small>${esc(item.plugin_id)}</small></td><td><span class="status ${item.status === "managed" ? "" : "off"}">${esc(item.status)}</span></td><td>${esc(item.reason || "-")}</td><td><button class="link" data-control-plugin="${esc(item.plugin_id)}">查看字段</button></td></tr>`).join("") || `<tr><td colspan="4" class="empty-cell">暂无可信插件控制契约</td></tr>`;
  const selected = state.controlSchema;
  const fields = selected?.schema?.fields || {};
  const fieldRows = Object.entries(fields).map(([name, definition]) => `<tr><td><code>${esc(name)}</code></td><td>${esc(definition.type || "unknown")}</td><td>${definition.secret ? "秘密字段" : "普通字段"}</td><td>${definition.control === "read_only" ? "只读" : "可覆盖"}</td></tr>`).join("");
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 统一接管</div><h1>系列接管</h1><p>核只保存覆盖层；关闭接管后插件自身配置立即恢复生效。</p></div><div class="actions"><button class="btn" id="refresh-control">刷新</button>${state.session?.role === "owner" ? `<button class="btn primary" id="toggle-control">${control.mode === "managed" ? "关闭统一接管" : "启用统一接管"}</button>` : ""}</div></div><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>当前模式：${esc(control.mode)}</h2><span>revision ${esc(control.revision)}</span></div></div><div class="table-wrap"><table class="table"><thead><tr><th>模块</th><th>运行来源</th><th>状态原因</th><th>操作</th></tr></thead><tbody>${rows}</tbody></table></div>${selected ? `<div class="workspace-head"><div class="section-title"><h2>${esc(selected.plugin_id)} 字段</h2><span>revision ${esc(selected.revision)}</span></div></div><div class="table-wrap"><table class="table"><thead><tr><th>字段</th><th>类型</th><th>敏感性</th><th>控制</th></tr></thead><tbody>${fieldRows || `<tr><td colspan="4" class="empty-cell">插件未声明可管理字段</td></tr>`}</tbody></table></div>` : ""}</section>`;
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
  document.getElementById("refresh")?.addEventListener("click", loadDashboard); document.getElementById("reload")?.addEventListener("click", loadDashboard); document.getElementById("check")?.addEventListener("click", async () => { await loadDashboard(); showToast("已完成可信模块状态检查"); }); document.getElementById("export")?.addEventListener("click", exportSummary);
  document.getElementById("refresh-diagnostics")?.addEventListener("click", () => loadDiagnostics()); document.getElementById("refresh-routes")?.addEventListener("click", () => loadModelRouting()); document.getElementById("refresh-control")?.addEventListener("click", () => loadControl()); document.getElementById("toggle-control")?.addEventListener("click", toggleControl); document.getElementById("security-logout")?.addEventListener("click", logout);
  document.querySelectorAll("[data-view]").forEach(node => node.addEventListener("click", () => { state.view = node.dataset.view || "modules"; state.selectedModule = node.dataset.module || ""; if (state.view === "diagnostics") loadDiagnostics(); else if (state.view === "settings") loadModelRouting(); else if (state.view === "control") loadControl(); else dashboard(); }));
  document.querySelectorAll("[data-diagnostic]").forEach(node => node.addEventListener("click", () => loadDiagnostics())); document.querySelectorAll("[data-module]").forEach(node => node.addEventListener("click", () => { state.view = "modules"; state.selectedModule = node.dataset.module || ""; dashboard(); })); document.getElementById("close-module-detail")?.addEventListener("click", () => { state.selectedModule = ""; dashboard(); });
  document.querySelectorAll("[data-filter]").forEach(node => node.addEventListener("click", () => { state.filter = node.dataset.filter; dashboard(); })); const query = document.getElementById("query"); query?.addEventListener("input", () => { state.query = query.value; dashboard(); requestAnimationFrame(() => { const next = document.getElementById("query"); next?.focus(); next?.setSelectionRange(state.query.length, state.query.length); }); });
  document.querySelectorAll("[data-control-plugin]").forEach(node => node.addEventListener("click", () => loadControlPlugin(node.dataset.controlPlugin)));
}
async function loadDiagnostics() { try { const result = await post("diagnostics", {}); state.providers = result.providers || []; state.view = "diagnostics"; dashboard(); } catch (error) { showToast(error.message, true); } }
async function loadModelRouting() { try { state.routes = await get("model-routing"); state.view = "settings"; dashboard(); } catch (error) { showToast(error.message, true); } }
async function loadControl() { try { state.control = await get("series/control"); state.view = "control"; dashboard(); } catch (error) { showToast(error.message, true); } }
async function loadControlPlugin(pluginId) { try { state.controlSchema = await get(`series/${encodeURIComponent(pluginId)}/control/schema`); state.controlSnapshot = await get(`series/${encodeURIComponent(pluginId)}/control/snapshot`); state.view = "control"; dashboard(); } catch (error) { showToast(error.message, true); } }
async function toggleControl() { try { const next = state.control?.mode === "managed" ? "native" : "managed"; await post("series/control/mode", { mode: next }); await loadControl(); showToast(next === "managed" ? "统一接管已启用" : "已恢复插件自身配置"); } catch (error) { showToast(error.message, true); } }
function exportSummary() { const payload = { generated_at: new Date().toISOString(), modules: state.modules.map(item => ({ plugin_id: item.plugin_id, version: item.version, status: item.status, contracts: item.contracts })) }; const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" }); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = "series-control-summary.json"; link.hidden = true; document.body.appendChild(link); link.click(); window.setTimeout(() => { link.remove(); URL.revokeObjectURL(url); }, 1000); showToast("已生成脱敏诊断摘要"); }
async function loadDashboard() { try { const session = await get("session"); state.configured = !!session.configured; if (!session.authenticated) { state.authenticated = false; loginView(); return; } state.authenticated = true; state.session = session.session; const modules = await get("modules"); state.modules = modules.modules || []; if (state.view === "settings") await loadModelRouting(); else if (state.view === "diagnostics") await loadDiagnostics(); else if (state.view === "control") await loadControl(); else dashboard(); } catch (error) { loginView(error.message); } }
async function logout() { try { await post("logout", {}); } finally { state.authenticated = false; state.session = null; loginView(); } }
async function start() { try { await loadDashboard(); } catch (error) { loginView(error.message); } }
start();
