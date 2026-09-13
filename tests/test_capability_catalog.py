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


def test_overview_payload_includes_capability_catalog():
    source = inspect.getsource(SeriesControlGateway.overview)
    assert '"capabilities": catalog_payload()' in source
