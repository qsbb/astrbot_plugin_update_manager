import json
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PAGES_DIR = PLUGIN_ROOT / "pages" / "manager"
I18N_FILE = PLUGIN_ROOT / ".astrbot-plugin" / "i18n" / "zh-CN.json"


def test_manager_page_zh_cn_metadata_is_complete():
    metadata = json.loads(I18N_FILE.read_text(encoding="utf-8"))
    manager = metadata["pages"]["manager"]
    assert manager["title"] == "系列插件核心"
    assert manager["description"] == "推荐安装，统一管理系列插件的更新、启用停用、回滚与调度"


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
    assert 'data-tab="recommendations"' in html
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
    assert 'apiGet("rule")' in js
    assert 'apiPost("rule", payload)' in js
    assert 'apiGet("catalog")' in js
    assert 'apiGet("recommendations")' in js
    assert 'apiPost("config", payload)' in js
    assert '["install", "update", "disable"].includes(action)' in js
    assert "{ plugin_id: pluginId, confirm: true }" in js
    assert ": { plugin_id: pluginId };" in js
    assert "await Promise.all([loadRecommendations(), loadOverview(), loadCatalog()])" in js
    assert "data?.success === false" in js
    assert "errorReason(data.error || data.detail)" in js
    assert "ClientResponseError" not in js
    assert "field.write_only" in js
    assert 'type="password"' in js
    assert "敏感 token 仅显示是否已配置" in html
    assert "Sensitive tokens are write-only" in js
    assert 'item.loaded ? t("loaded") : t("notLoaded")' in js
    assert "item.display_name || item.plugin_id" in js
    assert "<code>${escapeHtml(item.plugin_id)}</code>" in js
    assert "未加载插件不可更新" in html
    assert "unloaded plugins cannot be updated" in js
    assert "data.diagnostics?.messages" in js


def test_catalog_has_safe_lifecycle_switch_and_localized_errors():
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    css = (PAGES_DIR / "style.css").read_text(encoding="utf-8")
    assert "function catalogSwitch(item)" in js
    assert 'data-catalog-action="${action}"' in js
    assert 'apiPost(`catalog/${action}`, payload)' in js
    assert 'action === "disable" && !await confirmRecommendationAction' in js
    assert "item.lifecycle?.reason" in js
    assert "errorReason" in js
    assert "网络连接失败" in js
    assert ".catalog-actions" in css


def test_recommendations_have_forced_refresh_version_gate_and_accessible_switch():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    css = (PAGES_DIR / "style.css").read_text(encoding="utf-8")
    assert 'id="check-latest"' in html
    assert 'apiPost("recommendations/check-latest", {})' in js
    assert "actions.update" in js
    for status in (
        "update_available",
        "up_to_date",
        "local_newer",
        "not_installed",
        "check_failed",
        "unknown",
    ):
        assert status in js
    assert "function versionStatusBadge(item)" in js
    assert "function recommendationError(item)" in js
    assert '`${t("errorCode")}: ${item.error || "UNKNOWN"}`' in js
    assert '`${t("errorHttpStatus")}: ${context.http_status}`' in js
    assert '`${t("errorRepository")}: ${context.repo}`' in js
    assert '`${t("errorBranch")}: ${context.default_branch}`' in js
    assert "${recommendationError(item)}" in js
    assert 'role="switch"' in js
    assert 'aria-checked="${item.activated ? "true" : "false"}"' in js
    assert "await loadRecommendations();" in js
    assert ".lifecycle-switch input:focus-visible" in css
    assert "官方安装会直接加载" in html
    assert "不会额外重复重载" in html


def test_recommendations_show_self_update_repository_notice():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    css = (PAGES_DIR / "style.css").read_text(encoding="utf-8")
    assert 'id="self-update-notice"' in html
    assert "function renderSelfUpdateNotice(selfUpdate)" in js
    assert "selfUpdate?.update_available" in js
    assert "renderSelfUpdateNotice(data.self_update)" in js
    assert 'target="_blank" rel="noopener noreferrer"' in js
    assert "自身更新已禁用，请前往仓库更新" in js
    assert ".self-update-notice" in css


def test_recommendation_cards_confirm_only_destructive_actions_and_show_progress():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    css = (PAGES_DIR / "style.css").read_text(encoding="utf-8")
    assert "item.description_zh" in js
    assert 'id="confirmation-dialog"' in html
    assert 'id="recommendation-status"' in html
    assert "requiresConfirmation && !await confirmRecommendationAction" in js
    assert 'input[role=\'switch\']' in js
    assert "item.disabled = true" in js
    assert "setRecommendationBusy(action, pluginName)" in js
    assert "clearRecommendationBusy()" in js
    assert ".recommendation-description" in css
    assert ".operation-status" in css
    assert "dialog::backdrop" in css


def test_daily_rule_card_has_all_controls_and_check_only_warning():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    for element_id in (
        "rule-form",
        "rule-gate-hint",
        "rule-auto-update-enabled",
        "rule-enabled",
        "rule-time",
        "rule-timezone",
        "rule-policy",
        "rule-failure",
        "rule-jitter",
        "rule-minimum-age",
        "rule-prerelease",
        "rule-plugins",
        "rule-next-run",
    ):
        assert f'id="{element_id}"' in html
    assert "check_only 仅检查并记录，绝不会更新插件" in html
    assert "check_only checks and records only; it never updates plugins" in js
    assert "expected_revision: state.rule?.rule?.revision" in js
    assert 'document.getElementById("rule-form").addEventListener' in js


def test_daily_rule_master_gate_uses_safe_save_order_and_refreshes_all_sources():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    assert 'id="rule-auto-update-enabled"' in html
    assert 'role="switch"' in html
    assert "Boolean(data.global?.auto_update_enabled)" in js
    save_rule = js[js.index("async function saveRule") : js.index("async function saveConfig")]
    disable_branch = save_rule[
        save_rule.index("if (!autoUpdateEnabled)") : save_rule.index("} else {")
    ]
    enable_branch = save_rule[
        save_rule.index("} else {") : save_rule.index("toast(t(\"ruleSaved\"))")
    ]
    assert disable_branch.index('apiPost("config", { auto_update_enabled: false })') < disable_branch.index(
        'apiPost("rule", payload)'
    )
    assert enable_branch.index('apiPost("rule", payload)') < enable_branch.index(
        'apiPost("config", { auto_update_enabled: true })'
    )
    assert 'apiPost("config", { auto_update_enabled: false })' in save_rule[save_rule.index("catch (error)") :]
    assert "Promise.all([loadConfig(), loadRule(), loadOverview()])" in save_rule


def test_rule_policy_and_failure_options_have_bilingual_labels_and_keep_values():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    expected = {
        "check_only": "policyCheckOnly",
        "patch": "policyPatch",
        "minor": "policyMinor",
        "stable": "policyStable",
        "rollback_continue": "failureRollbackContinue",
        "rollback_stop": "failureRollbackStop",
    }
    for value, label_key in expected.items():
        assert f'value="{value}" data-i18n="{label_key}"' in html
        assert f'{label_key}:' in js
        assert value in js


def test_capability_cards_use_bilingual_label_comment_and_keep_code():
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    assert "item.label?.[state.locale] || item.code" in js
    assert "item.comment?.[state.locale]" in js
    assert "escapeHtml(item.code)" in js


def test_catalog_hint_describes_merged_runtime_and_metadata_catalog():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    assert "合并展示运行时插件与已安装元数据" in html
    assert "Runtime plugins and installed metadata are always merged" in js
    assert "运行时列表为空时展示" not in html


def test_manager_page_is_responsive_and_accessible():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    css = (PAGES_DIR / "style.css").read_text(encoding="utf-8")
    assert 'name="viewport"' in html
    assert 'aria-live="polite"' in html
    assert "@media (max-width:760px)" in css
    assert "prefers-reduced-motion" in css
