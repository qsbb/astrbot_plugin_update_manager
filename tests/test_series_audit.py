"""系列审计脚本的只读回归测试。"""

from __future__ import annotations

import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1].parent))

from astrbot_plugin_update_manager.core.series_audit import (
    _code_version,
    audit,
)


def _write_registry(root: pathlib.Path, contracts: list[dict]) -> pathlib.Path:
    path = root / "contracts.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "series_id": "ningxin_suxi",
                "members": [
                    {
                        "plugin_id": "astrbot_plugin_fake",
                        "alias": "假",
                        "version_source": "main.py:__version__",
                        "local_required": True,
                    }
                ],
                "contracts": contracts,
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def test_code_version_reads_literal_assignment(tmp_path):
    path = tmp_path / "main.py"
    path.write_text('__version__ = "1.2.3"\n', encoding="utf-8")
    assert _code_version(tmp_path, "main.py:__version__") == "1.2.3"


def test_audit_reports_version_drift_and_contract_missing(tmp_path):
    repo = tmp_path / "astrbot_plugin_fake"
    repo.mkdir()
    (repo / "metadata.yaml").write_text("version: 1.0.0\n", encoding="utf-8")
    (repo / "CHANGELOG.md").write_text("# 更新日志\n\n## 0.9.0 - 2026-01-01\n", encoding="utf-8")
    (repo / "main.py").write_text(
        '__version__ = "1.0.0"\n\n\nclass FakePlugin:\n    pass\n',
        encoding="utf-8",
    )
    registry = _write_registry(
        tmp_path,
        [
            {
                "name": "series.diagnostics",
                "version": "1.0",
                "provider": "*",
                "method": "diagnostic_log_contract",
                "required": True,
            }
        ],
    )

    report = audit(tmp_path, registry)

    assert any("version drift" in warning for warning in report["warnings"])
    assert report["contracts"]["series.diagnostics"]["missing"] == ["astrbot_plugin_fake"]
    assert report["errors"]


def test_audit_detects_request_context_hash_mismatch(tmp_path):
    for name, content in (
        ("astrbot_plugin_a", "A = 1\n"),
        ("astrbot_plugin_b", "B = 2\n"),
    ):
        repo = tmp_path / name
        repo.mkdir()
        (repo / "request_context.py").write_text(content, encoding="utf-8")
    registry = _write_registry(tmp_path, [])

    report = audit(tmp_path, registry)

    assert report["request_context"]["consistent"] is False
    assert any("request_context hash mismatch" in error for error in report["errors"])


def test_audit_flags_json_style_python_literals(tmp_path):
    repo = tmp_path / "astrbot_plugin_fake"
    repo.mkdir()
    (repo / "metadata.yaml").write_text("version: 1.0.0\n", encoding="utf-8")
    (repo / "CHANGELOG.md").write_text("# 更新日志\n\n## 1.0.0 - 2026-01-01\n", encoding="utf-8")
    (repo / "main.py").write_text(
        '__version__ = "1.0.0"\n\n\ndef contract():\n    return {"available": true}\n',
        encoding="utf-8",
    )
    registry = _write_registry(tmp_path, [])

    report = audit(tmp_path, registry)

    assert any("JSON-style Python literals" in error for error in report["errors"])


def test_audit_validates_flow_contract_references(tmp_path):
    repo = tmp_path / "astrbot_plugin_fake"
    repo.mkdir()
    (repo / "metadata.yaml").write_text("version: 1.0.0\n", encoding="utf-8")
    (repo / "CHANGELOG.md").write_text("# 更新日志\n\n## 1.0.0 - 2026-01-01\n", encoding="utf-8")
    (repo / "main.py").write_text('__version__ = "1.0.0"\n', encoding="utf-8")
    registry = _write_registry(
        tmp_path,
        [
            {
                "name": "environment.opportunity",
                "version": "1.0",
                "provider": "astrbot_plugin_fake",
                "method": "environment_opportunity_contract",
                "required": True,
            }
        ],
    )
    import yaml

    data = yaml.safe_load(registry.read_text(encoding="utf-8"))
    data["flows"] = [
        {
            "name": "series.test_flow",
            "version": "1.0",
            "steps": [
                {"order": 1, "contract": "environment.opportunity"},
                {"order": 2, "contract": "missing.contract", "version": "1.0"},
            ],
        }
    ]
    registry.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    report = audit(tmp_path, registry)

    assert report["flows"]["series.test_flow"]["steps"][0]["present"] is True
    assert report["flows"]["series.test_flow"]["missing"] == ["missing.contract@1.0"]
    assert any("flow references missing contracts" in error for error in report["errors"])
