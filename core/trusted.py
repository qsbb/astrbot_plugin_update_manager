"""凝心溯溪系列固定可信插件清单。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True)
class TrustedPlugin:
    key: str
    plugin_id: str
    display_name: str
    repo_url: str
    description_zh: str
    aliases: tuple[str, ...] = ()


TRUSTED_SERIES = (
    TrustedPlugin(
        "知",
        "astrbot_plugin_active_learner",
        "凝心溯溪-知",
        "https://github.com/qsbb/astrbot_plugin_active_learner",
        "主动学习对话知识，支持检索、验证与持续积累。",
    ),
    TrustedPlugin(
        "言",
        "astrbot_plugin_conversation_flow",
        "凝心溯溪-言",
        "https://github.com/qsbb/astrbot_plugin_conversation_flow",
        "管理对话流程与上下文衔接，提升多轮交流连贯性。",
    ),
    TrustedPlugin(
        "序",
        "astrbot_plugin_identity_guardian",
        "凝心溯溪-序",
        "https://github.com/qsbb/astrbot_plugin_identity_guardian",
        "提供身份、关系与权限守护，维护群组互动秩序。",
    ),
    TrustedPlugin(
        "情",
        "astrbot_plugin_relationship",
        "凝心溯溪-情",
        "https://github.com/qsbb/astrbot_plugin_relationship",
        "统一管理短期情绪、长期好感、信任与熟悉度，并输出结构化行为建议。",
    ),
    TrustedPlugin(
        "境",
        "astrbot_plugin_environment_awareness",
        "凝心溯溪-境",
        "https://github.com/qsbb/astrbot_plugin_environment_awareness",
        "按需感知当地日历、天气、空气质量、官方预警和相关自然事件；免 API Key。",
    ),
    TrustedPlugin(
        "声",
        "astrbot_plugin_voice_hub",
        "凝心溯溪-声",
        "https://github.com/qsbb/astrbot_plugin_voice_hub",
        "汇聚语音合成与音色管理能力，统一语音交互体验。",
    ),
    TrustedPlugin(
        "临",
        "astrbot_plugin_embodiment_bridge",
        "凝心溯溪-临",
        "https://github.com/qsbb/astrbot_plugin_embodiment_bridge",
        "连接 AstrBot 与具身交互运行时，提供独立、可诊断的人格与事件桥接。",
        aliases=("astrbot_plugin_quest_avatar_bridge",),
    ),
    TrustedPlugin(
        "核",
        "astrbot_plugin_update_manager",
        "凝心溯溪-核",
        "https://github.com/qsbb/astrbot_plugin_update_manager",
        "管理可信插件的安全更新、回滚与自动化调度。",
    ),
    TrustedPlugin(
        "枢",
        "astrbot_plugin_orchestration_hub",
        "凝心溯溪-枢",
        "https://github.com/qsbb/astrbot_plugin_orchestration_hub",
        "提供系列服务注册、契约解析与跨插件能力编排。",
    ),
)
TRUSTED_BY_ID = {
    identity: item
    for item in TRUSTED_SERIES
    for identity in (item.plugin_id, *item.aliases)
}


def trusted_plugin_identities(plugin: TrustedPlugin) -> tuple[str, ...]:
    """Return the canonical ID followed by accepted legacy runtime aliases."""
    return (plugin.plugin_id, *plugin.aliases)

DIAGNOSTIC_SERIES_ID = "ningxin_suxi"
DIAGNOSTIC_REPOSITORY_OWNER = "qsbb"
_PLUGIN_ID = re.compile(r"^astrbot_plugin_[a-z0-9_]{1,96}$")


def is_trusted_diagnostic_repository(plugin_id: str, repository: str) -> bool:
    """Accept only an exact qsbb GitHub repository matching the plugin ID."""
    if not _PLUGIN_ID.fullmatch(plugin_id):
        return False
    try:
        parsed = urlsplit(repository)
        port = parsed.port
    except (TypeError, ValueError):
        return False
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.query
        or parsed.fragment
    ):
        return False
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) != 2:
        return False
    owner, repository_name = parts
    if repository_name.endswith(".git"):
        repository_name = repository_name[:-4]
    return owner == DIAGNOSTIC_REPOSITORY_OWNER and repository_name == plugin_id
