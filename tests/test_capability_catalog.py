"""能力目录（能力优先信息架构）测试。"""

from __future__ import annotations

import inspect
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1].parent))

from astrbot_plugin_update_manager.core.capability_catalog import (  # noqa: E402
    CAPABILITIES,
    capability_provider_ids,
    catalog_payload,
    coverage_gaps,
    validate_catalog,
)
from astrbot_plugin_update_manager.core.series_control import (  # noqa: E402
    SeriesControlGateway,
)
from astrbot_plugin_update_manager.core.trusted import TRUSTED_BY_ID  # noqa: E402


def test_catalog_validates_clean():
    assert validate_catalog() == []


def test_payload_is_json_serializable_and_domains_have_capabilities():
    payload = catalog_payload()
    json.dumps(payload, ensure_ascii=False)
    assert len(payload["domains"]) == 7
    assert len(payload["capabilities"]) >= 30
    for domain in payload["domains"]:
        capabilities = [
            capability
            for capability in payload["capabilities"]
            if capability["domain"] == domain["id"]
        ]
        assert capabilities, domain["id"]


def test_domains_do_not_leak_plugin_identity():
    payload = catalog_payload()
    domain_text = json.dumps(payload["domains"], ensure_ascii=False)
    assert "astrbot_plugin_" not in domain_text
    assert "凝心溯溪" not in domain_text


def test_providers_reference_trusted_plugins_only():
    for capability in CAPABILITIES:
        for provider in capability.get("providers", []):
            assert provider["plugin_id"] in TRUSTED_BY_ID, capability["id"]


def test_governance_capabilities_use_kernel_views():
    for capability in CAPABILITIES:
        if capability["domain"] != "governance":
            continue
        assert capability.get("views"), capability["id"]
        assert not capability.get("providers"), capability["id"]


def test_multi_provider_capability_is_supported():
    providers = capability_provider_ids()["delivery_rhythm"]
    assert "astrbot_plugin_voice_hub" in providers
    assert "astrbot_plugin_conversation_flow" in providers


def test_coverage_gaps_reports_unmapped_fields():
    gaps = coverage_gaps(
        {"astrbot_plugin_conversation_flow": ["silence_enabled", "no_such_field"]}
    )
    assert gaps == {"astrbot_plugin_conversation_flow": ["no_such_field"]}


def test_switch_field_is_declared_on_boolean_master_switch_capabilities():
    payload = catalog_payload()
    caps = {capability["id"]: capability for capability in payload["capabilities"]}
    expected = {
        "silence": "silence_enabled",
        "chunking": "chunking_enabled",
        "interrupt": "interrupt_enabled",
        "context_bridge": "private_context_bridge_enabled",
        "group_context": "group_context_enabled",
        "context_budget": "context_budget_enforce",
        "mood": "mood_enabled",
        "retrieval": "embedding_enabled",
        "relationship_memory": "cross_platform_memory_enabled",
        "env_facts": "opportunity_cache_enabled",
        "identity_auth": "enabled",
        "join_review": "auto_moderate",
        "security_guard": "enable_api_guard",
        "proactive_env": "proactive_enabled",
        "delivery_rhythm": "segment_enabled",
        "bridge_diagnostics": "diagnostic_log_enabled",
    }
    for capability_id, field in expected.items():
        provider = caps[capability_id]["providers"][0]
        assert provider["switch_field"] == field, capability_id
        assert field in provider["fields"], capability_id
        # 卡面开关必须有中文短标签（插件 schema 常常不带标签，缺了会显示原始字段名）
        assert provider["switch_label"].strip(), capability_id
    assert caps["identity_auth"]["providers"][0]["switch_label"] == "身份守卫"
    assert caps["security_guard"]["providers"][0]["switch_label"] == "接口防护"
    assert caps["join_review"]["providers"][0]["switch_label"] == "自动审核"


def test_capabilities_without_boolean_master_switch_declare_none():
    payload = catalog_payload()
    caps = {capability["id"]: capability for capability in payload["capabilities"]}
    # 枚举型（非布尔）与只读能力不得抢占卡片开关位
    assert caps["tts_backend"]["providers"][0]["switch_field"] == ""
    assert caps["boundary"]["providers"][0]["switch_field"] == ""
    assert caps["boundary"]["providers"][1]["switch_field"] == ""
    assert caps["audio_pipeline"]["providers"][0]["switch_field"] == ""


def test_validate_catalog_rejects_switch_field_outside_fields():
    from astrbot_plugin_update_manager.core import capability_catalog as module

    capability = next(item for item in module.CAPABILITIES if item["id"] == "silence")
    provider = capability["providers"][0]
    original = provider.get("switch_field")
    provider["switch_field"] = "not_a_field"
    try:
        problems = module.validate_catalog()
    finally:
        if original is None:
            provider.pop("switch_field", None)
        else:
            provider["switch_field"] = original
    assert any("switch_field" in problem for problem in problems)


def test_overview_payload_includes_capability_catalog():
    source = inspect.getsource(SeriesControlGateway.overview)
    assert '"capabilities": catalog_payload()' in source
