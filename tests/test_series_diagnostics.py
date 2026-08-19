from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from astrbot_plugin_update_manager.series_diagnostics import (
    diagnostic_clear,
    diagnostic_event,
    diagnostic_events,
    logger,
)


def test_series_diagnostics_preserve_debug_details_and_mask_credentials():
    diagnostic_clear()
    diagnostic_event(
        "update.plan",
        "planned 123456789",
        details={
            "eligible": True,
            "token": "secret",
            "token_configured": True,
            "path": r"D:\AstrBot\data\plugins",
            "response": "full diagnostic response",
            "nested": {"user_id": "123456789", "api_key": "nested-secret"},
            "items": list(range(12)),
        },
    )
    diagnostic_event("page.webui.start", "页面 POST webui/start 完成")
    logger.warning(
        'failed authorization=secret message="private text" '
        "https://example.test/path?token=secret for 123456789 "
        "alice@example.com Abcdef1234567890Ghijkl private chat body "
        "uid=user-a token abcdefghijk"
    )
    payload = diagnostic_events(after_seq=0, limit=10)
    serialized = str(payload["events"])
    assert payload["stream_id"]
    assert diagnostic_events()["stream_id"] == payload["stream_id"]
    assert payload["events"][1]["summary"] == "页面 POST webui/start 完成"
    log_detail = payload["events"][2]["details"]["log_detail"]
    assert "private chat body" in log_detail
    assert "user-a" in serialized
    assert "abcdefghijk" not in serialized
    assert logger.propagate is False
    assert payload["events"][0]["details"] == {
        "eligible": True,
        "token": "<已隐藏凭据>",
        "token_configured": True,
        "path": r"D:\AstrBot\data\plugins",
        "response": "full diagnostic response",
        "nested": {"user_id": "123456789", "api_key": "<已隐藏凭据>"},
        "items": list(range(12)),
    }
    assert "123456789" in str(payload["events"])
    assert "token=secret" not in str(payload["events"])
    assert "authorization=secret" not in str(payload["events"])
    assert "private text" in str(payload["events"])
    assert "alice@example.com" in str(payload["events"])
    assert "Abcdef1234567890Ghijkl" in str(payload["events"])
    assert any(
        type(handler).__name__ == "DiagnosticBuffer" for handler in logger.handlers
    )


def test_series_diagnostics_cursor_and_capacity():
    diagnostic_clear()
    base = diagnostic_events()["next_seq"]
    for index in range(1005):
        diagnostic_event("update.event", index)
    payload = diagnostic_events(after_seq=base + 1000, limit=20)
    assert [event["seq"] for event in payload["events"]] == list(
        range(base + 1001, base + 1006)
    )
    assert payload["dropped_before"] == base + 5
    old_stream_id = payload["stream_id"]
    diagnostic_clear()
    assert diagnostic_events()["stream_id"] != old_stream_id
