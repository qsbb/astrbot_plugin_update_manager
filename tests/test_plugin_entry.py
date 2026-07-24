from __future__ import annotations

import asyncio
import importlib
import sys
import types
from pathlib import Path
from types import SimpleNamespace

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT.parent))


class Logger:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class CommandGroupDecorator:
    def __call__(self, func):
        func.command = lambda _name: lambda child: child
        return func


def passthrough_decorator(*args, **kwargs):
    return lambda func: func


def install_astrbot_api_stubs(monkeypatch):
    astrbot = types.ModuleType("astrbot")
    api = types.ModuleType("astrbot.api")
    event = types.ModuleType("astrbot.api.event")
    star = types.ModuleType("astrbot.api.star")

    class Star:
        def __init__(self, context):
            self.context = context

    event.AstrMessageEvent = object
    event.filter = SimpleNamespace(
        PermissionType=SimpleNamespace(ADMIN="admin"),
        permission_type=passthrough_decorator,
        command_group=lambda _name: CommandGroupDecorator(),
    )
    star.Context = object
    star.Star = Star
    star.register = passthrough_decorator
    api.logger = Logger()
    api.event = event
    api.star = star
    astrbot.api = api
    for name, module in {
        "astrbot": astrbot,
        "astrbot.api": api,
        "astrbot.api.event": event,
        "astrbot.api.star": star,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)


def import_main(monkeypatch):
    install_astrbot_api_stubs(monkeypatch)
    sys.modules.pop("astrbot_plugin_update_manager.main", None)
    return importlib.import_module("astrbot_plugin_update_manager.main")


def context(tmp_path):
    return SimpleNamespace(
        get_all_stars=lambda: [],
        cron_manager=None,
        version="4.26.4",
        get_plugin_data_dir=lambda name: tmp_path / name,
    )


def test_entry_identity_defaults_and_data_location(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    assert module.PLUGIN_NAME == "astrbot_plugin_update_manager"
    assert module.__version__ == "0.5.0"
    assert plugin.enabled is True and plugin.auto_update_enabled is False
    assert plugin.store.root == (tmp_path / module.PLUGIN_NAME).resolve()


def test_input_validation_and_rule_default_off(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    assert plugin._parse_ids("a,b,a") == ("a", "b")
    for value in ("", "../x", "a/b"):
        try:
            plugin._parse_ids(value)
            assert False
        except ValueError:
            pass
    assert plugin.scheduler.load().enabled is False


def test_commands_and_terminate_cleanup(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {})
    event = SimpleNamespace(plain_result=lambda text: text)

    async def collect(generator):
        return [item async for item in generator]

    probe = asyncio.run(collect(plugin.aup_probe(event)))[0]
    catalog = asyncio.run(collect(plugin.aup_catalog(event)))[0]
    cancel = asyncio.run(collect(plugin.aup_cancel(event)))[0]
    assert "能力探针" in probe and "插件目录（0 项）" in catalog
    assert "事务边界" in cancel
    asyncio.run(plugin.initialize())
    asyncio.run(plugin.terminate())
    assert (
        plugin._terminated
        and plugin.adapter is None
        and module._current_instance is None
    )


def _load_metadata():
    import yaml

    text = (PLUGIN_ROOT / "metadata.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(text)


def test_metadata_contract_matches_code(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    meta = _load_metadata()
    assert meta["name"] == module.PLUGIN_NAME
    assert meta["name"].startswith("astrbot_plugin_")
    assert str(meta["version"]) == module.__version__
    assert meta["author"] == "Justice-ocr"
    assert meta["repo"].startswith("https://github.com/")
    assert meta["repo"].endswith("/" + module.PLUGIN_NAME)
    assert not meta["repo"].endswith(".git")
    # 目录名必须与内部标识一致。
    assert PLUGIN_ROOT.name == module.PLUGIN_NAME


def test_conf_schema_every_field_has_type_desc_default():
    import json

    schema = json.loads((PLUGIN_ROOT / "_conf_schema.json").read_text(encoding="utf-8"))
    assert schema  # 非空
    for key, field in schema.items():
        assert "type" in field, f"{key} 缺少 type"
        assert "description" in field, f"{key} 缺少 description"
        assert "default" in field, f"{key} 缺少 default"


def test_string_bool_and_custom_config_values(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    config = {
        "enabled": "false",
        "auto_update_enabled": "yes",
        "data_dir": str(tmp_path / "custom"),
        "network_timeout_seconds": 42,
        "cache_ttl_seconds": 120,
        "proxy": "http://127.0.0.1:8080",
    }
    plugin = module.UpdateManagerPlugin(context(tmp_path), config)
    assert plugin.enabled is False
    assert plugin.auto_update_enabled is True
    # 自定义 data_dir 应生效并追加插件名。
    assert plugin.store.root == (tmp_path / "custom" / module.PLUGIN_NAME).resolve()
    # 自定义网络配置应传入 registry。
    assert plugin.registry.timeout.total == 42
    assert plugin.registry.cache_ttl == 120
    assert plugin.registry.proxy == "http://127.0.0.1:8080"


def test_disabled_config_gates_all_commands(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {"enabled": False})
    event = SimpleNamespace(plain_result=lambda text: text)

    async def first(generator):
        async for item in generator:
            return item
        return None

    invocations = [
        plugin.aup_probe(event),
        plugin.aup_catalog(event),
        plugin.aup_plan(event, "demo"),
        plugin.aup_run(event, "0" * 8),
        plugin.aup_rule(event, "show"),
        plugin.aup_dryrun(event, "demo"),
        plugin.aup_rollback(event, "demo"),
        plugin.aup_cancel(event),
        plugin.aup_status(event),
    ]
    for gen in invocations:
        message = asyncio.run(first(gen))
        assert message is not None and "enabled=false" in message
    # enabled=false 时不应在事务边界请求取消。
    assert plugin.coordinator._cancelled is False


def test_disabled_initialize_skips_scheduler(monkeypatch, tmp_path):
    module = import_main(monkeypatch)
    plugin = module.UpdateManagerPlugin(context(tmp_path), {"enabled": False})
    # initialize 在禁用时应直接返回，不抛异常。
    asyncio.run(plugin.initialize())
    assert plugin.scheduler.load().enabled is False
