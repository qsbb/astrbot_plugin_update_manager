"""凝心溯溪系列只读审计：契约注册表、版本、request_context 一致性。

设计原则（对抗审查结论）：
- 先做“期望 → 现实”和“现实 → 期望”的观测，不修改任何插件行为；
- 默认 warn-only；只有显式 --strict 才因错误退出 1；
- 审计脚本本身不 import 任何成员插件，不做运行时依赖。
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import pathlib
import re
import sys
from typing import Any

import yaml

from .series_ui import verify as verify_series_ui

IGNORED_REPOS = {"astrbot_plugin_orchestration_hub"}
KERNEL_PLUGIN_ID = "astrbot_plugin_update_manager"
REQUEST_CONTEXT_EXPECTED = 6
_CHANGELOG_RE = re.compile(
    r"^##\s*(?:\[)?v?(\d+\.\d+\.\d+)",
    re.MULTILINE,
)


def _read_yaml(path: pathlib.Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def _metadata_version(repo: pathlib.Path) -> str:
    data = _read_yaml(repo / "metadata.yaml")
    value = data.get("version")
    return str(value).strip() if value is not None else ""


def _changelog_top(repo: pathlib.Path) -> str:
    try:
        text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    except OSError:
        return ""
    match = _CHANGELOG_RE.search(text)
    return match.group(1) if match else ""


def _code_version(repo: pathlib.Path, spec: str) -> str:
    """从 ``file.py:SYMBOL`` 读取版本常量。只认字面量 str 赋值。"""
    if ":" not in spec:
        return ""
    file_name, symbol = spec.split(":", 1)
    path = repo / file_name
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError):
        return ""
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value_node = node.value
        if value_node is None:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id == symbol:
                if isinstance(value_node, ast.Constant) and isinstance(
                    value_node.value, str
                ):
                    return value_node.value.strip()
    return ""


def _contract_methods(repo: pathlib.Path) -> set[str]:
    """只扫描主插件类的公开 *_contract 方法，避免把 helper 当契约。"""
    methods: set[str] = set()
    for path in repo.rglob("*.py"):
        if ".git" in path.parts or "tests" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef) or not node.name.endswith("Plugin"):
                continue
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name.endswith("_contract") and not item.name.startswith("_"):
                        methods.add(item.name)
    return methods


def _json_literal_name_errors(repo: pathlib.Path) -> list[str]:
    """捕捉 Python 源码里误写的 JSON ``true/false/null`` 字面量。

    这类代码能通过 ``py_compile``，但一调用契约方法就会在运行时 ``NameError``。
    审计只做静态观察，帮助在进服务器前发现该问题。
    """
    found: list[str] = []
    for path in repo.rglob("*.py"):
        if ".git" in path.parts or "tests" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in {"true", "false", "null"}:
                found.append(
                    f"{path.relative_to(repo).as_posix()}:{node.lineno}:{node.id}"
                )
    return sorted(found)


def _request_context_files(root: pathlib.Path) -> list[pathlib.Path]:
    found: list[pathlib.Path] = []
    for repo in sorted(root.glob("astrbot_plugin_*")):
        if not repo.is_dir() or repo.name in IGNORED_REPOS:
            continue
        for candidate in (repo / "request_context.py", repo / "core" / "request_context.py"):
            if candidate.is_file():
                found.append(candidate)
    return found


def _hash_file(path: pathlib.Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    except OSError:
        return ""


def _conventions_copies(root: pathlib.Path) -> list[str]:
    copies: list[str] = []
    for path in root.rglob("CONVENTIONS*.md"):
        if "astrbot_plugin_" not in str(path):
            continue
        if path.parts and KERNEL_PLUGIN_ID in path.parts:
            continue
        copies.append(str(path.relative_to(root)))
    return sorted(copies)


def _member_lookup(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("plugin_id")): item
        for item in registry.get("members", [])
        if isinstance(item, dict) and item.get("plugin_id")
    }


def audit(
    root: pathlib.Path,
    registry_path: pathlib.Path | None = None,
) -> dict[str, Any]:
    registry_path = registry_path or pathlib.Path(__file__).resolve().parents[1] / "contracts.yaml"
    registry = _read_yaml(registry_path)
    members = _member_lookup(registry)
    warnings: list[str] = []
    errors: list[str] = []
    member_report: dict[str, Any] = {}
    methods_by_repo: dict[str, set[str]] = {}

    for plugin_id, spec in members.items():
        repo = root / plugin_id
        item: dict[str, Any] = {"present": repo.is_dir()}
        if not repo.is_dir():
            message = f"member missing locally: {plugin_id}"
            (errors if spec.get("local_required", False) else warnings).append(message)
            member_report[plugin_id] = item
            continue
        invalid_literals = _json_literal_name_errors(repo)
        if invalid_literals:
            errors.append(
                f"{plugin_id}: JSON-style Python literals: {invalid_literals}"
            )
        metadata = _metadata_version(repo)
        changelog = _changelog_top(repo)
        code = _code_version(repo, str(spec.get("version_source") or ""))
        present_versions = {value for value in (metadata, changelog, code) if value}
        item.update(
            {
                "metadata_version": metadata,
                "changelog_top": changelog,
                "code_version": code,
                "drift": sorted(present_versions) if len(present_versions) > 1 else [],
            }
        )
        if metadata and changelog and metadata != changelog:
            warnings.append(
                f"version drift: {plugin_id} metadata={metadata} changelog={changelog}"
            )
        if metadata and code and metadata != code:
            warnings.append(
                f"version drift: {plugin_id} metadata={metadata} code={code}"
            )
        member_report[plugin_id] = item
        methods_by_repo[plugin_id] = _contract_methods(repo)

    registered_methods: set[str] = set()
    contract_report: dict[str, Any] = {}
    for contract in registry.get("contracts", []):
        if not isinstance(contract, dict) or not contract.get("name"):
            continue
        name = str(contract["name"])
        method = str(contract.get("method") or "")
        provider = str(contract.get("provider") or "")
        required = bool(contract.get("required", False))
        exclude = {str(value) for value in contract.get("exclude", [])}
        registered_methods.add(method)
        providers = [provider] if provider not in ("", "*") else list(members)
        providers = [value for value in providers if value not in exclude]
        missing: list[str] = []
        checked: list[str] = []
        for plugin_id in providers:
            if plugin_id not in methods_by_repo:
                continue
            checked.append(plugin_id)
            if method and method not in methods_by_repo[plugin_id]:
                missing.append(plugin_id)
        contract_report[name] = {
            "method": method,
            "provider": provider or "*",
            "required": required,
            "checked": checked,
            "missing": missing,
        }
        if missing and required:
            errors.append(
                f"contract missing: {name} method={method} providers={missing}"
            )
        # optional 契约缺失只记录在报告里，不产生噪音警告。

    flow_report: dict[str, Any] = {}
    available_contracts = {
        f"{item.get('name')}@{item.get('version')}"
        for item in registry.get("contracts", [])
        if isinstance(item, dict) and item.get("name") and item.get("version")
    }
    for flow in registry.get("flows", []):
        if not isinstance(flow, dict) or not flow.get("name"):
            continue
        name = str(flow["name"])
        steps: list[dict[str, Any]] = []
        missing_steps: list[str] = []
        for raw_step in flow.get("steps", []):
            if not isinstance(raw_step, dict):
                continue
            contract = str(raw_step.get("contract") or "")
            version = str(raw_step.get("version") or "")
            # 未显式写版本时接受该契约的现行版本，便于流水线引用主版本语义。
            if not version:
                version = next(
                    (
                        str(item.get("version"))
                        for item in registry.get("contracts", [])
                        if isinstance(item, dict) and str(item.get("name")) == contract
                    ),
                    "",
                )
            reference = f"{contract}@{version}"
            present = reference in available_contracts
            step = {
                "order": int(raw_step.get("order") or len(steps) + 1),
                "contract": reference,
                "provider": str(raw_step.get("provider") or ""),
                "role": str(raw_step.get("role") or ""),
                "present": present,
            }
            steps.append(step)
            if not present:
                missing_steps.append(reference)
        flow_report[name] = {
            "version": str(flow.get("version") or ""),
            "steps": steps,
            "missing": missing_steps,
        }
        if missing_steps:
            errors.append(
                f"flow references missing contracts: {name} {missing_steps}"
            )

    observed: dict[str, list[str]] = {}
    for plugin_id, methods in methods_by_repo.items():
        unknown = sorted(methods - registered_methods)
        if unknown:
            observed[plugin_id] = unknown
            warnings.append(
                f"unregistered contract methods: {plugin_id} {unknown}"
            )

    rc_files = _request_context_files(root)
    groups: dict[str, list[str]] = {}
    for path in rc_files:
        groups.setdefault(_hash_file(path), []).append(
            str(path.relative_to(root))
        )
    rc_consistent = len(groups) <= 1
    if rc_files and not rc_consistent:
        errors.append(
            f"request_context hash mismatch across {len(groups)} groups"
        )
    if len(rc_files) != REQUEST_CONTEXT_EXPECTED:
        warnings.append(
            f"request_context copies: found {len(rc_files)}, expected {REQUEST_CONTEXT_EXPECTED}"
        )

    conventions = _conventions_copies(root)
    if conventions:
        errors.append(f"CONVENTIONS copies outside kernel: {conventions}")

    kernel_ui = root / KERNEL_PLUGIN_ID / "ui"
    if kernel_ui.is_dir():
        errors.extend(verify_series_ui(root))

    return {
        "schema_version": registry.get("schema_version", 0),
        "series_id": registry.get("series_id", ""),
        "root": str(root),
        "members": member_report,
        "contracts": contract_report,
        "flows": flow_report,
        "unregistered_contract_methods": observed,
        "request_context": {
            "files": [str(path.relative_to(root)) for path in rc_files],
            "consistent": rc_consistent,
            "hash_groups": groups,
        },
        "conventions_copies_outside_kernel": conventions,
        "ui_library": {"name": "series.ui", "version": "1.0.0", "clean": not verify_series_ui(root)},
        "warnings": warnings,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="凝心溯溪系列只读审计")
    parser.add_argument(
        "--root",
        default=str(pathlib.Path(__file__).resolve().parents[2]),
        help="包含所有 astrbot_plugin_* 仓库的父目录",
    )
    parser.add_argument("--registry", default="", help="contracts.yaml 路径")
    parser.add_argument("--strict", action="store_true", help="有错误时退出 1")
    args = parser.parse_args(argv)
    registry_path = (
        pathlib.Path(args.registry).resolve()
        if args.registry
        else pathlib.Path(__file__).resolve().parents[1] / "contracts.yaml"
    )
    report = audit(pathlib.Path(args.root).resolve(), registry_path)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.strict and report["errors"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
