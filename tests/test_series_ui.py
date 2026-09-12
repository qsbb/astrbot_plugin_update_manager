from __future__ import annotations

import shutil
from pathlib import Path

from astrbot_plugin_update_manager.core.series_ui import ASSETS, sync, verify


def _minimal_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    source = root / "astrbot_plugin_update_manager" / "ui"
    source.mkdir(parents=True)
    for name in ASSETS:
        (source / name).write_text(f"/* {name} */\n", encoding="utf-8")
    target = root / "astrbot_plugin_active_learner" / "pages" / "manager"
    target.mkdir(parents=True)
    (target / "index.html").write_text(
        '<html><head><link href="./style.css"><link href="./series-ui.css"></head>'
        '<body data-series-ui="1"><script src="./series-ui.js"></script>'
        '<script src="./app.js"></script></body></html>',
        encoding="utf-8",
    )
    return root


def test_series_ui_sync_and_verify(tmp_path):
    root = _minimal_root(tmp_path)
    targets = {
        "astrbot_plugin_active_learner": ("pages/manager",),
    }
    import astrbot_plugin_update_manager.core.series_ui as module

    original = module.TARGETS
    module.TARGETS = targets
    try:
        sync(root)
        assert verify(root) == []
        copied = root / "astrbot_plugin_active_learner/pages/manager/series-ui.css"
        copied.write_text("drift", encoding="utf-8")
        assert any("drifted" in error for error in verify(root))
    finally:
        module.TARGETS = original


def test_series_ui_verify_reports_missing_links(tmp_path):
    root = _minimal_root(tmp_path)
    target = root / "astrbot_plugin_active_learner" / "pages" / "manager"
    (target / "index.html").write_text("<html><body></body></html>", encoding="utf-8")
    import astrbot_plugin_update_manager.core.series_ui as module

    original = module.TARGETS
    module.TARGETS = {"astrbot_plugin_active_learner": ("pages/manager",)}
    try:
        errors = verify(root)
        assert any("stylesheet not linked" in error for error in errors)
        assert any("script not linked" in error for error in errors)
        assert any("body marker missing" in error for error in errors)
    finally:
        module.TARGETS = original
