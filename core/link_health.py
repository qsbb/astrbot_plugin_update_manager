"""联动健康聚合：合并各成员 series.diagnostics@1.1 的当前状态。

设计（见 docs/SERIES-CAPABILITY-PLAN-2026-09-14.md §4.2）：
- 事件流只做历史；当前状态只能来自成员声明的 diagnostic_state()（纯读）。
- 状态超过 STALE_AFTER_SECONDS 未刷新 -> 显示 stale，不沿用旧绿色。
- 字段白名单：只接受固定字段，杜绝 endpoint/token/正文等敏感内容进入聚合。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Iterable, Mapping

LINK_HEALTH_CONTRACT = "series.link_health@1.0"
STALE_AFTER_SECONDS = 180

STATES = ("ready", "degraded", "unavailable", "disabled", "stale", "unknown")
_SEVERITY = {
    "unavailable": 0,
    "degraded": 1,
    "disabled": 2,
    "stale": 3,
    "unknown": 4,
    "ready": 5,
}


def _text(value: Any, limit: int = 120) -> str:
    text = str(value or "").replace("\n", " ").strip()
    return text if len(text) <= limit else text[: max(1, limit - 1)] + "…"


def _int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _parse_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def normalize_link(
    plugin_id: str,
    plugin_name: str,
    link_id: str,
    entry: Mapping[str, Any],
    now: datetime,
) -> dict[str, Any]:
    state = _text(entry.get("state"), 24).lower()
    if state not in STATES:
        state = "unknown"
    observed = _parse_time(entry.get("observed_at"))
    stale = bool(
        observed is not None
        and (now - observed).total_seconds() > STALE_AFTER_SECONDS
    )
    effective = "stale" if stale and state in {"ready", "disabled"} else state
    return {
        "plugin_id": _text(plugin_id, 120),
        "plugin_name": _text(plugin_name, 60),
        "link_id": _text(link_id, 120),
        "state": effective,
        "since": _text(entry.get("since"), 40),
        "observed_at": _text(entry.get("observed_at"), 40),
        "last_success_at": _text(entry.get("last_success_at"), 40),
        "reason_code": _text(entry.get("reason_code"), 80),
        "peer_plugin_id": _text(entry.get("peer_plugin_id"), 120),
        "contract": _text(entry.get("contract"), 120),
        "contract_version": _text(entry.get("contract_version"), 40),
        "method": _text(entry.get("method"), 80),
        "fallback": _text(entry.get("fallback"), 120),
        "consecutive_failures": _int(entry.get("consecutive_failures")),
        "stale": stale,
    }


def aggregate_link_health(
    contributions: Iterable[Mapping[str, Any]],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """contributions: [{"plugin_id","plugin_name","payload": diagnostic_state_payload}]"""
    moment = now or datetime.now(UTC)
    links: list[dict[str, Any]] = []
    for item in contributions:
        if not isinstance(item, Mapping):
            continue
        payload = item.get("payload")
        if not isinstance(payload, Mapping):
            continue
        raw_links = payload.get("links")
        if not isinstance(raw_links, Mapping):
            continue
        plugin_id = _text(item.get("plugin_id"), 120)
        plugin_name = _text(item.get("plugin_name") or plugin_id, 60)
        for link_id, entry in raw_links.items():
            if not isinstance(entry, Mapping):
                continue
            links.append(normalize_link(plugin_id, plugin_name, str(link_id), entry, moment))
    links.sort(
        key=lambda link: (
            _SEVERITY.get(str(link.get("state")), 9),
            str(link.get("plugin_id")),
            str(link.get("link_id")),
        )
    )
    summary = {"total": len(links)}
    for state in STATES:
        summary[state] = 0
    for link in links:
        state = str(link.get("state") or "unknown")
        summary[state] = summary.get(state, 0) + 1
    return {
        "contract": LINK_HEALTH_CONTRACT,
        "observed_at": moment.isoformat(timespec="seconds"),
        "summary": summary,
        "links": links,
    }
