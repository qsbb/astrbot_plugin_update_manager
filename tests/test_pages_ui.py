import json
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PAGES_DIR = PLUGIN_ROOT / "pages" / "manager"
I18N_FILE = PLUGIN_ROOT / ".astrbot-plugin" / "i18n" / "zh-CN.json"


def test_manager_page_zh_cn_metadata_is_complete():
    metadata = json.loads(I18N_FILE.read_text(encoding="utf-8"))
    manager = metadata["pages"]["manager"]
    assert manager["title"] == "系列插件核心"
    assert (
        manager["description"]
        == "推荐安装，统一管理系列插件的更新、启用停用、回滚与调度"
    )


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
    assert 'data-tab="mirrors"' in html
    assert 'data-tab="catalog"' in html
    assert 'data-tab="logs"' in html
    assert 'id="tab-logs" class="active" role="tab"' in html
    assert 'id="logs" class="panel active" role="tabpanel"' in html
    assert 'id="overview" class="panel" role="tabpanel"' in html
    assert html.index('data-tab="logs"') < html.index('data-tab="overview"')
    assert 'id="startup-error"' in html
    assert 'role="alert"' in html
    assert '"zh-CN"' in js and '"en-US"' in js
    assert "async function resolveBridge" in js
    assert "waitForAstrBotBridge" in js


def test_manager_page_has_incremental_series_diagnostic_console():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    css = (PAGES_DIR / "style.css").read_text(encoding="utf-8")
    for element_id in (
        "diagnostic-pause",
        "diagnostic-refresh",
        "diagnostic-clear",
        "diagnostic-plugin-filter",
        "diagnostic-level-filter",
        "diagnostic-search",
        "diagnostic-members",
        "diagnostic-log-list",
    ):
        assert f'id="{element_id}"' in html
    assert 'apiPost("diagnostics/logs", {' in js
    assert "cursors: state.diagnosticCursors" in js
    assert "streams: state.diagnosticStreams" in js
    assert "const activePluginIds = new Set(nextMembers.map" in js
    assert "!activePluginIds.has(pluginId)" in js
    assert "delete state.diagnosticCursors[pluginId]" in js
    assert "delete state.diagnosticStreams[pluginId]" in js
    assert 'apiPost("diagnostics/clear", { confirm: true })' in js
    assert "startDiagnosticPolling" in js
    assert "stopDiagnosticPolling" in js
    assert "state.diagnosticPaused" in js
    assert "state.diagnosticGeneration" in js
    assert "state.diagnosticRefreshPending" in js
    assert "diagnosticDisabled" in js
    assert "diagnosticUnavailable" in js
    assert "generation !== state.diagnosticGeneration" in js
    assert "resetPluginIds" in js
    assert "!resetPluginIds.has(event.plugin_id)" in js
    assert "escapeHtml(event.summary" in js
    assert "diagnostic-plugin" in js
    assert '<details class="diagnostic-event' in js
    assert "state.diagnosticExpanded" in js
    assert 'details["log_detail"]' not in js
    assert "data.log_detail" in js
    assert "await loadDiagnostics(true)" in js
    assert "JSON.stringify(event.details || {})" in js
    assert ".diagnostic-log-list" in css
    assert ".diagnostic-log-detail" in css
    assert "content-visibility:auto" in css
    assert "contain-intrinsic-size:auto 88px" in css
    assert "max-height:560px" in css


def test_manager_page_waits_for_bridge_before_binding_events():
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    init_body = js[js.index("async function init()") : js.index("init().catch")]
    assert "bridge = await resolveBridge();" in init_body
    assert "await bridge.ready();" in init_body
    assert "bindEvents();" in init_body
    assert "const initialDiagnostics = loadDiagnostics(true);" in init_body
    assert "const initialPageData = refreshAll(false);" in init_body
    assert "await initialDiagnostics;" in init_body
    assert "await initialPageData;" in init_body
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
    assert "const state = { locale: localStorage.getItem" not in js


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
    assert (
        "await Promise.all([loadRecommendations(), loadOverview(), loadCatalog()])"
        in js
    )
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
    assert "apiPost(`catalog/${action}`, payload)" in js
    assert 'action === "disable" && !await confirmRecommendationAction' in js
    assert "item.lifecycle?.reason" in js
    assert "errorReason" in js
    assert "网络连接失败" in js
    assert ".catalog-actions" in css


def test_catalog_updates_are_click_only_and_never_auto_checked():
    """目录更新必须与系列推荐同款：按钮点击驱动，且不会进页面自动检查。

    这里逐条钉住"按需"的三个前提：右上角有独立的检查更新按钮、检查只在点击
    回调里发起、以及标签切换回调不会替目录触发检查。若哪天有人给目录加上
    自动检查，全量插件探测会拖慢首屏并快速耗尽 GitHub 匿名配额。
    """
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    assert 'id="catalog-check-updates"' in html
    assert 'data-i18n="checkUpdates"' in html
    assert 'id="catalog-rate-limit-notice"' in html
    assert 'apiPost("catalog/check-updates", payload)' in js
    assert (
        'document.getElementById("catalog-check-updates").addEventListener("click", runCatalogCheck)'
        in js
    )
    # 检查更新只能由 runCatalogCheck 发起；loadCatalog 保持零网络版本探测。
    load_catalog = js.split("async function loadCatalog()", 1)[1].split(
        "\n// 只在用户点击时调用", 1
    )[0]
    assert "check-updates" not in load_catalog
    # 标签切换只为系列推荐自动检查，目录不在其中。
    tab_handler = js.split('document.querySelectorAll("[data-tab]")', 1)[1].split(
        "config-form", 1
    )[0]
    assert "autoCheckRecommendations" in tab_handler
    assert "runCatalogCheck" not in tab_handler
    assert "checkCatalogUpdates" not in tab_handler
    # 普通与强制更新都必须二次确认；强制模式使用独立警示文案与显式 force。
    assert 'await confirmRecommendationAction("update", pluginName)' in js
    assert (
        'await showConfirmation(t("forceUpdateConfirm").replace("{name}", pluginName))'
        in js
    )
    assert "? { plugin_id: pluginId, confirm: true, force: true }" in js
    assert ": { plugin_id: pluginId, confirm: true };" in js
    assert 'apiPost("catalog/update", payload)' in js
    assert 'data-force-update="true"' in js
    assert "即使已是最新版或远端版本更旧" in js
    assert "even when it is the same version or older" in js
    # 普通更新仅允许新版本；强制更新额外允许同版本和本地较新。
    assert "Boolean(view?.update_available)" in js
    assert (
        '["update_available", "up_to_date", "local_newer"].includes(view?.version_status)'
        in js
    )
    assert 't("notChecked")' in js
    assert "未检查" in js
    assert 'checkUpdates: "Check for updates"' in js


def test_recommendations_have_forced_refresh_version_gate_and_accessible_switch():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    css = (PAGES_DIR / "style.css").read_text(encoding="utf-8")
    assert 'id="check-latest"' in html
    assert 'id="apply-all-recommendations"' in html
    assert 'data-i18n="applyAll"' in html
    assert (
        'apiPost("recommendations/check-latest", { force_refresh: forceRefresh })' in js
    )
    assert 'apiPost("recommendations/apply-all", { confirm: true })' in js
    assert "async function runApplyAllRecommendations()" in js
    assert "applyAllConfirm" in js
    assert "all_succeeded" in js
    assert "actions.update" in js
    assert "actions.force_update" in js
    assert 'data-recommendation-action="update" data-force-update="true"' in js
    assert "? { plugin_id: pluginId, confirm: true, force: true }" in js
    assert 'setRecommendationBusy(force ? "forceUpdate" : action, pluginName)' in js
    assert (
        'showConfirmation(t("forceUpdateConfirm").replace("{name}", pluginName))' in js
    )
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
    assert "function versionError(item)" in js
    assert '`${t("errorCode")}: ${item.error || "UNKNOWN"}`' in js
    assert '`${t("errorHttpStatus")}: ${context.http_status}`' in js
    assert '`${t("errorRepository")}: ${context.repo}`' in js
    assert '`${t("errorBranch")}: ${context.default_branch}`' in js
    assert "${versionError(item)}" in js
    assert 'role="switch"' in js
    assert 'aria-checked="${item.activated ? "true" : "false"}"' in js
    assert "await loadRecommendations();" in js
    assert ".lifecycle-switch input:focus-visible" in css
    assert "官方安装会直接加载" in html
    assert "不会额外重复重载" in html


def test_recommendations_tab_auto_checks_once_with_cached_request():
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    # 自动检查必须复用 loadRecommendations 与 check-latest，且不强制刷新。
    assert (
        "async function loadRecommendations(check = false, forceRefresh = true)" in js
    )
    assert "async function autoCheckRecommendations()" in js
    assert "await loadRecommendations(true, false);" in js
    assert "versionCheckBusy: false" in js
    assert "autoVersionCheckDone: false" in js
    auto_check = js[
        js.index("async function autoCheckRecommendations()") : js.index(
            "function confirmRecommendationAction"
        )
    ]
    # 会话内只自动检查一次，并与手动检查/推荐操作互斥。
    assert (
        "if (state.autoVersionCheckDone || state.versionCheckBusy || state.recommendationBusy) return;"
        in auto_check
    )
    assert auto_check.index("state.autoVersionCheckDone = true;") < auto_check.index(
        "await loadRecommendations(true, false);"
    )
    # 检查中显示状态，失败仍回落到缓存列表渲染。
    assert 'setVersionCheckBusy("autoCheckingLatest")' in auto_check
    assert "clearVersionCheckBusy();" in auto_check
    assert "await loadRecommendations();" in auto_check
    assert "catch (error)" in auto_check
    tab_handler = js[
        js.index('document.querySelectorAll("[data-tab]")') : js.index(
            'document.getElementById("config-form")'
        )
    ]
    assert 'button.dataset.tab === "recommendations"' in tab_handler
    assert "autoCheckRecommendations()" in tab_handler


def test_manual_and_auto_version_check_share_one_busy_lock():
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    assert "function setVersionCheckBusy(labelKey)" in js
    assert "function clearVersionCheckBusy()" in js
    assert "state.versionCheckBusy = true;" in js
    assert "state.versionCheckBusy = false;" in js
    manual = js[
        js.index('document.getElementById("check-latest").addEventListener') : js.index(
            'document.getElementById("refresh").addEventListener'
        )
    ]
    assert "if (state.versionCheckBusy) return;" in manual
    assert "state.autoVersionCheckDone = true;" in manual
    assert 'setVersionCheckBusy("checkingLatest")' in manual
    assert "await loadRecommendations(true);" in manual
    assert "clearVersionCheckBusy();" in manual
    # 版本检查不得抢走推荐操作的状态条。
    assert "if (status && !state.recommendationBusy) status.hidden = true;" in js
    assert 'autoCheckingLatest: "正在自动检查版本…"' in js
    assert 'autoCheckingLatest: "Checking versions automatically…"' in js


def test_recommendations_show_self_update_repository_notice():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    css = (PAGES_DIR / "style.css").read_text(encoding="utf-8")
    assert 'id="self-update-notice"' in html
    assert "function renderSelfUpdateNotice(selfUpdate)" in js
    assert "selfUpdate?.update_available" in js
    assert "renderSelfUpdateNotice(data.self_update)" in js
    assert 'target = "_top"' in js
    assert 'rel = "noopener noreferrer"' in js
    assert 'const installedRoute = "/extension#installed"' in js
    assert "link.dataset.internalRoute = installedRoute" in js
    assert "a[data-external-url]" in js
    assert "a[data-internal-route]" in js
    assert 'link.href = internalRouteUrl(installedRoute) || "#"' in js
    assert 'data-external-url="${escapeHtml(item.repo_url)}"' in js
    assert "自身更新已禁用，请前往已安装插件页更新" in js
    assert 'goToInstalledPlugins: "前往已安装插件页"' in js
    assert ".self-update-notice" in css


def test_mobile_self_update_prefers_bridge_then_top_level_dashboard_route():
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    helper = js[
        js.index("async function invokeBridgeNavigation") : js.index("function toast")
    ]
    self_update = helper[helper.index("async function openSelfUpdateTarget") :]

    assert 'typeof bridge[method] !== "function"' in helper
    assert "await bridge[method](target)" in helper
    assert 'invokeBridgeNavigation("navigate", target)' in helper
    assert "new URL(`/#${target}`, window.location.origin).href" in helper
    assert 'window.open(targetUrl, "_top")' in helper
    assert 'target.startsWith("/")' in helper
    assert 'target.startsWith("//")' in helper
    assert self_update.index("await openInternalRoute(route)") < self_update.index(
        "await copyInstalledPageUrl(link, internalRouteUrl(route))"
    )
    # iframe 自身的 hash/location 不能被当作宿主导航成功；兜底必须指向顶层 Dashboard。
    assert "topWindow.location.assign(targetUrl)" in helper
    assert 'if (!bridge || typeof bridge.navigate !== "function") return;' in js
    assert 'link.target = "_top"' in js


def test_restricted_host_reveals_and_copies_update_page_url_with_prompt_fallback():
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    css = (PAGES_DIR / "style.css").read_text(encoding="utf-8")
    fallback = js[
        js.index("function revealInstalledPageUrl") : js.index("function toast")
    ]

    assert 'link.closest(".self-update-notice")' in fallback
    assert 'fallback.className = "installed-page-url-fallback"' in fallback
    assert 'fallback.textContent = `${t("installedPageUrlLabel")}：${url}`' in fallback
    assert "await navigator.clipboard.writeText(url)" in fallback
    assert 'toast(t("installedPageUrlCopied"))' in fallback
    assert 'window.prompt(t("copyInstalledPageUrl"), url)' in fallback
    assert fallback.index("revealInstalledPageUrl(link, url)") < fallback.index(
        "await navigator.clipboard.writeText(url)"
    )
    assert ".installed-page-url-fallback" in css
    assert "user-select:all" in css


def test_recommendation_cards_confirm_only_destructive_actions_and_show_progress():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    css = (PAGES_DIR / "style.css").read_text(encoding="utf-8")
    assert "item.description_zh" in js
    assert 'id="confirmation-dialog"' in html
    assert 'id="recommendation-status"' in html
    assert "const confirmed = !requiresConfirmation" in js
    assert "await confirmRecommendationAction(action, pluginName)" in js
    assert "input[role='switch']" in js
    assert "item.disabled = true" in js
    assert 'setRecommendationBusy(force ? "forceUpdate" : action, pluginName)' in js
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
    save_rule = js[
        js.index("async function saveRule") : js.index("async function saveConfig")
    ]
    disable_branch = save_rule[
        save_rule.index("if (!autoUpdateEnabled)") : save_rule.index("} else {")
    ]
    enable_branch = save_rule[
        save_rule.index("} else {") : save_rule.index('toast(t("ruleSaved"))')
    ]
    assert disable_branch.index(
        'apiPost("config", { auto_update_enabled: false })'
    ) < disable_branch.index('apiPost("rule", payload)')
    assert enable_branch.index('apiPost("rule", payload)') < enable_branch.index(
        'apiPost("config", { auto_update_enabled: true })'
    )
    assert (
        'apiPost("config", { auto_update_enabled: false })'
        in save_rule[save_rule.index("catch (error)") :]
    )
    assert "Promise.allSettled([loadConfig(), loadRule(), loadOverview()])" in save_rule


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
        assert f"{label_key}:" in js
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


def test_rate_limit_notice_shows_retry_time_and_token_hint():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    css = (PAGES_DIR / "style.css").read_text(encoding="utf-8")
    assert 'id="rate-limit-notice"' in html
    assert (
        'function renderRateLimitNotice(rateLimit, nodeId = "rate-limit-notice")' in js
    )
    assert "renderRateLimitNotice(data.rate_limit)" in js
    assert "rateLimit?.limited" in js
    # 限流提示必须同时给出可重试时间、剩余额度与提额入口。
    assert 't("rateLimitBanner").replace("{retry}"' in js
    assert 't("rateLimitRemaining")' in js
    assert 'rateLimit.token_configured ? "" : t("errorTokenHint")' in js
    assert "GitHub 配额已用尽" in js
    assert "可在配置中填写 GitHub Token 提升额度" in js
    assert "Set a GitHub Token in configuration to raise the quota" in js
    assert ".rate-limit-notice" in css


def test_recommendation_error_renders_retry_delay_and_token_hint():
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    assert "function formatRetryDelay(seconds)" in js
    assert "function retryHint(context)" in js
    assert 'context.rate_limited ? retryHint(context) : ""' in js
    assert 'context.token_hint_required ? t("errorTokenHint") : ""' in js
    assert "errorRetryAfter" in js
    assert '"REGISTRY_RATE_LIMITED", "REGISTRY_HTTP_403", "REGISTRY_HTTP_429"' in js


def test_mirror_tab_lists_candidates_with_latency_and_custom_entry():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    css = (PAGES_DIR / "style.css").read_text(encoding="utf-8")
    for element_id in (
        "mirrors",
        "mirror-list",
        "mirror-benchmark",
        "mirror-add-form",
        "mirror-add-input",
        "mirror-probe",
    ):
        assert f'id="{element_id}"' in html
    assert "加速站只做前缀代理" in html
    assert 'data-i18n-placeholder="mirrorAddPlaceholder"' in html
    assert 'apiGet("mirrors")' in js
    assert 'apiPost("mirrors/benchmark", {})' in js
    assert 'apiPost("config", { github_mirror: mirror })' in js
    assert (
        'apiPost("config", { github_mirror_candidates: candidates.join("\\n") })' in js
    )
    # 单选 + 延迟展示 + 自定义增删必须同时存在。
    assert 'type="radio" name="mirror-choice"' in js
    assert "function mirrorLatencyLabel(url)" in js
    assert 'data-mirror-remove="${escapeHtml(url)}"' in js
    assert "async function addCustomMirror(event)" in js
    assert "async function removeCustomMirror(mirror)" in js
    assert "function isValidMirror(value)" in js
    assert 'url.protocol === "https:"' in js
    assert ".mirror-list" in css
    assert ".mirror-item" in css


def test_mirror_tab_escapes_interpolated_values_and_shares_i18n_keys():
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    mirror_block = js[
        js.index("function mirrorRow(url, selected, builtin)") : js.index(
            "async function loadMirrors()"
        )
    ]
    # 所有插值都必须过 escapeHtml，绝不能把加速站 URL 直接拼进 innerHTML。
    for fragment in (
        "${escapeHtml(url)}",
        '${escapeHtml(t("mirrorRemove"))}',
        '${escapeHtml(t("mirrorApply"))}',
        "${escapeHtml(mirrorLatencyLabel(url))}",
    ):
        assert fragment in mirror_block
    assert "${url}" not in mirror_block
    zh_block = js[js.index('"zh-CN": {') : js.index('"en-US": {')]
    en_block = js[js.index('"en-US": {') :]
    mirror_keys = (
        "mirrors:",
        "mirrorsTitle:",
        "mirrorsHint:",
        "mirrorDirect:",
        "mirrorBuiltin:",
        "mirrorCustom:",
        "mirrorBenchmark:",
        "mirrorBenchmarking:",
        "mirrorBenchmarkDone:",
        "mirrorLatency:",
        "mirrorUnreachable:",
        "mirrorUntested:",
        "mirrorApply:",
        "mirrorApplied:",
        "mirrorAddTitle:",
        "mirrorAddPlaceholder:",
        "mirrorAdd:",
        "mirrorAdded:",
        "mirrorInvalid:",
        "mirrorDuplicate:",
        "mirrorRemove:",
        "mirrorRemoved:",
        "mirrorProbeHint:",
    )
    for key in mirror_keys:
        assert key in zh_block, key
        assert key in en_block, key
    assert "GitHub mirror acceleration" in en_block
    assert "镜像不可用会自动回退直连" in zh_block
    # 测速期间必须禁用按钮并展示进行中文案，避免重复并发测速。
    assert "if (state.mirrorBusy) return;" in js
    assert 'state.mirrorBusy ? t("mirrorBenchmarking") : t("mirrorBenchmark")' in js
    assert (
        'document.getElementById("mirror-benchmark").addEventListener("click", benchmarkMirrors)'
        in js
    )
    # 自定义输入框的占位文案同样跟随语言切换。
    assert "[data-i18n-placeholder]" in js
    assert "t(node.dataset.i18nPlaceholder)" in js
    resilient_refresh = js[
        js.index("const sectionLoaders") : js.index("function showStartupError")
    ]
    assert "load: loadMirrors" in resilient_refresh
    assert "Promise.allSettled" in resilient_refresh


def test_manager_page_has_resilient_accessible_loading_and_bounded_logs():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    css = (PAGES_DIR / "style.css").read_text(encoding="utf-8")
    readme = (PLUGIN_ROOT / "README.md").read_text(encoding="utf-8")

    assert 'role="tablist"' in html
    assert 'aria-selected="true"' in html
    assert 'aria-controls="logs"' in html
    assert 'aria-labelledby="tab-logs"' in html
    assert 'data-i18n-aria-label="languageLabel"' in html
    for key in ("ArrowLeft", "ArrowRight", "Home", "End"):
        assert f'event.key === "{key}"' in js
    assert "matchingEvents.slice(-500)" in js
    assert "window.setTimeout(renderDiagnostics, 200)" in js
    assert "if (membersChanged || eventsChanged) renderDiagnostics();" in js
    assert 'data-retry-section="${escapeHtml(name)}"' in js
    assert 'event.target.closest("[data-retry-section]")' in js
    assert "async function refreshPage(button)" in js
    assert "button:disabled" in css
    assert ".section-load-error" in css
    assert "flex-wrap:wrap" in css
    assert "一次最多渲染最近 500 条" in readme
    assert "其余区域继续可用" in readme


def test_recommendation_version_error_has_no_empty_separator():
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    block = js[
        js.index("function versionError") : js.index("function renderRateLimitNotice")
    ]
    assert '[reason, ...details].filter(Boolean).join(" · ")' in block
    assert '${escapeHtml(reason)} · ${escapeHtml(details.join(" · "))}' not in block


def test_manager_page_is_responsive_and_accessible():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    css = (PAGES_DIR / "style.css").read_text(encoding="utf-8")
    assert 'name="viewport"' in html
    assert 'aria-live="polite"' in html
    assert "@media (max-width:760px)" in css
    assert "prefers-reduced-motion" in css
    assert "transition:transform 140ms var(--ease-out)" in css
    assert "button:active:not(:disabled)" in css
    assert "@media (hover:hover) and (pointer:fine)" in css
    assert "transition:.2s" not in css


def test_control_center_has_login_only_and_trusted_module_ui():
    directory = PLUGIN_ROOT / "webui"
    html = (directory / "index.html").read_text(encoding="utf-8")
    js = (directory / "app.js").read_text(encoding="utf-8")
    css = (directory / "style.css").read_text(encoding="utf-8")
    assert "/api/plugin/page/bridge-sdk.js" not in html
    assert "login-form" in js
    assert "不提供注册入口" in js
    assert "注册账户" not in js
    assert 'get("modules")' in js
    assert 'post("diagnostics"' in js
    assert "source=registry_and_qsbb_repository" not in js
    assert "@media(max-width:720px)" in css
    assert "@media (min-width:721px){.mobile-nav{display:none!important}}" in css


def test_manager_page_exposes_dashboard_protected_admin_management():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    assert 'id="webui-admin-create-form"' in html
    assert 'apiGet("webui/admins")' in js
    assert 'apiPost("webui/admins/create"' in js
    assert 'apiPost("webui/admins/update"' in js
    assert 'apiPost("webui/start"' in js
    assert 'id="webui-address"' in html
    assert 'window.open("about:blank", "_blank")' in js
    assert "renderWebUiAddress(data)" in js


def test_manager_page_exposes_copy_and_direct_open_webui_actions():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    css = (PAGES_DIR / "style.css").read_text(encoding="utf-8")
    assert 'id="copy-webui"' in html
    assert 'id="open-webui-direct"' in html
    assert 'data-i18n="copyWebUiLink"' in html
    assert 'data-i18n-aria-label="webuiActionsLabel"' in html
    assert ".webui-address-row" in css
