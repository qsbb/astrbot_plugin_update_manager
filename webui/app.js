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
  settingsTab: "route",
  panelsList: null,
  panelData: null,
  selectedPanel: "",
  selectedControlPlugin: "",
  takeoverDisabled: false,
  panelStream: null,
  logs: [],
  logMembers: [],
  logLevel: "",
  logAuto: false,
  logTimer: null,
  logPaused: false,
  logAutoScroll: true,
  logBusy: false,
  logCatchUp: false,
  logPendingScroll: false,
  logRefreshPending: false,
  updatesCheck: null,
  transactions: null,
  rulesData: null,
  mirrorsData: null,
  mirrorResults: [],
  recommendationsData: null,
  adminsData: null,
  settingsData: null,
  modelOptions: null,
  logModules: [],
  logThreshold: "",
  logRange: "all",
  logQuery: "",
  logExpanded: new Set(),
  logNewKeys: new Set(),
  filter: "all",
  query: "",
  view: "modules",
  selectedModule: "",
};
const app = document.getElementById("app");
const NAV_ITEMS = [
  ["modules", "▦", "模块总览"],
  ["control", "◈", "系列接管"],
  ["recommendations", "＋", "系列推荐"],
  ["rules", "▤", "每日规则"],
  ["mirrors", "⇄", "镜像加速"],
  ["diagnostics", "⌁", "运行诊断"],
  ["updates", "↻", "更新与回滚"],
  ["settings", "⚙", "全局设置"],
  ["security", "◇", "安全与账户"],
];
const VIEW_TITLES = Object.fromEntries(NAV_ITEMS.map(([view, , label]) => [view, label]));

const notify = (message, error = false) => {
  if (window.SeriesUI?.toast) {
    window.SeriesUI.toast(message, error ? "error" : "info");
    return;
  }
  const fallback = document.querySelector("[data-toast-fallback], #bridge-error, #startup-error, #page-error");
  if (fallback) {
    fallback.textContent = String(message || "");
    fallback.hidden = false;
  } else {
    console.error(message);
  }
};

// 界面一律显示中文功能名；原始 key 只在 title 提示与技术详情中出现。
const FIELD_LABELS = {
  auto_update_enabled: "启用自动更新", log_level: "日志级别",
  webui_host: "WebUI 监听地址", webui_port: "WebUI 端口", webui_public_url: "WebUI 对外地址",
  enabled: "启用此规则", local_time: "执行时间", timezone: "时区",
  jitter_minutes: "随机延迟（分钟）", misfire_grace_minutes: "错过执行的宽限（分钟）",
  policy: "更新策略", minimum_release_age_hours: "最小发布年龄（小时）",
  on_failure: "失败处理", prerelease: "允许预发布版本",
  username: "用户名", password: "初始密码", role: "角色",
  chunking_enabled: "智能分段", chunking_delay_mode: "分段等待方式",
  chunking_min_length: "分段最小长度", chunking_max_segments: "最多分段数",
  silence_enabled: "沉默判断", silence_strategy: "沉默判断策略",
  interrupt_enabled: "插话中断", interrupt_mode: "插话处理模式", interrupt_scope: "插话作用域",
  interrupt_merge_strategy: "插话合并策略", plain_text_mode: "纯文本模式",
  image_intent_mode: "图片意图识别", group_context_enabled: "群聊上下文",
  private_context_bridge_enabled: "私聊上下文承接",
  dynamic_context_enabled: "动态上下文续接", recent_activity_context_enabled: "跨会话活动承接",
  context_budget_enforce: "上下文预算强制执行",
  mood_enabled: "情绪追踪", mood_private_enabled: "私聊情绪追踪",
  emotion_routing_enabled: "自动情绪路由", ai_style_director_enabled: "AI 风格导演",
  segment_enabled: "长段落兜底分段", api_server_enabled: "启用外部语音接口",
  file_fallback_enabled: "失败时回退为文件", replace_url_in_tts: "朗读时替换网址",
  proactive_enabled: "允许主动发送", proactive_paused: "暂停主动发送",
  official_weather_warnings_enabled: "官方天气预警", opportunity_cache_enabled: "后台刷新候选",
};

const TYPE_LABELS = { bool: "开关", int: "整数", float: "小数", str: "文本", string: "文本", value: "值" };

function typeLabel(type) { return TYPE_LABELS[String(type || "").toLowerCase()] || "配置项"; }

// 词根表：用于把未登记的 snake_case 配置键翻译成中文功能名。
const KEY_TOKENS = {
  context: "上下文", budget: "预算", soft: "软", hard: "硬", limit: "上限",
  max: "最大", min: "最小", turns: "轮数", chars: "字数", length: "长度",
  private: "私聊", group: "群聊", bridge: "承接", dynamic: "动态",
  recent: "近期", activity: "活动", retention: "保留", minutes: "分钟", seconds: "秒",
  days: "天数", hours: "小时", count: "数量", size: "大小", mode: "模式",
  strategy: "策略", scope: "作用域", list: "名单", users: "用户", user: "用户",
  interval: "间隔", threshold: "阈值", timeout: "超时", ratio: "比例",
  enabled: "开关", enable: "开关", disabled: "关闭", merge: "合并",
  image: "图片", intent: "意图", plain: "纯文本", text: "文本", emotion: "情绪",
  routing: "路由", director: "导演", style: "风格", segment: "分段", voice: "音色",
  api: "接口", server: "服务", token: "令牌", url: "地址", port: "端口",
  weather: "天气", warning: "预警", earthquake: "地震", proactive: "主动",
  quiet: "安静", daily: "每日", policy: "策略", failure: "失败", prerelease: "预发布",
  minimum: "最小", release: "发布", age: "年龄", jitter: "随机延迟", misfire: "错过执行",
  grace: "宽限", webui: "WebUI", host: "监听地址", public: "对外", level: "级别",
};

// 每个字段一句“干什么用/什么效果”，避免只有名字看不懂。
const FIELD_HINTS = {
  chunking_enabled: "把长回复按语义拆成多条发送，避免一次性刷屏。",
  chunking_delay_mode: "决定分段之间按固定间隔还是按语音时长等待。",
  chunking_min_length: "短于该长度的回复不再拆分。",
  chunking_max_segments: "单条回复最多拆成几段，防止过于零碎。",
  silence_enabled: "按策略判断这条消息是否需要沉默不回复。",
  silence_strategy: "沉默判断方式：指令注入 / 独立预判 / 两者结合。",
  interrupt_enabled: "用户插话时把新消息并入本轮，而不是重新开一轮。",
  interrupt_mode: "运行中插话的任务归属判定方式。",
  interrupt_scope: "群聊里哪类新消息算打断（本群 / 同一发送者 / @Bot）。",
  interrupt_merge_strategy: "多条插话如何合并为一次补充说明。",
  context_budget_enforce: "开启后超出预算会真正裁剪上下文，关闭只统计不裁剪。",
  context_budget_soft_limit: "软上限：接近时只提醒，不裁剪。",
  context_budget_hard_limit: "硬上限：超过后强制裁剪上下文。",
  plain_text_mode: "去掉 Markdown 等格式，只发纯文本。",
  image_intent_mode: "识别图片意图，决定是否要看图后回复。",
  group_context_enabled: "把群聊最近消息作为上下文参考。",
  private_context_bridge_enabled: "私聊中断后自动接续上一轮话题。",
  private_context_bridge_max_turns: "最多回看多少轮私聊内容用于承接。",
  private_context_bridge_short_max_chars: "短消息承接时最多拼接多少字。",
  dynamic_context_enabled: "按当前话题动态挑选要注入的上下文。",
  dynamic_context_max_turns: "动态上下文最多参考的轮数。",
  dynamic_context_max_chars: "动态上下文最多注入的字数。",
  recent_activity_context_enabled: "跨会话参考最近活动记录，衔接更自然。",
  recent_activity_retention_minutes: "活动记录保留多久后失效。",
  mood_enabled: "记录用户情绪，并影响回复语气。",
  mood_private_enabled: "私聊场景同样启用情绪追踪。",
  emotion_routing_enabled: "按情绪自动挑选音色与说话风格。",
  ai_style_director_enabled: "用 AI 生成用户看不到的说话方式指令。",
  segment_enabled: "单段语音过长时按句界兜底拆分。",
  api_server_enabled: "开放外部语音接口，供其它程序调用。",
  file_fallback_enabled: "合成失败时改用语音文件发送，避免整条丢失。",
  replace_url_in_tts: "朗读时把网址念成「这个网址」。",
  proactive_enabled: "允许主动发送环境关心消息。",
  proactive_paused: "临时暂停主动发送，候选与记录继续累积。",
  official_weather_warnings_enabled: "额外查询中央气象台官方预警。",
  opportunity_cache_enabled: "后台刷新环境关心候选，发送更及时。",
  auto_update_enabled: "到期自动检查并更新系列插件。",
  log_level: "核自身日志的详细程度。",
  webui_host: "独立 WebUI 的监听地址（重启生效）。",
  webui_port: "独立 WebUI 的监听端口（重启生效）。",
  webui_public_url: "对外展示的 WebUI 地址（重启生效）。",
  enabled: "关闭后这条规则不会执行。",
  local_time: "每天在这个时间点运行。",
  timezone: "按哪个时区计算运行时间。",
  jitter_minutes: "在运行时间前后随机浮动，避免所有任务同一秒发起。",
  misfire_grace_minutes: "错过运行时间后，多久内仍补跑一次。",
  policy: "允许更新到哪个版本范围。",
  minimum_release_age_hours: "只更新发布超过该时长、已稳定的版本。",
  on_failure: "更新失败时回滚并继续，还是回滚后停止。",
  prerelease: "是否允许更新到预发布版本。",
  username: "登录用的管理员账户名。",
  password: "初始密码，至少 8 位。",
  role: "所有者可管理全部，管理员可操作，只读仅查看。",
};

function fieldHint(key, def) {
  return (def && (def.hint || def.description)) || FIELD_HINTS[key] || "";
}

function humanizeKey(key) {
  const parts = String(key || "").split("_").filter(Boolean);
  if (!parts.length) return "";
  const words = parts.map((part) => KEY_TOKENS[part] || "");
  if (words.some((word) => !word)) return "";
  return words.join("");
}

function fieldLabel(key, def) {
  const explicit = def && (def.label || def.title || def.description);
  if (explicit) return explicit;
  if (FIELD_LABELS[key]) return FIELD_LABELS[key];
  return humanizeKey(key) || "配置项";
}

function parse(value) { return typeof value === "string" ? JSON.parse(value) : value; }
function esc(value) { return String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c])); }
async function get(name) { const response = await fetch(`${API_PREFIX}/${name}`, { credentials: "same-origin" }); const data = parse(await response.json()); if (!response.ok || data?.success === false) throw new Error(data.error || "请求失败"); return data; }
async function post(name, payload, extraHeaders = {}) { const response = await fetch(`${API_PREFIX}/${name}`, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", ...extraHeaders }, body: JSON.stringify(payload || {}) }); const data = parse(await response.json()); if (!response.ok || data?.success === false) throw new Error(data.error || "请求失败"); return data; }

async function confirmDialog(message, options = {}) {
  if (window.SeriesUI?.confirm) {
    return window.SeriesUI.confirm({
      title: options.title || "确认操作",
      message,
      confirmText: options.confirmText || "确认",
      cancelText: "取消",
      danger: options.danger !== false,
    });
  }
  notify("确认组件未加载，操作已取消", true);
  return false;
}
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
  return list.length ? list.map(item => `<tr><td><button class="module module-button" data-module="${esc(item.plugin_id)}"><span class="mark" style="--color:${color(item.plugin_id)}">${esc(item.display_name.slice(-1))}</span><span><b>${esc(item.display_name)}</b><small>${esc(item.plugin_id)}</small></span></button></td><td><span class="status ${item.status === "normal" ? "" : "off"}">${item.status === "normal" ? "正常" : item.status === "not_installed" ? "未安装" : "已停用/未加载"}</span></td><td><span class="pill">${item.contracts} 条契约</span>${item.contract_details?.module?.role ? `<span class="pill">${esc(item.contract_details.module.role)}</span>` : ""}${item.contract_details?.control ? `<span class="pill managed">控制</span>` : ""}${item.contract_details?.webui_panels ? `<span class="pill native">面板 ${item.contract_details.webui_panels}</span>` : ""}</td><td><code>v${esc(item.version || "未知")}</code></td><td>${item.status === "not_installed" ? `<button class="link" data-install="${esc(item.plugin_id)}">安装</button>` : `<button class="link" data-diagnostic="${esc(item.plugin_id)}">诊断</button>`}</td></tr>`).join("") : `<tr><td colspan="5" style="padding:40px;text-align:center;color:#667085">没有匹配的可信模块。</td></tr>`;
}
function selectedDetail() {
  const item = state.modules.find(value => value.plugin_id === state.selectedModule);
  if (!item) return "";
  return `<section class="workspace module-detail"><div class="workspace-head"><div class="section-title"><h2>${esc(item.display_name)}</h2><button class="btn" id="close-module-detail">返回列表</button></div><p class="detail-copy">${esc(item.plugin_id)} · v${esc(item.version || "未知")} · ${item.status === "normal" ? "运行正常" : "需要关注"}</p><div class="detail-grid"><div><span>加载</span><strong>${item.loaded ? "是" : "否"}</strong></div><div><span>激活</span><strong>${item.activated ? "是" : "否"}</strong></div><div><span>契约</span><strong>${item.contracts}</strong></div><div><span>模块角色</span><strong>${esc(item.contract_details?.module?.role || "未声明")}</strong></div><div><span>统一接管</span><strong>${item.contract_details?.control ? "字段已接入" : "未接入"}</strong></div><div><span>管理面板</span><strong>${item.contract_details?.webui_panels || 0} 个</strong></div><div><span>Standalone</span><strong>${item.contract_details?.module?.standalone?.available ? "已声明" : "未声明"}</strong></div></div><p class="detail-note">字段接管、专属面板与生命周期操作在「系列接管」管理台完成；此处展示运行状态与诊断入口。</p><button class="btn primary" data-control-open="${esc(item.plugin_id)}">打开管理台</button></div></section>`;
}
function modulesView() {
  const normal = state.modules.filter(x => x.status === "normal").length;
  const offline = state.modules.length - normal;
  const updatesPending = state.modules.filter(x => x.update_available).length;
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 生产状态</div><h1>模块运营中心</h1><p>统一查看可信自有模块的运行状态、版本、契约与诊断入口。</p></div><div class="actions"><button class="btn" id="export">导出摘要</button><button class="btn primary" id="check">检查更新</button></div></div><div class="stats"><div class="stat"><label>可信模块</label><strong>${state.modules.length}</strong><small>来自可信登记</small></div><div class="stat"><label>运行正常</label><strong>${normal}</strong><small>核心链路可用</small></div><div class="stat"><label>需关注</label><strong>${offline}</strong><small>非阻断状态</small></div><div class="stat"><label>契约发现</label><strong>已接入</strong><small>版本化能力</small></div><div class="stat"><label>管理边界</label><strong>安全</strong><small>高危操作仍需确认</small></div></div><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>系列模块</h2><span>${filtered().length} 个匹配当前视图 · ${updatesPending} 个有更新 · <button class="link" data-view="updates">查看更新与回滚</button></span></div><div class="filters"><label class="search">⌕<input id="query" placeholder="搜索模块名称或 ID" value="${esc(state.query)}"></label><div class="seg"><button data-filter="all" class="${state.filter === "all" ? "active" : ""}">全部</button><button data-filter="normal" class="${state.filter === "normal" ? "active" : ""}">正常</button><button data-filter="offline" class="${state.filter === "offline" ? "active" : ""}">需关注</button></div><span class="grow"></span><button class="btn" id="reload">刷新状态</button></div></div><div class="table-wrap"><table class="table"><thead><tr><th>模块</th><th>运行状态</th><th>契约</th><th>版本</th><th>操作</th></tr></thead><tbody>${moduleRows()}</tbody></table></div><div class="footer"><span>只纳管可信登记中的凝心溯溪系列插件。</span><span>${state.modules.length} 个模块</span></div></section>${selectedDetail()}`;
}
function relativeTime(timestamp) {
  const time = Date.parse(timestamp || "");
  if (!Number.isFinite(time)) return timestamp || "未知时间";
  const seconds = Math.max(0, Math.round((Date.now() - time) / 1000));
  if (seconds < 60) return `${seconds} 秒前`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)} 分钟前`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} 小时前`;
  return `${Math.floor(seconds / 86400)} 天前`;
}
function logDetailRows(details) {
  if (!details || typeof details !== "object" || !Object.keys(details).length) return `<span class="empty-cell">无附加详情</span>`;
  return `<dl class="log-detail-list">${Object.entries(details).map(([key, value]) => `<div><dt>${esc(key)}</dt><dd>${esc(typeof value === "object" ? JSON.stringify(value) : value)}</dd></div>`).join("")}</dl>`;
}
function diagnosticEvents() {
  const levels = { DEBUG: 0, INFO: 1, WARNING: 2, ERROR: 3, CRITICAL: 4 };
  const now = Date.now();
  const query = state.logQuery.trim().toLowerCase();
  return (state.logs || []).filter(item => {
    if (state.logModules.length && !state.logModules.includes(item.plugin_id)) return false;
    if (state.logThreshold && (levels[item.level] ?? 0) < (levels[state.logThreshold] ?? 0)) return false;
    const timestamp = Date.parse(item.timestamp || "");
    if (state.logRange !== "all" && Number.isFinite(timestamp)) {
      const ranges = { "15m": 900000, "1h": 3600000, today: 86400000 };
      if (now - timestamp > ranges[state.logRange]) return false;
    }
    if (query) return `${item.plugin_name || ""} ${item.plugin_id || ""} ${item.code || ""} ${item.summary || ""} ${JSON.stringify(item.details || {})}`.toLowerCase().includes(query);
    return true;
  }).slice(-500).reverse();
}
function diagnosticProblems() {
  const groups = {};
  (state.logs || []).filter(item => ["ERROR", "WARNING", "CRITICAL"].includes(String(item.level || "").toUpperCase())).forEach(item => {
    const key = `${item.plugin_id}:${item.code || "UNKNOWN"}`;
    const current = groups[key] || { plugin_id: item.plugin_id, plugin_name: item.plugin_name || item.plugin_id, code: item.code || "UNKNOWN", level: item.level, count: 0, last: item.timestamp };
    current.count += 1;
    if (String(item.timestamp || "") > String(current.last || "")) current.last = item.timestamp;
    if (String(item.level || "").toUpperCase() !== "WARNING") current.level = "ERROR";
    groups[key] = current;
  });
  return Object.values(groups).sort((a, b) => (b.level === "ERROR") - (a.level === "ERROR") || b.count - a.count);
}
function problemSuggestion(item) {
  const code = String(item?.code || "").toUpperCase();
  if (code.includes("RATE_LIMIT")) return "GitHub 限流：稍后重试，或先在核 Page 配置镜像 / Token。";
  if (code.includes("TIMEOUT") || code.includes("UNREACHABLE") || code.includes("NETWORK")) return "网络或超时：确认代理与镜像可达后重试。";
  if (code.includes("MIGRAT") || code.includes("SCHEMA") || code.includes("CONFIG")) return "配置或迁移：核对核 Page 中该模块的配置与版本后重试。";
  if (code.includes("AUTH") || code.includes("TOKEN") || code.includes("CREDENTIAL")) return "凭据问题：检查 GitHub Token 或控制中心账户权限。";
  if (code.includes("IMPORT") || code.includes("LOAD")) return "加载失败：展开同模块上下文，确认依赖与运行环境。";
  return "展开事件详情查看同模块上下文后，再决定是否重试。";
}

function diagnosticsView() {
  const problems = diagnosticProblems();
  const memberTotal = (state.logMembers || []).length;
  const memberReady = (state.logMembers || []).filter(item => item.status === "ready").length;
  const memberGap = (state.logMembers || []).filter(item => item.gap).length;
  const memberUnavailable = memberTotal - memberReady;
  const members = memberTotal
    ? `<span class="pill native">${memberReady}/${memberTotal} 正常</span>${memberUnavailable ? `<span class="pill warn">${memberUnavailable} 个未就绪</span>` : ""}${memberGap ? `<span class="pill warn">${memberGap} 个有断层</span>` : ""}`
    : `<span class="pill">未加载</span>`;
  const modules = [...new Map((state.logs || []).map(item => [item.plugin_id, item.plugin_name || item.plugin_id])).entries()];
  const events = diagnosticEvents();
  const problemRows = problems.length ? problems.slice(0, 8).map(item => `<button class="problem-item" data-log-problem="${esc(item.plugin_id)}" data-log-code="${esc(item.code)}"><span class="pill ${item.level === "ERROR" ? "managed" : "warn"}">${esc(item.level)}</span><b>${esc(item.plugin_name)}</b><code>${esc(item.code)}</code><small>${item.count} 次 · ${esc(relativeTime(item.last))}</small><span class="problem-impact">影响范围：仅 ${esc(item.plugin_name)}（当前日志缓冲内 ${item.count} 条）</span><span class="problem-suggestion">建议动作：${esc(problemSuggestion(item))}</span></button>`).join("") : `<p class="empty-cell">当前缓冲区没有警告或错误。</p>`;
  const eventCards = events.length ? events.map(item => {
    const key = `${item.plugin_id}:${item.seq}`;
    const expanded = state.logExpanded.has(key);
    const level = String(item.level || "INFO").toLowerCase();
    const context = expanded ? (state.logs || []).filter(row => row.plugin_id === item.plugin_id && Math.abs(Number(row.seq || 0) - Number(item.seq || 0)) <= 3 && row.seq !== item.seq).sort((a, b) => Number(a.seq || 0) - Number(b.seq || 0)).map(row => `<button class="log-context-item" data-log-seq="${esc(row.seq)}"><code>${esc(row.seq)}</code> ${esc(row.summary || "")}</button>`).join("") : "";
    return `<article class="diagnostic-event level-${esc(level)} ${expanded ? "expanded" : ""} ${state.logNewKeys.has(key) ? "new-event" : ""}" data-log-event="${esc(key)}"><button class="diagnostic-event-head" data-log-toggle="${esc(key)}"><time title="${esc(item.timestamp || "")}">${esc(relativeTime(item.timestamp))}</time><span class="event-module">${esc(item.plugin_name || item.plugin_id)}</span><span class="level-chip level-${esc(level)}">${esc(item.level)}</span><b class="event-message">${esc(item.summary || "未命名事件")}</b><span class="event-chevron">${expanded ? "收起" : "详情"}</span></button>${expanded ? `<div class="diagnostic-event-detail"><div class="event-meta"><span>代码 <code>${esc(item.code || "-")}</code></span><span>序号 <code>${esc(item.seq)}</code></span></div>${logDetailRows(item.details)}${context ? `<div class="log-context"><strong>同模块上下文</strong>${context}</div>` : ""}</div>` : ""}</article>`;
  }).join("") : `<div class="empty-cell">暂无匹配日志，请调整过滤条件或点击「加载日志」。</div>`;
  const selectedModules = modules.map(([id, name]) => `<button class="filter-chip ${state.logModules.includes(id) ? "active" : ""}" data-log-module="${esc(id)}">${esc(name)}</button>`).join("");
  const cursorLabel = state.logPaused ? "已暂停" : state.logCatchUp ? "追平中" : "增量游标";
  const canClear = state.session?.role === "owner" || state.session?.role === "admin";
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 可观测性</div><h1>运行日志</h1><p>先看问题聚合，再展开事件流与上下文。日志来自各模块的 series.diagnostics 业务事件。</p></div><div class="actions"><span class="pill" id="log-cursor">${cursorLabel}</span><label class="switch"><input type="checkbox" id="log-auto" ${state.logAuto ? "checked" : ""} /><span>5 秒自动刷新</span></label><button class="btn" id="log-pause">${state.logPaused ? "继续" : "暂停"}</button><button class="btn" id="log-autoscroll" aria-pressed="${state.logAutoScroll}">自动滚动${state.logAutoScroll ? " ✓" : ""}</button><button class="btn" id="log-export">导出</button><button class="btn" id="refresh-logs">加载日志</button><button class="btn danger" id="clear-logs" ${canClear ? "" : "disabled"}>清空</button></div></div><section class="workspace diagnostic-summary"><div class="workspace-head"><div class="section-title"><h2>待处理问题</h2><span>${problems.length ? `${problems.length} 组待分析问题` : "状态良好"}</span></div></div><div class="problem-list">${problemRows}</div></section><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>事件流</h2><span id="log-summary">显示最近 ${events.length} 条 · 缓存 ${state.logs.length}</span></div></div><div class="diagnostic-filters"><label class="search">⌕<input id="log-search" placeholder="搜索摘要、代码或详情" value="${esc(state.logQuery)}"></label><select id="log-level" class="select"><option value="">全部级别</option>${["ERROR", "WARNING", "INFO", "DEBUG", "CRITICAL"].map(level => `<option value="${level}" ${state.logThreshold === level ? "selected" : ""}>至少 ${level}</option>`).join("")}</select><select id="log-range" class="select">${[["15m", "最近 15 分钟"], ["1h", "最近 1 小时"], ["today", "今天"], ["all", "全部时间"]].map(([value, label]) => `<option value="${value}" ${state.logRange === value ? "selected" : ""}>${label}</option>`).join("")}</select><div class="log-module-filters">${selectedModules || `<span class="form-hint">加载日志后可按模块筛选</span>`}</div></div><div class="diagnostic-log-list" id="diagnostic-log-list">${eventCards}</div></section>`;
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
function modelOptionsFor(kind) {
  const options = state.modelOptions?.capabilities?.[kind];
  if (Array.isArray(options)) return options;
  return (state.settingsData?.providers || []).map(item => ({ ...item, display_name: item.display_name || item.provider_id, models: [] }));
}
function providerSelect(kind, selected, canWrite) {
  const options = [...modelOptionsFor(kind)];
  if (selected && !options.some(item => item.provider_id === selected)) options.unshift({ provider_id: selected, display_name: selected, models: [], in_use: true });
  const body = [`<option value="">回退 AstrBot 原生 Provider</option>`, ...options.map(item => `<option value="${esc(item.provider_id)}" ${item.provider_id === selected ? "selected" : ""}>${esc(item.display_name || item.provider_id)} · ${esc(item.provider_id)}${item.in_use ? "（使用中）" : ""}</option>`)].join("");
  return `<select class="select route-provider" data-route-provider="${esc(kind)}" ${canWrite ? "" : "disabled"}>${body}</select>`;
}
function modelSelect(kind, providerId, selected, canWrite) {
  const provider = modelOptionsFor(kind).find(item => item.provider_id === providerId);
  const models = provider?.models || [];
  const hasSelected = models.includes(selected);
  if (!providerId || !models.length || (selected && !hasSelected)) return `<input class="route-model" data-route-model="${esc(kind)}" type="text" value="${esc(selected)}" placeholder="模型名（可自定义）" ${canWrite ? "" : "disabled"} />`;
  return `<select class="select route-model" data-route-model="${esc(kind)}" ${canWrite ? "" : "disabled"}><option value="">选择模型…</option>${models.map(model => `<option value="${esc(model)}" ${model === selected ? "selected" : ""}>${esc(model)}</option>`).join("")}<option value="__custom__">自定义输入…</option></select>`;
}
function settingsView() {
  const s = state.settingsData?.settings || {};
  const route = s.model_routing || {};
  const canWrite = state.session?.role === "owner" || state.session?.role === "admin";
  const labels = [["conversation", "对话 / LLM"], ["fast", "快速模型 / Fast"], ["reasoning", "推理模型 / Reasoning"], ["embedding", "向量 / Embedding"], ["vision", "识图 / 视觉"], ["stt", "语音识别 / STT"], ["tts", "语音合成 / TTS"]];
  const routeRows = labels.map(([kind, label]) => {
    const item = route[kind] || {};
    const voice = kind === "tts" ? `<td><input class="route-voice" data-setting-route="${kind}.voice" type="text" value="${esc(item.voice || "")}" placeholder="音色（可选）" ${canWrite ? "" : "disabled"} /></td>` : "";
    return `<tr><td><b>${label}</b><small>${kind === "tts" ? "Provider · 模型 · 音色" : "Provider · 模型"}</small></td><td>${providerSelect(kind, item.provider_id || "", canWrite)}</td><td>${modelSelect(kind, item.provider_id || "", item.model || "", canWrite)}</td>${voice}</tr>`;
  }).join("");
  const resolvedRows = Object.entries(state.routes?.routes || {}).map(([kind, item]) => { const label = (labels.find(entry => entry[0] === kind) || [kind, kind])[1]; return `<tr><td>${esc(label)}</td><td><code>${esc(item.provider_id || "未配置")}</code></td><td>${esc(item.model || "自动")}</td><td>${esc(item.source || "unavailable")}</td><td><span class="status ${item.available ? "" : "off"}">${item.available ? "可用" : "不可用"}</span></td></tr>`; }).join("");
  const handled = new Set(["model_routing", "auto_update_enabled", "log_level", "webui_host", "webui_port", "webui_public_url"]);
  const genericRows = Object.entries(state.settingsData?.schema || {}).filter(([key]) => !handled.has(key) && key !== "model_routing").map(([key, def]) => {
    const value = s[key];
    const disabled = !canWrite || def.read_only;
    let input;
    if (def.type === "bool") input = `<label class="switch"><input type="checkbox" data-setting-key="${esc(key)}" data-setting-type="bool" ${value?.configured ?? value ? "checked" : ""} ${disabled ? "disabled" : ""} /><span>${def.read_only ? "只读" : "启用"}</span></label>`;
    else if (def.type === "int" || def.type === "float") input = `<input type="number" step="${def.type === "float" ? "any" : "1"}" ${def.minimum != null ? `min="${esc(def.minimum)}"` : ""} ${def.maximum != null ? `max="${esc(def.maximum)}"` : ""} data-setting-key="${esc(key)}" data-setting-type="${esc(def.type)}" value="${esc(def.write_only ? "" : (value ?? ""))}" placeholder="${def.write_only ? (value?.configured ? "已配置；留空保持不变" : "未配置") : ""}" ${disabled ? "disabled" : ""} />`;
    else if (Array.isArray(def.options)) input = `<select data-setting-key="${esc(key)}" data-setting-type="string" ${disabled ? "disabled" : ""}>${def.options.map(option => `<option value="${esc(option)}" ${String(value) === String(option) ? "selected" : ""}>${esc(option)}</option>`).join("")}</select>`;
    else input = `<input type="${def.write_only ? "password" : "text"}" data-setting-key="${esc(key)}" data-setting-type="string" value="${esc(def.write_only ? "" : (value ?? ""))}" placeholder="${def.write_only ? (value?.configured ? "已配置；留空保持不变" : "未配置") : ""}" ${disabled ? "disabled" : ""} />`;
    const label = fieldLabel(key, def);
    const meta = [typeLabel(def.type), def.read_only ? "重启/部署层字段" : "", def.write_only ? "写入后不回显" : ""].filter(Boolean).join(" · ");
    const hint = fieldHint(key, def);
    const hintHtml = `<small class="field-hint row-hint">${hint && hint !== label ? esc(hint) : ""}</small>`;
    return `<div class="form-row" title="技术名：${esc(key)}"><label><strong>${esc(label)}</strong><small>${esc(meta)}</small></label><div class="form-input">${input}</div><div class="form-meta"></div>${hintHtml}</div>`;
  }).join("");
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 模型策略</div><h1>全局设置</h1><p>统一模型路由与运行项可直接在此编辑；密钥类配置仍在核 Page 维护。WebUI 连接项保存后需重启生效。</p></div><div class="actions"><button class="btn" id="settings-reload">重读</button><button class="btn primary" id="save-settings" ${canWrite ? "" : "disabled"}>保存设置</button></div></div><nav class="si-subnav" role="tablist" aria-label="设置分区"><button type="button" role="tab" data-si-tab="route">模型路由</button><button type="button" role="tab" data-si-tab="runtime">运行项</button><button type="button" role="tab" data-si-tab="config">完整配置</button><button type="button" role="tab" data-si-tab="resolved">解析快照</button></nav><section class="workspace" data-si-panel="route"><div class="workspace-head"><div class="section-title"><h2>统一模型路由</h2><span>留空 = 回退 AstrBot 原生模型服务</span></div></div><div class="route-note">模型服务商与模型来自 AstrBot 当前已加载配置；无法枚举模型的服务商保留手动输入。</div><div class="table-wrap"><table class="table"><thead><tr><th>能力</th><th>模型服务商</th><th>模型</th><th>TTS 音色</th></tr></thead><tbody>${routeRows}</tbody></table></div></section><section class="workspace" data-si-panel="runtime"><div class="workspace-head"><div class="section-title"><h2>运行项</h2><span>保存后即时生效</span></div></div><div class="form-grid"><div class="form-row"><label title="技术名：auto_update_enabled"><strong>启用自动更新</strong><small>开关 · 到期自动检查并更新系列插件</small></label><div class="form-input"><label class="switch"><input type="checkbox" id="setting-auto-update" ${s.auto_update_enabled ? "checked" : ""} ${canWrite ? "" : "disabled"} /><span>启用自动更新</span></label></div><div class="form-meta"></div></div><div class="form-row"><label title="技术名：log_level"><strong>日志级别</strong><small>文本 · 核自身日志级别</small></label><div class="form-input"><select id="setting-log-level" class="select" ${canWrite ? "" : "disabled"}>${["DEBUG", "INFO", "WARNING", "ERROR"].map(level => `<option value="${level}" ${String(s.log_level || "INFO").toUpperCase() === level ? "selected" : ""}>${level}</option>`).join("")}</select></div><div class="form-meta"></div></div><div class="form-row"><label title="技术名：webui_host"><strong>WebUI 监听地址</strong><small>文本 · 绑定地址（重启生效）</small></label><div class="form-input"><input type="text" id="setting-webui-host" value="${esc(s.webui_host || "")}" ${canWrite ? "" : "disabled"} /></div><div class="form-meta"></div></div><div class="form-row"><label title="技术名：webui_port"><strong>WebUI 端口</strong><small>整数 · 修改后需重启（重启生效）</small></label><div class="form-input"><input type="number" id="setting-webui-port" min="1" max="65535" value="${esc(s.webui_port ?? "")}" ${canWrite ? "" : "disabled"} /></div><div class="form-meta"></div></div><div class="form-row"><label title="技术名：webui_public_url"><strong>WebUI 对外地址</strong><small>文本 · 对外展示地址（重启生效）</small></label><div class="form-input"><input type="text" id="setting-webui-url" value="${esc(s.webui_public_url || "")}" ${canWrite ? "" : "disabled"} /></div><div class="form-meta"></div></div></div></section><section class="workspace" data-si-panel="config"><div class="workspace-head"><div class="section-title"><h2>完整配置</h2><span>${Object.keys(state.settingsData?.schema || {}).length} 个字段；只读字段不会提交</span></div></div><div class="form-grid">${genericRows || `<p class="empty-cell">当前后端未提供配置 schema。</p>`}</div></section><section class="workspace" data-si-panel="resolved"><div class="workspace-head"><div class="section-title"><h2>当前路由解析快照</h2><span>模型路由 1.0</span></div></div><div class="table-wrap"><table class="table"><thead><tr><th>能力</th><th>模型服务商</th><th>模型</th><th>来源</th><th>状态</th></tr></thead><tbody>${resolvedRows}</tbody></table></div><div class="footer"><span>插件显式配置 &gt; 核路由 &gt; AstrBot 原生模型服务。</span><span>只接受安全字段，不回显密钥。</span></div></section>`;
}
const FEATURE_DOMAINS = [
  {
    id: "message",
    title: "对话与消息",
    icon: "言",
    description: "沉默、分段、防抖、插话、上下文承接与回复交付。",
    features: ["沉默判断", "智能分段", "运行中插话", "话题承接", "上下文预算", "群聊语境"],
    actions: [{ kind: "plugin", label: "管理对话策略", plugin_id: "astrbot_plugin_conversation_flow" }],
  },
  {
    id: "identity",
    title: "身份与权限",
    icon: "序",
    description: "身份识别、私聊授权、群管理边界与入群审核。",
    features: ["身份识别", "行动授权", "群管理", "入群审核", "权限否决"],
    actions: [{ kind: "plugin", label: "管理身份权限", plugin_id: "astrbot_plugin_identity_guardian" }],
  },
  {
    id: "relationship",
    title: "关系与情绪",
    icon: "情",
    description: "好感、信任、熟悉度、关系性质与表达建议。",
    features: ["好感度", "四维信任", "熟悉度", "关系性质", "情绪建议", "账号归属"],
    actions: [{ kind: "plugin", label: "管理关系状态", plugin_id: "astrbot_plugin_relationship" }],
  },
  {
    id: "knowledge",
    title: "知识与记忆",
    icon: "知",
    description: "知识检索、交叉验证、知识图谱、记忆生命周期与导入导出。",
    features: ["知识检索", "交叉验证", "知识图谱", "记忆管理", "导入导出"],
    actions: [{ kind: "plugin", label: "管理知识记忆", plugin_id: "astrbot_plugin_active_learner" }],
  },
  {
    id: "environment",
    title: "环境与时间",
    icon: "境",
    description: "时间、天气、空气质量、日历、预警和主动环境关心。",
    features: ["时间", "天气", "空气质量", "日历", "预警", "主动关心"],
    actions: [{ kind: "plugin", label: "管理环境感知", plugin_id: "astrbot_plugin_environment_awareness" }],
  },
  {
    id: "voice",
    title: "语音与表达",
    icon: "声",
    description: "语音合成、音色、情绪映射、语音导演与音频交付。",
    features: ["语音合成", "音色管理", "情绪映射", "语音导演", "音频试听"],
    actions: [{ kind: "plugin", label: "管理语音表达", plugin_id: "astrbot_plugin_voice_hub" }],
  },
  {
    id: "embodiment",
    title: "具身与设备",
    icon: "临",
    description: "设备配对、会话桥接、角色动作与具身诊断。",
    features: ["设备配对", "会话桥接", "角色动作", "人格模式", "实时诊断"],
    actions: [{ kind: "plugin", label: "管理具身设备", plugin_id: "astrbot_plugin_embodiment_bridge" }],
  },
  {
    id: "governance",
    title: "更新与治理",
    icon: "核",
    description: "更新规则、镜像、推荐、回滚、模型角色与全局设置。",
    features: ["每日规则", "镜像加速", "系列推荐", "更新回滚", "模型角色", "全局设置"],
    actions: [
      { kind: "view", label: "每日规则", view: "rules" },
      { kind: "view", label: "镜像加速", view: "mirrors" },
      { kind: "view", label: "全局设置", view: "settings" },
    ],
  },
];

function controlStatusLabel(member, domainId = "") {
  if (domainId === "governance") return "核内置";
  if (!member) return "未接入";
  if (member.status === "managed") return "统一接管";
  if (member.status === "native") return "独立配置";
  return member.status === "not_loaded" ? "未加载" : "待检查";
}

function controlReasonLabel(reason) {
  return ({
    OK: "运行正常",
    CONTRACT_UNAVAILABLE: "未提供统一控制",
    PLUGIN_NOT_LOADED: "模块未加载",
    CONTRACT_VERSION_UNSUPPORTED: "契约版本不兼容",
    TAKEOVER_DISABLED: "当前为独立配置",
  })[String(reason || "")] || String(reason || "运行正常");
}

function controlView() {
  const control = state.control || { mode: "native", members: [], revision: 0 };
  const members = new Map((control.members || []).map(item => [item.plugin_id, item]));
  const cards = FEATURE_DOMAINS.map(domain => {
    const pluginAction = domain.actions.find(action => action.kind === "plugin");
    const member = pluginAction ? members.get(pluginAction.plugin_id) : null;
    const status = controlStatusLabel(member, domain.id);
    const statusClass = status === "统一接管" ? "" : status === "独立配置" ? "native" : "warn";
    const available = Boolean(member && member.status !== "not_loaded");
    const buttons = domain.actions.map(action => action.kind === "view"
      ? `<button class="btn" data-domain-view="${esc(action.view)}">${esc(action.label)}</button>`
      : `<button class="btn primary" data-control-plugin="${esc(action.plugin_id)}" ${available ? "" : "disabled"}>${esc(action.label)}</button>`
    ).join("");
    const features = domain.features.map(feature => `<span class="pill">${esc(feature)}</span>`).join("");
    return `<article class="workspace feature-domain" data-feature-domain="${esc(domain.id)}"><div class="feature-domain-head"><span class="feature-domain-icon">${esc(domain.icon)}</span><div><h2>${esc(domain.title)}</h2><p>${esc(domain.description)}</p></div><span class="pill ${statusClass}">${esc(status)}</span></div><div class="feature-domain-tags">${features}</div><div class="feature-domain-foot"><small>${member?.reason ? `状态：${esc(controlReasonLabel(member.reason))}` : "功能按领域统一归口，不展示模块身份细节。"}</small><div class="actions">${buttons}</div></div></article>`;
  }).join("");
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 统一接管</div><h1>系列接管</h1><p>功能按使用场景分类统一管理；关闭接管后各模块恢复独立配置。高级更新与生命周期操作仍在对应功能域内。</p></div><div class="actions"><button class="btn" id="refresh-control">刷新</button>${state.session?.role === "owner" ? `<button class="btn primary" id="toggle-control">${control.mode === "managed" ? "关闭统一接管" : "启用统一接管"}</button>` : ""}</div></div><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>当前接管模式</h2><span>版本号 ${esc(control.revision)}</span></div></div><div class="control-mode-summary"><div><span>运行模式</span><strong>${control.mode === "managed" ? "统一接管" : "独立配置"}</strong></div><div><span>功能域</span><strong>${FEATURE_DOMAINS.length}</strong></div><div><span>已接管</span><strong>${[...members.values()].filter(item => item.status === "managed").length}</strong></div><div><span>待检查</span><strong>${[...members.values()].filter(item => !["managed", "native"].includes(item.status)).length}</strong></div></div></section><section class="feature-domain-grid">${cards}</section>${controlDetail()}`;
}
function controlDetail() {
  if (!state.selectedControlPlugin) return "";
  const schema = state.controlSchema;
  const pluginId = schema?.plugin_id || state.selectedControlPlugin;
  const member = (state.control?.members || []).find(item => item.plugin_id === pluginId);
  const displayName = member?.display_name || pluginId;
  const snapshot = state.controlSnapshot || { snapshot: { fields: {} } };
  const tabs = [["fields", "字段接管"], ["panels", "插件面板"], ["lifecycle", "生命周期"]];
  const strip = `<div class="tab-strip">${tabs.map(([id, label]) => `<button class="${state.controlTab === id ? "active" : ""}" data-control-tab="${id}">${label}</button>`).join("")}</div>`;
  let body = "";
  if (state.controlTab === "panels") body = controlPanelsTab();
  else if (state.controlTab === "lifecycle") body = controlLifecycleTab();
  else body = controlFieldsTab(schema, snapshot);
  const domain = FEATURE_DOMAINS.find(item => item.actions.some(action => action.kind === "plugin" && action.plugin_id === pluginId));
  const title = domain?.title || "功能控制";
  return `<section class="workspace"><div class="workspace-head"><div class="section-title"><h2>${esc(title)}</h2><span>版本号 ${esc(schema?.revision ?? "—")}</span></div><button class="btn" id="close-control-detail">返回功能域</button></div>${strip}<div class="control-body">${body}</div></section>`;
}
function controlFieldsTab(schema, snapshot) {
  const fields = schema?.schema?.fields || {};
  const values = snapshot?.snapshot?.fields || {};
  const managed = schema?.mode === "managed";
  const canWrite = (state.session?.role === "owner" || state.session?.role === "admin") && managed;
  const rowsHtml = Object.entries(fields).map(([name, def]) => {
    const value = values[name] || {};
    const current = value.effective_value ?? def.default ?? "";
    const managed = !!value.managed_configured;
    const source = managed ? `<span class="pill managed">核覆盖</span>` : `<span class="pill native">插件</span>`;
    let input = "";
    if (def.secret) input = `<input type="password" data-control-field="${esc(name)}" placeholder="${current ? "已配置（不回显）" : "未配置"}" ${canWrite ? "" : "disabled"}>`;
    else if (def.type === "bool") input = `<label class="switch"><input type="checkbox" data-control-field="${esc(name)}" ${current === true ? "checked" : ""} ${canWrite ? "" : "disabled"} /><span>启用</span></label>`;
    else if (def.type === "int" || def.type === "float") input = `<input type="number" step="${def.type === "float" ? "any" : "1"}" min="${esc(def.minimum ?? "")}" max="${esc(def.maximum ?? "")}" value="${esc(current === null ? "" : current)}" data-control-field="${esc(name)}" ${canWrite ? "" : "disabled"}>`;
    else input = `<input type="text" value="${esc(current === null ? "" : current)}" data-control-field="${esc(name)}" ${canWrite ? "" : "disabled"}>`;
    const note = def.control === "read_only" ? `<span class="pill">只读</span>` : "";
    const ctrlLabel = fieldLabel(name, def);
    const ctrlHint = fieldHint(name, def);
    const ctrlHintHtml = `<small class="field-hint row-hint">${ctrlHint && ctrlHint !== ctrlLabel ? esc(ctrlHint) : ""}</small>`;
    return `<div class="form-row" title="技术名：${esc(name)}"><label><strong>${esc(ctrlLabel)}</strong><small>${esc(typeLabel(def.type))}</small></label><div class="form-input">${input}</div><div class="form-meta">${source}${note}</div>${ctrlHintHtml}</div>`;
  }).join("") || `<p class="empty-cell">该插件未声明可管理字段。</p>`;
  const hint = !managed
    ? "统一接管未启用：字段以插件 native 配置为准，开启统一接管后才能在此修改。"
    : canWrite
      ? "修改后点击「应用修改」：先校验再写入覆盖层，带并发保护。"
      : "当前角色为 viewer，仅可查看字段。";
  return `<div class="form-hint">${hint}</div><div class="form-grid">${rowsHtml}</div><div class="form-actions"><button class="btn primary" id="control-apply" ${canWrite ? "" : "disabled"}>应用修改</button><button class="btn" id="control-reset" ${canWrite ? "" : "disabled"}>重置全部覆盖</button><button class="btn" id="control-refresh-fields">刷新字段</button></div>`;
}
function controlPanelsTab() {
  const pluginId = state.selectedControlPlugin;
  if (state.takeoverDisabled) return `<p class="empty-cell">统一接管未启用：managed 面板已关闭，请使用该插件的独立 Page。</p><p class="form-hint">开启“统一接管”后，核会重新加载该模块面板。</p>`;
  if (!state.panelsList) return `<p class="empty-cell">尚未加载面板。${`<button class="btn primary" id="panel-load">加载该插件面板</button>`}</p><p class="form-hint">面板来自插件提供的面板接口；未实现该接口的插件此区为空。</p>`;
  const panels = state.panelsList.panels || [];
  if (!panels.length) return `<p class="empty-cell">该插件未提供管理面板（未提供面板接口）。</p>`;
  const buttons = panels.map(panel => `<button class="btn ${state.selectedPanel === panel.id ? "primary" : ""}" data-panel-select="${esc(panel.id)}">${esc(panel.title)}</button>`).join("");
  const unsupported = state.panelsList?.unsupported_capabilities || [];
  const capabilityHint = unsupported.length
    ? `<p class="form-hint">当前核版本尚不支持：${unsupported.map(esc).join("、")}；相关功能请使用插件独立 Page。</p>`
    : "";
  let content = "";
  if (state.panelData && state.selectedPanel) content = panelContent(state.panelData);
  return `<div class="panel-nav">${buttons}</div>${capabilityHint}<div class="panel-body">${content || `<p class="empty-cell">选择一个面板查看。</p>`}</div>`;
}
function roleRank(role) { return ({ viewer: 0, admin: 1, owner: 2 })[role] ?? -1; }
function actionAllowed(action) { return roleRank(state.session?.role) >= roleRank(action.min_role || "admin"); }
function panelContent(data) {
  const columns = data.columns || [];
  const rows = data.rows || [];
  const table = columns.length ? `<div class="table-wrap"><table class="table"><thead><tr>${columns.map(col => `<th>${esc(col.label || col.key)}</th>`).join("")}</tr></thead><tbody>${rows.length ? rows.map(row => `<tr>${columns.map(col => `<td>${esc(row[col.key] ?? "—")}</td>`).join("")}</tr>`).join("") : `<tr><td colspan="${columns.length}" class="empty-cell">暂无数据</td></tr>`}</tbody></table></div>` : "";
  const actions = (data.actions || []).map(action => {
    const allowed = actionAllowed(action);
    const disabled = allowed ? "" : "disabled";
    const fields = (action.payload_fields || []).map(field => {
      const name = esc(field.name);
      const label = esc(field.label || field.name);
      const hint = esc(field.hint || "");
      const value = field.default == null ? "" : esc(field.default);
      if (field.type === "select") return `<label><span>${label}</span><select data-panel-field="${name}" ${disabled}>${(field.options || []).map(opt => `<option value="${esc(opt[0])}" ${String(opt[0]) === String(field.default ?? "") ? "selected" : ""}>${esc(opt[1])}</option>`).join("")}</select></label>`;
      if (field.type === "file") return `<label><span>${label}</span><input type="file" data-panel-file="${name}" ${field.multiple ? "multiple" : ""} ${disabled} /></label>`;
      if (field.type === "bool" || field.type === "boolean") return `<label><span>${label}</span><span class="switch"><input type="checkbox" data-panel-field="${name}" data-field-type="bool" ${field.default ? "checked" : ""} ${disabled} /><span>${hint || "启用"}</span></span></label>`;
      if (field.type === "textarea") return `<label><span>${label}</span><textarea data-panel-field="${name}" data-field-type="text" placeholder="${hint}" ${disabled}>${value}</textarea></label>`;
      const inputType = field.type === "number" ? "number" : field.type === "password" || field.secret ? "password" : "text";
      return `<label><span>${label}</span><input type="${inputType}" data-panel-field="${name}" data-field-type="${field.type === "number" ? "number" : "text"}" value="${value}" placeholder="${hint}" ${disabled} /></label>`;
    }).join("");
    return `<div class="panel-action">${fields ? `<div class="panel-action-form">${fields}</div>` : ""}<button class="btn ${action.danger ? "danger" : "primary"}" data-panel-action="${esc(action.id)}" data-action-effect="${esc(action.effect || "idempotent")}" data-action-revision-required="${action.revision_required ? "true" : "false"}" data-action-idempotency-required="${action.idempotency_required ? "true" : "false"}" ${disabled}>${esc(action.label || action.id)}${allowed ? "" : ` · 需要 ${esc(action.min_role || "admin")}`}</button></div>`;
  }).join("");
  const artifacts = Array.isArray(data.artifacts) ? data.artifacts : [];
  const artifactHtml = artifacts.length
    ? `<div class="artifact-list">${artifacts.map(item => `<a class="btn" href="/api/artifacts/${encodeURIComponent(item.artifact_id || "")}" target="_blank" rel="noopener">${esc(item.filename || item.artifact_id || "下载")}</a>`).join("")}</div>`
    : "";
  const audioHtml = data.audio?.artifact_id
    ? `<audio controls preload="none" src="/api/artifacts/${encodeURIComponent(data.audio.artifact_id)}"></audio>`
    : "";
  const streamHtml = data.stream
    ? `<div class="panel-stream-controls"><button class="btn" id="panel-stream-start" type="button">开始实时流</button><pre id="panel-stream" class="panel-stream"></pre></div>`
    : "";
  return `${data.title ? `<div class="section-title"><h3>${esc(data.title)}</h3>${data.description ? `<span>${esc(data.description)}</span>` : ""}</div>` : ""}${table}${actions ? `<div class="panel-actions">${actions}</div>` : ""}${artifactHtml}${audioHtml}${streamHtml}${data.footer ? `<p class="form-hint">${esc(data.footer)}</p>` : ""}`;
}
function controlLifecycleTab() {
  const pluginId = state.selectedControlPlugin;
  const module = state.modules.find(item => item.plugin_id === pluginId);
  const isOwner = state.session?.role === "owner";
  const status = module ? `<span class="status ${module.status === "normal" ? "" : "off"}">${module.status === "normal" ? "运行正常" : "已停用/未加载"}</span>` : `<span class="pill">未安装</span>`;
  return `<div class="detail-grid"><div><span>当前状态</span><strong>${status}</strong></div><div><span>当前版本</span><strong><code>v${esc(module?.version || "未知")}</code></strong></div><div><span>更新检查</span><strong>${module?.update_available ? "有更新" : "未检查/当前"}</strong></div></div><p class="form-hint">${isOwner ? "操作走核的事务路径（串行、可回滚、热重载），执行前需确认；仅 owner 可执行。" : "生命周期操作仅 owner 可执行。"}</p><div class="form-actions"><label class="switch"><input type="checkbox" id="lifecycle-force" /><span>强制更新（覆盖本地）</span></label><button class="btn primary" data-lifecycle="update" ${isOwner && module ? "" : "disabled"}>更新</button><button class="btn" data-lifecycle="enable" ${isOwner && module ? "" : "disabled"}>启用</button><button class="btn danger" data-lifecycle="disable" ${isOwner && module ? "" : "disabled"}>停用</button><button class="btn" data-lifecycle="install" ${isOwner && !module ? "" : "disabled"}>安装</button></div>`;
}
function rulesView() {
  const data = state.rulesData;
  const canWrite = state.session?.role === "owner" || state.session?.role === "admin";
  if (!data) return `<div class="page-head"><div><div class="eyebrow">系列治理 / 生命周期</div><h1>每日规则</h1><p>加载中…</p></div></div>`;
  const rule = data.rule || {};
  const selected = new Set(rule.plugin_ids || []);
  const policies = [["check_only", "只检查，不更新"], ["patch", "补丁版本"], ["minor", "次版本"], ["stable", "稳定版本"]];
  const failures = [["rollback_continue", "失败回滚后继续"], ["rollback_stop", "失败回滚并停止"]];
  const pluginRows = (data.catalog || []).map(item => `<label class="filter-chip ${selected.has(item.plugin_id) ? "active" : ""}"><input type="checkbox" data-rule-plugin="${esc(item.plugin_id)}" ${selected.has(item.plugin_id) ? "checked" : ""} ${canWrite ? "" : "disabled"} /> ${esc(item.display_name || item.plugin_id)} <small>v${esc(item.version || "?")}</small></label>`).join("");
  const globalState = data.global?.effective ? "规则与总开关均已启用" : "当前不会自动执行，请检查总开关、自动更新与规则开关";
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 生命周期</div><h1>每日规则</h1><p>统一管理更新窗口、版本策略、失败处理与目标模块；保存带并发保护，避免两台页面互相覆盖。</p></div><div class="actions"><button class="btn" id="rules-reload">重读</button><button class="btn primary" id="save-rule" ${canWrite ? "" : "disabled"}>保存规则</button></div></div><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>执行窗口</h2><span>${esc(globalState)}</span></div></div><div class="form-grid"><div class="form-row"><label title="技术名：enabled"><strong>启用此规则</strong><small>每日规则自身开关</small></label><div class="form-input"><label class="switch"><input id="rule-enabled" type="checkbox" ${rule.enabled ? "checked" : ""} ${canWrite ? "" : "disabled"} /><span>启用此规则</span></label></div><div class="form-meta"><span class="pill">revision ${esc(rule.revision ?? 0)}</span></div></div><div class="form-row"><label title="技术名：local_time"><strong>执行时间</strong><small>每天执行时间</small></label><div class="form-input"><input id="rule-time" type="time" value="${esc(rule.local_time || "04:00")}" ${canWrite ? "" : "disabled"} /></div><div class="form-meta"></div></div><div class="form-row"><label title="技术名：timezone"><strong>时区</strong><small>IANA 时区</small></label><div class="form-input"><input id="rule-timezone" value="${esc(rule.timezone || "Asia/Shanghai")}" ${canWrite ? "" : "disabled"} /></div><div class="form-meta"></div></div><div class="form-row"><label title="技术名：jitter_minutes"><strong>随机延迟（分钟）</strong><small>随机抖动，避免同时请求</small></label><div class="form-input"><input id="rule-jitter" type="number" min="0" max="120" value="${esc(rule.jitter_minutes ?? 0)}" ${canWrite ? "" : "disabled"} /></div><div class="form-meta"></div></div><div class="form-row"><label title="技术名：misfire_grace_minutes"><strong>错过执行的宽限（分钟）</strong><small>错过后的补执行窗口</small></label><div class="form-input"><input id="rule-misfire" type="number" min="0" max="1440" value="${esc(rule.misfire_grace_minutes ?? 60)}" ${canWrite ? "" : "disabled"} /></div><div class="form-meta"></div></div></div></section><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>版本与失败策略</h2><span>${data.next_run ? `下次执行：${esc(data.next_run)}` : "当前无计划"}</span></div></div><div class="form-grid"><div class="form-row"><label title="技术名：policy"><strong>更新策略</strong><small>允许升级的最大范围</small></label><div class="form-input"><select id="rule-policy" ${canWrite ? "" : "disabled"}>${policies.map(([value, label]) => `<option value="${value}" ${rule.policy === value ? "selected" : ""}>${label}</option>`).join("")}</select></div><div class="form-meta"></div></div><div class="form-row"><label title="技术名：minimum_release_age_hours"><strong>最小发布年龄（小时）</strong><small>发布冷却时间</small></label><div class="form-input"><input id="rule-age" type="number" min="0" max="8760" value="${esc(rule.minimum_release_age_hours ?? 24)}" ${canWrite ? "" : "disabled"} /></div><div class="form-meta"></div></div><div class="form-row"><label title="技术名：on_failure"><strong>失败处理</strong><small>失败回滚策略</small></label><div class="form-input"><select id="rule-failure" ${canWrite ? "" : "disabled"}>${failures.map(([value, label]) => `<option value="${value}" ${rule.on_failure === value ? "selected" : ""}>${label}</option>`).join("")}</select></div><div class="form-meta"></div></div><div class="form-row"><label title="技术名：prerelease"><strong>允许预发布版本</strong><small>是否接受预发布版本</small></label><div class="form-input"><label class="switch"><input id="rule-prerelease" type="checkbox" ${rule.prerelease ? "checked" : ""} ${canWrite ? "" : "disabled"} /><span>允许 prerelease</span></label></div><div class="form-meta"></div></div></div></section><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>目标模块</h2><span>${selected.size} 个已选择；核自身始终排除</span></div></div><div class="log-module-filters">${pluginRows || `<span class="empty-cell">当前没有可选择的已加载模块。</span>`}</div><p class="form-hint">${esc(data.policy_note || "规则保存后会立即重建调度。")}</p></section>`;
}
function mirrorsView() {
  const data = state.mirrorsData;
  const canWrite = state.session?.role === "owner" || state.session?.role === "admin";
  if (!data) return `<div class="page-head"><div><div class="eyebrow">系列治理 / 网络</div><h1>镜像加速</h1><p>加载中…</p></div></div>`;
  const results = new Map((state.mirrorResults || []).map(item => [item.url, item]));
  const candidates = (data.candidates || []).map(item => {
    const result = results.get(item.url);
    const measured = result ? `<span class="pill ${result.available ? "native" : "managed"}">${result.available ? `${result.latency_ms ?? "?"} ms` : "不可用"}</span>` : `<span class="pill">未测速</span>`;
    return `<tr><td><label class="switch"><input type="radio" name="mirror-choice" value="${esc(item.url)}" ${item.selected ? "checked" : ""} ${canWrite ? "" : "disabled"} /><span>${item.builtin ? "内置" : "自定义"}</span></label></td><td><code>${esc(item.url)}</code></td><td>${measured}</td></tr>`;
  }).join("");
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 网络</div><h1>镜像加速</h1><p>镜像只加速 GitHub 下载；失败自动回退直连。测速只做诊断，不会改变已选配置。</p></div><div class="actions"><button class="btn" id="mirrors-reload">重读</button><button class="btn" id="benchmark-mirrors" ${canWrite ? "" : "disabled"}>一键测速</button><button class="btn primary" id="save-mirror" ${canWrite ? "" : "disabled"}>保存选择</button></div></div><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>候选站点</h2><span>超时 ${esc(data.benchmark_timeout_seconds || "?")} 秒/站</span></div></div><div class="table-wrap"><table class="table"><thead><tr><th>类型</th><th>地址</th><th>延迟</th></tr></thead><tbody><tr><td><label class="switch"><input type="radio" name="mirror-choice" value="" ${data.direct ? "checked" : ""} ${canWrite ? "" : "disabled"} /><span>直连</span></label></td><td><code>github.com</code></td><td><span class="pill native">默认</span></td></tr>${candidates}</tbody></table></div><div class="footer"><span>探测目标：<code>${esc(data.probe_url || "")}</code></span><span>${state.mirrorResults?.length || 0} 个结果</span></div></section>`;
}
function recommendationsView() {
  const data = state.recommendationsData;
  const canCheck = state.session?.role === "owner" || state.session?.role === "admin";
  const canApply = state.session?.role === "owner";
  if (!data) return `<div class="page-head"><div><div class="eyebrow">系列治理 / 全系列</div><h1>系列推荐</h1><p>加载中…</p></div></div>`;
  const rows = (data.items || []).map(item => {
    const actions = item.actions || {};
    const status = item.installed ? (item.update_available ? `<span class="pill managed">可更新${item.latest_version ? ` → v${esc(item.latest_version)}` : ""}</span>` : `<span class="pill native">${esc(item.version_status || "已安装")}</span>`) : `<span class="pill">未安装</span>`;
    return `<tr><td><b>${esc(item.name || item.plugin_id)}</b><small>${esc(item.plugin_id)}</small></td><td>${status}</td><td><code>${item.installed ? "v" + esc(item.version || "?") : "—"}</code></td><td><button class="link" data-control-open="${esc(item.plugin_id)}">${actions.install || actions.update ? "前往接管台" : "查看状态"}</button></td></tr>`;
  }).join("");
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 全系列</div><h1>系列推荐</h1><p>固定可信清单的安装与版本状态；批量操作串行执行，核自身不会自更新。</p></div><div class="actions"><button class="btn primary" id="check-recommendations" ${canCheck ? "" : "disabled"}>检查最新版本</button><button class="btn danger" id="apply-recommendations" ${canApply ? "" : "disabled"}>一键安装/更新</button></div></div><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>可信模块</h2><span>${data.items?.length || 0} 个模块</span></div></div><div class="table-wrap"><table class="table"><thead><tr><th>模块</th><th>状态与目标版本</th><th>当前版本</th><th>操作</th></tr></thead><tbody>${rows || `<tr><td colspan="4" class="empty-cell">暂无模块。</td></tr>`}</tbody></table></div><div class="footer"><span>普通更新只在远端版本更高时执行。</span><span>${data.rate_limit ? `GitHub 剩余 ${esc(data.rate_limit.remaining ?? "?")}` : "未读取限流状态"}</span></div></section>`;
}
function securityView() {
  const data = state.adminsData;
  const canManage = state.session?.role === "owner";
  const admins = data?.admins || [];
  const rows = admins.map(item => `<article class="account-card" data-admin-card="${esc(item.id)}"><header class="account-card-head"><div><b>${esc(item.username)}</b><small>${esc(item.id)}</small></div><span class="pill ${item.enabled ? "native" : "warn"}">${item.enabled ? "启用" : "禁用"}</span></header><div class="account-card-grid"><label class="account-card-field"><span>角色</span><select data-admin-role="${esc(item.id)}" ${canManage ? "" : "disabled"}>${[["owner", "所有者"], ["admin", "管理员"], ["viewer", "只读"]].map(([role, label]) => `<option value="${role}" ${item.role === role ? "selected" : ""}>${label}</option>`).join("")}</select></label><label class="account-card-field"><span>状态</span><span class="switch"><input type="checkbox" data-admin-enabled="${esc(item.id)}" ${item.enabled ? "checked" : ""} ${canManage ? "" : "disabled"} /><span>${item.enabled ? "启用" : "禁用"}</span></span></label><label class="account-card-field"><span>重置密码</span><input type="password" data-admin-password="${esc(item.id)}" placeholder="留空不改密码" ${canManage ? "" : "disabled"} /></label></div><div class="account-card-actions"><button class="btn primary" data-admin-update="${esc(item.id)}" ${canManage ? "" : "disabled"}>保存这个账户</button></div></article>`).join("");
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 访问控制</div><h1>安全与账户</h1><p>控制中心管理员与核 Page 共用同一份本地账户；密码只保存 PBKDF2 派生值，浏览器不持久化令牌。</p></div><div class="actions"><button class="btn" id="admins-reload">刷新账户</button><button class="btn danger" id="security-logout">退出登录</button></div></div><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>当前会话</h2><span>服务端 Cookie · 8 小时空闲 / 24 小时绝对过期</span></div></div><div class="detail-grid account-grid"><div><span>用户名</span><strong>${esc(state.session?.username || "管理员")}</strong></div><div><span>角色</span><strong>${esc(state.session?.role || "admin")}</strong></div><div><span>会话状态</span><strong>已认证</strong></div></div></section><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>管理员账户</h2><span>${canManage ? `${admins.length} 个账户` : "仅 owner 可管理账户"}</span></div></div><div class="account-card-list">${rows || `<p class="empty-cell">加载中或暂无账户。</p>`}</div></section><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>新建管理员</h2><span>至少 8 位密码；用户名不可包含空格</span></div></div><div class="form-grid"><div class="form-row"><label title="技术名：username"><strong>用户名</strong><small>登录名</small></label><div class="form-input"><input id="admin-new-username" ${canManage ? "" : "disabled"} /></div><div class="form-meta"></div></div><div class="form-row"><label title="技术名：password"><strong>初始密码</strong><small>至少 8 位</small></label><div class="form-input"><input id="admin-new-password" type="password" minlength="8" ${canManage ? "" : "disabled"} /></div><div class="form-meta"></div></div><div class="form-row"><label title="技术名：role"><strong>角色</strong><small>最小权限优先</small></label><div class="form-input"><select id="admin-new-role" ${canManage ? "" : "disabled"}><option value="viewer">只读</option><option value="admin">管理员</option><option value="owner">所有者</option></select></div><div class="form-meta"><button class="btn primary" id="admin-create" ${canManage ? "" : "disabled"}>创建</button></div></div></div></section>`;
}
function viewContent() { if (state.view === "diagnostics") return diagnosticsView(); if (state.view === "updates") return updatesView(); if (state.view === "settings") return settingsView(); if (state.view === "control") return controlView(); if (state.view === "security") return securityView(); if (state.view === "rules") return rulesView(); if (state.view === "mirrors") return mirrorsView(); if (state.view === "recommendations") return recommendationsView(); return modulesView(); }
function rail() {
  return `<aside class="rail"><div class="brand"><span class="brand-mark">核</span><div><strong>凝心溯溪</strong><small>模块运营中心</small></div></div><div class="nav-label">工作区</div><nav class="nav">${NAV_ITEMS.map(([view, icon, label]) => `<button class="${state.view === view ? "active" : ""}" data-view="${view}" aria-current="${state.view === view ? "page" : "false"}">${icon}　${label}</button>`).join("")}</nav><div class="spacer"></div><div class="health"><b>系列健康度</b><p>${state.modules.length} 个可信模块已纳管。模块发现不执行任意第三方代码。</p><div class="bar"><i></i></div></div><div class="user"><span class="avatar">管</span><span>${esc(state.session?.username || "管理员")}</span><button class="logout" id="rail-logout">↪</button></div></aside>`;
}
function dashboard() {
  app.innerHTML = `<div class="shell">${rail()}<main class="main"><header class="topbar"><div class="crumb">凝心溯溪 / <b>核 · ${VIEW_TITLES[state.view] || "模块运营中心"}</b></div><div class="top-actions"><button class="btn" id="refresh">刷新</button><button class="btn" id="logout">退出登录</button></div></header><div class="content">${viewContent()}</div></main></div><nav class="mobile-nav" aria-label="移动端工作区导航">${["modules", "control", "diagnostics"].map((view) => { const item = NAV_ITEMS.find(([id]) => id === view); return `<button class="${state.view === view ? "active" : ""}" data-view="${view}" aria-current="${state.view === view ? "page" : "false"}"><span>${item[1]}</span>${item[2]}</button>`; }).join("")}<button id="mobile-more" aria-expanded="false"><span>⋯</span>更多</button></nav><div id="mobile-more-sheet" class="si-mobile-more-sheet" hidden>${NAV_ITEMS.filter(([view]) => !["modules", "control", "diagnostics"].includes(view)).map(([view, icon, label]) => `<button class="btn" data-view="${view}" aria-current="${state.view === view ? "page" : "false"}"><span>${icon}</span>${label}</button>`).join("")}<button class="btn" id="mobile-logout"><span>⇥</span>退出</button></div>`;
  bindDashboard();
}
function bindSettingsTabs() {
  const tabs = [...document.querySelectorAll("[data-si-tab]")];
  const panels = [...document.querySelectorAll("[data-si-panel]")];
  if (!tabs.length || !panels.length) return;
  const activate = (value) => {
    const target = tabs.some((tab) => tab.dataset.siTab === value) ? value : tabs[0].dataset.siTab;
    state.settingsTab = target;
    tabs.forEach((tab) => {
      const active = tab.dataset.siTab === target;
      tab.classList.toggle("active", active);
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    panels.forEach((panel) => {
      panel.hidden = panel.dataset.siPanel !== target;
    });
  };
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => activate(tab.dataset.siTab));
    tab.addEventListener("keydown", (event) => {
      let next = index;
      if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
      else if (event.key === "ArrowLeft") next = (index - 1 + tabs.length) % tabs.length;
      else if (event.key === "Home") next = 0;
      else if (event.key === "End") next = tabs.length - 1;
      else return;
      event.preventDefault();
      activate(tabs[next].dataset.siTab);
      tabs[next].focus();
    });
  });
  activate(state.settingsTab);
}

function bindDashboard() {
  bindSettingsTabs();
  document.getElementById("logout")?.addEventListener("click", logout); document.getElementById("rail-logout")?.addEventListener("click", logout); document.getElementById("mobile-logout")?.addEventListener("click", logout);
  document.getElementById("refresh")?.addEventListener("click", loadDashboard); document.getElementById("reload")?.addEventListener("click", loadDashboard); document.getElementById("check")?.addEventListener("click", () => checkUpdates()); document.getElementById("export")?.addEventListener("click", exportSummary);
  document.getElementById("refresh-logs")?.addEventListener("click", () => loadDiagnosticLogs(true)); document.getElementById("clear-logs")?.addEventListener("click", () => clearDiagnosticLogs()); document.getElementById("log-auto")?.addEventListener("change", () => toggleLogAuto()); document.getElementById("log-pause")?.addEventListener("click", toggleLogPause); document.getElementById("log-autoscroll")?.addEventListener("click", toggleLogAutoScroll); document.getElementById("log-export")?.addEventListener("click", exportDiagnosticLogs); document.getElementById("log-level")?.addEventListener("change", event => { state.logThreshold = event.target.value || ""; dashboard(); }); document.getElementById("log-range")?.addEventListener("change", event => { state.logRange = event.target.value || "all"; dashboard(); }); document.getElementById("settings-reload")?.addEventListener("click", () => loadSettings()); document.getElementById("save-settings")?.addEventListener("click", () => saveSettings()); document.getElementById("refresh-control")?.addEventListener("click", () => loadControl()); document.getElementById("toggle-control")?.addEventListener("click", toggleControl); document.getElementById("security-logout")?.addEventListener("click", logout);
  document.getElementById("rules-reload")?.addEventListener("click", () => loadRules()); document.getElementById("save-rule")?.addEventListener("click", () => saveRule()); document.getElementById("mirrors-reload")?.addEventListener("click", () => loadMirrors()); document.getElementById("save-mirror")?.addEventListener("click", () => saveMirror()); document.getElementById("benchmark-mirrors")?.addEventListener("click", () => benchmarkMirrors()); document.getElementById("check-recommendations")?.addEventListener("click", () => checkRecommendations()); document.getElementById("apply-recommendations")?.addEventListener("click", () => applyAllRecommendations()); document.getElementById("admins-reload")?.addEventListener("click", () => loadAdmins()); document.getElementById("admin-create")?.addEventListener("click", () => createAdmin()); document.querySelectorAll("[data-admin-update]").forEach(node => node.addEventListener("click", () => updateAdmin(node.dataset.adminUpdate)));
  document.querySelectorAll("[data-log-module]").forEach(node => node.addEventListener("click", () => { const id = node.dataset.logModule; state.logModules = state.logModules.includes(id) ? state.logModules.filter(item => item !== id) : [...state.logModules, id]; dashboard(); })); document.querySelectorAll("[data-log-toggle]").forEach(node => node.addEventListener("click", () => { const key = node.dataset.logToggle; if (state.logExpanded.has(key)) state.logExpanded.delete(key); else state.logExpanded.add(key); dashboard(); })); document.querySelectorAll("[data-log-problem]").forEach(node => node.addEventListener("click", () => { state.logModules = [node.dataset.logProblem]; state.logThreshold = node.querySelector(".managed") ? "ERROR" : "WARNING"; state.logQuery = node.dataset.logCode || ""; dashboard(); })); const logSearch = document.getElementById("log-search"); logSearch?.addEventListener("input", () => { state.logQuery = logSearch.value; dashboard(); requestAnimationFrame(() => { const next = document.getElementById("log-search"); next?.focus(); next?.setSelectionRange(state.logQuery.length, state.logQuery.length); }); });
  const bindRouteModels = () => document.querySelectorAll("[data-route-model]").forEach(node => node.addEventListener("change", () => { if (node.value !== "__custom__") return; const input = document.createElement("input"); input.className = "route-model"; input.dataset.routeModel = node.dataset.routeModel; input.type = "text"; input.placeholder = "模型名（可自定义）"; input.disabled = node.disabled; node.replaceWith(input); input.focus(); }));
  document.querySelectorAll("[data-route-provider]").forEach(node => node.addEventListener("change", () => { const kind = node.dataset.routeProvider; const model = document.querySelector(`[data-route-model="${CSS.escape(kind)}"]`); const next = modelSelect(kind, node.value, "", !(model?.disabled)); if (model) { const wrapper = model.parentElement; wrapper.innerHTML = next; bindRouteModels(); } }));
  bindRouteModels();
  document.getElementById("check-updates")?.addEventListener("click", () => checkUpdates()); document.getElementById("reload-transactions")?.addEventListener("click", () => loadTransactions()); document.querySelectorAll("[data-rollback]").forEach(node => node.addEventListener("click", () => rollbackUpdate(node.dataset.rollback)));
  document.getElementById("mobile-more")?.addEventListener("click", () => { const sheet = document.getElementById("mobile-more-sheet"); sheet.hidden = !sheet.hidden; document.getElementById("mobile-more")?.setAttribute("aria-expanded", String(!sheet.hidden)); });
  document.querySelectorAll("#mobile-more-sheet [data-view], #mobile-more-sheet #mobile-logout").forEach(node => node.addEventListener("click", () => { const sheet = document.getElementById("mobile-more-sheet"); if (sheet) sheet.hidden = true; document.getElementById("mobile-more")?.setAttribute("aria-expanded", "false"); }));
  document.querySelectorAll("[data-view]").forEach(node => node.addEventListener("click", () => { state.view = node.dataset.view || "modules"; state.selectedModule = node.dataset.module || ""; if (state.view === "diagnostics") loadDiagnostics(); else if (state.view === "settings") loadSettings(); else if (state.view === "updates") { dashboard(); loadTransactions(); } else if (state.view === "control") loadControl(); else if (state.view === "rules") loadRules(); else if (state.view === "mirrors") loadMirrors(); else if (state.view === "recommendations") loadRecommendations(); else if (state.view === "security") loadAdmins(); else dashboard(); }));
  document.querySelectorAll("[data-diagnostic]").forEach(node => node.addEventListener("click", async () => { state.logModules = [node.dataset.diagnostic]; await loadDiagnostics(); })); document.querySelectorAll("[data-module]").forEach(node => node.addEventListener("click", () => { state.view = "modules"; state.selectedModule = node.dataset.module || ""; dashboard(); })); document.getElementById("close-module-detail")?.addEventListener("click", () => { state.selectedModule = ""; dashboard(); });
  document.querySelectorAll("[data-filter]").forEach(node => node.addEventListener("click", () => { state.filter = node.dataset.filter; dashboard(); })); const query = document.getElementById("query"); query?.addEventListener("input", () => { state.query = query.value; dashboard(); requestAnimationFrame(() => { const next = document.getElementById("query"); next?.focus(); next?.setSelectionRange(state.query.length, state.query.length); }); });
  document.querySelectorAll("[data-control-plugin]").forEach(node => node.addEventListener("click", () => loadControlPlugin(node.dataset.controlPlugin)));
  document.querySelectorAll("[data-domain-view]").forEach(node => node.addEventListener("click", async () => { state.view = node.dataset.domainView || "modules"; if (state.view === "rules") await loadRules(); else if (state.view === "mirrors") await loadMirrors(); else if (state.view === "settings") await loadSettings(); else dashboard(); }));
  document.getElementById("close-control-detail")?.addEventListener("click", () => { state.selectedControlPlugin = ""; state.controlSchema = null; state.controlSnapshot = null; state.panelsList = null; state.panelData = null; state.selectedPanel = ""; dashboard(); });
  document.querySelectorAll("[data-control-tab]").forEach(node => node.addEventListener("click", () => { state.controlTab = node.dataset.controlTab || "fields"; dashboard(); }));
  document.getElementById("control-apply")?.addEventListener("click", () => applyControlPatch());
  document.getElementById("control-reset")?.addEventListener("click", () => resetControlFields());
  document.getElementById("control-refresh-fields")?.addEventListener("click", () => refreshControlFields());
  document.getElementById("panel-load")?.addEventListener("click", () => loadPanelsList());
  document.querySelectorAll("[data-panel-select]").forEach(node => node.addEventListener("click", () => loadPanelData(node.dataset.panelSelect)));
  document.querySelectorAll("[data-panel-action]").forEach(node => node.addEventListener("click", () => runPanelAction(node.dataset.panelAction)));
  document.getElementById("panel-stream-start")?.addEventListener("click", () => streamPanel(state.selectedControlPlugin, state.selectedPanel));
  document.querySelectorAll("[data-lifecycle]").forEach(node => node.addEventListener("click", () => runLifecycle(node.dataset.lifecycle)));
  document.querySelectorAll("[data-control-open]").forEach(node => node.addEventListener("click", async () => { state.view = "control"; await loadControl(); await loadControlPlugin(node.dataset.controlOpen); }));
  document.querySelectorAll("[data-install]").forEach(node => node.addEventListener("click", () => installModule(node.dataset.install)));
}
async function loadDiagnostics() { try { const result = await post("diagnostics", {}); state.providers = result.providers || []; state.view = "diagnostics"; dashboard(); await loadDiagnosticLogs(true); } catch (error) { notify(error.message, true); } }
function logCursors() {
  const cursors = {};
  const streams = {};
  (state.logMembers || []).forEach(item => {
    const next = Number(item.next_seq);
    cursors[item.plugin_id] = Number.isFinite(next) && next >= 0 ? next : 0;
    streams[item.plugin_id] = item.stream_id || "";
  });
  return { cursors, streams };
}
function logMemberHasMore(member) {
  return Boolean(member?.has_more ?? member?.truncated ?? member?.payload_has_more);
}
function applyDiagnosticPage(result, wasReset) {
  const members = result.members || [];
  state.logMembers = members;
  const activeIds = new Set(members.map(item => item.plugin_id));
  const resetIds = new Set(members.filter(item => item.reset).map(item => item.plugin_id));
  if (state.logs.some(item => !activeIds.has(item.plugin_id)) || resetIds.size) {
    state.logs = state.logs.filter(item => activeIds.has(item.plugin_id) && !resetIds.has(item.plugin_id));
  }
  const seen = new Set(state.logs.map(item => `${item.plugin_id}:${item.seq}`));
  const fresh = (result.events || []).filter(item => {
    const key = `${item.plugin_id}:${item.seq}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  state.logNewKeys = new Set(fresh.map(item => `${item.plugin_id}:${item.seq}`));
  if (fresh.length) state.logPendingScroll = true;
  state.logs = [...state.logs, ...fresh];
  if (state.logs.length > 3000) state.logs = state.logs.slice(-3000);
  return members.some(item => item.status === "ready" && logMemberHasMore(item));
}
async function loadDiagnosticLogs(reset = false) {
  if (state.logBusy) {
    if (reset) state.logRefreshPending = true;
    return;
  }
  state.logBusy = true;
  if (reset) {
    state.logs = [];
    state.logMembers = [];
    state.logExpanded.clear();
    state.logNewKeys = new Set();
    state.logPendingScroll = false;
  }
  try {
    let pass = 0;
    while (true) {
      const { cursors, streams } = logCursors();
      const result = await post("diagnostics/logs", { cursors, streams, limit: 500 });
      const hasMore = applyDiagnosticPage(result, reset && pass === 0);
      state.logCatchUp = hasMore;
      dashboard();
      if (!hasMore || pass >= 4) break;
      pass += 1;
    }
  } catch (error) {
    notify(error.message, true);
  } finally {
    const wasCatchingUp = state.logCatchUp;
    const shouldScroll = state.logAutoScroll && state.logPendingScroll;
    state.logCatchUp = false;
    state.logBusy = false;
    state.logPendingScroll = false;
    if (wasCatchingUp) dashboard();
    if (shouldScroll) requestAnimationFrame(() => { const list = document.getElementById("diagnostic-log-list"); if (list) list.scrollTop = 0; });
    if (state.logRefreshPending) {
      state.logRefreshPending = false;
      await loadDiagnosticLogs(true);
    }
  }
}
async function clearDiagnosticLogs() {
  if (!(await confirmDialog("清空所有模块的诊断日志？该操作不可恢复。"))) return;
  try {
    await post("diagnostics/clear", { confirm: true });
    state.logs = [];
    state.logMembers = [];
    state.logExpanded.clear();
    state.logNewKeys = new Set();
    state.logCatchUp = false;
    notify("诊断日志已清空");
    await loadDiagnostics();
  } catch (error) { notify(error.message, true); }
}
function toggleLogAuto() {
  state.logAuto = !state.logAuto;
  if (state.logTimer) { clearInterval(state.logTimer); state.logTimer = null; }
  if (state.logAuto) state.logTimer = setInterval(() => { if (!state.logPaused && state.view === "diagnostics") loadDiagnosticLogs(); }, 5000);
  dashboard();
}
function toggleLogPause() {
  state.logPaused = !state.logPaused;
  if (!state.logPaused && state.logAuto) loadDiagnosticLogs();
  dashboard();
}
function toggleLogAutoScroll() {
  state.logAutoScroll = !state.logAutoScroll;
  if (state.logAutoScroll) { const list = document.getElementById("diagnostic-log-list"); if (list) list.scrollTop = 0; }
  dashboard();
}
function exportDiagnosticLogs() {
  const events = diagnosticEvents().slice().reverse();
  const payload = {
    generated_at: new Date().toISOString(),
    contract: "series.diagnostics.aggregate@1.0",
    filters: { modules: state.logModules, level: state.logThreshold, range: state.logRange, query: state.logQuery },
    cached: state.logs.length,
    count: events.length,
    members: state.logMembers,
    events
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `series-diagnostics-${new Date().toISOString().replace(/[:.]/g, "-")}.json`;
  link.hidden = true;
  document.body.appendChild(link);
  link.click();
  window.setTimeout(() => { link.remove(); URL.revokeObjectURL(url); }, 1000);
  notify(events.length ? "诊断事件已导出" : "暂无可导出事件", !events.length);
}
async function checkUpdates() {
  try { notify("正在检查更新…"); state.updatesCheck = await post("updates/check", {}); notify("检查完成"); await loadDashboard(); if (state.view === "updates") await loadTransactions(); } catch (error) { notify(error.message, true); }
}
async function loadTransactions() {
  try { state.transactions = (await get("updates/transactions")).transactions || []; if (state.view === "updates") dashboard(); } catch (error) { notify(error.message, true); }
}
async function rollbackUpdate(txId) {
  if (!(await confirmDialog("确定回滚该次更新？插件将恢复到更新前版本并热重载。"))) return;
  try { const result = await post("updates/rollback", { tx_id: txId }); notify(`已回滚 ${result.plugin_id || ""} → v${result.from_version || "?"}`); await Promise.all([loadDashboard(), loadTransactions()]); } catch (error) { notify(error.message, true); }
}
async function loadRules() {
  try { state.rulesData = await get("rules"); } catch (error) { notify(error.message, true); }
  if (state.view === "rules") dashboard();
}
async function saveRule() {
  const data = state.rulesData;
  if (!data) return;
  const pluginIds = [...document.querySelectorAll("[data-rule-plugin]")].filter(node => node.checked).map(node => node.dataset.rulePlugin);
  const number = (id, fallback) => { const raw = document.getElementById(id)?.value; const value = parseInt(raw, 10); return Number.isFinite(value) ? value : fallback; };
  const payload = {
    expected_revision: Number(data.rule?.revision ?? 0),
    enabled: !!document.getElementById("rule-enabled")?.checked,
    plugin_ids: pluginIds,
    local_time: document.getElementById("rule-time")?.value || "04:00",
    timezone: document.getElementById("rule-timezone")?.value || "Asia/Shanghai",
    jitter_minutes: number("rule-jitter", 0),
    misfire_grace_minutes: number("rule-misfire", 60),
    policy: document.getElementById("rule-policy")?.value || "patch",
    minimum_release_age_hours: number("rule-age", 24),
    on_failure: document.getElementById("rule-failure")?.value || "rollback_continue",
    prerelease: !!document.getElementById("rule-prerelease")?.checked,
  };
  try { await post("rules", payload); notify("每日规则已保存并重建调度"); await loadRules(); } catch (error) { notify(error.message, true); await loadRules(); }
}
async function loadMirrors() {
  try { state.mirrorsData = await get("mirrors"); } catch (error) { notify(error.message, true); }
  if (state.view === "mirrors") dashboard();
}
async function saveMirror() {
  const selected = document.querySelector('input[name="mirror-choice"]:checked')?.value || "";
  try { await post("settings", { github_mirror: selected }); notify(selected ? "镜像已启用" : "已恢复 GitHub 直连"); await loadMirrors(); } catch (error) { notify(error.message, true); }
}
async function benchmarkMirrors() {
  const urls = (state.mirrorsData?.candidates || []).map(item => item.url);
  try { const result = await post("mirrors/benchmark", { mirrors: urls }); state.mirrorResults = result.results || []; notify(`测速完成：${state.mirrorResults.length} 个站点`); dashboard(); } catch (error) { notify(error.message, true); }
}
async function loadRecommendations() {
  try { state.recommendationsData = await get("recommendations"); } catch (error) { notify(error.message, true); }
  if (state.view === "recommendations") dashboard();
}
async function checkRecommendations() {
  try { state.recommendationsData = await post("recommendations/check", {}); notify("最新版本检查完成"); await Promise.all([loadRecommendations(), loadDashboard()]); } catch (error) { notify(error.message, true); }
}
async function applyAllRecommendations() {
  if (!(await confirmDialog("确定安装未安装模块并更新所有确有新版本的模块？核自身不会更新。"))) return;
  try { const result = await post("recommendations/apply-all", { confirm: true }); notify(`批量完成：成功 ${result.succeeded} / 失败 ${result.failed}`); await Promise.all([loadRecommendations(), loadDashboard()]); } catch (error) { notify(error.message, true); }
}
async function loadAdmins() {
  try { state.adminsData = await get("admins"); } catch (error) { notify(error.message, true); }
  if (state.view === "security") dashboard();
}
async function createAdmin() {
  const username = document.getElementById("admin-new-username")?.value.trim() || "";
  const password = document.getElementById("admin-new-password")?.value || "";
  const role = document.getElementById("admin-new-role")?.value || "viewer";
  try { await post("admins/create", { username, password, role }); notify(`已创建 ${username}`); await loadAdmins(); } catch (error) { notify(error.message, true); }
}
async function updateAdmin(adminId) {
  const role = document.querySelector(`[data-admin-role="${CSS.escape(adminId)}"]`)?.value || "viewer";
  const enabled = !!document.querySelector(`[data-admin-enabled="${CSS.escape(adminId)}"]`)?.checked;
  const password = document.querySelector(`[data-admin-password="${CSS.escape(adminId)}"]`)?.value || "";
  const payload = { admin_id: adminId, role, enabled };
  if (password) payload.password = password;
  try { await post("admins/update", payload); notify("账户已更新"); await loadAdmins(); } catch (error) { notify(error.message, true); }
}
async function loadSettings() {
  try {
    state.settingsData = await get("settings");
    try { state.modelOptions = await get("model-options"); } catch (error) { state.modelOptions = null; }
    try { state.routes = await get("model-routing"); } catch (error) { state.routes = null; }
    if (state.view === "settings") dashboard();
  } catch (error) { notify(error.message, true); }
}
async function saveSettings() {
  if (!(state.session?.role === "owner" || state.session?.role === "admin")) { notify("设置修改仅 admin 及以上可执行", true); return; }
  const routes = {};
  document.querySelectorAll("[data-route-provider]").forEach(node => {
    const kind = node.dataset.routeProvider;
    const model = document.querySelector(`[data-route-model="${CSS.escape(kind)}"]`);
    const voice = document.querySelector(`[data-setting-route="${CSS.escape(kind)}.voice"]`);
    const providerId = node.value.trim();
    const modelValue = model?.value === "__custom__" ? "" : (model?.value || "").trim();
    if (!providerId && !modelValue && !voice?.value.trim()) return;
    routes[kind] = { provider_id: providerId, model: modelValue };
    if (kind === "tts" && voice?.value.trim()) routes[kind].voice = voice.value.trim();
  });
  document.querySelectorAll("[data-setting-route]").forEach(node => {
    if (node.dataset.settingRoute.endsWith(".voice")) return;
    const [kind, field] = String(node.dataset.settingRoute).split(".");
    if (!routes[kind] && node.value.trim()) routes[kind] = { [field]: node.value.trim() };
  });
  const payload = { model_routing: routes, auto_update_enabled: !!document.getElementById("setting-auto-update")?.checked, log_level: document.getElementById("setting-log-level")?.value || "INFO" };
  const host = document.getElementById("setting-webui-host")?.value.trim() || "";
  const portRaw = document.getElementById("setting-webui-port")?.value.trim() || "";
  const publicUrl = document.getElementById("setting-webui-url")?.value.trim() || "";
  if (portRaw) { const port = parseInt(portRaw, 10); if (!(port >= 1 && port <= 65535)) { notify("WebUI 端口必须是 1-65535", true); return; } payload.webui_port = port; }
  if (host) payload.webui_host = host;
  if (publicUrl) payload.webui_public_url = publicUrl;
  document.querySelectorAll("[data-setting-key]").forEach(node => {
    const key = node.dataset.settingKey;
    const type = node.dataset.settingType;
    if (node.disabled || !key) return;
    if (type === "bool") { payload[key] = !!node.checked; return; }
    const raw = String(node.value ?? "").trim();
    if (!raw) return;
    if (type === "int") { const value = parseInt(raw, 10); if (Number.isFinite(value)) payload[key] = value; return; }
    if (type === "float") { const value = parseFloat(raw); if (Number.isFinite(value)) payload[key] = value; return; }
    payload[key] = raw;
  });
  try { const result = await post("settings", payload); notify("设置已保存并生效（连接项重启后生效）"); await Promise.all([loadSettings(), loadDashboard()]); } catch (error) { notify(error.message, true); }
}
async function loadControl() { try { state.control = await get("series/control"); state.view = "control"; dashboard(); } catch (error) { notify(error.message, true); } }
async function loadControlPlugin(pluginId) {
  state.selectedControlPlugin = pluginId;
  state.controlTab = "fields";
  state.panelsList = null;
  state.panelData = null;
  state.selectedPanel = "";
  state.controlSchema = null;
  state.controlSnapshot = null;
  state.takeoverDisabled = false;
  const [schemaResult, snapshotResult, panelsResult] = await Promise.allSettled([
    get(`series/${encodeURIComponent(pluginId)}/control/schema`),
    get(`series/${encodeURIComponent(pluginId)}/control/snapshot`),
    get(`series/${encodeURIComponent(pluginId)}/panels`)
  ]);
  if (schemaResult.status === "fulfilled") state.controlSchema = schemaResult.value;
  if (snapshotResult.status === "fulfilled") state.controlSnapshot = snapshotResult.value;
  if (panelsResult.status === "fulfilled") state.panelsList = panelsResult.value;
  else state.takeoverDisabled = String(panelsResult.reason?.message || panelsResult.reason || "").includes("TAKEOVER_DISABLED");
  const panelCount = state.panelsList?.panels?.length || 0;
  if (!state.controlSchema && panelCount > 0) state.controlTab = "panels";
  if (!state.controlSchema && panelCount === 0) notify("该插件未提供统一接管或管理面板契约", true);
  state.view = "control"; dashboard();
  if (panelCount > 0) loadPanelData(state.panelsList.panels[0].id);
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
  if (!Object.keys(patch).length) { notify("没有修改需要应用"); return; }
  try {
    const revision = schema.revision;
    await post(`series/${encodeURIComponent(pluginId)}/control/validate`, { patch, expected_revision: revision });
    await post(`series/${encodeURIComponent(pluginId)}/control/apply`, { patch, expected_revision: revision });
    notify("覆盖已应用");
    await loadControlPlugin(pluginId);
    await loadControl();
  } catch (error) {
    notify(error.message, true);
    if (String(error.message).includes("REVISION")) await loadControlPlugin(pluginId);
  }
}
async function resetControlFields() {
  const pluginId = state.selectedControlPlugin;
  if (!pluginId) return;
  if (!(await confirmDialog("重置该插件的全部核覆盖字段？插件自身配置将立即恢复生效。"))) return;
  try {
    await post(`series/${encodeURIComponent(pluginId)}/control/reset`, { fields: null });
    notify("已恢复插件自身配置");
    await loadControlPlugin(pluginId);
    await loadControl();
  } catch (error) { notify(error.message, true); }
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
  } catch (error) { notify(error.message, true); }
}
async function loadPanelData(panelId) {
  const pluginId = state.selectedControlPlugin;
  if (!pluginId || !panelId) return;
  try {
    state.selectedPanel = panelId;
    state.panelData = await get(`series/${encodeURIComponent(pluginId)}/panels/${encodeURIComponent(panelId)}`);
    dashboard();
  } catch (error) { notify(error.message, true); }
}
async function uploadArtifact(file, pluginId, panelId) {
  const form = new FormData();
  form.append("plugin_id", pluginId);
  form.append("panel", panelId);
  form.append("file", file);
  const response = await fetch(`${API_PREFIX}/artifacts`, {
    method: "POST",
    credentials: "same-origin",
    body: form,
  });
  const data = parse(await response.json());
  if (!response.ok || data?.success === false) throw new Error(data.error || "上传失败");
  return data.artifact_id;
}
async function runPanelAction(actionId) {
  const pluginId = state.selectedControlPlugin;
  const panelId = state.selectedPanel;
  const action = (state.panelData?.actions || []).find(item => item.id === actionId);
  if (!pluginId || !panelId || !action) return;
  const payload = {};
  let missing = false;
  const fileUploads = [];
  (action.payload_fields || []).forEach(field => {
    if (field.type === "file") {
      const fileNode = document.querySelector(`[data-panel-file="${CSS.escape(field.name)}"]`);
      const files = [...(fileNode?.files || [])];
      if (field.required && !files.length) missing = true;
      files.forEach(file => fileUploads.push([field.name, file, field.multiple === true]));
      return;
    }
    const node = document.querySelector(`[data-panel-field="${CSS.escape(field.name)}"]`);
    if (field.type === "bool" || field.type === "boolean") { payload[field.name] = !!node?.checked; return; }
    const value = node ? node.value : "";
    if (field.required && !value) missing = true;
    if (field.type === "number") payload[field.name] = value === "" ? null : Number(value);
    else if (value !== "" || field.secret !== true) payload[field.name] = value;
  });
  if (missing) { notify("请填写动作所需的必填字段", true); return; }
  try {
    for (const [name, file, multiple] of fileUploads) {
      const artifactId = await uploadArtifact(file, pluginId, panelId);
      if (multiple) payload[name] = [...(Array.isArray(payload[name]) ? payload[name] : []), artifactId];
      else payload[name] = artifactId;
    }
  } catch (error) { notify(error.message, true); return; }
  if (action.confirm && !(await confirmDialog(action.confirm))) return;
  const headers = { "X-Request-Id": (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`) };
  if (action.revision_required && state.panelData?.revision != null) headers["X-Expected-Revision"] = String(state.panelData.revision);
  try {
    const result = await post(`series/${encodeURIComponent(pluginId)}/panels/${encodeURIComponent(panelId)}/actions/${encodeURIComponent(actionId)}`, payload, headers);
    notify(result.message || "操作完成");
    if (result.job_id) { pollJob(result.job_id, panelId); return; }
    if ((Array.isArray(result.artifacts) && result.artifacts.length) || result.audio?.artifact_id) {
      state.panelData = {
        ...(state.panelData || {}),
        artifacts: [...(state.panelData?.artifacts || []), ...(result.artifacts || [])],
        audio: result.audio || state.panelData?.audio || null,
      };
      dashboard();
      return;
    }
    await loadPanelData(panelId);
  } catch (error) { notify(error.message, true); }
}
async function installModule(pluginId) {
  if (state.session?.role !== "owner") { notify("安装仅 owner 可执行", true); return; }
  if (!(await confirmDialog(`确定安装「${pluginId}」？`))) return;
  try {
    const result = await post(`series/${encodeURIComponent(pluginId)}/lifecycle/install`, {});
    notify(result.message || `已请求安装 ${pluginId}`);
    await loadDashboard();
  } catch (error) { notify(error.message, true); }
}
function streamPanel(pluginId, panelId) {
  const output = document.getElementById("panel-stream");
  if (!pluginId || !panelId) return;
  if (state.panelStream) { state.panelStream.close(); state.panelStream = null; }
  const url = `/api/series/${encodeURIComponent(pluginId)}/panels/${encodeURIComponent(panelId)}/stream`;
  const source = new EventSource(url, { withCredentials: true });
  state.panelStream = source;
  source.onmessage = event => { if (output) output.textContent += `${event.data}\n`; };
  source.addEventListener("done", () => { source.close(); state.panelStream = null; });
  source.addEventListener("error", () => { source.close(); state.panelStream = null; if (output) output.textContent += "[stream closed]\n"; });
}
async function pollJob(jobId, panelId) {
  for (let attempt = 0; attempt < 300; attempt += 1) {
    await new Promise(resolve => setTimeout(resolve, 1000));
    try {
      const job = await get(`jobs/${encodeURIComponent(jobId)}`);
      const progress = Math.round((job.progress || 0) * 100);
      if (job.message) notify(`${job.message} ${progress}%`);
      if (job.status === "done") { await loadPanelData(panelId); return; }
      if (job.status === "failed") { notify(job.error || "任务失败", true); return; }
      if (job.status === "cancelled") return;
    } catch (error) { notify(error.message, true); return; }
  }
  notify("任务轮询超时，请稍后刷新面板", true);
}
async function runLifecycle(action) {
  const pluginId = state.selectedControlPlugin;
  if (!pluginId) return;
  if (state.session?.role !== "owner") { notify("生命周期操作仅 owner 可执行", true); return; }
  const labels = { install: "安装", update: "更新", enable: "启用", disable: "停用" };
  const forceNode = document.getElementById("lifecycle-force");
  const force = action === "update" && forceNode && forceNode.checked;
  const confirmText = force ? `确定强制更新「${pluginId}」？远端版本将覆盖本地代码。` : `确定对「${pluginId}」执行${labels[action] || action}？`;
  if (!(await confirmDialog(confirmText))) return;
  try {
    const result = await post(`series/${encodeURIComponent(pluginId)}/lifecycle/${action}`, { force });
    notify(`${labels[action] || action}完成${result.version ? ` · v${result.version}` : ""}`);
    await loadDashboard();
    await loadControl();
    if (state.selectedControlPlugin) await loadControlPlugin(state.selectedControlPlugin);
  } catch (error) { notify(error.message, true); }
}
async function toggleControl() { try { const next = state.control?.mode === "managed" ? "native" : "managed"; await post("series/control/mode", { mode: next }); await loadControl(); notify(next === "managed" ? "统一接管已启用" : "已恢复插件自身配置"); } catch (error) { notify(error.message, true); } }
function exportSummary() { const payload = { generated_at: new Date().toISOString(), modules: state.modules.map(item => ({ plugin_id: item.plugin_id, version: item.version, status: item.status, contracts: item.contracts })) }; const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" }); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = "series-control-summary.json"; link.hidden = true; document.body.appendChild(link); link.click(); window.setTimeout(() => { link.remove(); URL.revokeObjectURL(url); }, 1000); notify("已生成脱敏诊断摘要"); }
async function loadDashboard() { try { const session = await get("session"); state.configured = !!session.configured; if (!session.authenticated) { state.authenticated = false; loginView(); return; } state.authenticated = true; state.session = session.session; const modules = await get("modules"); state.modules = modules.modules || []; if (state.view === "settings") await loadSettings(); else if (state.view === "diagnostics") await loadDiagnostics(); else if (state.view === "updates") { dashboard(); await loadTransactions(); } else if (state.view === "control") await loadControl(); else if (state.view === "rules") await loadRules(); else if (state.view === "mirrors") await loadMirrors(); else if (state.view === "recommendations") await loadRecommendations(); else if (state.view === "security") await loadAdmins(); else dashboard(); } catch (error) { loginView(error.message); } }
async function logout() { try { await post("logout", {}); } finally { state.authenticated = false; state.session = null; loginView(); } }
async function start() { try { await loadDashboard(); } catch (error) { loginView(error.message); } }
start();
