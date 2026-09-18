const API_PREFIX = "/api";
let state = {
  authenticated: false,
  configured: false,
  session: null,
  modules: [],
  providers: [],
  routes: null,
  control: null,
  controlSwitches: {},
  settingsTab: "route",
  capTabs: {},
  capPanels: {},
  takeoverDisabled: false,
  panelStream: null,
  logs: [],
  linkHealth: null,
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
  view: "control",
  selectedModule: "",
};
const app = document.getElementById("app");
// 视图注册表：单一事实源（导航/标题/渲染/进入逻辑都由它驱动）。
// 一级分类 = 控制中心真正要做的五件事：
//   总览（看状态） · 系列接管（管功能） · 更新与安装（管版本） · 诊断与日志（排障） · 设置与安全（管系统）
// 更新与安装、设置与安全是"套件"：一级只出现一次，内部用子页签切换。
const NAV_GROUPS = [
  ["workbench", "工作台"],
  ["operations", "运维"],
];
const VIEWS = {
  modules: { icon: "▦", label: "模块总览", tabLabel: "模块总览", group: "operations", inSuite: "diagnostics" },
  control: { icon: "◈", label: "系列接管", group: "workbench" },
  updates: { icon: "↻", label: "更新与安装", tabLabel: "更新与回滚", group: "operations", suite: ["updates", "recommendations", "rules", "mirrors"] },
  recommendations: { icon: "＋", label: "系列推荐", group: "operations", inSuite: "updates" },
  rules: { icon: "▤", label: "每日规则", group: "operations", inSuite: "updates" },
  mirrors: { icon: "⇄", label: "镜像加速", group: "operations", inSuite: "updates" },
  diagnostics: { icon: "⌁", label: "诊断与日志", tabLabel: "日志", group: "operations", suite: ["diagnostics", "modules"] },
  settings: { icon: "⚙", label: "设置与安全", group: "operations" },
  security: { icon: "◇", label: "账户与安全", group: "operations", hidden: true },
};
// 兼容既有代码/测试的元组形态：[view, icon, label, group, inSuite, suite]
const NAV_ITEMS = Object.entries(VIEWS).map(([view, meta]) => [
  view,
  meta.icon,
  meta.label,
  meta.group || "",
  meta.inSuite || "",
  Array.isArray(meta.suite) ? meta.suite : null,
]);
const VIEW_TITLES = Object.fromEntries(NAV_ITEMS.map(([view, , label]) => [view, label]));
function railItemsForGroup(groupId) {
  return NAV_ITEMS.filter(([view, , , group, inSuite]) => group === groupId && !inSuite && !VIEWS[view]?.hidden);
}
function suiteTabStrip(suiteId) {
  const head = NAV_ITEMS.find(([view]) => view === suiteId);
  if (!head || !Array.isArray(head[5])) return "";
  const buttons = head[5].map(id => {
    const item = NAV_ITEMS.find(([view]) => view === id);
    if (!item) return "";
    const active = state.view === id;
    const label = id === suiteId && VIEWS[id]?.tabLabel ? VIEWS[id].tabLabel : item[2];
    return `<button class="${active ? "active" : ""}" role="tab" aria-selected="${active}" data-view="${id}">${esc(label)}</button>`;
  }).join("");
  return `<div class="tab-strip suite-tabs" role="tablist">${buttons}</div>`;
}

const notify = (message, error = false, action = null) => {
  if (window.SeriesUI?.toast) {
    window.SeriesUI.toast(message, error ? "error" : "info", undefined, action);
    return;
  }
  const fallback = document.querySelector("[data-toast-fallback]");
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

// 每个插件自己的字段中文名与一句说明（取自各仓 _conf_schema.json；核只做展示兜底，插件 schema 里的 label/hint 优先）。
const PLUGIN_FIELD_TEXT = {
  "astrbot_plugin_active_learner": {
    "embedding_enabled": ["启用向量检索", "无可用 Embedding Provider 时自动降级为纯 FTS5。需要先在 AstrBot 中配置 Embedding Provider。"],
    "context_inject_count": ["上下文注入记忆条数", "每次对话最多注入 3 条记忆；同时受总约 1800 字符、单条约 700 字符预算限制。为兼容旧配置，大于 3 的值会自动收紧为 3。"],
    "search_top_k": ["工具搜索返回条数", "search_and_learn / memory_search 返回的最大搜索结果数（1~20）。越多 LLM 看的信息越全，但占用上下文也越多。"],
  },
  "astrbot_plugin_conversation_flow": {
    "chunking_enabled": ["启用智能分段", "开启后会向 LLM 注入分段引导指令，让模型主动用双空行分段；并在结果装饰阶段按双空行优先 + 句末标点保底切分。"],
    "chunking_delay_mode": ["分段延迟模式", "fixed=每段固定延迟；per_char=按下一段有效字数乘以每字延迟，并受最小/最大值限制。推荐 per_char。"],
    "chunking_min_length": ["触发分段的最小长度", "常规回复短于此长度（字符数）保持单条发送；但若无双空行、存在全角/半角强语气句界且前后都是完整自然句，可放宽一次拆分，避免长短句黏在一起。默认 60。"],
    "chunking_long_paragraph_threshold": ["段落进一步拆分阈值", "段落超过该长度才继续按句切开（默认 120，尊重她自己用空行分的段）。"],
    "chunking_newline_mode": ["单换行处理方式", "auto=主链优先（用空行表达分条），只对极短行例外切分；always=一律切；never=不切。"],
    "chunking_llm_assist": ["LLM 辅助分段", "长回复（默认 >120 字）额外调用一次快速模型再判断怎么切。"],
    "chunking_delay_per_char_ms": ["每字延迟（毫秒）", "按字数延迟模式下每个字的等待毫秒数（默认 80ms/字）。"],
    "chunking_short_line_chars": ["极短行长度上限", "称呼、笑声、短反应这类极短行（默认 ≤12 字）在 auto 模式下独立成条。"],
    "chunking_max_segments": ["单次回复最大分段数", "超过此数量时会合并末尾的多段为一段，避免刷屏。默认 5。"],
    "silence_enabled": ["启用沉默判断", "开启后由模型结合上下文判断是否真的无需回应。只有明确收口、明确要求停止交流或确实无法承接的纯噪声才允许沉默；普通问候、称呼、呼唤、撒娇、求关注和表达亲近必须自然回应。'好的''嗯''谢谢''晚安'等短句不能脱离上下文直接判定。"],
    "silence_strategy": ["沉默判断策略", "inject=指令注入（省一次 LLM 调用，推荐）；prejudge=独立预判断（更可控但慢）；both=二者结合。"],
    "interrupt_enabled": ["启用插话中断", "开启后，bot 还在思考时用户追加消息，旧回复会被抑制或合并到新请求。"],
    "interrupt_mode": ["插话处理模式", "steering：单条消息不额外等待，生成中的补充/纠正/媒体延续按同一任务合并，新话题不硬合并；window：保持旧的固定时间窗逻辑。默认 steering。"],
    "interrupt_scope": ["群聊中断作用域", "room=房间内任何新消息可中断旧回复；sender=仅同一发送者的新消息可中断（推荐）；mention_or_sender=同一发送者或明确@/回复bot时中断。"],
    "interrupt_merge_strategy": ["插话合并策略", "append=把旧消息作为追加上下文注入（推荐）；rewrite=让 LLM 重写为新语境；discard_old=直接丢弃旧响应不合并。"],
    "context_budget_enforce": ["严格裁剪上下文", "默认关闭（shadow）：只统计各来源注入片段的字符数并写入诊断，不改变发给模型的 Prompt。开启后，注入总量超过软上限时按“语音风格→语义知识→环境→情节记忆”整条裁掉低优先级片段；仍超硬上限时才截断“关系情绪/人格”；身份授权与当前轮永不裁剪。"],
    "context_budget_soft_limit": ["软上限", "所有来源提示词片段合计超过该字符数时，严格模式下优先整条裁掉低优先级片段。默认 12000；shadow 模式下只影响诊断数值。"],
    "context_budget_hard_limit": ["硬上限", "软上限裁剪后仍超出该字符数时，才截断关系情绪与人格片段（按 Unicode 字符截断，不会切坏中文或 emoji）；身份授权与当前轮仍然保留。默认 14000，且不会低于软上限。"],
    "plain_text_mode": ["纯文本回复模式", "开启后向 LLM 注入指令要求用纯文本聊天（不用 Markdown 格式），并在分段发送前剥离残留的 **加粗**、# 标题、- 列表等标记。代码块内容不受影响。推荐开启。"],
    "image_intent_mode": ["图片意图判断", "开启后检测到用户发送图片时，按对话作用判断为话题收口型、社交互动型、观点态度型或信息内容型。卖萌/撒娇/求关注会简短互动，只有明确结束话题才沉默。依赖 AstrBot 原生图片识别，不接管图片识别本身。"],
    "private_context_bridge_enabled": ["启用短消息承接", "记录少量已实际回复的私聊轮次。遇到‘试试能不能用’、简称、纠正等短承接语时，把最近对象和任务重新靠近当前请求；普通长消息在框架历史完整时不会重复注入。"],
    "private_context_bridge_max_turns": ["最近完成轮次数", "承接兜底最多保留和注入多少个已完成轮次，仅驻留内存，范围 1-10。默认 3。"],
    "private_context_bridge_short_max_chars": ["短承接消息长度上限", "不超过该字符数的私聊消息会主动获得最近轮次提示，用于名称、简称、省略式追问和纠正。范围 4-200，默认 40。"],
    "dynamic_context_enabled": ["启用动态上下文补回", "开启后，言会在内存里多保留几轮同一私聊。只有 AstrBot 交给模型的公开聊天记录已经缺页时才补回；记录完整时不会重复注入。主模型会自行判断当前消息是在继续旧话题还是已经换题，不额外调用一次模型。"],
    "dynamic_context_max_turns": ["最多保留多少轮当前话题", "范围 2-12，默认 8。数值越大越不容易忘记较早的目标和约定，但缺页时会占用更多上下文。只保存在内存，重载或重启后清空。"],
    "dynamic_context_max_chars": ["单次补回的文字上限", "范围 600-4000，默认 1800。言优先保留最近的缺失轮次；超过上限会停止继续向前补，避免聊天越久提示词越大。"],
    "recent_activity_context_enabled": ["启用近期弱上下文", "开启后，只对在“情”的账号归属页由管理员绑定为同一自然人的账号生效。言会在内存里保留少量近期对话片段，让你换软件或从群聊回私聊时能自然接上。默认关闭；不会联网，也不会额外调用模型。"],
    "recent_activity_retention_minutes": ["近期片段最多保留多久", "范围 30-360，默认 120。5 分钟内的唯一私聊可承接“继续”这类短话；半小时内可按相同话题自动关联；更久的片段只有你明确说“接着另一个会话”时才会用。重载或重启后立即清空。"],
    "group_context_enabled": ["群聊上下文注入", "开启后，bot 在群聊中被@或被回复时，会获取最近若干条群聊消息作为上下文注入到 LLM 请求，帮助 bot 理解群聊氛围。"],
    "group_context_max_messages": ["群聊上下文最大消息条数", "被唤醒时获取的最近群聊消息条数上限；用户先发一句话再单独 @Bot 时，也使用这里的数量让模型回看上下文并判断是否回应。默认 10，可按群聊活跃程度调整，推荐 10-20 条。"],
    "group_context_only_when_woken": ["仅在被唤醒时注入", "开启后只在 bot 被@或被回复时才注入群聊上下文；关闭则每次群聊消息都注入（消耗更多 Token）。"],
    "group_air_guard_enabled": ["群聊读空气限制", "限制短时间连续回复和礼貌收尾循环，避免机器人互相引用、互道晚安停不下来。判定完全基于本地计数，不额外调用 LLM。推荐开启。"],
    "group_air_guard_window_seconds": ["读空气检测窗口秒数", "统计最近多少秒内 Bot 在本群的回复次数。建议 60-180 秒；越短越宽松。"],
    "group_air_guard_max_bot_replies": ["窗口内最大 Bot 回复", "窗口内 Bot 回复达到该次数后，后续即使被明确唤醒也会硬拦截，用来兜住机器人互相引用的死循环。注意这条规则不区分说话的是人还是 Bot，调太小会把正常连续对话的人也拦掉，建议保持 6 或更大。填 0 关闭这条规则，只留礼貌收尾判定。"],
    "group_air_guard_polite_loop_limit": ["礼貌收尾循环上限", "窗口内 Bot 已回复过几次晚安/谢谢/拜拜等收尾话术后，再遇到同类消息就静默。建议 1-2。填 0 关闭这条规则。"],
    "followup_guard_enabled": ["抑制服务式追问", "抑制『还需要我帮你……吗』『有需要随时告诉我』等客服式收尾。只约束表达方式，不阻止必要的澄清问题；按当前会话和用户独立统计。"],
    "followup_streak_limit": ["连续追问强约束阈值", "连续出现多少轮服务式追问后，从提醒改为禁止征询式结尾。默认 2。"],
    "followup_window_seconds": ["连续追问统计窗口秒数", "超过该时间未再次出现服务式追问时自然清零。默认 900 秒。"],
    "scene_awareness_enabled": ["群聊场景感知", "判断当前这句话是在对你说、对群里另一个人说、还是对整个群说，并据此调整回应方式。判定基于 @ 段、引用段与最近发言者昵称，不额外调用 LLM。默认开启。"],
    "mood_enabled": ["启用回复意愿变化", "开启后，Bot 在群聊中被连续打扰、复读或长时间连聊时，会逐渐变得懒散或烦躁；即使被 @ 也可自行选择不回。默认仅群聊生效。"],
    "mood_private_enabled": ["私聊也启用", "开启后私聊同样会积累疲劳并可能不回复。默认关闭，避免重要的一对一消息被漏掉。"],
    "mood_window_seconds": ["疲劳统计窗口秒数", "只统计该窗口内的互动与复读；长时间没人说话后情绪会自然恢复。默认 300 秒。"],
    "mood_frequent_after": ["开始厌烦的窗口互动数", "窗口内超过该次数后开始降低回复意愿。默认 6；越小越容易烦。"],
    "mood_streak_after": ["开始疲劳的连续对话轮数", "连续对话超过该轮数后开始降低回复意愿。默认 8。"],
    "mood_streak_gap_seconds": ["连续对话中断秒数", "两条消息间隔超过该秒数后，连续轮数重新计算。默认 90 秒。"],
    "mood_lazy_score": ["懒散阈值", "回复意愿低于该分数时，Bot 仍会回复但会更短、更随口。范围 0-100，默认 72。"],
    "mood_annoyed_score": ["烦躁阈值", "回复意愿低于该分数时，Bot 可自行输出沉默标记或只敷衍一句。默认 45。"],
    "mood_silence_score": ["概率硬静默阈值", "回复意愿低于该分数时，可在调用 LLM 前直接装作没看见。默认 25。"],
    "mood_silence_chance_percent": ["极低意愿时静默概率", "达到硬静默阈值后的不回复概率，范围 0-100。默认 45%；填 0 关闭硬静默，只让模型自行决定。"],
    "mood_max_consecutive_silences": ["最大连续静默次数", "连续装作没看见达到该次数后，下一条强制交给模型回应，避免长期失联。默认 2；填 0 表示不限制。"],
  },
  "astrbot_plugin_identity_guardian": {
    "enabled": ["身份守卫总开关", "关闭后不再做身份识别与授权判定。"],
    "auto_moderate": ["入群自动审核", "开启后未命中规则的群消息会调用独立审核 LLM 判断是否违规。与主对话 LLM 完全隔离，无注入风险。若已安装其他防注入/内容过滤插件，可关闭此项避免重复审核。"],
    "join_audit_mode": ["入群审核模式（兼容）", "仅保留旧配置兼容，不会自动应用到任何群。请在插件的“入群审核”页面选择具体 Bot 和群后显式迁移；新群和未配置群的两个开关始终默认关闭。"],
    "enable_api_guard": ["API 层硬拦截", "在管理 API 真正执行前校验紧急停止与全局熔断状态，命中即阻断。强烈建议始终开启。"],
  },
  "astrbot_plugin_relationship": {
    "mood_enabled": ["情绪联动", ""],
    "cross_platform_memory_enabled": ["跨平台关系记忆", ""],
    "cross_platform_memory_top_k": ["关系记忆条数", ""],
    "cross_platform_memory_max_chars": ["关系记忆字数上限", ""],
  },
  "astrbot_plugin_environment_awareness": {
    "proactive_enabled": ["主动发送环境关心", "默认关闭。开启后仍必须同时配置自然人、私聊 UMO，并在序中授权；情或序缺失、言契约不兼容时一律不发送。"],
    "opportunity_cache_enabled": ["后台刷新环境关心候选", "开启且已设置常驻地点时，境会在后台定时刷新预警、空气质量、紫外线和降温数据，只缓存一条真正值得关心的中性事实。普通回复钩子只读缓存，不等待联网；真正主动发送仍由下方独立开关控制。"],
    "opportunity_refresh_seconds": ["环境关心候选刷新间隔", "范围 300-21600，默认 15 分钟。刷新在后台运行，不计入普通回复耗时。"],
  },
  "astrbot_plugin_voice_hub": {
    "segment_enabled": ["长文本分段合成", "统一朗读工具会保留显式空行和编号段落；此开关只控制单段过长时是否按句界兜底。"],
    "segment_threshold_chars": ["单段句界兜底阈值字符数", "显式段落低于此长度时保持一段；只有超过此长度的单段才按句界继续切分。"],
    "segment_max_segments": ["单段兜底最大分段数", "仅用于没有显式段落的单段句界兜底；不会为了达到上限而合并显式编号段落。"],
    "reply_mode": ["回复模式", "回复模式"],
    "tts_trigger_mode": ["TTS 触发方式", "probability=过滤 voice_hub_speak 工具并按概率自动语音化；llm_decides=只向 LLM 提供唯一的 voice_hub_speak 工具，不执行概率自动 TTS。旧配置未填写时按 probability 处理。"],
  },
  "astrbot_plugin_embodiment_bridge": {
    "diagnostic_log_enabled": ["独立诊断日志", "日志仅写入插件自有 data/plugin_data 目录；默认关闭，不接入 AstrBot 总日志。"],
    "diagnostic_platform_log_enabled": ["诊断摘要写入临", "默认关闭。启用后只写事件状态、错误码和耗时；不会写入正文、身份、凭据或音频。日志使用“临”的独立命名空间。"],
    "server_timing_enabled": ["服务端耗时统计", "默认关闭。启用后只发送 server_timing@1.0 的非负整数耗时和固定决策路径，不发送正文、身份、Provider 或日志。"],
    "max_sessions": ["最大并发会话数", "最大并发具身客户端会话数"],
    "event_queue_size": ["会话事件队列长度", "慢客户端会先合并或丢弃可重建的增量事件，关键事件不会丢失。"],
    "max_audio_seconds": ["单轮音频最大秒数", "单轮输入音频最大秒数"],
    "max_audio_chunk_bytes": ["音频分块最大字节", "16000 Hz 单声道 PCM16 的 40-100 毫秒约为 1280-3200 字节；默认允许更大的网络批次。"],
    "interaction_debounce_ms": ["交互去抖窗口（毫秒）", "相同交互名称和阶段的去抖窗口（毫秒）"],
    "output_chunk_ms": ["输出分块时长（毫秒）", "输出 PCM16 SSE 音频块时长（毫秒）"],
    "sse_heartbeat_seconds": ["SSE 心跳间隔（秒）", "SSE 心跳间隔（秒）"],
    "max_tts_audio_seconds": ["TTS 输出最大秒数", "单轮 TTS 输出最大秒数"],
  },
};

function pluginFieldText(pluginId, key) {
  return ((PLUGIN_FIELD_TEXT[pluginId] || {})[key]) || null;
}
function fieldHint(key, def, pluginId) {
  const explicit = def && (def.hint || def.description);
  if (explicit) return explicit;
  const mapped = pluginFieldText(pluginId, key);
  if (mapped && mapped[1]) return mapped[1];
  return FIELD_HINTS[key] || "";
}

function humanizeKey(key) {
  const parts = String(key || "").split("_").filter(Boolean);
  if (!parts.length) return "";
  const words = parts.map((part) => KEY_TOKENS[part] || "");
  if (words.some((word) => !word)) return "";
  return words.join("");
}

function fieldLabel(key, def, pluginId) {
  const explicit = def && (def.label || def.title);
  if (explicit) return explicit;
  const mapped = pluginFieldText(pluginId, key);
  if (mapped && mapped[0]) return mapped[0];
  if (FIELD_LABELS[key]) return FIELD_LABELS[key];
  if (def && def.description) return def.description;
  // 兜底显示原始字段名：绝不返回“配置项”这种没有信息量的占位
  return humanizeKey(key) || key;
}

function parse(value) { return typeof value === "string" ? JSON.parse(value) : value; }
function esc(value) {
  if (window.SeriesUI?.escapeHtml) return window.SeriesUI.escapeHtml(value);
  return String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
}
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
  app.innerHTML = `<section class="login"><div class="login-side"><div class="brand"><span class="brand-mark">核</span><div><strong>凝心溯溪</strong><small>模块运营中心</small></div></div><div class="login-copy"><h1>把每个模块，放进同一张工作台。</h1><p>管理员账户由「核」 Page 创建和维护，WebUI 不提供注册入口。</p></div></div><div class="login-main"><form class="login-card" id="login-form"><h2>登录模块运营中心</h2><p>${state.configured ? "请输入在“核” Page 中配置的管理员账户。" : "当前还没有可用管理员，请先回到“核” Page 设置管理员。"}</p><div class="field"><label for="username">管理员账户</label><input id="username" name="username" autocomplete="username" required ${state.configured ? "" : "disabled"}></div><div class="field"><label for="password">密码</label><input id="password" name="password" type="password" autocomplete="current-password" required ${state.configured ? "" : "disabled"}></div><div class="error" role="alert">${esc(message)}</div><button class="btn primary" type="submit" ${state.configured ? "" : "disabled"}>安全登录</button><div class="note">账户、角色与禁用状态请在「核」 Page 管理。</div></form></div></section>`;
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
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 生产状态</div><h1>模块总览</h1><p>统一查看可信自有模块的运行状态、版本与诊断入口。</p></div><div class="actions"><button class="btn" id="export">导出摘要</button><button class="btn primary" id="check">检查更新</button></div></div><div class="stats"><div class="stat"><label>可信模块</label><strong>${state.modules.length}</strong><small>来自可信登记</small></div><div class="stat"><label>运行正常</label><strong>${normal}</strong><small>核心链路可用</small></div><div class="stat"><label>需关注</label><strong>${offline}</strong><small>非阻断状态</small></div><div class="stat"><label>有更新</label><strong>${updatesPending}</strong><small>可前往更新页处理</small></div></div><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>系列模块</h2><span>${filtered().length} 个匹配当前视图 · ${updatesPending} 个有更新 · <button class="link" data-view="updates">查看更新与回滚</button></span></div><div class="filters"><label class="search">⌕<input id="query" placeholder="搜索模块名称或 ID" value="${esc(state.query)}"></label><div class="seg"><button data-filter="all" class="${state.filter === "all" ? "active" : ""}">全部</button><button data-filter="normal" class="${state.filter === "normal" ? "active" : ""}">正常</button><button data-filter="offline" class="${state.filter === "offline" ? "active" : ""}">需关注</button></div><span class="grow"></span></div></div><div class="table-wrap"><table class="table"><thead><tr><th>模块</th><th>运行状态</th><th>契约</th><th>版本</th><th>操作</th></tr></thead><tbody>${moduleRows()}</tbody></table></div><div class="footer"><span>只纳管可信登记中的凝心溯溪系列插件。</span><span>${state.modules.length} 个模块</span></div></section>${selectedDetail()}`;
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
  return window.SeriesKernel.aggregateProblems(state.logs || []);
}
function problemSuggestion(item) {
  return window.SeriesKernel.problemSuggestion(item?.code);
}

function linkStateLabel(state) {
  return window.SeriesKernel.linkStateLabel(state);
}
function linkStateClass(state) {
  return window.SeriesKernel.linkStateClass(state);
}
function linkHealthCard() {
  const health = state.linkHealth;
  if (!health || !Array.isArray(health.links)) return "";
  const summary = health.summary || {};
  const links = health.links;
  const chips = [["ready", "正常", "native"], ["degraded", "降级", "warn"], ["unavailable", "不可用", "managed"], ["stale", "陈旧", "warn"], ["unknown", "未知", ""]]
    .filter(([key]) => summary[key])
    .map(([key, label, cls]) => `<span class="pill ${cls}">${label} ${summary[key]}</span>`)
    .join("");
  const rows = links.length
    ? links.map(link => `<tr><td>${esc(link.plugin_name || link.plugin_id)}</td><td><code>${esc(link.link_id)}</code></td><td><span class="status-dot ${linkStateClass(link.state)}"></span>${esc(linkStateLabel(link.state))}</td><td>${esc(link.reason_code || "—")}</td><td>${esc(link.peer_plugin_id || "—")}</td><td>${esc(link.contract ? `${link.contract}@${link.contract_version || "?"}` : "—")}</td><td>${esc(link.fallback || "—")}</td><td>${link.last_success_at ? esc(relativeTime(link.last_success_at)) : "—"}</td></tr>`).join("")
    : `<tr><td colspan="8">暂无联动链路状态：成员需声明 series.diagnostics@1.1 的 read_state 能力并记录链路。</td></tr>`;
  return `<section class="workspace link-health"><div class="workspace-head"><div class="section-title"><h2>联动健康</h2><span>${links.length} 条链路${health.observed_at ? ` · ${esc(relativeTime(health.observed_at))}` : ""}</span></div></div><div class="link-health-summary">${chips || `<span class="pill">暂无数据</span>`}</div><div class="table-wrap"><table class="table"><thead><tr><th>模块</th><th>链路</th><th>状态</th><th>原因</th><th>对端</th><th>契约</th><th>回退</th><th>最近成功</th></tr></thead><tbody>${rows}</tbody></table></div></section>`;
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
  const problemRows = problems.length ? problems.slice(0, 8).map(item => `<button class="problem-item" data-log-problem="${esc(item.plugin_id)}" data-log-code="${esc(item.code)}"><span class="pill ${item.level === "ERROR" ? "managed" : "warn"}">${esc(item.level)}</span><b>${esc(item.plugin_name)}</b><code>${esc(item.code)}</code><small>${item.count} 次 · ${esc(relativeTime(item.last))}</small><span class="problem-impact">影响范围：${esc(item.plugin_name)}</span><span class="problem-suggestion">建议动作：${esc(problemSuggestion(item))}</span></button>`).join("") : `<p class="empty-cell">当前缓冲区没有警告或错误。</p>`;
  const eventCards = events.length ? events.map(item => {
    const key = `${item.plugin_id}:${item.seq}`;
    const expanded = state.logExpanded.has(key);
    const level = String(item.level || "INFO").toLowerCase();
    const context = expanded ? (state.logs || []).filter(row => row.plugin_id === item.plugin_id && Math.abs(Number(row.seq || 0) - Number(item.seq || 0)) <= 3 && row.seq !== item.seq).sort((a, b) => Number(a.seq || 0) - Number(b.seq || 0)).map(row => `<button class="log-context-item" data-log-seq="${esc(row.seq)}"><code>${esc(row.seq)}</code> ${esc(row.summary || "")}</button>`).join("") : "";
    return `<article class="diagnostic-event level-${esc(level)} ${expanded ? "expanded" : ""} ${state.logNewKeys.has(key) ? "new-event" : ""}" data-log-event="${esc(key)}"><button class="diagnostic-event-head" data-log-toggle="${esc(key)}"><time title="${esc(item.timestamp || "")}">${esc(relativeTime(item.timestamp))}</time><span class="event-module">${esc(item.plugin_name || item.plugin_id)}</span><span class="level-chip level-${esc(level)}">${esc(item.level)}</span><b class="event-message">${esc(item.summary || "未命名事件")}</b><span class="event-chevron">${expanded ? "收起" : "详情"}</span></button>${expanded ? `<div class="diagnostic-event-detail"><div class="event-meta"><span>代码 <code>${esc(item.code || "-")}</code></span><span>序号 <code>${esc(item.seq)}</code></span></div>${logDetailRows(item.details)}${context ? `<div class="log-context"><strong>同模块上下文</strong>${context}</div>` : ""}</div>` : ""}</article>`;
  }).join("") : `<div class="empty-cell">暂无匹配日志，请调整过滤条件或点击「加载日志」。</div>`;
  const selectedModules = modules.map(([id, name]) => `<button class="filter-chip ${state.logModules.includes(id) ? "active" : ""}" data-log-module="${esc(id)}">${esc(name)}</button>`).join("");
  const canClear = state.session?.role === "owner" || state.session?.role === "admin";
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 可观测性</div><h1>诊断与日志</h1><p>先看问题聚合，再展开事件流与上下文。</p></div><div class="actions"><label class="switch"><input type="checkbox" id="log-auto" ${state.logAuto ? "checked" : ""} /><span>5 秒自动刷新</span></label><button class="btn" id="log-pause">${state.logPaused ? "继续" : "暂停"}</button><button class="btn" id="log-autoscroll" aria-pressed="${state.logAutoScroll}">自动滚动${state.logAutoScroll ? " ✓" : ""}</button><button class="btn" id="log-export">导出</button><button class="btn" id="refresh-logs">加载日志</button><button class="btn danger" id="clear-logs" ${canClear ? "" : "disabled"}>清空</button></div></div>${linkHealthCard()}<section class="workspace diagnostic-summary"><div class="workspace-head"><div class="section-title"><h2>待处理问题</h2><span>${problems.length ? `${problems.length} 组待分析问题` : "状态良好"}</span></div></div><div class="problem-list">${problemRows}</div></section><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>事件流</h2><span id="log-summary">显示最近 ${events.length} 条 · 缓存 ${state.logs.length}</span></div></div><div class="diagnostic-filters"><label class="search">⌕<input id="log-search" placeholder="搜索摘要、代码或详情" value="${esc(state.logQuery)}"></label><select id="log-level" class="select"><option value="">全部级别</option>${["ERROR", "WARNING", "INFO", "DEBUG", "CRITICAL"].map(level => `<option value="${level}" ${state.logThreshold === level ? "selected" : ""}>至少 ${level}</option>`).join("")}</select><select id="log-range" class="select">${[["15m", "最近 15 分钟"], ["1h", "最近 1 小时"], ["today", "今天"], ["all", "全部时间"]].map(([value, label]) => `<option value="${value}" ${state.logRange === value ? "selected" : ""}>${label}</option>`).join("")}</select><div class="log-module-filters">${selectedModules || `<span class="form-hint">加载日志后可按模块筛选</span>`}</div></div><div class="diagnostic-log-list" id="diagnostic-log-list">${eventCards}</div></section>`;
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
  const kindHints = { conversation: "决定她怎么想、怎么答", fast: "插话合并、会话判定等即时任务", reasoning: "学习、反思与长期记忆整理", embedding: "记忆检索用的向量模型", vision: "看图、截图理解", stt: "把她的语音消息转成文字", tts: "「声」接管时的默认音色" };
  const routeCards = labels.map(([kind, label]) => {
    const item = route[kind] || {};
    const resolved = (state.routes?.routes || {})[kind] || {};
    const custom = Boolean(item.provider_id || item.model || item.voice);
    const statusChip = custom ? `<span class="pill managed">已自定义</span>` : `<span class="pill native">跟随原生</span>`;
    const effective = resolved.available
      ? `${esc(resolved.provider_id || "AstrBot 原生")} · ${esc(resolved.model || "自动")}${resolved.voice ? ` · ${esc(resolved.voice)}` : ""}`
      : "不可用（未配置或模型服务缺失）";
    const effectiveClass = resolved.available ? "" : " style=\"color:var(--orange)\"";
    const voice = kind === "tts" ? `<input class="route-voice" data-setting-route="${kind}.voice" type="text" value="${esc(item.voice || "")}" placeholder="音色（可选）" ${canWrite ? "" : "disabled"} />` : "";
    return `<div class="route-card"><div class="route-card-head"><b>${label}</b>${statusChip}</div><small>${esc(kindHints[kind] || "")}</small><div class="route-inputs">${providerSelect(kind, item.provider_id || "", canWrite)}${modelSelect(kind, item.provider_id || "", item.model || "", canWrite)}${voice}</div><div class="route-effective">当前生效：<b${effectiveClass}>${effective}</b>${resolved.source ? `（来源：${esc(resolved.source)}）` : ""}</div></div>`;
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
    const meta = [def.read_only ? "重启后生效" : "", def.write_only ? "写入后不回显" : ""].filter(Boolean).join(" · ");
    const hint = fieldHint(key, def);
    const hintHtml = `<small class="field-hint row-hint">${hint && hint !== label ? esc(hint) : ""}</small>`;
    return `<div class="form-row" title="技术名：${esc(key)}"><label><strong>${esc(label)}</strong><small>${esc(meta)}</small></label><div class="form-input">${input}</div><div class="form-meta"></div>${hintHtml}</div>`;
  }).join("");
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 模型策略</div><h1>全局设置</h1><p>统一模型路由与运行项可直接在此编辑；密钥类配置仍在核 Page 维护。WebUI 连接项保存后需重启生效。</p></div><div class="actions"><button class="btn" id="settings-reload">重读</button><button class="btn primary" id="save-settings" ${canWrite ? "" : "disabled"}>保存设置</button></div></div><nav class="si-subnav" role="tablist" aria-label="设置分区"><button type="button" role="tab" data-si-tab="route">模型路由</button><button type="button" role="tab" data-si-tab="runtime">运行项</button><button type="button" role="tab" data-si-tab="config">完整配置</button><button type="button" role="tab" data-si-tab="resolved">解析快照</button><button type="button" role="tab" data-si-tab="security">账户与安全</button></nav><section class="workspace" data-si-panel="route"><div class="workspace-head"><div class="section-title"><h2>统一模型路由</h2><span>留空 = 跟随 AstrBot 原生模型服务；改完点右上角「保存设置」</span></div></div><div class="route-note">「当前生效」优先级：插件显式配置 &gt; 核路由 &gt; AstrBot 原生。</div><div class="route-cards">${routeCards}<div class="route-card route-card-quiet"><div class="route-card-head"><b>一键回退</b><span class="pill">安全操作</span></div><small>把所有职责恢复为「跟随 AstrBot 原生」；插件自己的显式配置不受影响。</small><div class="form-actions" style="margin-top:2px"><button class="btn" id="route-reset-all" ${canWrite ? "" : "disabled"}>全部跟随原生</button><button class="btn" id="route-export">导出当前路由</button></div></div></div></section><section class="workspace" data-si-panel="runtime"><div class="workspace-head"><div class="section-title"><h2>运行项</h2><span>保存后即时生效</span></div></div><div class="form-grid"><div class="form-row"><label title="技术名：auto_update_enabled"><strong>启用自动更新</strong><small>开关 · 到期自动检查并更新系列插件</small></label><div class="form-input"><label class="switch"><input type="checkbox" id="setting-auto-update" ${s.auto_update_enabled ? "checked" : ""} ${canWrite ? "" : "disabled"} /><span>启用自动更新</span></label></div><div class="form-meta"></div></div><div class="form-row"><label title="技术名：log_level"><strong>日志级别</strong><small>文本 · 核自身日志级别</small></label><div class="form-input"><select id="setting-log-level" class="select" ${canWrite ? "" : "disabled"}>${["DEBUG", "INFO", "WARNING", "ERROR"].map(level => `<option value="${level}" ${String(s.log_level || "INFO").toUpperCase() === level ? "selected" : ""}>${level}</option>`).join("")}</select></div><div class="form-meta"></div></div><div class="form-row"><label title="技术名：webui_host"><strong>WebUI 监听地址</strong><small>文本 · 绑定地址（重启生效）</small></label><div class="form-input"><input type="text" id="setting-webui-host" value="${esc(s.webui_host || "")}" ${canWrite ? "" : "disabled"} /></div><div class="form-meta"></div></div><div class="form-row"><label title="技术名：webui_port"><strong>WebUI 端口</strong><small>整数 · 修改后需重启（重启生效）</small></label><div class="form-input"><input type="number" id="setting-webui-port" min="1" max="65535" value="${esc(s.webui_port ?? "")}" ${canWrite ? "" : "disabled"} /></div><div class="form-meta"></div></div><div class="form-row"><label title="技术名：webui_public_url"><strong>WebUI 对外地址</strong><small>文本 · 对外展示地址（重启生效）</small></label><div class="form-input"><input type="text" id="setting-webui-url" value="${esc(s.webui_public_url || "")}" ${canWrite ? "" : "disabled"} /></div><div class="form-meta"></div></div></div></section><section class="workspace" data-si-panel="config"><div class="workspace-head"><div class="section-title"><h2>完整配置</h2><span>${Object.keys(state.settingsData?.schema || {}).length} 个字段；只读字段不会提交</span></div></div><div class="form-grid">${genericRows || `<p class="empty-cell">当前后端未提供配置 schema。</p>`}</div></section><section class="workspace" data-si-panel="resolved"><div class="workspace-head"><div class="section-title"><h2>当前路由解析快照</h2><span>模型路由 1.0</span></div></div><div class="table-wrap"><table class="table"><thead><tr><th>能力</th><th>模型服务商</th><th>模型</th><th>来源</th><th>状态</th></tr></thead><tbody>${resolvedRows}</tbody></table></div><div class="footer"><span>插件显式配置 &gt; 核路由 &gt; AstrBot 原生模型服务。</span><span>只接受安全字段，不回显密钥。</span></div></section><section class="workspace" data-si-panel="security">${securityPanel()}</section>`;
}
function controlCatalog() {
  const catalog = state.control?.capabilities;
  if (!catalog || !Array.isArray(catalog.domains) || !Array.isArray(catalog.capabilities)) return { domains: [], capabilities: [] };
  return catalog;
}
function catalogCapabilities() { return controlCatalog().capabilities || []; }
function capabilitiesOfDomain(domainId) { return catalogCapabilities().filter(cap => cap.domain === domainId); }
function capabilityById(id) { return catalogCapabilities().find(cap => cap.id === id) || null; }
function controlMember(pluginId) { return (state.control?.members || []).find(item => item.plugin_id === pluginId) || null; }
function memberDisplayName(pluginId) { return controlMember(pluginId)?.display_name || pluginId; }
function capabilityBadge(status) {
  return ({
    "统一接管": "正常",
    "核内置": "核自带",
    "独立配置": "独立配置",
    "部分独立配置": "部分独立",
    "部分不可用": "不可用",
    "部分接管": "部分接管",
  })[status?.label] || (status?.label || "未知");
}
function capabilityMetaText(capability) {
  const providers = capability.providers || [];
  const views = capability.views || [];
  const fieldCount = providers.reduce((sum, provider) => sum + (provider.fields || []).length, 0);
  if (!providers.length) return views.length ? "核自带" : "暂无可用入口";
  if (providers.length === 1) return fieldCount ? `${fieldCount} 项可调` : "在模块里设置";
  return `${providers.length} 个模块共同提供` + (fieldCount ? ` · ${fieldCount} 项可调` : " · 在模块里设置");
}
function capabilityAction(capability) {
  if ((capability.providers || []).length) return "设置 ›";
  if ((capability.views || []).length) return "打开 ›";
  return "暂无入口";
}
function capabilityNeedsAttention(capability) {
  return capabilityStatus(capability).cls !== "ok";
}
function sortCapabilities(capabilities) {
  const rank = { warn: 0, mixed: 1, native: 2, ok: 3 };
  return [...capabilities].sort((left, right) => {
    const delta = (rank[capabilityStatus(left).cls] ?? 9) - (rank[capabilityStatus(right).cls] ?? 9);
    if (delta) return delta;
    return String(left.title || "").localeCompare(String(right.title || ""), "zh-Hans-CN");
  });
}
function capabilityStatus(capability) {
  const ids = (capability.providers || []).map(provider => provider.plugin_id);
  if (!ids.length) return { label: "核内置", cls: "ok" };
  const statuses = ids.map(id => controlMember(id)?.status || "not_loaded");
  if (statuses.every(status => status === "managed")) return { label: "统一接管", cls: "ok" };
  if (statuses.every(status => status === "native")) return { label: "独立配置", cls: "native" };
  if (statuses.some(status => status === "not_loaded")) return { label: "部分不可用", cls: "warn" };
  if (statuses.some(status => status === "native")) return { label: "部分独立配置", cls: "mixed" };
  return { label: "部分接管", cls: "mixed" };
}
function domainStatus(capabilities) {
  const labels = capabilities.map(cap => capabilityStatus(cap).label);
  if (!labels.length) return { label: "无能力", cls: "native" };
  if (labels.every(label => label === "统一接管" || label === "核内置")) return { label: "统一接管", cls: "ok" };
  if (labels.every(label => label === "独立配置")) return { label: "独立配置", cls: "native" };
  if (labels.some(label => label === "部分不可用")) return { label: "部分不可用", cls: "warn" };
  return { label: "部分独立配置", cls: "mixed" };
}

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
    MODE_SYNC_FAILED: "接管模式同步失败",
  })[String(reason || "")] || String(reason || "运行正常");
}

function controlView() {
  const control = state.control || { mode: "native", members: [], revision: 0 };
  const catalog = controlCatalog();
  const capabilities = catalog.capabilities || [];
  const attention = capabilities.filter(capabilityNeedsAttention).length;
  const modeLabel = control.mode === "managed" ? "统一接管" : "独立配置";
  const legend = `<span class="status-legend"><span><i class="status-dot ok"></i>正常</span><span><i class="status-dot mixed"></i>部分独立</span><span><i class="status-dot warn"></i>不可用</span><span><i class="status-dot native"></i>独立配置</span></span>`;
  const modeLine = `<div class="control-mode-line"><span class="pill ${control.mode === "managed" ? "" : "native"}">${modeLabel}</span><span>${catalog.domains.length} 个功能域</span><span>${capabilities.length} 项能力</span>${attention ? `<span class="pending">待处理 ${attention}</span>` : ""}${legend}<span class="muted">版本号 ${esc(control.revision)}</span></div>`;
  const detail = state.selectedCapability ? capabilityDetail() : "";
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 统一接管</div><h1>系列接管</h1><p>按功能分类管理：左边选功能域，右边点能力卡片直接调整；模块身份只在模块详情与排障中出现。</p></div><div class="actions"><button class="btn" id="refresh-control">刷新</button>${state.session?.role === "owner" ? `<button class="btn primary" id="toggle-control">${control.mode === "managed" ? "关闭统一接管" : "启用统一接管"}</button>` : ""}${state.session?.role === "owner" || state.session?.role === "admin" ? `<button class="btn danger" id="freeze-all" title="把所有模块的当前生效配置写入它们自己的配置（先自动备份）">一键固化全部</button>` : ""}</div></div>${modeLine}${detail || masterDetail()}`;
}
function masterDetail() {
  const catalog = controlCatalog();
  const domains = catalog.domains || [];
  if (!domains.length) return `<p class="empty-cell">能力目录未加载：请刷新或检查核版本。</p>`;
  const active = domains.find(item => item.id === state.selectedDomain) || domains[0];
  const domainCapabilities = sortCapabilities(capabilitiesOfDomain(active.id));
  const items = domains.map(domain => domainItem(domain, domain.id === active.id)).join("");
  const cards = domainCapabilities.map(capabilityCard).join("") || `<p class="empty-cell">该功能域暂无能力。</p>`;
  const attention = domainCapabilities.filter(capabilityNeedsAttention).length;
  const head = `<div class="capability-head"><b>${esc(active.title)}</b><span>${domainCapabilities.length} 项能力${attention ? ` · ${attention} 项待处理` : ""}</span><span class="sort-tag" title="异常项排在前面">异常优先 ▾</span></div>`;
  return `<div class="master-detail"><div class="domain-list" role="tablist" aria-label="功能域">${items}</div><div class="capability-column">${head}<div class="capability-grid" role="list" aria-label="${esc(active.title)}能力">${cards}</div></div></div>`;
}
function domainItem(domain, active) {
  const capabilities = capabilitiesOfDomain(domain.id);
  const status = domainStatus(capabilities);
  const attention = capabilities.filter(capabilityNeedsAttention).length;
  const preview = capabilities.slice(0, 2).map(item => item.title).join(" · ");
  const stateText = attention ? `${attention} 项待处理` : status.label;
  return `<button class="domain-item ${active ? "active" : ""}" role="tab" aria-selected="${active ? "true" : "false"}" data-catalog-domain-open="${esc(domain.id)}"><span class="domain-top"><span class="status-dot ${status.cls}" title="${esc(status.label)}"></span><b>${esc(domain.title)}</b><i>${capabilities.length}</i></span><small><em class="domain-state ${status.cls}">${esc(stateText)}</em> · ${esc(preview)}${capabilities.length > 2 ? " …" : ""}</small></button>`;
}
function capabilitySwitchSpec(capability) {
  return (capability.providers || []).find(provider => provider.switch_field) || null;
}
function capabilitySwitchState(provider, field) {
  const data = (state.controlSwitches || {})[provider.plugin_id];
  if (!data) return { pending: true };
  if (data.error) return { error: data.error };
  const def = data.schema?.schema?.fields?.[field];
  if (!def || def.type !== "bool") return { unsupported: true };
  const value = data.snapshot?.snapshot?.fields?.[field] || {};
  return {
    data,
    def,
    checked: value.effective_value === true,
    managed: !!value.managed_configured,
    canWrite: (state.session?.role === "owner" || state.session?.role === "admin") && data.schema?.mode === "managed",
  };
}
function capabilitySwitchHtml(capability) {
  const provider = capabilitySwitchSpec(capability);
  if (!provider) return "";
  const field = provider.switch_field;
  const info = capabilitySwitchState(provider, field);
  // 目录里的 switch_label 优先（插件 schema 往往不带中文标签，兜底会是原始字段名）
  const label = provider.switch_label || fieldLabel(field, info.def, provider.plugin_id);
  const modeError = info.data?.schema?.mode_error || "";
  const title = info.error
    ? `开关读取失败：${info.error}`
    : info.pending
      ? `${label}：正在读取当前状态`
      : modeError
        ? `${label} · 接管模式同步失败：${modeError}`
        : `${label} · ${info.managed ? "核覆盖" : "插件原生"}`;
  const disabled = Boolean(info.pending || info.error || info.unsupported || !info.canWrite);
  return `<label class="si-switch cap-switch${info.pending ? " busy" : ""}" title="${esc(title)}"><span class="cap-switch-text">${esc(label)}</span><input type="checkbox" role="switch" data-cap-switch-plugin="${esc(provider.plugin_id)}" data-cap-switch-field="${esc(field)}" aria-label="${esc(label)}" ${info.checked ? "checked" : ""} ${disabled ? "disabled" : ""} /></label>`;
}
function capabilityCard(capability) {
  const status = capabilityStatus(capability);
  const providers = capability.providers || [];
  const views = capability.views || [];
  const disabled = !providers.length && !views.length;
  const toggle = capabilitySwitchHtml(capability);
  const openAttr = `data-capability-open="${esc(capability.id)}" ${disabled ? "disabled" : ""}`;
  const head = `<div class="cap-card-head"><button class="cap-card-open" ${openAttr}><span class="cap-badge ${status.cls}">${esc(capabilityBadge(status))}</span><b>${esc(capability.title)}</b></button>${toggle}</div>`;
  return `<div class="capability-card${toggle ? " has-switch" : ""}" role="listitem">${head}<small class="cap-card-desc">${esc(capability.description)}</small><button class="cap-card-meta cap-card-meta-link" ${openAttr}>${esc(capabilityMetaText(capability))} <em>${esc(capabilityAction(capability))}</em></button></div>`;
}

function capTabFor(pluginId) { return (state.capTabs || {})[pluginId] || "fields"; }
function setCapTab(pluginId, tab) { state.capTabs = state.capTabs || {}; state.capTabs[pluginId] = tab; }
function capPanelStore(pluginId) {
  state.capPanels = state.capPanels || {};
  if (!state.capPanels[pluginId]) state.capPanels[pluginId] = { list: null, data: null, selected: "", disabled: false };
  return state.capPanels[pluginId];
}
function capabilityProviderHead(provider) {
  const pluginId = provider.plugin_id;
  const tab = capTabFor(pluginId);
  const tabs = [["fields", "本能力字段"], ["all", "全部字段"], ["panels", "插件面板"], ["lifecycle", "生命周期"]];
  const strip = `<div class="cap-provider-tabs" role="tablist" aria-label="${esc(memberDisplayName(pluginId))}视图">${tabs.map(([id, label]) => `<button type="button" role="tab" aria-selected="${tab === id ? "true" : "false"}" class="cap-provider-tab ${tab === id ? "active" : ""}" data-cap-tab="${esc(pluginId)}|${id}">${label}</button>`).join("")}</div>`;
  const canOperate = state.session?.role === "owner" || state.session?.role === "admin";
  const ops = canOperate
    ? `<span class="cap-provider-ops"><button class="btn" data-native-read="${esc(pluginId)}" title="读取插件自身配置并与核接管值对比">读取当前配置</button><button class="btn" data-native-freeze="${esc(pluginId)}" title="把当前生效配置写入插件自身配置，核掉线也保持一致">固化到插件</button></span>`
    : "";
  return `<div class="capability-provider-head"><strong>${esc(memberDisplayName(pluginId))}</strong>${provider.hint ? `<small>${esc(provider.hint)}</small>` : ""}${ops}</div>${strip}`;
}
function capabilityDetail() {
  const capability = capabilityById(state.selectedCapability);
  if (!capability) return "";
  const providers = capability.providers || [];
  const sections = providers.map(provider => {
    const data = (state.capabilityData || {})[provider.plugin_id] || {};
    const head = capabilityProviderHead(provider);
    const shell = (inner) => `<div class="capability-provider" data-capability-provider="${esc(provider.plugin_id)}">${head}${inner}</div>`;
    const tab = capTabFor(provider.plugin_id);
    // 面板与生命周期不依赖字段契约：没有 series.control 也能进
    if (tab === "panels") return shell(capabilityPanelsTab(provider.plugin_id));
    if (tab === "lifecycle") return shell(capabilityLifecycleTab(provider.plugin_id));
    if (data.error) return shell(`<p class="empty-cell">读取失败：${esc(data.error)}</p><p class="form-hint">仍可切到「插件面板」或「生命周期」查看该模块。</p>`);
    if (!data.schema) return shell(`<p class="empty-cell">该模块未提供统一接管字段契约。</p><p class="form-hint">可切到「插件面板」或「生命周期」；完整设置请用插件自己的 Page。</p>`);
    const body = tab === "all"
      ? controlFieldsTab(data.schema, data.snapshot, { pluginId: provider.plugin_id })
      : controlFieldsTab(data.schema, data.snapshot, { fields: provider.fields || [], capabilityTitle: capability.title, pluginId: provider.plugin_id });
    return shell(body);
  }).join("");
  return `<section class="workspace" id="capability-detail"><div class="workspace-head"><div class="section-title"><h2>${esc(capability.title)}</h2><span>${esc(capability.description)}</span></div><button class="btn" data-capability-back>返回能力列表</button></div>${sections || `<p class="empty-cell">该能力由核内置提供，请使用对应治理视图。</p>`}</section>`;
}
async function loadCapability(capabilityId) {
  const capability = capabilityById(capabilityId);
  if (!capability) return;
  state.selectedCapability = capabilityId;
  state.selectedControlPlugin = "";
  state.capabilityData = {};
  await Promise.all((capability.providers || []).map(async provider => {
    try {
      const [schema, snapshot] = await Promise.all([
        get(`series/${encodeURIComponent(provider.plugin_id)}/control/schema`),
        get(`series/${encodeURIComponent(provider.plugin_id)}/control/snapshot`)
      ]);
      state.capabilityData[provider.plugin_id] = { schema, snapshot };
    } catch (error) {
      state.capabilityData[provider.plugin_id] = { error: error.message };
    }
  }));
  state.view = "control";
  dashboard();
}

function controlFieldsTab(schema, snapshot, opts) {
  const options = opts || {};
  const allFields = schema?.schema?.fields || {};
  const values = snapshot?.snapshot?.fields || {};
  const managed = schema?.mode === "managed";
  const canWrite = (state.session?.role === "owner" || state.session?.role === "admin") && managed;
  const pluginId = schema?.plugin_id || "";
  const filter = Array.isArray(options.fields) ? new Set(options.fields.map(String)) : null;
  const filtered = filter ? Object.entries(allFields).filter(([name]) => filter.has(name)) : Object.entries(allFields);
  const missing = filter ? [...filter].filter(name => !(name in allFields)) : [];
  const emptyText = filter
    ? `该能力在当前模块没有可接管字段${options.capabilityTitle ? `（${esc(options.capabilityTitle)}）` : ""}，请到插件页设置中心调整。`
    : "该插件未声明可管理字段。";
  const rowsHtml = filtered.map(([name, def]) => {
    const value = values[name] || {};
    const current = value.effective_value ?? def.default ?? "";
    const isManaged = !!value.managed_configured;
    const source = isManaged ? `<span class="pill managed">核覆盖</span>` : "";
    let input = "";
    if (def.secret) input = `<input type="password" data-control-field="${esc(name)}" placeholder="${current ? "已配置（不回显）" : "未配置"}" ${canWrite ? "" : "disabled"}>`;
    else if (def.type === "bool") input = `<label class="si-switch"><input type="checkbox" data-control-field="${esc(name)}" ${current === true ? "checked" : ""} ${canWrite ? "" : "disabled"} /><span>${current === true ? "启用" : "停用"}</span></label>`;
    else if (def.type === "int" || def.type === "float") input = `<input type="number" step="${def.type === "float" ? "any" : "1"}" min="${esc(def.minimum ?? "")}" max="${esc(def.maximum ?? "")}" value="${esc(current === null ? "" : current)}" data-control-field="${esc(name)}" ${canWrite ? "" : "disabled"}>`;
    else input = `<input type="text" value="${esc(current === null ? "" : current)}" data-control-field="${esc(name)}" ${canWrite ? "" : "disabled"}>`;
    const note = def.control === "read_only" ? `<span class="pill">只读</span>` : "";
    const ctrlLabel = fieldLabel(name, def, pluginId);
    const ctrlHint = fieldHint(name, def, pluginId);
    const ctrlHintHtml = `<small class="field-hint row-hint">${ctrlHint && ctrlHint !== ctrlLabel ? esc(ctrlHint) : ""}</small>`;
    return `<div class="form-row" title="技术名：${esc(name)}"><label><strong>${esc(ctrlLabel)}</strong><small>${esc(typeLabel(def.type))}</small></label><div class="form-input">${input}</div><div class="form-meta">${source}${note}</div>${ctrlHintHtml}</div>`;
  }).join("") || `<p class="empty-cell">${emptyText}</p>`;
  const missingHint = missing.length
    ? `<p class="form-hint">以下字段在当前版本不存在：${missing.map(esc).join("、")}</p>`
    : "";
  const scopeHint = options.capabilityTitle
    ? `<div class="form-hint">正在编辑能力「${esc(options.capabilityTitle)}」，仅显示该能力的字段。</div>`
    : "";
  const hint = !managed
    ? "统一接管未启用：字段以插件 native 配置为准，开启统一接管后才能在此修改。"
    : canWrite
      ? "修改后点击「应用修改」：先校验再写入覆盖层，带并发保护。"
      : "当前角色为 viewer，仅可查看字段。";
  return `<div class="form-hint">${hint}</div>${scopeHint}${missingHint}<div class="form-grid">${rowsHtml}</div><div class="form-actions"><button class="btn primary" data-control-apply="${esc(pluginId)}" ${canWrite ? "" : "disabled"}>应用修改</button><button class="btn" data-control-reset="${esc(pluginId)}" ${canWrite ? "" : "disabled"}>重置全部覆盖</button><button class="btn" data-control-refresh="${esc(pluginId)}">刷新字段</button></div>`;
}

function capabilityPanelsTab(pluginId) {
  const store = capPanelStore(pluginId);
  if (!store.list) {
    return `<p class="empty-cell">尚未加载该插件的管理面板。</p><p class="form-hint"><button class="btn primary" data-cap-panels-load="${esc(pluginId)}">加载该插件面板</button> 面板来自插件提供的面板接口；未实现该接口的插件此区为空。</p>`;
  }
  if (store.disabled) return `<p class="empty-cell">统一接管未启用：managed 面板已关闭，请使用该插件的独立 Page。</p>`;
  const panels = store.list.panels || [];
  if (!panels.length) return `<p class="empty-cell">该插件未提供管理面板（未提供面板接口）。</p>`;
  const buttons = panels.map(panel => `<button class="btn ${store.selected === panel.id ? "primary" : ""}" data-panel-plugin="${esc(pluginId)}" data-panel-select="${esc(panel.id)}">${esc(panel.title)}</button>`).join("");
  const unsupported = store.list.unsupported_capabilities || [];
  const capabilityHint = unsupported.length ? `<p class="form-hint">当前核版本尚不支持：${unsupported.map(esc).join("、")}；相关功能请使用插件独立 Page。</p>` : "";
  const content = store.data && store.selected ? panelContent(store.data, pluginId) : `<p class="empty-cell">选择一个面板查看。</p>`;
  return `<div data-cap-panels="${esc(pluginId)}"><div class="panel-nav">${buttons}</div>${capabilityHint}<div class="panel-body">${content}</div></div>`;
}
function roleRank(role) { return ({ viewer: 0, admin: 1, owner: 2 })[role] ?? -1; }
function actionAllowed(action) { return roleRank(state.session?.role) >= roleRank(action.min_role || "admin"); }
function panelContent(data, pluginId = "") {
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
    return `<div class="panel-action">${fields ? `<div class="panel-action-form">${fields}</div>` : ""}<button class="btn ${action.danger ? "danger" : "primary"}" data-panel-plugin="${esc(pluginId)}" data-panel-action="${esc(action.id)}" data-action-effect="${esc(action.effect || "idempotent")}" data-action-revision-required="${action.revision_required ? "true" : "false"}" data-action-idempotency-required="${action.idempotency_required ? "true" : "false"}" ${disabled}>${esc(action.label || action.id)}${allowed ? "" : ` · 需要 ${esc(action.min_role || "admin")}`}</button></div>`;
  }).join("");
  const artifacts = Array.isArray(data.artifacts) ? data.artifacts : [];
  const artifactHtml = artifacts.length
    ? `<div class="artifact-list">${artifacts.map(item => `<a class="btn" href="/api/artifacts/${encodeURIComponent(item.artifact_id || "")}" target="_blank" rel="noopener">${esc(item.filename || item.artifact_id || "下载")}</a>`).join("")}</div>`
    : "";
  const audioHtml = data.audio?.artifact_id
    ? `<audio controls preload="none" src="/api/artifacts/${encodeURIComponent(data.audio.artifact_id)}"></audio>`
    : "";
  const streamHtml = data.stream
    ? `<div class="panel-stream-controls"><button class="btn" data-panel-stream-start="${esc(pluginId)}" type="button">开始实时流</button><pre data-panel-stream="${esc(pluginId)}" class="panel-stream"></pre></div>`
    : "";
  return `${data.title ? `<div class="section-title"><h3>${esc(data.title)}</h3>${data.description ? `<span>${esc(data.description)}</span>` : ""}</div>` : ""}${table}${actions ? `<div class="panel-actions">${actions}</div>` : ""}${artifactHtml}${audioHtml}${streamHtml}${data.footer ? `<p class="form-hint">${esc(data.footer)}</p>` : ""}`;
}
function capabilityLifecycleTab(pluginId) {
  const module = state.modules.find(item => item.plugin_id === pluginId);
  const isOwner = state.session?.role === "owner";
  const status = module ? `<span class="status ${module.status === "normal" ? "" : "off"}">${module.status === "normal" ? "运行正常" : "已停用/未加载"}</span>` : `<span class="pill">未安装</span>`;
  return `<div class="detail-grid"><div><span>当前状态</span><strong>${status}</strong></div><div><span>当前版本</span><strong><code>v${esc(module?.version || "未知")}</code></strong></div><div><span>更新检查</span><strong>${module?.update_available ? "有更新" : "未检查/当前"}</strong></div></div><p class="form-hint">${isOwner ? "更新与启停失败可回滚，执行前需确认。" : "生命周期操作仅 owner 可执行。"}</p><div class="form-actions"><label class="switch"><input type="checkbox" id="lifecycle-force" /><span>强制更新（覆盖本地）</span></label><button class="btn primary" data-lifecycle="update" data-lifecycle-plugin="${esc(pluginId)}" ${isOwner && module ? "" : "disabled"}>更新</button><button class="btn" data-lifecycle="enable" data-lifecycle-plugin="${esc(pluginId)}" ${isOwner && module ? "" : "disabled"}>启用</button><button class="btn danger" data-lifecycle="disable" data-lifecycle-plugin="${esc(pluginId)}" ${isOwner && module ? "" : "disabled"}>停用</button><button class="btn" data-lifecycle="install" data-lifecycle-plugin="${esc(pluginId)}" ${isOwner && !module ? "" : "disabled"}>安装</button></div>`;
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
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 生命周期</div><h1>每日规则</h1><p>统一管理更新窗口、版本策略、失败处理与目标模块；保存带并发保护，避免两台页面互相覆盖。</p></div><div class="actions"><button class="btn" id="rules-reload">重读</button><button class="btn primary" id="save-rule" ${canWrite ? "" : "disabled"}>保存规则</button></div></div><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>执行窗口</h2><span>${esc(globalState)}</span></div></div><div class="form-grid"><div class="form-row"><label title="技术名：enabled"><strong>启用此规则</strong><small>每日规则自身开关</small></label><div class="form-input"><label class="switch"><input id="rule-enabled" type="checkbox" ${rule.enabled ? "checked" : ""} ${canWrite ? "" : "disabled"} /><span>启用此规则</span></label></div><div class="form-meta"></div></div><div class="form-row"><label title="技术名：local_time"><strong>执行时间</strong><small>每天执行时间</small></label><div class="form-input"><input id="rule-time" type="time" value="${esc(rule.local_time || "04:00")}" ${canWrite ? "" : "disabled"} /></div><div class="form-meta"></div></div><div class="form-row"><label title="技术名：timezone"><strong>时区</strong><small>IANA 时区</small></label><div class="form-input"><input id="rule-timezone" value="${esc(rule.timezone || "Asia/Shanghai")}" ${canWrite ? "" : "disabled"} /></div><div class="form-meta"></div></div><div class="form-row"><label title="技术名：jitter_minutes"><strong>随机延迟（分钟）</strong><small>随机抖动，避免同时请求</small></label><div class="form-input"><input id="rule-jitter" type="number" min="0" max="120" value="${esc(rule.jitter_minutes ?? 0)}" ${canWrite ? "" : "disabled"} /></div><div class="form-meta"></div></div><div class="form-row"><label title="技术名：misfire_grace_minutes"><strong>错过执行的宽限（分钟）</strong><small>错过后的补执行窗口</small></label><div class="form-input"><input id="rule-misfire" type="number" min="0" max="1440" value="${esc(rule.misfire_grace_minutes ?? 60)}" ${canWrite ? "" : "disabled"} /></div><div class="form-meta"></div></div></div></section><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>版本与失败策略</h2><span>${data.next_run ? `下次执行：${esc(data.next_run)}` : "当前无计划"}</span></div></div><div class="form-grid"><div class="form-row"><label title="技术名：policy"><strong>更新策略</strong><small>允许升级的最大范围</small></label><div class="form-input"><select id="rule-policy" ${canWrite ? "" : "disabled"}>${policies.map(([value, label]) => `<option value="${value}" ${rule.policy === value ? "selected" : ""}>${label}</option>`).join("")}</select></div><div class="form-meta"></div></div><div class="form-row"><label title="技术名：minimum_release_age_hours"><strong>最小发布年龄（小时）</strong><small>发布冷却时间</small></label><div class="form-input"><input id="rule-age" type="number" min="0" max="8760" value="${esc(rule.minimum_release_age_hours ?? 24)}" ${canWrite ? "" : "disabled"} /></div><div class="form-meta"></div></div><div class="form-row"><label title="技术名：on_failure"><strong>失败处理</strong><small>失败回滚策略</small></label><div class="form-input"><select id="rule-failure" ${canWrite ? "" : "disabled"}>${failures.map(([value, label]) => `<option value="${value}" ${rule.on_failure === value ? "selected" : ""}>${label}</option>`).join("")}</select></div><div class="form-meta"></div></div><div class="form-row"><label title="技术名：prerelease"><strong>允许预发布版本</strong><small>是否接受预发布版本</small></label><div class="form-input"><label class="switch"><input id="rule-prerelease" type="checkbox" ${rule.prerelease ? "checked" : ""} ${canWrite ? "" : "disabled"} /><span>允许 prerelease</span></label></div><div class="form-meta"></div></div></div></section><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>目标模块</h2><span>${selected.size} 个已选择；核自身始终排除</span></div></div><div class="log-module-filters">${pluginRows || `<span class="empty-cell">当前没有可选择的已加载模块。</span>`}</div><p class="form-hint">${esc(data.policy_note || "规则保存后会立即重建调度。")}</p></section>`;
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
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 全系列</div><h1>系列推荐</h1><p>固定可信清单的安装与版本状态；批量操作逐个执行并保留恢复点，核自身不会更新。</p></div><div class="actions"><button class="btn primary" id="check-recommendations" ${canCheck ? "" : "disabled"}>检查最新版本</button><button class="btn danger" id="apply-recommendations" ${canApply ? "" : "disabled"}>一键安装/更新</button></div></div><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>可信模块</h2><span>${data.items?.length || 0} 个模块</span></div></div><div class="table-wrap"><table class="table"><thead><tr><th>模块</th><th>状态与目标版本</th><th>当前版本</th><th>操作</th></tr></thead><tbody>${rows || `<tr><td colspan="4" class="empty-cell">暂无模块。</td></tr>`}</tbody></table></div><div class="footer"><span>普通更新只在远端版本更高时执行。</span><span>${data.rate_limit ? `GitHub 剩余 ${esc(data.rate_limit.remaining ?? "?")}` : "未读取限流状态"}</span></div></section>`;
}
function securityPanel() {
  const data = state.adminsData;
  const canManage = state.session?.role === "owner";
  const admins = data?.admins || [];
  const rows = admins.map(item => `<article class="account-card" data-admin-card="${esc(item.id)}"><header class="account-card-head"><div><b>${esc(item.username)}</b><small>${esc(item.id)}</small></div><span class="pill ${item.enabled ? "native" : "warn"}">${item.enabled ? "启用" : "禁用"}</span></header><div class="account-card-grid"><label class="account-card-field"><span>角色</span><select data-admin-role="${esc(item.id)}" ${canManage ? "" : "disabled"}>${[["owner", "所有者"], ["admin", "管理员"], ["viewer", "只读"]].map(([role, label]) => `<option value="${role}" ${item.role === role ? "selected" : ""}>${label}</option>`).join("")}</select></label><label class="account-card-field"><span>状态</span><span class="switch"><input type="checkbox" data-admin-enabled="${esc(item.id)}" ${item.enabled ? "checked" : ""} ${canManage ? "" : "disabled"} /><span>${item.enabled ? "启用" : "禁用"}</span></span></label><label class="account-card-field"><span>重置密码</span><input type="password" data-admin-password="${esc(item.id)}" placeholder="留空不改密码" ${canManage ? "" : "disabled"} /></label></div><div class="account-card-actions"><button class="btn primary" data-admin-update="${esc(item.id)}" ${canManage ? "" : "disabled"}>保存这个账户</button></div></article>`).join("");
  return `<section class="workspace"><div class="workspace-head"><div class="section-title"><h2>当前会话</h2><span>服务端 Cookie · 8 小时空闲 / 24 小时绝对过期</span></div></div><div class="detail-grid account-grid"><div><span>用户名</span><strong>${esc(state.session?.username || "管理员")}</strong></div><div><span>角色</span><strong>${esc(state.session?.role || "admin")}</strong></div><div><span>会话状态</span><strong>已认证</strong></div></div></section><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>管理员账户</h2><span>${canManage ? `${admins.length} 个账户` : "仅 owner 可管理账户"}</span></div></div><div class="account-card-list">${rows || `<p class="empty-cell">加载中或暂无账户。</p>`}</div></section><section class="workspace"><div class="workspace-head"><div class="section-title"><h2>新建管理员</h2><span>至少 8 位密码；用户名不可包含空格</span></div></div><div class="form-grid"><div class="form-row"><label title="技术名：username"><strong>用户名</strong><small>登录名</small></label><div class="form-input"><input id="admin-new-username" ${canManage ? "" : "disabled"} /></div><div class="form-meta"></div></div><div class="form-row"><label title="技术名：password"><strong>初始密码</strong><small>至少 8 位</small></label><div class="form-input"><input id="admin-new-password" type="password" minlength="8" ${canManage ? "" : "disabled"} /></div><div class="form-meta"></div></div><div class="form-row"><label title="技术名：role"><strong>角色</strong><small>最小权限优先</small></label><div class="form-input"><select id="admin-new-role" ${canManage ? "" : "disabled"}><option value="viewer">只读</option><option value="admin">管理员</option><option value="owner">所有者</option></select></div><div class="form-meta"><button class="btn primary" id="admin-create" ${canManage ? "" : "disabled"}>创建</button></div></div></div></section>`;
}

function securityView() {
  return `<div class="page-head"><div><div class="eyebrow">系列治理 / 访问控制</div><h1>安全与账户</h1><p>控制中心管理员与核 Page 共用同一份本地账户；登录状态有时效，过期后需重新登录。</p></div><div class="actions"><button class="btn" id="admins-reload">刷新账户</button><button class="btn danger" id="security-logout">退出登录</button></div></div>${securityPanel()}`;
}
const VIEW_RENDERERS = { modules: modulesView, control: controlView, updates: updatesView, recommendations: recommendationsView, rules: rulesView, mirrors: mirrorsView, diagnostics: diagnosticsView, settings: settingsView, security: securityView };
const VIEW_ENTERS = { control: loadControl, updates: async () => { dashboard(); await loadTransactions(); }, recommendations: loadRecommendations, rules: loadRules, mirrors: loadMirrors, diagnostics: loadDiagnostics, settings: loadSettings, security: loadAdmins };
async function enterView(view) {
  const id = VIEWS[view] ? view : "control";
  state.view = id;
  const enter = VIEW_ENTERS[id];
  if (enter) await enter();
  else dashboard();
}
function viewContent() {
  const entry = VIEWS[state.view] || VIEWS.modules;
  const renderer = VIEW_RENDERERS[state.view] || controlView;
  const suiteId = Array.isArray(entry.suite) ? state.view : (entry.inSuite || "");
  const tabs = suiteId ? suiteTabStrip(suiteId) : "";
  return tabs + renderer();
}
function rail() {
  const groups = NAV_GROUPS.map(([groupId, label]) => {
    const items = railItemsForGroup(groupId);
    if (!items.length) return "";
    const buttons = items.map(([view, icon, itemLabel, , , suite]) => {
      const isSuiteHead = Array.isArray(suite);
      const active = state.view === view || (isSuiteHead && suite.includes(state.view));
      return `<button class="${active ? "active" : ""}" data-view="${view}" aria-current="${active ? "page" : "false"}">${icon}　${itemLabel}</button>`;
    }).join("");
    return `<div class="nav-label">${label}</div><nav class="nav">${buttons}</nav>`;
  }).join("");
  return `<aside class="rail"><div class="brand"><span class="brand-mark">核</span><div><strong>凝心溯溪</strong><small>模块运营中心</small></div></div>${groups}<div class="spacer"></div><div class="health"><b>系列健康度</b><p>${state.modules.length} 个可信模块已纳管。模块发现不执行任意第三方代码。</p><div class="bar"><i></i></div></div><div class="user"><span class="avatar">管</span><span>${esc(state.session?.username || "管理员")}</span><button class="logout" id="rail-logout">↪</button></div></aside>`;
}

function dashboard() {
  app.innerHTML = `<div class="shell">${rail()}<main class="main"><header class="topbar"><div class="crumb">凝心溯溪 / <b>核 · ${VIEW_TITLES[state.view] || "模块运营中心"}</b></div><div class="top-actions"><button class="btn" id="refresh">刷新</button><button class="btn" id="logout">退出登录</button></div></header><div class="content">${viewContent()}</div></main></div><nav class="mobile-nav" aria-label="移动端工作区导航">${["control", "diagnostics", "updates"].map((view) => { const item = NAV_ITEMS.find(([id]) => id === view); return `<button class="${state.view === view ? "active" : ""}" data-view="${view}" aria-current="${state.view === view ? "page" : "false"}"><span>${item[1]}</span>${item[2]}</button>`; }).join("")}<button id="mobile-more" aria-expanded="false"><span>⋯</span>更多</button></nav><div id="mobile-more-sheet" class="si-mobile-more-sheet" hidden>${NAV_ITEMS.filter(([view]) => !["control", "diagnostics", "updates"].includes(view) && !VIEWS[view]?.hidden).map(([view, icon, label]) => `<button class="btn" data-view="${view}" aria-current="${state.view === view ? "page" : "false"}"><span>${icon}</span>${label}</button>`).join("")}<button class="btn" id="mobile-logout"><span>⇥</span>退出</button></div>`;
  bindDashboard();
}
function bindSettingsTabs() {
  const tabs = [...document.querySelectorAll("[data-si-tab]")];
  const panels = [...document.querySelectorAll("[data-si-panel]")];
  if (!tabs.length || !panels.length) return;
  const activate = (value) => {
    const target = tabs.some((tab) => tab.dataset.siTab === value) ? value : tabs[0].dataset.siTab;
    state.settingsTab = target;
    if (target === "security" && !state.adminsData) loadAdmins();
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
  document.getElementById("refresh")?.addEventListener("click", loadDashboard); document.getElementById("check")?.addEventListener("click", () => checkUpdates()); document.getElementById("export")?.addEventListener("click", exportSummary);
  document.getElementById("refresh-logs")?.addEventListener("click", () => loadDiagnosticLogs(true)); document.getElementById("clear-logs")?.addEventListener("click", () => clearDiagnosticLogs()); document.getElementById("log-auto")?.addEventListener("change", () => toggleLogAuto()); document.getElementById("log-pause")?.addEventListener("click", toggleLogPause); document.getElementById("log-autoscroll")?.addEventListener("click", toggleLogAutoScroll); document.getElementById("log-export")?.addEventListener("click", exportDiagnosticLogs); document.getElementById("log-level")?.addEventListener("change", event => { state.logThreshold = event.target.value || ""; dashboard(); }); document.getElementById("log-range")?.addEventListener("change", event => { state.logRange = event.target.value || "all"; dashboard(); }); document.getElementById("settings-reload")?.addEventListener("click", () => loadSettings());
  document.getElementById("route-reset-all")?.addEventListener("click", resetAllRoutes);
  document.getElementById("route-export")?.addEventListener("click", exportRoutes); document.getElementById("save-settings")?.addEventListener("click", () => saveSettings()); document.getElementById("refresh-control")?.addEventListener("click", () => loadControl({ force: true })); document.getElementById("toggle-control")?.addEventListener("click", toggleControl); document.getElementById("security-logout")?.addEventListener("click", logout);
  document.getElementById("rules-reload")?.addEventListener("click", () => loadRules()); document.getElementById("save-rule")?.addEventListener("click", () => saveRule()); document.getElementById("mirrors-reload")?.addEventListener("click", () => loadMirrors()); document.getElementById("save-mirror")?.addEventListener("click", () => saveMirror()); document.getElementById("benchmark-mirrors")?.addEventListener("click", () => benchmarkMirrors()); document.getElementById("check-recommendations")?.addEventListener("click", () => checkRecommendations()); document.getElementById("apply-recommendations")?.addEventListener("click", () => applyAllRecommendations()); document.getElementById("admins-reload")?.addEventListener("click", () => loadAdmins()); document.getElementById("admin-create")?.addEventListener("click", () => createAdmin()); document.querySelectorAll("[data-admin-update]").forEach(node => node.addEventListener("click", () => updateAdmin(node.dataset.adminUpdate)));
  document.querySelectorAll("[data-log-module]").forEach(node => node.addEventListener("click", () => { const id = node.dataset.logModule; state.logModules = state.logModules.includes(id) ? state.logModules.filter(item => item !== id) : [...state.logModules, id]; dashboard(); })); document.querySelectorAll("[data-log-toggle]").forEach(node => node.addEventListener("click", () => { const key = node.dataset.logToggle; if (state.logExpanded.has(key)) state.logExpanded.delete(key); else state.logExpanded.add(key); dashboard(); })); document.querySelectorAll("[data-log-problem]").forEach(node => node.addEventListener("click", () => { state.logModules = [node.dataset.logProblem]; state.logThreshold = node.querySelector(".managed") ? "ERROR" : "WARNING"; state.logQuery = node.dataset.logCode || ""; dashboard(); })); const logSearch = document.getElementById("log-search"); logSearch?.addEventListener("input", () => { state.logQuery = logSearch.value; dashboard(); requestAnimationFrame(() => { const next = document.getElementById("log-search"); next?.focus(); next?.setSelectionRange(state.logQuery.length, state.logQuery.length); }); });
  const bindRouteModels = () => document.querySelectorAll("[data-route-model]").forEach(node => node.addEventListener("change", () => { if (node.value !== "__custom__") return; const input = document.createElement("input"); input.className = "route-model"; input.dataset.routeModel = node.dataset.routeModel; input.type = "text"; input.placeholder = "模型名（可自定义）"; input.disabled = node.disabled; node.replaceWith(input); input.focus(); }));
  document.querySelectorAll("[data-route-provider]").forEach(node => node.addEventListener("change", () => { const kind = node.dataset.routeProvider; const model = document.querySelector(`[data-route-model="${CSS.escape(kind)}"]`); const next = modelSelect(kind, node.value, "", !(model?.disabled)); if (model) { const wrapper = model.parentElement; wrapper.innerHTML = next; bindRouteModels(); } }));
  bindRouteModels();
  document.getElementById("check-updates")?.addEventListener("click", () => checkUpdates()); document.getElementById("reload-transactions")?.addEventListener("click", () => loadTransactions()); document.querySelectorAll("[data-rollback]").forEach(node => node.addEventListener("click", () => rollbackUpdate(node.dataset.rollback)));
  document.getElementById("mobile-more")?.addEventListener("click", () => { const sheet = document.getElementById("mobile-more-sheet"); sheet.hidden = !sheet.hidden; document.getElementById("mobile-more")?.setAttribute("aria-expanded", String(!sheet.hidden)); });
  document.querySelectorAll("#mobile-more-sheet [data-view], #mobile-more-sheet #mobile-logout").forEach(node => node.addEventListener("click", () => { const sheet = document.getElementById("mobile-more-sheet"); if (sheet) sheet.hidden = true; document.getElementById("mobile-more")?.setAttribute("aria-expanded", "false"); }));
  document.querySelectorAll("[data-view]").forEach(node => node.addEventListener("click", () => { state.selectedModule = node.dataset.module || ""; enterView(node.dataset.view || "modules"); }));
  document.querySelectorAll("[data-diagnostic]").forEach(node => node.addEventListener("click", async () => { state.logModules = [node.dataset.diagnostic]; await loadDiagnostics(); })); document.querySelectorAll("[data-module]").forEach(node => node.addEventListener("click", () => { state.view = "modules"; state.selectedModule = node.dataset.module || ""; dashboard(); })); document.getElementById("close-module-detail")?.addEventListener("click", () => { state.selectedModule = ""; dashboard(); });
  document.querySelectorAll("[data-filter]").forEach(node => node.addEventListener("click", () => { state.filter = node.dataset.filter; dashboard(); })); const query = document.getElementById("query"); query?.addEventListener("input", () => { state.query = query.value; dashboard(); requestAnimationFrame(() => { const next = document.getElementById("query"); next?.focus(); next?.setSelectionRange(state.query.length, state.query.length); }); });
  document.querySelectorAll("[data-cap-tab]").forEach(node => node.addEventListener("click", async () => {
    const [pluginId, tab] = String(node.dataset.capTab || "").split("|");
    if (!pluginId || !tab) return;
    setCapTab(pluginId, tab);
    if (tab === "panels" && !capPanelStore(pluginId).list) { dashboard(); await loadCapPanels(pluginId); return; }
    dashboard();
  }));
  document.querySelectorAll("[data-control-apply]").forEach(node => node.addEventListener("click", () => applyControlPatch(node.dataset.controlApply, node.closest("[data-capability-provider]") || document)));
  document.querySelectorAll("[data-control-reset]").forEach(node => node.addEventListener("click", () => resetControlFields(node.dataset.controlReset)));
  document.querySelectorAll("[data-control-refresh]").forEach(node => node.addEventListener("click", () => refreshControlFields(node.dataset.controlRefresh)));
  document.querySelectorAll("[data-catalog-domain-open]").forEach(node => node.addEventListener("click", async () => { state.selectedDomain = node.dataset.catalogDomainOpen; state.selectedCapability = ""; dashboard(); await ensureCapabilitySwitchData(); }));
  document.querySelectorAll("[data-cap-switch-field]").forEach(node => node.addEventListener("change", () => applyCapabilitySwitch(node)));
  document.querySelectorAll("[data-capability-open]").forEach(node => node.addEventListener("click", () => loadCapability(node.dataset.capabilityOpen)));
  document.querySelectorAll("[data-capability-back]").forEach(node => node.addEventListener("click", () => { state.selectedCapability = ""; state.capabilityData = {}; dashboard(); }));
  document.querySelectorAll("[data-cap-panels-load]").forEach(node => node.addEventListener("click", () => loadCapPanels(node.dataset.capPanelsLoad)));
  document.querySelectorAll("[data-panel-select]").forEach(node => node.addEventListener("click", () => loadCapPanelData(node.dataset.panelPlugin, node.dataset.panelSelect)));
  document.querySelectorAll("[data-panel-action]").forEach(node => node.addEventListener("click", () => runPanelAction(node.dataset.panelPlugin, node.dataset.panelAction)));
  document.querySelectorAll("[data-panel-stream-start]").forEach(node => node.addEventListener("click", () => streamPanel(node.dataset.panelStreamStart, capPanelStore(node.dataset.panelStreamStart).selected)));
  document.querySelectorAll("[data-lifecycle]").forEach(node => node.addEventListener("click", () => runLifecycle(node.dataset.lifecycle, node.dataset.lifecyclePlugin)));
  document.querySelectorAll("[data-control-open]").forEach(node => node.addEventListener("click", () => openModuleInControl(node.dataset.controlOpen)));
  document.querySelectorAll("[data-native-read]").forEach(node => node.addEventListener("click", () => importNativeConfig(node.dataset.nativeRead)));
  document.querySelectorAll("[data-native-freeze]").forEach(node => node.addEventListener("click", () => freezeNativeConfig(node.dataset.nativeFreeze)));
  document.getElementById("freeze-all")?.addEventListener("click", freezeAllNative);
  document.querySelectorAll("[data-install]").forEach(node => node.addEventListener("click", () => installModule(node.dataset.install)));
}
async function loadDiagnostics() { try { const result = await post("diagnostics", {}); state.providers = result.providers || []; state.view = "diagnostics"; dashboard(); await loadDiagnosticLogs(true); } catch (error) { notify(error.message, true); } }
function logCursors() {
  return window.SeriesKernel.deriveCursors(state.logMembers || []);
}
// 诊断协议细节统一走 series-kernel.js（核 Page 与 WebUI 共用一份）。
function logMemberHasMore(member) {
  return window.SeriesKernel.memberHasMore(member);
}
function applyDiagnosticPage(result, wasReset) {
  const members = result.members || [];
  state.logMembers = members;
  if (result.link_health) state.linkHealth = result.link_health;
  window.SeriesKernel.pruneForMembers(state.logs, {}, {}, members);
  const merge = window.SeriesKernel.mergeLogEvents(state.logs, result.events, { cap: 3000 });
  const fresh = merge.fresh;
  state.logNewKeys = new Set(fresh.map(item => `${item.plugin_id}:${item.seq}`));
  if (fresh.length) state.logPendingScroll = true;
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
  window.SeriesUI.downloadJson(`series-diagnostics-${new Date().toISOString().replace(/[:.]/g, "-")}.json`, payload);
  notify(events.length ? "诊断事件已导出" : "暂无可导出事件", !events.length);
}
async function checkUpdates() {
  try { notify("正在检查更新…"); state.updatesCheck = await post("updates/check", {}); notify("检查完成"); await loadDashboard(); } catch (error) { notify(error.message, true); }
}
async function loadTransactions() {
  try { state.transactions = (await get("updates/transactions")).transactions || []; if (state.view === "updates") dashboard(); } catch (error) { notify(error.message, true); }
}
async function rollbackUpdate(txId) {
  if (!(await confirmDialog("确定回滚该次更新？插件将恢复到更新前版本并热重载。"))) return;
  try { const result = await post("updates/rollback", { tx_id: txId }); notify(`已回滚 ${result.plugin_id || ""} → v${result.from_version || "?"}`); await loadDashboard(); } catch (error) { notify(error.message, true); }
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
  try { state.recommendationsData = await post("recommendations/check", {}); notify("最新版本检查完成"); dashboard(); } catch (error) { notify(error.message, true); }
}
async function applyAllRecommendations() {
  if (!(await confirmDialog("确定安装未安装模块并更新所有确有新版本的模块？核自身不会更新。"))) return;
  try { const result = await post("recommendations/apply-all", { confirm: true }); notify(`批量完成：成功 ${result.succeeded} / 失败 ${result.failed}`); await loadDashboard(); } catch (error) { notify(error.message, true); }
}
async function loadAdmins() {
  try { state.adminsData = await get("admins"); } catch (error) { notify(error.message, true); }
  if (state.view === "security" || (state.view === "settings" && state.settingsTab === "security")) dashboard();
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
async function resetAllRoutes() {
  if (!(await confirmDialog("把所有职责恢复为「跟随 AstrBot 原生」？插件自己的显式配置不受影响。"))) return;
  document.querySelectorAll("[data-route-provider]").forEach(node => { node.value = ""; });
  document.querySelectorAll("[data-route-model]").forEach(node => { node.value = ""; });
  document.querySelectorAll("[data-setting-route]").forEach(node => { node.value = ""; });
  await saveSettings();
}
function exportRoutes() {
  const payload = { generated_at: new Date().toISOString(), model_routing: state.settingsData?.settings?.model_routing || {}, resolved: state.routes?.routes || {} };
  window.SeriesUI.downloadJson("series-model-routing.json", payload);
  notify("已导出当前路由");
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
  try { const result = await post("settings", payload); notify("设置已保存并生效（连接项重启后生效）"); await loadDashboard(); } catch (error) { notify(error.message, true); }
}
async function loadControl(options = {}) {
  try {
    state.control = await get("series/control");
    state.view = "control";
    dashboard();
    await ensureCapabilitySwitchData({ force: Boolean(options.force) });
  } catch (error) { notify(error.message, true); }
}
async function ensureCapabilitySwitchData(options = {}) {
  const force = Boolean(options.force);
  const domains = controlCatalog().domains || [];
  if (!domains.length) return;
  const active = domains.find(item => item.id === state.selectedDomain) || domains[0];
  const ids = [...new Set(capabilitiesOfDomain(active.id).flatMap(capability => (capability.providers || []).filter(provider => provider.switch_field).map(provider => provider.plugin_id)))].filter(Boolean);
  state.controlSwitches = state.controlSwitches || {};
  const pending = ids.filter(id => force || !state.controlSwitches[id]);
  if (!pending.length) return;
  await Promise.all(pending.map(async id => {
    try {
      const [schema, snapshot] = await Promise.all([
        get(`series/${encodeURIComponent(id)}/control/schema`),
        get(`series/${encodeURIComponent(id)}/control/snapshot`)
      ]);
      state.controlSwitches[id] = { schema, snapshot };
    } catch (error) {
      state.controlSwitches[id] = { error: error.message };
    }
  }));
  if (state.view === "control") dashboard();
}
async function revertCapabilitySwitch(pluginId, field, value) {
  const data = (state.controlSwitches || {})[pluginId];
  if (!data?.schema) { notify("撤销失败：配置已刷新，请重新操作", true); return; }
  try {
    const patch = { [field]: Boolean(value) };
    await post(`series/${encodeURIComponent(pluginId)}/control/validate`, { patch, expected_revision: data.schema.revision });
    await post(`series/${encodeURIComponent(pluginId)}/control/apply`, { patch, expected_revision: data.schema.revision });
    notify(Boolean(value) ? "已恢复开启" : "已恢复关闭");
    await refreshCapabilitySwitchData(pluginId);
    await loadControl();
  } catch (error) {
    notify(`撤销失败：${error.message}`, true);
    await refreshCapabilitySwitchData(pluginId);
  }
}
async function refreshCapabilitySwitchData(pluginId) {
  if (!pluginId) return;
  try {
    const [schema, snapshot] = await Promise.all([
      get(`series/${encodeURIComponent(pluginId)}/control/schema`),
      get(`series/${encodeURIComponent(pluginId)}/control/snapshot`)
    ]);
    state.controlSwitches = state.controlSwitches || {};
    state.controlSwitches[pluginId] = { schema, snapshot };
  } catch (error) {
    state.controlSwitches = state.controlSwitches || {};
    state.controlSwitches[pluginId] = { error: error.message };
  }
  if (state.view === "control") dashboard();
}
async function applyCapabilitySwitch(input) {
  const pluginId = input.dataset.capSwitchPlugin || "";
  const field = input.dataset.capSwitchField || "";
  const data = (state.controlSwitches || {})[pluginId];
  if (!pluginId || !field || !data?.schema) { if (state.view === "control") dashboard(); return; }
  const next = input.checked;
  const row = input.closest(".cap-switch");
  input.disabled = true;
  row?.classList.add("busy");
  try {
    const patch = { [field]: next };
    await post(`series/${encodeURIComponent(pluginId)}/control/validate`, { patch, expected_revision: data.schema.revision });
    await post(`series/${encodeURIComponent(pluginId)}/control/apply`, { patch, expected_revision: data.schema.revision });
    notify(next ? "开关已开启" : "开关已关闭", false, {
      label: "撤销",
      onClick: () => revertCapabilitySwitch(pluginId, field, !next),
    });
    await refreshCapabilitySwitchData(pluginId);
    await loadControl();
  } catch (error) {
    input.checked = !next;
    notify(error.message, true);
    await refreshCapabilitySwitchData(pluginId);
  } finally {
    row?.classList.remove("busy");
  }
}
async function importNativeConfig(pluginId) {
  try {
    const native = await get(`series/${encodeURIComponent(pluginId)}/control/native`);
    if (!native?.supported) { notify(native?.note || "该模块暂不支持读取原生配置（需要升级插件）", true); return; }
    const diff = Object.entries(native.fields || {}).filter(([, value]) => !value.secret && value.native_value !== value.effective_value);
    if (!diff.length) { notify("核接管值与插件现状一致，无需导入"); return; }
    const preview = diff.slice(0, 8).map(([key, value]) => `· ${key}：插件 ${JSON.stringify(value.native_value)} → 核 ${JSON.stringify(value.effective_value)}`).join("\n");
    if (!(await confirmDialog(`把插件当前配置导入核接管层？共 ${diff.length} 项：\n${preview}${diff.length > 8 ? "\n…" : ""}`))) return;
    const result = await post(`series/${encodeURIComponent(pluginId)}/control/import-native`, {});
    notify(result.status === "noop" ? "已是最新，无需导入" : `已导入 ${result.imported?.length || 0} 项`);
    await loadControl();
  } catch (error) { notify(error.message, true); }
}
async function freezeNativeConfig(pluginId) {
  if (!(await confirmDialog("把当前生效配置写入插件自身的配置文件？\n\n固化后：核掉线/关闭统一接管都不影响功能；会先自动备份插件配置，并清空该项的核覆盖层。"))) return;
  try {
    const result = await post(`series/${encodeURIComponent(pluginId)}/control/freeze`, { reset_overlay: true });
    if (result.status === "noop") { notify(result.message || "无需固化（原生配置已是最新）"); return; }
    notify(`已固化 ${result.written?.length || 0} 项${result.backup_id ? ` · 备份 ${result.backup_id}` : ""}`);
    await loadControl();
  } catch (error) { notify(error.message, true); }
}
async function freezeAllNative() {
  if (!(await confirmDialog("把当前生效配置写入所有模块的自身配置文件？\n\n每个模块会先自动备份；固化后核掉线也不影响功能。"))) return;
  try {
    const result = await post("series/control/freeze-all", { reset_overlay: true });
    notify(`已固化 ${result.frozen || 0}/${result.total || 0} 个模块`);
    await loadControl();
  } catch (error) { notify(error.message, true); }
}
async function openModuleInControl(pluginId) {
  const capability = catalogCapabilities().find(cap => (cap.providers || []).some(provider => provider.plugin_id === pluginId));
  if (!capability) { notify("该模块没有可接管字段，请使用它的独立 Page", true); return; }
  state.selectedDomain = capability.domain;
  state.selectedCapability = capability.id;
  state.capTabs = state.capTabs || {};
  state.capTabs[pluginId] = "all";
  await loadCapability(capability.id);
}
async function loadCapPanels(pluginId) {
  const store = capPanelStore(pluginId);
  try {
    store.list = await get(`series/${encodeURIComponent(pluginId)}/panels`);
    store.disabled = false;
  } catch (error) {
    store.list = null;
    store.disabled = String(error.message).includes("TAKEOVER_DISABLED");
    notify(error.message, true);
  }
  dashboard();
  const first = (store.list?.panels || [])[0];
  if (first) await loadCapPanelData(pluginId, first.id);
}
async function loadCapPanelData(pluginId, panelId) {
  if (!pluginId || !panelId) return;
  const store = capPanelStore(pluginId);
  try {
    store.selected = panelId;
    store.data = await get(`series/${encodeURIComponent(pluginId)}/panels/${encodeURIComponent(panelId)}`);
    dashboard();
  } catch (error) { notify(error.message, true); }
}
function controlFieldInputs(root) { return [...(root || document).querySelectorAll("[data-control-field]")]; }
function collectControlPatch(schema, snapshot, root) {
  const fields = schema?.schema?.fields || {};
  const values = snapshot?.snapshot?.fields || {};
  const patch = {};
  controlFieldInputs(root).forEach(node => {
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
async function applyControlPatch(pluginId, root) {
  const id = pluginId || "";
  if (!id) return;
  const fromCapability = (state.capabilityData || {})[id];
  const schema = fromCapability?.schema;
  const snapshot = fromCapability?.snapshot;
  if (!schema) return;
  const patch = collectControlPatch(schema, snapshot, root);
  if (!Object.keys(patch).length) { notify("没有修改需要应用"); return; }
  try {
    const revision = schema.revision;
    await post(`series/${encodeURIComponent(id)}/control/validate`, { patch, expected_revision: revision });
    await post(`series/${encodeURIComponent(id)}/control/apply`, { patch, expected_revision: revision });
    notify("覆盖已应用");
    await refreshControlFields(id);
    await loadControl();
  } catch (error) {
    notify(error.message, true);
    if (String(error.message).includes("REVISION")) await refreshControlFields(id);
  }
}
async function resetControlFields(pluginId) {
  const id = pluginId || "";
  if (!id) return;
  if (!(await confirmDialog("重置该模块的全部核覆盖字段？插件自身配置将立即恢复生效。"))) return;
  try {
    await post(`series/${encodeURIComponent(id)}/control/reset`, { fields: null });
    notify("已恢复插件自身配置");
    await refreshControlFields(id);
    await loadControl();
  } catch (error) { notify(error.message, true); }
}
async function refreshControlFields(pluginId) {
  const id = pluginId || "";
  if (!id) return;
  try {
    const [schema, snapshot] = await Promise.all([
      get(`series/${encodeURIComponent(id)}/control/schema`),
      get(`series/${encodeURIComponent(id)}/control/snapshot`)
    ]);
    state.capabilityData[id] = { schema, snapshot };
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
async function runPanelAction(pluginId, actionId) {
  const store = capPanelStore(pluginId);
  const panelId = store.selected;
  const action = (store.data?.actions || []).find(item => item.id === actionId);
  if (!pluginId || !panelId || !action) return;
  const scope = document.querySelector(`[data-cap-panels="${CSS.escape(pluginId)}"]`) || document;
  const payload = {};
  let missing = false;
  const fileUploads = [];
  (action.payload_fields || []).forEach(field => {
    if (field.type === "file") {
      const fileNode = scope.querySelector(`[data-panel-file="${CSS.escape(field.name)}"]`);
      const files = [...(fileNode?.files || [])];
      if (field.required && !files.length) missing = true;
      files.forEach(file => fileUploads.push([field.name, file, field.multiple === true]));
      return;
    }
    const node = scope.querySelector(`[data-panel-field="${CSS.escape(field.name)}"]`);
    if (field.type === "bool" || field.type === "boolean") { payload[field.name] = !!node?.checked; return; }
    const value = node ? node.value : "";
    if (field.required && !value) missing = true;
    if (field.type === "number") payload[field.name] = value === "" ? null : Number(value);
    else if (value !== "" || field.secret !== true) payload[field.name] = value;
  });
  if (missing) { notify("请填写动作所需的必填字段", true); return; }
  try {
    for (const [name, file] of fileUploads) {
      const artifactId = await uploadArtifact(file, pluginId, panelId);
      payload[name] = Array.isArray(payload[name]) ? [...payload[name], artifactId] : artifactId;
    }
  } catch (error) { notify(error.message, true); return; }
  if (action.confirm && !(await confirmDialog(action.confirm))) return;
  const headers = { "X-Request-Id": (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`) };
  if (action.revision_required && store.data?.revision != null) headers["X-Expected-Revision"] = String(store.data.revision);
  try {
    const result = await post(`series/${encodeURIComponent(pluginId)}/panels/${encodeURIComponent(panelId)}/actions/${encodeURIComponent(actionId)}`, payload, headers);
    notify(result.message || "操作完成");
    if (result.job_id) { pollJob(result.job_id, pluginId, panelId); return; }
    if ((Array.isArray(result.artifacts) && result.artifacts.length) || result.audio?.artifact_id) {
      store.data = {
        ...(store.data || {}),
        artifacts: [...(store.data?.artifacts || []), ...(result.artifacts || [])],
        audio: result.audio || store.data?.audio || null,
      };
      dashboard();
      return;
    }
    await loadCapPanelData(pluginId, panelId);
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
  const output = document.querySelector(`[data-panel-stream="${CSS.escape(pluginId)}"]`);
  if (!pluginId || !panelId) return;
  if (state.panelStream) { state.panelStream.close(); state.panelStream = null; }
  const url = `/api/series/${encodeURIComponent(pluginId)}/panels/${encodeURIComponent(panelId)}/stream`;
  const source = new EventSource(url, { withCredentials: true });
  state.panelStream = source;
  source.onmessage = event => { if (output) output.textContent += `${event.data}\n`; };
  source.addEventListener("done", () => { source.close(); state.panelStream = null; });
  source.addEventListener("error", () => { source.close(); state.panelStream = null; if (output) output.textContent += "[stream closed]\n"; });
}
async function pollJob(jobId, pluginId, panelId) {
  for (let attempt = 0; attempt < 300; attempt += 1) {
    await new Promise(resolve => setTimeout(resolve, 1000));
    try {
      const job = await get(`jobs/${encodeURIComponent(jobId)}`);
      const progress = Math.round((job.progress || 0) * 100);
      if (job.message) notify(`${job.message} ${progress}%`);
      if (job.status === "done") { await loadCapPanelData(pluginId, panelId); return; }
      if (job.status === "failed") { notify(job.error || "任务失败", true); return; }
      if (job.status === "cancelled") return;
    } catch (error) { notify(error.message, true); return; }
  }
  notify("任务轮询超时，请稍后刷新面板", true);
}
async function runLifecycle(action, pluginId) {
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
    if (state.selectedCapability) await loadCapability(state.selectedCapability);
  } catch (error) { notify(error.message, true); }
}
async function toggleControl() { try { const next = state.control?.mode === "managed" ? "native" : "managed"; await post("series/control/mode", { mode: next }); await loadControl(); notify(next === "managed" ? "统一接管已启用" : "已恢复插件自身配置"); } catch (error) { notify(error.message, true); } }
function exportSummary() { const payload = { generated_at: new Date().toISOString(), modules: state.modules.map(item => ({ plugin_id: item.plugin_id, version: item.version, status: item.status, contracts: item.contracts })) }; window.SeriesUI.downloadJson("series-control-summary.json", payload); notify("已生成脱敏诊断摘要"); }
async function loadDashboard() { try { const session = await get("session"); state.configured = !!session.configured; if (!session.authenticated) { state.authenticated = false; loginView(); return; } state.authenticated = true; state.session = session.session; const modules = await get("modules"); state.modules = modules.modules || []; await enterView(state.view); } catch (error) { loginView(error.message); } }
async function logout() { try { await post("logout", {}); } finally { state.authenticated = false; state.session = null; loginView(); } }
async function start() { try { await loadDashboard(); } catch (error) { loginView(error.message); } }
start();
