"""系列能力目录：功能域 → 能力 → 提供者（能力优先的统一接管信息架构）。

设计要点（见 docs/SERIES-CAPABILITY-PLAN-2026-09-14.md）：
- 用户界面按「功能域 → 能力」组织，不再按插件分类；插件身份只出现在排障视图。
- 一个能力可以由多个插件共同提供（多对多），状态按提供者聚合并。
- providers.fields 只引用各插件 series.control 真实暴露的字段；更多设置在
  providers.hint 指向插件页设置中心。
- providers.switch_field 指定该能力的“主开关”字段（必须是 fields 里的布尔项），
  核 WebUI 会把它直接渲染成能力卡片上的滑块开关，点开详情再调其余字段。
- 治理域（核自身）用 views 指向核 WebUI 既有视图。
- 目录是 P0-1 的策展映射；P2 会改为插件在契约里声明 capabilities[]，
  本目录降级为兼容兜底。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping

CATALOG_VERSION = "1.0"

# ---------------------------------------------------------------- 功能域

DOMAINS: tuple[dict[str, Any], ...] = (
    {
        "id": "message",
        "title": "对话与消息",
        "description": "她怎么听、怎么想、怎么接话：沉默、分段、插话、上下文与群聊语境。",
        "icon": "💬",
        "order": 10,
    },
    {
        "id": "memory",
        "title": "记忆与知识",
        "description": "记住什么、学到什么、怎么取用：记忆库、学习验证、检索与导入导出。",
        "icon": "🧠",
        "order": 20,
    },
    {
        "id": "identity",
        "title": "关系与身份",
        "description": "她认得出谁、边界在哪：身份授权、入群审核、关系档案与账号归属。",
        "icon": "🪪",
        "order": 30,
    },
    {
        "id": "environment",
        "title": "环境与感知",
        "description": "她感知到的世界：时间、天气、空气质量、日历、预警与主动关心。",
        "icon": "🌤️",
        "order": 40,
    },
    {
        "id": "voice",
        "title": "语音与表达",
        "description": "她怎么说话：语音后端、音色、情绪路由、说话节奏与音频交付。",
        "icon": "🔊",
        "order": 50,
    },
    {
        "id": "device",
        "title": "设备与联动",
        "description": "她连着什么：设备配对、平台实例、会话桥接与桥接诊断。",
        "icon": "🔌",
        "order": 60,
    },
    {
        "id": "governance",
        "title": "治理与更新",
        "description": "系列的运行底座：更新回滚、推荐、规则、镜像、全局设置与账号安全。",
        "icon": "🧩",
        "order": 70,
    },
)

_CF = "astrbot_plugin_conversation_flow"
_AL = "astrbot_plugin_active_learner"
_ID = "astrbot_plugin_identity_guardian"
_RL = "astrbot_plugin_relationship"
_EA = "astrbot_plugin_environment_awareness"
_VH = "astrbot_plugin_voice_hub"
_EB = "astrbot_plugin_embodiment_bridge"

# ---------------------------------------------------------------- 能力

CAPABILITIES: tuple[dict[str, Any], ...] = (
    # ---- 对话与消息 ----
    {
        "id": "silence",
        "domain": "message",
        "title": "沉默判断",
        "description": "判断这条消息要不要回、什么时候不回。",
        "providers": [
            {
                "plugin_id": _CF,
                "fields": ["silence_enabled", "silence_strategy"],
                "switch_field": "silence_enabled",
                "switch_label": "沉默判断",
                "hint": "沉默标记、预判模型等细节在「言 → 设置中心 → 沉默判断」。",
            }
        ],
    },
    {
        "id": "chunking",
        "domain": "message",
        "title": "智能分段",
        "description": "把长回复按语义拆成多条发送，避免一次性刷屏。",
        "providers": [
            {
                "plugin_id": _CF,
                "fields": ["chunking_enabled", "chunking_min_length", "chunking_max_segments"],
                "switch_field": "chunking_enabled",
                "switch_label": "智能分段",
                "hint": "段落策略与「分段延迟」（打字节奏）在「言 → 设置中心 → 智能分段 / 分段延迟」。",
            }
        ],
    },
    {
        "id": "interrupt",
        "domain": "message",
        "title": "插话合并",
        "description": "她在思考时你补充的消息并进同一轮；她已开口时接着回应不重复。",
        "providers": [
            {
                "plugin_id": _CF,
                "fields": ["interrupt_enabled", "interrupt_mode", "interrupt_scope", "interrupt_merge_strategy"],
                "switch_field": "interrupt_enabled",
                "switch_label": "插话中断",
                "hint": "steering 窗口等高级项在「言 → 设置中心 → 插话中断」。",
            }
        ],
    },
    {
        "id": "context_bridge",
        "domain": "message",
        "title": "上下文承接",
        "description": "私聊/动态/跨会话承接上一条话题，让回复不断线。",
        "providers": [
            {
                "plugin_id": _CF,
                "fields": [
                    "private_context_bridge_enabled",
                    "private_context_bridge_max_turns",
                    "private_context_bridge_short_max_chars",
                    "dynamic_context_enabled",
                    "dynamic_context_max_turns",
                    "dynamic_context_max_chars",
                    "recent_activity_context_enabled",
                    "recent_activity_retention_minutes",
                ],
                "switch_field": "private_context_bridge_enabled",
                "switch_label": "私聊上下文承接",
            }
        ],
    },
    {
        "id": "group_context",
        "domain": "message",
        "title": "群聊语境与读空气",
        "description": "群聊上下文、被唤醒才参与、以及不刷屏的读空气护栏。",
        "providers": [
            {
                "plugin_id": _CF,
                "fields": [
                    "group_context_enabled",
                    "group_context_max_messages",
                    "group_context_only_when_woken",
                    "group_air_guard_enabled",
                    "group_air_guard_window_seconds",
                    "group_air_guard_max_bot_replies",
                    "group_air_guard_polite_loop_limit",
                ],
                "switch_field": "group_context_enabled",
                "switch_label": "群聊语境",
            }
        ],
    },
    {
        "id": "conversation_style",
        "domain": "message",
        "title": "回复风格与收尾",
        "description": "纯文本、场景感知与不追问的服务式收尾控制。",
        "providers": [
            {
                "plugin_id": _CF,
                "fields": [
                    "plain_text_mode",
                    "followup_guard_enabled",
                    "followup_streak_limit",
                    "followup_window_seconds",
                    "scene_awareness_enabled",
                ],
                "switch_field": "followup_guard_enabled",
                "switch_label": "追问护栏",
            }
        ],
    },
    {
        "id": "image_intent",
        "domain": "message",
        "title": "图片意图",
        "description": "看到图片时决定是否先看懂再回复。",
        "providers": [{"plugin_id": _CF, "fields": ["image_intent_mode"]}],
    },
    {
        "id": "context_budget",
        "domain": "message",
        "title": "上下文预算",
        "description": "上下文接近上限时提醒或硬裁剪，防止越聊越贵。",
        "providers": [
            {
                "plugin_id": _CF,
                "fields": [
                    "context_budget_enforce",
                    "context_budget_soft_limit",
                    "context_budget_hard_limit",
                ],
                "switch_field": "context_budget_enforce",
                "switch_label": "预算强制",
            }
        ],
    },
    {
        "id": "mood",
        "domain": "message",
        "title": "拟人化情绪",
        "description": "回复意愿会随互动变化：偶尔懒散、烦躁或不想回。",
        "providers": [
            {
                "plugin_id": _CF,
                "fields": [
                    "mood_enabled",
                    "mood_private_enabled",
                    "mood_window_seconds",
                    "mood_frequent_after",
                    "mood_streak_after",
                    "mood_streak_gap_seconds",
                    "mood_lazy_score",
                    "mood_annoyed_score",
                    "mood_silence_score",
                    "mood_silence_chance_percent",
                    "mood_max_consecutive_silences",
                ],
                "switch_field": "mood_enabled",
                "switch_label": "情绪波动",
            },
            {"plugin_id": _RL, "fields": ["mood_enabled"], "hint": "关系侧情绪联动。"},
        ],
    },
    {
        "id": "memory_injection",
        "domain": "message",
        "title": "记忆注入",
        "description": "把检索到的记忆按预算注入当前回复。",
        "providers": [
            {
                "plugin_id": _AL,
                "fields": ["context_inject_count", "search_top_k"],
                "hint": "检索范围、权重等更多设置在「知 → 设置中心」。",
            }
        ],
    },
    # ---- 记忆与知识 ----
    {
        "id": "memory_store",
        "domain": "memory",
        "title": "记忆库与生命周期",
        "description": "记忆的增删改查、置信度与失效策略。",
        "providers": [
            {
                "plugin_id": _AL,
                "fields": [],
                "hint": "在「知 → 设置中心」或知的管理页维护记忆条目。",
            }
        ],
    },
    {
        "id": "learning",
        "domain": "memory",
        "title": "学习与交叉验证",
        "description": "主动学习、搜索学习与交叉验证。",
        "providers": [{"plugin_id": _AL, "fields": [], "hint": "在「知 → 设置中心 → 学习」配置。"}],
    },
    {
        "id": "retrieval",
        "domain": "memory",
        "title": "检索与向量",
        "description": "向量化开关与检索策略。",
        "providers": [
            {
                "plugin_id": _AL,
                "fields": ["embedding_enabled"],
                "switch_field": "embedding_enabled",
                "switch_label": "向量检索",
                "hint": "嵌入模型与检索权重在「知 → 设置中心 → 搜索」。",
            }
        ],
    },
    {
        "id": "knowledge_io",
        "domain": "memory",
        "title": "导入导出与知识库",
        "description": "文本/Markdown/PDF/Word/ZIP 导入、导出 JSON、内置知识库导入。",
        "providers": [
            {"plugin_id": _AL, "fields": [], "hint": "在「知」的管理页执行导入/导出。"}
        ],
    },
    {
        "id": "slang",
        "domain": "memory",
        "title": "群黑话",
        "description": "群黑话候选审核、晋升全局与拉黑。",
        "providers": [{"plugin_id": _AL, "fields": [], "hint": "在「知 → 黑话」管理。"}],
    },
    {
        "id": "relationship_memory",
        "domain": "memory",
        "title": "关系记忆",
        "description": "跨平台关系记忆的开关与读取预算。",
        "providers": [
            {
                "plugin_id": _RL,
                "fields": [
                    "cross_platform_memory_enabled",
                    "cross_platform_memory_top_k",
                    "cross_platform_memory_max_chars",
                ],
                "switch_field": "cross_platform_memory_enabled",
                "switch_label": "跨平台记忆",
            }
        ],
    },
    {
        "id": "env_facts",
        "domain": "memory",
        "title": "环境事实缓存",
        "description": "后台刷新的环境候选事实，用于主动关心。",
        "providers": [
            {
                "plugin_id": _EA,
                "fields": ["opportunity_cache_enabled", "opportunity_refresh_seconds"],
                "switch_field": "opportunity_cache_enabled",
                "switch_label": "事实缓存",
            }
        ],
    },
    # ---- 关系与身份 ----
    {
        "id": "relationship_profile",
        "domain": "identity",
        "title": "关系档案与信任",
        "description": "好感度、四维信任、熟悉度与关系性质。",
        "providers": [
            {"plugin_id": _RL, "fields": [], "hint": "在「情 → 关系明细 / 设置中心」维护。"}
        ],
    },
    {
        "id": "account_binding",
        "domain": "identity",
        "title": "账号归属",
        "description": "把不同平台的账号归到同一个自然人。",
        "providers": [
            {"plugin_id": _RL, "fields": [], "hint": "在「情 → 账号归属」维护。"}
        ],
    },
    {
        "id": "boundary",
        "domain": "identity",
        "title": "白名单与边界",
        "description": "谁能触发她、能触发到什么程度。",
        "providers": [
            {"plugin_id": _RL, "fields": [], "hint": "在「情」的白名单/边界中维护。"},
            {"plugin_id": _ID, "fields": ["enabled"], "hint": "身份守卫总开关。"},
        ],
    },
    {
        "id": "identity_auth",
        "domain": "identity",
        "title": "身份识别与授权",
        "description": "owner/管理员识别、私聊授权与行动许可。",
        "providers": [
            {"plugin_id": _ID, "fields": ["enabled"],
            "switch_field": "enabled",
                "switch_label": "身份守卫", "hint": "owner/管理员名单在「序 → 设置中心」。"}
        ],
    },
    {
        "id": "join_review",
        "domain": "identity",
        "title": "入群审核",
        "description": "入群申请自动审核、阈值与待审时长。",
        "providers": [
            {
                "plugin_id": _ID,
                "fields": ["auto_moderate", "join_audit_mode"],
                "switch_field": "auto_moderate",
                "switch_label": "自动审核",
                "hint": "入群问题、通过阈值与推送模型在「序 → 设置中心 → 入群」。",
            }
        ],
    },
    {
        "id": "moderation",
        "domain": "identity",
        "title": "群管理与处罚",
        "description": "禁言阈值、玩笑禁言与二次确认。",
        "providers": [
            {"plugin_id": _ID, "fields": [], "hint": "在「序 → 设置中心 → 处罚 / 互动」配置。"}
        ],
    },
    {
        "id": "security_guard",
        "domain": "identity",
        "title": "安全防护",
        "description": "接口防护、跨群违规与保护名单。",
        "providers": [
            {
                "plugin_id": _ID,
                "fields": ["enable_api_guard"],
                "switch_field": "enable_api_guard",
                "switch_label": "接口防护",
                "hint": "保护名单与跨群规则在「序 → 设置中心 → 安全」。",
            }
        ],
    },
    # ---- 环境与感知 ----
    {
        "id": "weather_air",
        "domain": "environment",
        "title": "天气与空气",
        "description": "实时天气、空气质量与紫外线。",
        "providers": [
            {"plugin_id": _EA, "fields": [], "hint": "数据源与刷新在「境 → 配置」。"}
        ],
    },
    {
        "id": "calendar_alerts",
        "domain": "environment",
        "title": "日历与预警",
        "description": "节假日/调休、官方气象预警与地震相关性过滤。",
        "providers": [
            {"plugin_id": _EA, "fields": [], "hint": "在「境 → 实时检查」验证数据源。"}
        ],
    },
    {
        "id": "proactive_env",
        "domain": "environment",
        "title": "主动环境关心",
        "description": "达到阈值时主动提一句天气/风险。",
        "providers": [{"plugin_id": _EA, "fields": ["proactive_enabled"],
        "switch_field": "proactive_enabled",
                "switch_label": "主动关心",}],
    },
    {
        "id": "location",
        "domain": "environment",
        "title": "地点与校验",
        "description": "常驻地点与地点解析校验。",
        "providers": [
            {"plugin_id": _EA, "fields": [], "hint": "在「境 → 配置 → 常驻地点」保存并校验。"}
        ],
    },
    # ---- 语音与表达 ----
    {
        "id": "tts_backend",
        "domain": "voice",
        "title": "语音后端与音色",
        "description": "选哪家 TTS、用哪个音色、什么时候说话。",
        "providers": [
            {
                "plugin_id": _VH,
                "fields": ["tts_trigger_mode", "reply_mode"],
                "hint": "后端、密钥与音色库在「声 → 设置中心」。",
            }
        ],
    },
    {
        "id": "delivery_rhythm",
        "domain": "voice",
        "title": "说话节奏与分段",
        "description": "回复拆成几条、每条隔多久，模拟人打字。",
        "providers": [
            {
                "plugin_id": _VH,
                "fields": ["segment_enabled", "segment_threshold_chars", "segment_max_segments"],
                "switch_field": "segment_enabled",
                "switch_label": "句界兜底",
            },
            {
                "plugin_id": _CF,
                "fields": ["chunking_delay_mode"],
                "hint": "按字数延迟、最小/最大间隔在「言 → 设置中心 → 分段延迟」。",
            },
        ],
    },
    {
        "id": "audio_pipeline",
        "domain": "voice",
        "title": "音频通道",
        "description": "音频分片、时长上限与输出节奏。",
        "providers": [
            {
                "plugin_id": _EB,
                "fields": ["max_audio_seconds", "max_audio_chunk_bytes", "max_tts_audio_seconds", "output_chunk_ms"],
            }
        ],
    },
    # ---- 设备与联动 ----
    {
        "id": "pairing",
        "domain": "device",
        "title": "设备配对与实例",
        "description": "快速绑定、平台实例与会话容量。",
        "providers": [
            {
                "plugin_id": _EB,
                "fields": ["max_sessions", "event_queue_size", "interaction_debounce_ms"],
                "hint": "服务地址、监听端口与二维码在「临 → 设备与绑定」。",
            }
        ],
    },
    {
        "id": "bridge_diagnostics",
        "domain": "device",
        "title": "桥接诊断",
        "description": "桥接日志、服务计时与 SSE 心跳。",
        "providers": [
            {
                "plugin_id": _EB,
                "fields": [
                    "diagnostic_log_enabled",
                    "diagnostic_platform_log_enabled",
                    "server_timing_enabled",
                    "sse_heartbeat_seconds",
                ],
                "switch_field": "diagnostic_log_enabled",
                "switch_label": "桥接日志",
            }
        ],
    },
    # ---- 治理与更新（核自身，使用既有视图） ----
    {
        "id": "updates",
        "domain": "governance",
        "title": "更新与回滚",
        "description": "检查更新、单模块更新、一键全量与回滚。",
        "views": ["updates"],
    },
    {
        "id": "recommendations",
        "domain": "governance",
        "title": "系列推荐",
        "description": "可信模块的推荐、安装与状态检查。",
        "views": ["recommendations"],
    },
    {
        "id": "rules",
        "domain": "governance",
        "title": "每日规则",
        "description": "定时检查与自动更新的执行规则。",
        "views": ["rules"],
    },
    {
        "id": "mirrors",
        "domain": "governance",
        "title": "镜像加速",
        "description": "镜像候选、测速与直连策略。",
        "views": ["mirrors"],
    },
    {
        "id": "global_settings",
        "domain": "governance",
        "title": "全局设置",
        "description": "自动更新、日志级别、WebUI 与数据目录。",
        "views": ["settings"],
    },
    {
        "id": "account_security",
        "domain": "governance",
        "title": "账号与安全",
        "description": "控制中心账户与角色。",
        "views": ["security"],
    },
    {
        "id": "runtime_diagnostics",
        "domain": "governance",
        "title": "运行诊断",
        "description": "跨模块事件流、问题聚合与联动健康。",
        "views": ["diagnostics"],
    },
)


def _public_domain(domain: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": str(domain.get("id") or ""),
        "title": str(domain.get("title") or ""),
        "description": str(domain.get("description") or ""),
        "icon": str(domain.get("icon") or ""),
        "order": int(domain.get("order") or 0),
    }


def _public_provider(provider: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "plugin_id": str(provider.get("plugin_id") or ""),
        "fields": [str(field) for field in (provider.get("fields") or [])],
        "switch_field": str(provider.get("switch_field") or ""),
        "switch_label": str(provider.get("switch_label") or ""),
        "panels": [str(panel) for panel in (provider.get("panels") or [])],
        "hint": str(provider.get("hint") or ""),
    }


def catalog_payload() -> dict[str, Any]:
    """返回给核 WebUI / Page 的目录快照（JSON 可序列化）。"""
    domains = sorted(
        (_public_domain(domain) for domain in DOMAINS),
        key=lambda item: item["order"],
    )
    capabilities: list[dict[str, Any]] = []
    for capability in CAPABILITIES:
        entry: dict[str, Any] = {
            "id": str(capability.get("id") or ""),
            "domain": str(capability.get("domain") or ""),
            "title": str(capability.get("title") or ""),
            "description": str(capability.get("description") or ""),
            "providers": [
                _public_provider(provider) for provider in (capability.get("providers") or [])
            ],
            "views": [str(view) for view in (capability.get("views") or [])],
        }
        capabilities.append(entry)
    return {"version": CATALOG_VERSION, "domains": domains, "capabilities": capabilities}


def validate_catalog() -> list[str]:
    """静态校验：供测试与系列审计使用。返回问题列表（空表示通过）。"""
    problems: list[str] = []
    domain_ids = [str(domain.get("id")) for domain in DOMAINS]
    if len(domain_ids) != len(set(domain_ids)):
        problems.append("duplicate domain id")
    capability_ids: list[str] = []
    for capability in CAPABILITIES:
        cid = str(capability.get("id") or "")
        capability_ids.append(cid)
        if not cid:
            problems.append("capability missing id")
        domain = str(capability.get("domain") or "")
        if domain not in domain_ids:
            problems.append(f"{cid}: unknown domain {domain!r}")
        if not str(capability.get("title") or "").strip():
            problems.append(f"{cid}: missing title")
        providers = capability.get("providers") or []
        views = capability.get("views") or []
        if not providers and not views:
            problems.append(f"{cid}: no providers and no views")
        for provider in providers:
            plugin_id = str(provider.get("plugin_id") or "")
            if not plugin_id:
                problems.append(f"{cid}: provider missing plugin_id")
            fields = [str(field) for field in provider.get("fields") or []]
            for field in fields:
                if not field.strip():
                    problems.append(f"{cid}: empty field name")
            switch_field = str(provider.get("switch_field") or "")
            if switch_field and switch_field not in fields:
                problems.append(f"{cid}: switch_field {switch_field!r} not in fields")
            if switch_field and not str(provider.get("switch_label") or "").strip():
                problems.append(f"{cid}: switch_label missing for switch_field {switch_field!r}")
    if len(capability_ids) != len(set(capability_ids)):
        problems.append("duplicate capability id")
    return problems


def coverage_gaps(field_map: Mapping[str, Iterable[str]]) -> dict[str, list[str]]:
    """给定 plugin_id → 可接管字段集合，返回未被任何能力覆盖的字段。"""
    covered: dict[str, set[str]] = {}
    for capability in CAPABILITIES:
        for provider in capability.get("providers") or []:
            plugin_id = str(provider.get("plugin_id") or "")
            bucket = covered.setdefault(plugin_id, set())
            bucket.update(str(field) for field in provider.get("fields") or [])
    gaps: dict[str, list[str]] = {}
    for plugin_id, fields in field_map.items():
        missing = sorted({str(field) for field in fields} - covered.get(plugin_id, set()))
        if missing:
            gaps[plugin_id] = missing
    return gaps


def capability_provider_ids() -> dict[str, tuple[str, ...]]:
    """能力 → 提供者插件 id（供核侧状态聚合）。"""
    return {
        str(capability.get("id") or ""): tuple(
            dict.fromkeys(
                str(provider.get("plugin_id") or "")
                for provider in (capability.get("providers") or [])
                if provider.get("plugin_id")
            )
        )
        for capability in CAPABILITIES
    }


def domain_payload(domain_id: str) -> dict[str, Any] | None:
    for domain in catalog_payload()["domains"]:
        if domain["id"] == domain_id:
            return deepcopy(domain)
    return None
