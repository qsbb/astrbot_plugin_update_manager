from __future__ import annotations

import shutil
from pathlib import Path

from astrbot_plugin_update_manager.core.series_ui import (
    ASSETS,
    EXTRA_ASSETS,
    audit_interactions,
    sync,
    verify,
)


def _minimal_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    source = root / "astrbot_plugin_update_manager" / "ui"
    source.mkdir(parents=True)
    for name in ASSETS:
        (source / name).write_text(f"/* {name} */\n", encoding="utf-8")
    for extra_names in EXTRA_ASSETS.values():
        for name in extra_names:
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

def test_series_ui_ships_canonical_toggle_switch():
    root = Path(__file__).resolve().parents[1]
    css = (root / "ui" / "series-ui.css").read_text(encoding="utf-8")
    js = (root / "ui" / "series-ui.js").read_text(encoding="utf-8")

    # 共享库提供统一滑块开关：checkbox.si-toggle 或 label.switch / label.si-switch 包裹
    assert 'input[type="checkbox"].si-toggle' in css
    assert '.si-switch input[type="checkbox"]' in css
    assert "border-radius: 999px" in css
    assert "translateX(18px)" in css
    # 单选与列表勾选不受影响
    assert 'input[type="radio"].si-toggle' not in css
    assert 'input[type="radio"]' not in css.split("/* 统一开关控件")[1].split(":where(/* Forms")[0]
    # 无障碍：自动补 role=switch 与 aria-checked
    assert "enhanceSwitches" in js
    # toast 支持可选操作按钮（核 WebUI 的「撤销」用它实现），旧调用保持兼容
    assert "function toast(message, type = \"info\", duration = 2600, action = null)" in js
    assert 'button.className = "toast-action"' in js
    assert "action.onClick()" in js
    assert "toast-action" in css
    assert "setAttribute('role', 'switch')" in js
    assert "setAttribute('aria-checked'" in js
    assert 'input[type="checkbox"].si-toggle, .switch input[type="checkbox"]' in js


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


def test_series_ui_header_surface_does_not_clip_dropdowns():
    """页头通用面必须让下拉菜单能完整显示。

    两个条件缺一不可（实拍回归：知的「更多 ▾」只露出第一项）：
    1) overflow: visible —— 面板用绝对定位展开，被祖先裁切就只剩一条；
    2) 页头自带层叠上下文（z-index + isolation）—— 页面外壳 .shell 常带
       backdrop-filter，会把同级 <main> 画在页头之上，面板即便没被裁也会被盖住。
    """
    root = Path(__file__).resolve().parents[1]
    css = (root / "ui" / "series-ui.css").read_text(encoding="utf-8")

    start = css.index(":where(body[data-series-ui] .hero)")
    header_rule = css[start : css.index("}", start)]
    assert "overflow: visible" in header_rule, "页头不能裁掉下拉菜单"
    assert "overflow: hidden" not in header_rule
    assert "z-index: 1" in header_rule, "页头需要层叠上下文，否则被 <main> 盖住"
    assert "isolation: isolate" in header_rule

    # 面板层级要高于页头自身，且低于弹窗层（1200+）
    panel_rule_start = css.index(".topbar-inner .more-panel")
    panel_rule = css[panel_rule_start : css.index("}", panel_rule_start)]
    assert "z-index: 60" in panel_rule
    assert "z-index: 1200" not in css and "z-index: 1300" not in css


def test_series_ui_header_clipping_override_is_page_owned():
    """需要裁剪溢出装饰的页面必须自己声明 overflow: hidden。

    核仓库只放规范与正本，其它插件是同级目录（CI 上可能不在场），
    因此这里在缺失时跳过，只在同仓布局下做断言。
    """
    import pytest

    root = Path(__file__).resolve().parents[1]
    voice_css = root.parent / "astrbot_plugin_voice_hub" / "pages" / "settings" / "style.css"
    if not voice_css.is_file():
        pytest.skip("声仓库不在同仓布局，跳过页面级裁剪断言")
    text = voice_css.read_text(encoding="utf-8")
    marker = "body[data-series-ui] .studio-hero {"
    assert marker in text
    hero_block = text[text.index(marker) :]
    hero_block = hero_block[: hero_block.index("}")]
    assert "overflow: hidden" in hero_block, "声的 hero 光斑依赖自身裁剪"
