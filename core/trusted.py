"""凝心溯溪系列固定可信插件清单。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TrustedPlugin:
    key: str
    plugin_id: str
    display_name: str
    repo_url: str
    description_zh: str


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
        "声",
        "astrbot_plugin_voice_hub",
        "凝心溯溪-声",
        "https://github.com/qsbb/astrbot_plugin_voice_hub",
        "汇聚语音合成与音色管理能力，统一语音交互体验。",
    ),
    TrustedPlugin(
        "核",
        "astrbot_plugin_update_manager",
        "凝心溯溪-核",
        "https://github.com/qsbb/astrbot_plugin_update_manager",
        "管理可信插件的安全更新、回滚与自动化调度。",
    ),
)
TRUSTED_BY_ID = {item.plugin_id: item for item in TRUSTED_SERIES}
