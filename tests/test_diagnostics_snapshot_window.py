from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from astrbot_plugin_update_manager.series_diagnostics import (
    diagnostic_clear,
    diagnostic_event,
    diagnostic_events,
)


def test_snapshot_returns_earliest_window_and_cursor_can_catch_up():
    diagnostic_clear()
    for index in range(7):
        diagnostic_event("window.event", f"e{index}")

    first = diagnostic_events(after_seq=0, limit=3)
    assert [event["summary"] for event in first["events"]] == ["e0", "e1", "e2"]
    assert first["has_more"] is True
    assert first["truncated"] is True
    assert first["next_seq"] == first["events"][-1]["seq"]

    second = diagnostic_events(after_seq=first["next_seq"], limit=3)
    assert [event["summary"] for event in second["events"]] == ["e3", "e4", "e5"]
    assert second["has_more"] is True

    third = diagnostic_events(after_seq=second["next_seq"], limit=3)
    assert [event["summary"] for event in third["events"]] == ["e6"]
    assert third["has_more"] is False
    assert third["truncated"] is False

    seen = [event["seq"] for page in (first, second, third) for event in page["events"]]
    assert seen == sorted(seen)
    assert len(seen) == len(set(seen)) == 7


def test_snapshot_cursor_never_jumps_over_backlog():
    diagnostic_clear()
    for index in range(700):
        diagnostic_event("backlog.event", str(index))

    cursor = 0
    collected: list[int] = []
    for _ in range(10):
        page = diagnostic_events(after_seq=cursor, limit=200)
        collected.extend(event["seq"] for event in page["events"])
        cursor = page["next_seq"]
        if not page["has_more"]:
            break

    assert len(collected) == 700
    assert collected == sorted(set(collected))


def test_snapshot_keeps_ring_overwrite_semantics():
    diagnostic_clear()
    for index in range(1005):
        diagnostic_event("ring.event", str(index))

    page = diagnostic_events(after_seq=0, limit=1000)
    assert len(page["events"]) == 1000
    assert page["has_more"] is False
    first_seq = page["events"][0]["seq"]
    assert page["dropped_before"] == first_seq - 1
    assert page["next_seq"] == page["events"][-1]["seq"]


def test_empty_buffer_cursor_still_allows_new_events():
    diagnostic_clear()
    before = diagnostic_events()["next_seq"]
    diagnostic_event("after.clear", "new event")

    payload = diagnostic_events(after_seq=before, limit=10)
    assert len(payload["events"]) == 1
    assert payload["events"][0]["seq"] > before


def test_update_manager_consumers_can_catch_up_without_duplicates():
    root = Path(__file__).resolve().parents[1]
    webui = (root / "webui" / "app.js").read_text(encoding="utf-8")
    manager = (root / "pages" / "manager" / "app.js").read_text(encoding="utf-8")

    # 两端都必须识别 has_more/truncated，并用有界追平循环推进 next_seq。
    for source in (webui, manager):
        assert "has_more ?? member?.truncated" in source
        assert "pass >= 4" in source
    assert "function applyDiagnosticPage(result, wasReset)" in webui
    assert "seen.has(key)" in webui
    assert "resetIds" in webui
    assert "function applyDiagnosticPage(data, generation, wasReset)" in manager
    assert "resetPluginIds" in manager
    assert "diagnosticMemberHasMore" in manager
