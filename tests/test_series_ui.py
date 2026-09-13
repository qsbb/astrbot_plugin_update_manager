from __future__ import annotations

import shutil
from pathlib import Path

from astrbot_plugin_update_manager.core.series_ui import ASSETS, audit_interactions, sync, verify


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

def test_series_ui_modal_layers_keep_card_interactive():
    root = Path(__file__).resolve().parents[1]
    css = (root / "ui" / "series-ui.css").read_text(encoding="utf-8")
    js = (root / "ui" / "series-ui.js").read_text(encoding="utf-8")

    # 通用控件规则已用 :where() 降权，这里的定位文本同步跟随新写法。
    backdrop_start = css.index(".modal-backdrop")
    backdrop_rule = css[backdrop_start : css.index(".modal-card", backdrop_start)]
    card_start = css.index(".modal-card", backdrop_start)
    card_rule = css[card_start : css.index(".modal-header", card_start)]

    assert "position: absolute" in backdrop_rule
    assert "z-index: 0" in backdrop_rule
    assert "position: relative" in card_rule
    assert "z-index: 1" in card_rule
    assert "display: flex" in card_rule
    assert 'copy.style.whiteSpace = "pre-line";' in js


def test_series_ui_rich_dialog_has_focus_and_escape_contract():
    root = Path(__file__).resolve().parents[1]
    js = (root / "ui" / "series-ui.js").read_text(encoding="utf-8")
    assert "function dialog(options = {})" in js
    assert "dialogStack" in js
    assert "setBackgroundInert" in js
    assert "focusableElements(card)" in js
    assert 'event.key === "Escape" && closeOnEscape' in js
    assert "closeOnBackdrop && event.target === host" in js
    assert "dialog," in js
    assert "onKeydown" in js


def test_series_ui_interaction_audit_flags_native_dialogs_and_local_toast(tmp_path):
    root = tmp_path / "project"
    target = root / "astrbot_plugin_active_learner" / "pages" / "manager"
    target.mkdir(parents=True)
    (target / "app.js").write_text(
        'window?.confirm("x"); globalThis.prompt("y"); const toast = (message) => message;',
        encoding="utf-8",
    )
    (target / "index.html").write_text(
        '<div id="toast"></div><div class="modal hidden"></div>',
        encoding="utf-8",
    )
    (target / "style.css").write_text("#toast { display: none; }", encoding="utf-8")
    import astrbot_plugin_update_manager.core.series_ui as module

    original = module.TARGETS
    module.TARGETS = {"astrbot_plugin_active_learner": ("pages/manager",)}
    try:
        result = audit_interactions(root)
    finally:
        module.TARGETS = original
    assert any("native dialog bypass" in error for error in result["errors"])
    assert any("page-local toast bypass" in error for error in result["errors"])
    assert any("static #toast node" in error for error in result["errors"])
    assert any("page-local #toast CSS" in error for error in result["errors"])
    assert any("page-local toast bypass" in error for error in result["errors"])
    assert any("static modal remains page-owned" in warning for warning in result["warnings"])


def test_series_ui_interaction_audit_accepts_shared_series_ui(tmp_path):
    root = tmp_path / "project"
    target = root / "astrbot_plugin_active_learner" / "pages" / "manager"
    target.mkdir(parents=True)
    (target / "app.js").write_text(
        'window.SeriesUI.confirm("x"); window.SeriesUI.toast("ok");',
        encoding="utf-8",
    )
    (target / "index.html").write_text("<main></main>", encoding="utf-8")
    import astrbot_plugin_update_manager.core.series_ui as module

    original = module.TARGETS
    module.TARGETS = {"astrbot_plugin_active_learner": ("pages/manager",)}
    try:
        result = audit_interactions(root)
    finally:
        module.TARGETS = original
    assert result == {"errors": [], "warnings": []}
