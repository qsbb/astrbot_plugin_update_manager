import json
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PAGES_DIR = PLUGIN_ROOT / "pages" / "manager"
I18N_FILE = PLUGIN_ROOT / ".astrbot-plugin" / "i18n" / "zh-CN.json"


def test_manager_page_zh_cn_metadata_is_complete():
    metadata = json.loads(I18N_FILE.read_text(encoding="utf-8"))
    manager = metadata["pages"]["manager"]
    assert manager["title"] == "更新管理"
    assert manager["description"]


def test_release_docs_cover_page_fallback_and_secret_behavior():
    readme = (PLUGIN_ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (PLUGIN_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    for document in (readme, changelog):
        assert "Plugin Page" in document
        assert "旧版" in document
        assert "不回显" in document
    assert "## 0.1.0" in changelog


def test_manager_page_has_bridge_tabs_and_i18n():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    assert '<script src="/api/plugin/page/bridge-sdk.js"></script>' in html
    assert '<script type="module" src="./app.js"></script>' in html
    assert html.index("bridge-sdk.js") < html.index("./app.js")
    assert 'data-tab="overview"' in html
    assert 'data-tab="config"' in html
    assert 'data-tab="catalog"' in html
    assert 'id="startup-error"' in html
    assert 'role="alert"' in html
    assert '"zh-CN"' in js and '"en-US"' in js
    assert "async function resolveBridge" in js
    assert "waitForAstrBotBridge" in js


def test_manager_page_waits_for_bridge_before_binding_events():
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    init_body = js[js.index("async function init()") : js.index("init().catch")]
    assert "bridge = await resolveBridge();" in init_body
    assert "await bridge.ready();" in init_body
    assert "bindEvents();" in init_body
    assert init_body.index("bridge = await resolveBridge();") < init_body.index(
        "await bridge.ready();"
    )
    assert init_body.index("await bridge.ready();") < init_body.index("bindEvents();")
    assert 'document.getElementById("refresh").addEventListener' in js
    assert 'document.getElementById("config-form").addEventListener' in js


def test_manager_page_handles_storage_and_startup_failures():
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    assert "function readStoredLocale()" in js
    assert "function storeLocale(locale)" in js
    assert "window.localStorage.getItem" in js
    assert "window.localStorage.setItem" in js
    assert "catch (error)" in js
    assert "function showStartupError(error)" in js
    assert 'document.getElementById("startup-error")' in js
    assert "init().catch(showStartupError);" in js
    assert "Object.prototype.hasOwnProperty.call(messages, storedLocale)" in js
    assert "Object.hasOwn(" not in js
    assert 'const state = { locale: localStorage.getItem' not in js


def test_manager_ui_calls_independent_api_and_treats_token_as_write_only():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    assert 'apiGet("overview")' in js
    assert 'apiGet("config")' in js
    assert 'apiGet("catalog")' in js
    assert 'apiPost("config", payload)' in js
    assert "data?.success === false" in js
    assert "data.detail || data.error" in js
    assert "field.write_only" in js
    assert 'type="password"' in js
    assert "敏感 token 仅显示是否已配置" in html
    assert "Sensitive tokens are write-only" in js


def test_manager_page_is_responsive_and_accessible():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    css = (PAGES_DIR / "style.css").read_text(encoding="utf-8")
    assert 'name="viewport"' in html
    assert 'aria-live="polite"' in html
    assert "@media (max-width:760px)" in css
    assert "prefers-reduced-motion" in css
