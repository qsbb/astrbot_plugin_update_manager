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
    assert 'src="./app.js?v=' in html
    assert html.index("bridge-sdk.js") < html.index("./app.js")
    assert 'data-tab="overview"' in html
    assert 'data-tab="modules"' in html
    assert 'data-tab="recommendations"' not in html
    assert 'data-tab="settings"' in html
    assert 'data-tab="config"' not in html
    assert 'data-tab="mirrors"' not in html
    assert 'data-tab="catalog"' not in html
    assert 'data-tab="logs"' in html
    assert 'id="tab-overview" class="active" role="tab"' in html
    assert 'id="tab-logs" role="tab" aria-selected="false"' in html
    assert 'id="overview" class="panel active" role="tabpanel"' in html
    assert 'id="logs" class="panel" role="tabpanel"' in html
    assert html.index('data-tab="overview"') < html.index('data-tab="logs"')
    assert 'id="startup-error"' in html
    assert 'role="alert"' in html
    assert '"zh-CN"' in js and '"en-US"' in js
    assert "async function resolveBridge" in js
    assert "waitForAstrBotBridge" in js


def test_standalone_webui_has_clickable_views_and_model_routing():
    js = (PLUGIN_ROOT / "webui" / "app.js").read_text(encoding="utf-8")
    css = (PLUGIN_ROOT / "webui" / "style.css").read_text(encoding="utf-8")
    for view in (
        "modules",
        "control",
        "recommendations",
        "rules",
        "mirrors",
        "diagnostics",
        "updates",
        "settings",
        "security",
    ):
        assert f'"{view}"' in js
    assert 'document.querySelectorAll("[data-view]")' in js
    assert 'get("model-routing")' in js
    assert 'post("diagnostics", {})' in js
    assert "module-button" in js and ".module-button" in css
    assert "detail-grid" in js and ".detail-grid" in css
    for endpoint in (
        'get("rules")',
        'post("rules", payload)',
        'get("mirrors")',
        'post("mirrors/benchmark", { mirrors: urls })',
        'get("recommendations")',
        'post("recommendations/check", {})',
        'post("recommendations/apply-all", { confirm: true })',
        'get("admins")',
        'post("admins/create", { username, password, role })',
        'post("admins/update", payload)',
    ):
        assert endpoint in js
    assert "完整配置" in js
    assert "data-setting-key" in js


def test_standalone_webui_control_console_takes_over_series_plugins():
    """系列接管管理台：字段接管表单、插件面板、生命周期三区齐全。"""
    js = (PLUGIN_ROOT / "webui" / "app.js").read_text(encoding="utf-8")
    css = (PLUGIN_ROOT / "webui" / "style.css").read_text(encoding="utf-8")
    # 模块级视图内嵌进能力详情：本能力字段 / 全部字段 / 插件面板 / 生命周期
    assert '[["fields", "本能力字段"], ["all", "全部字段"], ["panels", "插件面板"], ["lifecycle", "生命周期"]]' in js
    assert "data-cap-tab" in js
    assert "function capabilityProviderHead(" in js
    assert "function capabilityPanelsTab(" in js
    assert "function capabilityLifecycleTab(" in js
    assert "async function openModuleInControl(" in js
    # 独立的模块详情页已删除（不再有两个页面来回跳）
    assert "function controlDetail()" not in js
    assert "data-control-tab" not in js
    assert "close-control-detail" not in js
    # 字段接管：可编辑表单 + validate/apply + 重置 + revision 乐观锁
    assert "function controlFieldsTab" in js
    assert "function collectControlPatch" in js
    assert "async function applyControlPatch" in js
    assert "async function resetControlFields" in js
    assert "/control/validate" in js
    assert "/control/apply" in js
    assert "/control/reset" in js
    assert "expected_revision" in js
    assert 'data-control-field' in js
    # 插件面板：series.webui 契约分发 + 通用渲染 + 动作
    assert "async function loadCapPanels(" in js
    assert "async function loadCapPanelData(" in js
    assert "async function runPanelAction" in js
    assert "/panels" in js
    assert "/actions/" in js
    assert "function panelContent" in js
    assert "payload_fields" in js
    assert "result.artifacts" in js and "result.audio?.artifact_id" in js
    assert "function actionAllowed" in js and "data-field-type" in js
    assert 'field.type === "textarea"' in js and "field.multiple" in js
    assert 'data-panel-select' in js and 'data-panel-action' in js
    # 生命周期：owner 门控 + 确认 + force 选项
    assert "async function runLifecycle" in js
    assert "/lifecycle/" in js
    assert 'data-lifecycle="update"' in js
    assert 'data-lifecycle="disable"' in js
    assert "lifecycle-force" in js
    assert 'role !== "owner"' in js
    # 生命周期走核事务路径提示，更新视图跳转接管台
    assert "前往接管台" in js
    assert "data-control-open" in js
    # 样式支撑
    for cls in (".tab-strip", ".form-row", ".panel-nav", ".panel-actions", ".pill.managed"):
        assert cls in css


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
    assert "pruneForMembers" in js
    assert "mergeLogEvents" in js
    assert "deriveCursors" in js
    assert 'apiPost("diagnostics/clear", { confirm: true })' in js
    assert "startDiagnosticPolling" in js
    assert "stopDiagnosticPolling" in js
    assert "state.diagnosticPaused" in js
    assert "state.diagnosticGeneration" in js
    assert "state.diagnosticRefreshPending" in js
    assert "diagnosticDisabled" in js
    assert "diagnosticUnavailable" in js
    assert "generation !== state.diagnosticGeneration" in js
    assert "pruneForMembers" in js
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
    # 沙箱页禁用 localStorage：死持久化链已删除，语言选择仅会话内生效
    assert "readStoredLocale" not in js
    assert "storeLocale" not in js
    assert "catch (error)" in js
    assert "function showStartupError(error)" in js
    assert 'document.getElementById("startup-error")' in js
    assert "init().catch(showStartupError);" in js
    assert 'locale: "zh-CN"' in js
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
    assert "未加载的插件不可更新" in html
    assert "Unloaded plugins cannot be updated" in js
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
    # 标签切换不触发任何远端版本探测；推荐和目录都由明确按钮触发。
    tab_handler = js.split('document.querySelectorAll("[data-tab]")', 1)[1].split(
        "config-form", 1
    )[0]
    assert "autoCheckRecommendations" not in tab_handler
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
    assert 'checkUpdates: "Check catalog updates"' in js


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
    # 实现细节元注释已按审查结论删除
    assert "不会额外重复重载" not in html


def test_recommendations_tab_does_not_start_implicit_network_check():
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    # 推荐列表切换只读本地状态；远端检查必须由用户明确点击按钮触发。
    assert (
        "async function loadRecommendations(check = false, forceRefresh = true)" in js
    )
    assert "versionCheckBusy: false" in js
    assert "async function autoCheckRecommendations()" not in js
    tab_handler = js[
        js.index('document.querySelectorAll("[data-tab]")') : js.index(
            'document.getElementById("config-form")'
        )
    ]
    assert 'button.dataset.tab === "recommendations"' not in tab_handler
    assert "autoCheckRecommendations()" not in tab_handler


def test_manager_settings_area_uses_four_sub_tabs():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    css = (PAGES_DIR / "style.css").read_text(encoding="utf-8")

    assert 'id="tab-settings"' in html
    assert 'id="settings" class="panel" role="tabpanel"' in html
    assert html.count("data-si-tab=") == 4
    for tab in ("config", "auto", "accounts", "mirrors"):
        assert f'data-si-tab="{tab}"' in html
        assert f'data-si-panel="{tab}"' in html
    # 四个分区各自保留原有表单与列表 id，不改变保存/加载接口
    for element_id in ("config-form", "rule-form", "webui-admins", "mirror-list", "mirror-add-form"):
        assert f'id="{element_id}"' in html
    # 旧顶层 tab 已合并
    assert 'data-tab="config"' not in html
    assert 'data-tab="mirrors"' not in html

    assert "function bindSettingsSubnav()" in js
    assert 'state.settingsTab = target;' in js
    assert "async function loadSettingsPanel()" in js
    assert 'settings: { targetId: "config-fields", labelKey: "settings", load: loadSettingsPanel },' in js
    assert 'if (button.dataset.tab === "settings" && !state.settingsLoaded) {' in js
    assert 'settings: "设置"' in js
    assert "#settings [data-si-panel] > * + *" in css
    assert "#settings [data-si-panel][hidden]" in css


def test_manager_merges_recommendations_and_catalog_into_one_tab():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")

    assert 'id="tab-modules"' in html
    assert 'id="modules" class="panel" role="tabpanel"' in html
    assert 'id="module-scope"' in html
    assert 'id="module-search"' in html
    assert 'id="module-scope-summary"' in html
    assert 'data-module-scope-card="series"' in html
    assert 'data-module-scope-card="catalog"' in html
    assert 'id="recommendations-list"' in html
    assert 'id="catalog-list"' in html
    # 两个旧面板不再存在，避免同一插件两套版本信息
    assert 'id="catalog" class="panel"' not in html
    assert 'id="recommendations" class="panel"' not in html

    assert "function applyModuleScope()" in js
    assert "scope === \"series\"" in js
    assert "scope === \"catalog\"" in js
    assert 'scope !== "updates" || item.dataset.updateAvailable === "true"' in js
    assert "async function loadModules()" in js
    assert "state.recommendationItems = items;" in js
    assert "const recommended = new Set((state.recommendationItems || []).map((item) => item.plugin_id));" in js
    assert 'data-update-available="${String(Boolean(item.update_available))}"' in js
    assert 'modules: { targetId: "recommendations-list", labelKey: "modules", load: loadModules },' in js
    assert 'modules: "推荐与目录"' in js
    assert 'if (button.dataset.tab === "modules")' in js


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
    assert "state.autoVersionCheckDone" not in manual
    assert 'setVersionCheckBusy("checkingLatest")' in manual
    assert "await loadRecommendations(true);" in manual
    assert "clearVersionCheckBusy();" in manual
    # 版本检查不得抢走推荐操作的状态条。
    assert "if (status && !state.recommendationBusy) status.hidden = true;" in js
    assert "autoCheckingLatest" not in js


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
    assert "核禁止自更新，请前往已安装插件页更新" in js
    assert 'goToInstalledPlugins: "前往已安装插件页"' in js
    assert ".self-update-notice" in css


def test_mobile_self_update_prefers_bridge_then_top_level_dashboard_route():
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    helper = js[
        js.index("async function invokeBridgeNavigation") : js.index("function applyI18n")
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


def test_restricted_host_reveals_and_copies_update_page_url_without_prompt_fallback():
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    css = (PAGES_DIR / "style.css").read_text(encoding="utf-8")
    fallback = js[
        js.index("function revealInstalledPageUrl") : js.index("function applyI18n")
    ]

    assert 'link.closest(".self-update-notice")' in fallback
    assert 'fallback.className = "installed-page-url-fallback"' in fallback
    assert 'fallback.textContent = `${t("installedPageUrlLabel")}：${url}`' in fallback
    assert "function legacyCopyText" in fallback
    assert 'document.execCommand("copy")' in fallback
    assert "async function copyText" in fallback
    assert 'notify(t("installedPageUrlCopied"))' in fallback
    assert "window.prompt" not in fallback
    assert ".installed-page-url-fallback" in css
    assert "user-select:all" in css


def test_recommendation_cards_confirm_only_destructive_actions_and_show_progress():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    css = (PAGES_DIR / "style.css").read_text(encoding="utf-8")
    assert "item.description_zh" in js
    assert "window.SeriesUI.confirm" in js
    assert "showConfirmation(" in js
    assert 'id="recommendation-status"' in html
    assert "const confirmed = !requiresConfirmation" in js
    assert "await confirmRecommendationAction(action, pluginName)" in js
    assert "input[role='switch']" in js
    assert "item.disabled = true" in js
    assert 'setRecommendationBusy(force ? "forceUpdate" : action, pluginName)' in js
    assert "clearRecommendationBusy()" in js
    assert ".recommendation-description" in css
    assert ".operation-status" in css


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
    assert "该策略只做检查与记录，绝不会更新插件" in html
    assert "仅检查（不更新）" in html
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
        save_rule.index("} else {") : save_rule.index('notify(t("ruleSaved"))')
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
    assert "未加载的插件不可更新" in html
    assert "Unloaded plugins cannot be updated" in js
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
        "settingsMirrorsTab:",
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
    # 镜像与网络现在是「设置」下的子分区，随设置区一起加载。
    assert "load: loadSettingsPanel" in resilient_refresh
    assert 'loadOnce("config", loadConfig)' in js
    assert 'loadOnce("rule", loadRule)' in js
    assert 'loadOnce("mirrors", loadMirrors)' in js
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
    assert "if (result.changed || previousCatchUp !== state.diagnosticCatchUp) renderDiagnostics();" in js
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
    assert "transition:transform 140ms var(--ease-out)" not in css
    assert "button:active:not(:disabled)" not in css
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
    assert '<p data-toast-fallback' in html
    assert ".toast{position:fixed;right:22px;bottom:22px" not in css


def test_control_center_export_uses_document_download_lifecycle():
    js = (PLUGIN_ROOT / "webui" / "app.js").read_text(encoding="utf-8")
    export_block = js[
        js.index("function exportSummary") : js.index("async function loadDashboard")
    ]
    assert "SeriesUI.downloadJson" in export_block


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
    css = (PAGES_DIR / "style.css").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    assert 'id="copy-webui"' in html
    assert 'id="open-webui"' in html
    assert 'data-i18n="copyWebUiLink"' in html
    # 地址行的第二个打开按钮已收敛为头部单一入口
    assert ".webui-address-row" in css
    assert 'id="webui-manual"' in html
    assert 'id="webui-manual-url"' in html
    assert 'id="webui-open-frame"' in html
    assert "function legacyCopyText" in js
    assert "function openStandaloneWebUiInFrame" in js
    assert "window.location.assign(url)" in js
    assert "if (openStandaloneWebUiInFrame()) return;" in js
    assert "function revealWebUiUrl" in js
    assert "openWebUiBlocked" in js
    assert ".webui-manual" in css
    assert ".hero { flex-wrap:wrap; }" in css
    assert ".hero > div:first-child" in css


def test_webui_control_plugin_loads_panels_independently():
    """插件面板不应因缺少 series.control 而不可达。"""
    js = (PLUGIN_ROOT / "webui" / "app.js").read_text(encoding="utf-8")
    assert "function capPanelStore(" in js
    assert "async function loadCapPanels(" in js
    assert "const first = (store.list?.panels || [])[0]" in js
    assert "await loadCapPanelData(pluginId, first.id)" in js
    assert "data-cap-panels-load" in js
    # 没有字段契约时，插件面板与生命周期仍可达（按页签独立加载）
    assert 'if (tab === "panels") return shell(capabilityPanelsTab(provider.plugin_id));' in js
    assert 'if (tab === "lifecycle") return shell(capabilityLifecycleTab(provider.plugin_id));' in js
    assert "contract_details?.webui_panels" in js


def test_manager_page_exposes_unified_model_routing_fields():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    assert 'id="config-fields"' in html
    assert 'key === "model_routing" && field.type === "object"' in js
    assert "data-model-kind" in js
    assert "插件显式配置优先" in js


def test_standalone_webui_has_working_diagnostics_updates_settings():
    """用户视角可用性：诊断日志、更新检查/回滚、设置编辑三条链路齐全。"""
    js = (PLUGIN_ROOT / "webui" / "app.js").read_text(encoding="utf-8")
    # 诊断：游标续读 + 级别过滤 + 自动刷新 + 清空
    assert "diagnostics/logs" in js
    assert "diagnostics/clear" in js
    assert "logCursors" in js and "deriveCursors" in js
    assert 'id="log-level"' in js and 'id="log-auto"' in js
    assert 'id="log-search"' in js and 'id="log-range"' in js
    assert "diagnosticProblems" in js and "diagnosticEvents" in js
    assert "diagnostic-event" in js and "log-detail-list" in js
    assert "data-log-module" in js and "data-log-problem" in js
    assert 'get("model-options")' in js
    assert "data-route-provider" in js and "data-route-model" in js
    assert "kind === \"tts\"" in js
    # 更新：真实检查更新 + 恢复点回滚
    assert "updates/check" in js
    assert "updates/transactions" in js
    assert "updates/rollback" in js
    assert "data-rollback" in js
    assert "async function checkUpdates" in js
    # 设置：模型路由编辑 + 白名单字段保存
    assert "data-setting-route" in js
    assert "async function saveSettings" in js
    assert 'post("settings"' in js
    # 模块列表不再伪造检查结果
    assert 'id="check"' in js
    assert "version_status === \"not_checked\"" in js


def test_series_control_is_capability_first_not_plugin_cards():
    """能力优先：接管页按功能域与能力组织，不铺开插件身份。"""
    js = (PLUGIN_ROOT / "webui" / "app.js").read_text(encoding="utf-8")
    css = (PLUGIN_ROOT / "webui" / "style.css").read_text(encoding="utf-8")

    # 不再有写死的"一插件一张卡"目录
    assert "const FEATURE_DOMAINS = [" not in js
    # 目录来自核侧能力目录（state.control.capabilities）
    assert "state.control?.capabilities" in js
    assert "function controlCatalog()" in js
    assert "function capabilitiesOfDomain(" in js
    assert "function capabilityStatus(" in js
    assert "function domainStatus(" in js
    assert "function capabilityDetail(" in js
    assert "async function loadCapability(" in js
    # D3.1 主从结构：左域列表 + 右能力网格
    assert "function masterDetail(" in js
    assert "function domainItem(" in js
    assert "function capabilityCard(" in js
    # D3.1 三行卡：状态徽标 / 能力名 / 动作 / 描述 / 元信息
    assert "function capabilityBadge(" in js
    assert "function capabilityMetaText(" in js
    assert "function sortCapabilities(" in js
    assert "function capabilityNeedsAttention(" in js
    assert '"正常"' in js and '"核自带"' in js
    assert "设置 ›" in js and "打开 ›" in js
    assert "项可调" in js
    # 盲测批评的旧文案必须消失
    assert "来源 ${providerNames.length} 个模块" not in js
    # 交互入口：域 → 能力 → 设置
    assert "data-catalog-domain-open=" in js
    assert "data-capability-open=" in js
    assert "status-legend" in js
    # 复评修正：域行状态文字 + 能力区头部（异常优先标识）
    assert 'class="domain-state' in js
    assert "function capabilityCard(" in js
    assert 'class="capability-head"' in js
    assert "异常优先 ▾" in js
    # 能力级状态与 D3.1 布局样式
    assert ".status-dot" in css
    assert ".capability-row" not in css
    assert ".control-mode-line" in css
    assert ".capability-provider" in css
    assert ".master-detail" in css
    assert ".domain-item" in css
    assert ".capability-card" in css
    assert ".cap-badge" in css
    assert ".cap-card-meta" in css
    assert "@media (max-width:1120px)" in css
    assert "@media (max-width:620px)" in css


def test_capability_cards_expose_inline_master_switch():
    """能力卡片把「主开关」直接放出来，不必点进详情；卡片本体不再是 button。"""
    js = (PLUGIN_ROOT / "webui" / "app.js").read_text(encoding="utf-8")
    css = (PLUGIN_ROOT / "webui" / "style.css").read_text(encoding="utf-8")

    assert "function capabilitySwitchSpec(" in js
    assert "provider.switch_field" in js
    assert "function capabilitySwitchState(" in js
    assert "function capabilitySwitchHtml(" in js
    assert "provider.switch_label" in js
    assert "data-cap-switch-field=" in js
    assert "data-cap-switch-plugin=" in js
    assert "async function ensureCapabilitySwitchData(" in js
    assert "async function applyCapabilitySwitch(" in js
    assert "function refreshCapabilitySwitchData(" in js
    # 卡片开关复用同一套校验 + 覆盖写入接口（带 revision 并发保护）
    assert "/control/validate" in js and "/control/apply" in js
    # 开关不能嵌在 button 里：卡片拆成「标题按钮 + 标题行右侧开关 + 设置行」
    assert '<button class="capability-card"' not in js
    assert 'class="cap-card-open"' in js
    assert 'class="cap-card-head"' in js
    assert "cap-card-open" in css and ".cap-card-head" in css and ".cap-switch" in css
    # 方案 A：开关贴在标题行右侧，文字在左、轨道在右
    assert '<span class="cap-switch-text">' in js
    assert '<span class="cap-switch-text">${esc(label)}</span><input type="checkbox" role="switch"' in js
    # 误触兜底：应用成功后的提示带「撤销」
    assert "async function revertCapabilitySwitch(" in js
    assert 'label: "撤销"' in js
    assert "onClick: () => revertCapabilitySwitch(" in js
    assert "toast-action" in (PLUGIN_ROOT / "ui" / "series-ui.css").read_text(encoding="utf-8")
    # 插件侧模式同步失败要给出中文原因，而不是让整页“读取失败”
    assert "MODE_SYNC_FAILED" in js
    assert '"接管模式同步失败"' in js
    assert "modeError" in js


def test_series_boolean_switches_use_shared_toggle_not_local_checkbox():
    """全系列布尔开关统一走共享滑块开关，页面不再自绘尺寸或自造滑块。"""
    js = (PLUGIN_ROOT / "webui" / "app.js").read_text(encoding="utf-8")
    page_css = (PAGES_DIR / "style.css").read_text(encoding="utf-8")
    webui_css = (PLUGIN_ROOT / "webui" / "style.css").read_text(encoding="utf-8")

    assert 'def.type === "bool") input = `<label class="si-switch">' in js
    assert ".switch input { width:18px;height:18px; }" not in page_css
    assert ".form-input .switch input{width:17px;height:17px}" not in webui_css
    assert ".form-actions .switch input{width:16px;height:16px}" not in webui_css


def test_field_labels_cover_series_plugins_and_never_fall_back_to_placeholder():
    """字段中文名兜底：7 仓 75 个字段都有名字，且不再回退成"配置项"。"""
    js = (PLUGIN_ROOT / "webui" / "app.js").read_text(encoding="utf-8")
    assert "const PLUGIN_FIELD_TEXT = {" in js
    for plugin_id in (
        "astrbot_plugin_active_learner",
        "astrbot_plugin_conversation_flow",
        "astrbot_plugin_identity_guardian",
        "astrbot_plugin_relationship",
        "astrbot_plugin_environment_awareness",
        "astrbot_plugin_voice_hub",
        "astrbot_plugin_embodiment_bridge",
    ):
        assert f'"{plugin_id}": {{' in js, plugin_id
    assert js.count('": [') >= 75
    assert "function pluginFieldText(pluginId, key)" in js
    assert "fieldLabel(name, def, pluginId)" in js
    assert "return humanizeKey(key) || key;" in js
    assert 'return humanizeKey(key) || "配置项"' not in js
    # 来源标签只在核覆盖时出现，避免每行重复"插件"
    assert 'const source = isManaged ? `<span class="pill managed">核覆盖</span>` : "";' in js


def test_settings_route_uses_responsibility_cards_and_safe_fallback():
    """全局设置：模型路由改为职责卡片 + 一键回退 / 导出；当前生效来自解析快照。"""
    js = (PLUGIN_ROOT / "webui" / "app.js").read_text(encoding="utf-8")
    css = (PLUGIN_ROOT / "webui" / "style.css").read_text(encoding="utf-8")
    assert "const routeCards = labels.map(" in js
    assert 'class="route-cards"' in js
    assert "当前生效：" in js
    assert "async function resetAllRoutes(" in js
    assert "function exportRoutes(" in js
    assert 'id="route-reset-all"' in js and 'id="route-export"' in js
    assert ".route-cards" in css and ".route-card" in css and ".route-effective" in css


def test_control_center_mobile_nav_can_reach_every_view():
    js = (PLUGIN_ROOT / "webui" / "app.js").read_text(encoding="utf-8")
    css = (PLUGIN_ROOT / "webui" / "style.css").read_text(encoding="utf-8")

    # 视图注册表是唯一事实源：导航 / 标题 / 渲染 / 进入逻辑都由它驱动
    assert "const VIEWS = {" in js
    assert "const NAV_GROUPS = [" in js
    assert "const NAV_ITEMS = Object.entries(VIEWS).map(" in js
    assert "function railItemsForGroup(" in js
    assert "function suiteTabStrip(" in js
    assert "const VIEW_RENDERERS = {" in js
    assert "const VIEW_ENTERS = {" in js
    assert "async function enterView(" in js
    # 四个导航分组
    for group in ("workbench", "operations"):
        assert f'"{group}"' in js
    # 更新与安装套件：更新与回滚内含推荐 / 规则 / 镜像子页签
    assert 'suite: ["updates", "recommendations", "rules", "mirrors"]' in js
    assert 'inSuite: "updates"' in js
    assert 'tabLabel: "更新与回滚"' in js
    # 账户与安全收进「设置与安全」内部页签，不再占一级入口
    assert 'hidden: true' in js
    assert '!VIEWS[view]?.hidden' in js
    assert 'data-si-tab="security"' in js
    assert "function securityPanel()" in js
    assert "function securityView()" in js
    # 单一分发：点击与刷新都走 enterView，不再各自维护 if 链
    assert 'enterView(node.dataset.view || "modules")' in js
    assert "await enterView(state.view);" in js
    assert 'if (state.view === "control") await loadControl();' not in js

    nav_block = js[js.index('class="mobile-nav"') : js.index("</nav>", js.index('class="mobile-nav"'))]
    assert '["control", "diagnostics", "updates"]' in nav_block
    assert 'id="mobile-more"' in nav_block
    assert 'NAV_ITEMS.filter(([view])' in js
    assert 'data-view="${view}"' in js
    assert 'aria-current="${state.view === view ? "page" : "false"}"' in js
    mobile_css = css[css.index("@media(max-width:720px)") : css.index("@media (min-width:721px)")]
    assert ".mobile-nav{" in mobile_css
    assert "overflow-x:auto" in mobile_css
    assert "flex:0 0 auto" in mobile_css
    assert ".suite-tabs" in css
    # 总览并入「诊断与日志」套件，一级入口从 5 项减到 4 项
    assert 'suite: ["diagnostics", "modules"]' in js
    assert 'tabLabel: "模块总览"' in js
    assert 'modules: { icon: "▦", label: "模块总览"' in js
    assert 'const id = VIEWS[view] ? view : "control";' in js

def test_manager_page_does_not_duplicate_dark_legacy_theme():
    css = (PAGES_DIR / "style.css").read_text(encoding="utf-8")
    assert "color-scheme: dark" not in css
    assert "#102236" not in css
    assert "#26364a" not in css
    assert "var(--surface)" not in css
    assert ".diagnostic-log-list" in css
    assert ".diagnostic-log-detail" in css


def test_control_center_uses_shared_confirmation_component():
    js = (PLUGIN_ROOT / "webui" / "app.js").read_text(encoding="utf-8")
    assert "async function confirmDialog(" in js
    assert "window.SeriesUI.confirm" in js
    assert "!confirm(" not in js
    assert "确认组件未加载，操作已取消" in js


def test_manager_page_uses_shared_confirmation_and_prompt():
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    assert "window.confirm" not in js
    assert "window.prompt" not in js
    assert "window.SeriesUI.confirm" in js
    assert "window.SeriesUI?.prompt" in js


def test_manager_page_style_does_not_duplicate_series_ui_controls():
    css = (PAGES_DIR / "style.css").read_text(encoding="utf-8")
    shared = (PLUGIN_ROOT / "ui" / "series-ui.css").read_text(encoding="utf-8")
    assert ":root {" not in css
    assert "button,select,input" not in css
    assert "dialog::backdrop" not in css
    assert "#toast" not in css
    assert ":where(body[data-series-ui] .card)" in shared
    assert ":where(body[data-series-ui] .modal-card)" in shared
    assert ".diagnostic-log-list" in css
    assert ".diagnostic-log-detail" in css

def test_manager_overview_is_compact_and_consumes_commit_fields():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    css = (PAGES_DIR / "style.css").read_text(encoding="utf-8")
    # 任务A：Hero≈110px；4 KPI + 模块状态表 + 更新队列全部在总览首屏。
    assert "min-height:110px" in css
    assert ".overview-grid" in css
    for element_id in (
        "summary",
        "overview-module-rows",
        "overview-module-count",
        "overview-queue-list",
        "overview-queue-summary",
        "overview-apply-all",
        "overview-check-only",
        "overview-budget",
    ):
        assert f'id="{element_id}"' in html
    assert 'id="tab-overview" class="active" role="tab"' in html
    for label in ("可信模块", "运行正常", "需关注", "有更新"):
        assert label in js
    # 最新提交：防御性消费 Godel 新增字段。
    for field in ("local_commit", "remote_commit", "commit_status", "commit_source"):
        assert field in js
    assert 'status === "different"' in js
    assert 't("overviewCommitUnknown")' in js
    assert "overview-commit empty" in js
    assert "function overviewBudgetText(rate)" in js
    assert "1次/仓 · 条件请求" in js
    assert "overview-queue-item" in js
    assert "content-visibility:auto" in css
    # 静态资源 N+1，不改版本号。
    assert "?v=0.19.11-1" in html


def test_log_views_are_problem_first_with_cursor_catchup_and_export():
    html = (PAGES_DIR / "index.html").read_text(encoding="utf-8")
    js = (PAGES_DIR / "app.js").read_text(encoding="utf-8")
    webui_html = (PLUGIN_ROOT / "webui" / "index.html").read_text(encoding="utf-8")
    webui_js = (PLUGIN_ROOT / "webui" / "app.js").read_text(encoding="utf-8")
    webui_css = (PLUGIN_ROOT / "webui" / "style.css").read_text(encoding="utf-8")
    # 管理页：待处理问题聚合 + 事件流控制条 + 事件 JSON 导出。
    for element_id in (
        "diagnostic-problem-count",
        "diagnostic-autoscroll",
        "diagnostic-export",
    ):
        assert f'id="{element_id}"' in html
    assert "function diagnosticMemberHasMore(member)" in js
    # has_more/truncated 识别已收敛到 series-kernel.js（双前端共用）
    assert "kernel().memberHasMore" in js
    assert "pass >= 4" in js
    assert "function exportDiagnostics()" in js
    assert "diagnosticShowing" in js
    # 独立 WebUI：问题优先、暂停/自动滚动、导出、按 plugin_id:seq 去重、has_more 追平。
    for element_id in ("log-pause", "log-autoscroll", "log-export", "log-summary"):
        assert f'id="{element_id}"' in webui_js
    assert "function logMemberHasMore(member)" in webui_js
    assert "SeriesKernel.memberHasMore" in webui_js
    assert "state.logBusy" in webui_js
    # 去重与 3000 条上限已收敛进 series-kernel 的 mergeLogEvents
    assert "mergeLogEvents" in webui_js
    assert "pass >= 4" in webui_js
    assert "function exportDiagnosticLogs()" in webui_js
    assert "level-chip.level-error" in webui_css
    assert "level-chip.level-critical" in webui_css
    assert "max-height:62vh" in webui_css
    assert "?v=0.19.11-1" in webui_html
