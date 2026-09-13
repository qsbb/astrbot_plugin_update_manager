"""联动健康聚合测试（series.link_health@1.0）。"""

from __future__ import annotations

import pathlib
import sys
from datetime import UTC, datetime, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1].parent))

from astrbot_plugin_update_manager.core.link_health import (  # noqa: E402
    aggregate_link_health,
    normalize_link,
)

NOW = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)


def _link(state: str, **extra):
    entry = {"state": state, "observed_at": NOW.isoformat(timespec="seconds")}
    entry.update(extra)
    return entry


def test_aggregate_sorts_by_severity_and_summarizes():
    contributions = [
        {"plugin_id": "p1", "plugin_name": "言", "payload": {"links": {"a->b": _link("ready")}}},
        {"plugin_id": "p2", "plugin_name": "序", "payload": {"links": {
            "c->d": _link("degraded", reason_code="CONTRACT_VERSION_UNSUPPORTED", consecutive_failures=3),
            "e->f": _link("unavailable"),
        }}},
    ]

    result = aggregate_link_health(contributions, now=NOW)

    assert result["contract"] == "series.link_health@1.0"
    assert [link["state"] for link in result["links"]] == ["unavailable", "degraded", "ready"]
    assert result["summary"]["total"] == 3
    assert result["summary"]["ready"] == 1
    assert result["summary"]["degraded"] == 1
    assert result["links"][1]["consecutive_failures"] == 3


def test_stale_ready_becomes_stale_not_green():
    old = (NOW - timedelta(minutes=10)).isoformat(timespec="seconds")

    result = aggregate_link_health(
        [{"plugin_id": "p1", "plugin_name": "言", "payload": {"links": {"a->b": _link("ready", observed_at=old)}}}],
        now=NOW,
    )

    link = result["links"][0]
    assert link["state"] == "stale"
    assert link["stale"] is True
    assert result["summary"]["stale"] == 1
    assert result["summary"]["ready"] == 0


def test_invalid_contributions_are_ignored_and_sensitive_fields_dropped():
    result = aggregate_link_health(
        [
            {"plugin_id": "p1", "plugin_name": "言", "payload": {"links": {
                "x->y": _link("ready", token="SECRET", endpoint="http://internal", reason_code="OK"),
            }}},
            {"plugin_id": "p2", "plugin_name": "序", "payload": "not-a-mapping"},
            {"plugin_id": "p3", "plugin_name": "境", "payload": {"links": {"bad": "not-a-mapping"}}},
        ],
        now=NOW,
    )

    assert result["summary"]["total"] == 1
    link = result["links"][0]
    assert "token" not in link
    assert "endpoint" not in link
    assert link["reason_code"] == "OK"


def test_unknown_state_is_reported_as_unknown():
    link = normalize_link("p1", "言", "x", {"state": "weird"}, NOW)

    assert link["state"] == "unknown"
