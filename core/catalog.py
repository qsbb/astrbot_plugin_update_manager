"""插件目录发现与自动更新资格解释。"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from .adapters.astrbot import PluginSnapshot, resolve_display_name
from .models import CatalogItem, SELF_PLUGIN_NAME, parse_version, stable_hash

_ALLOWED_SOURCE_KINDS = {"market", "github"}
_GITHUB_REPOSITORY_PATH = re.compile(
    r"^/([A-Za-z0-9][A-Za-z0-9._-]*)/([A-Za-z0-9][A-Za-z0-9._-]*)(?:\.git)?/?$"
)


def _normalize_github_repository_url(value: str) -> str | None:
    candidate = value.strip()
    if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in candidate):
        return None
    try:
        parsed = urlsplit(candidate)
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme.lower() != "https"
        or (parsed.hostname or "").lower() != "github.com"
        or "@" in parsed.netloc
        or port is not None
        or parsed.query
        or parsed.fragment
        or "?" in candidate
        or "#" in candidate
        or parsed.path.count("/") < 2
    ):
        return None
    match = _GITHUB_REPOSITORY_PATH.fullmatch(parsed.path)
    if match is None:
        return None
    owner, repository = match.groups()
    if repository.endswith(".git"):
        repository = repository[:-4]
    if not repository:
        return None
    return f"https://github.com/{owner}/{repository}"


def normalize_source(snapshot: PluginSnapshot) -> tuple[str | None, str | None]:
    source = snapshot.install_source or {}
    kind = str(
        source.get("install_method")
        or source.get("source")
        or source.get("source_kind")
        or ""
    ).lower().strip()
    url = str(
        source.get("repo")
        or source.get("url")
        or source.get("source_url")
        or snapshot.repo
        or ""
    ).strip()
    github_url = _normalize_github_repository_url(url) if url else None
    if kind in {"github", "repository"}:
        if github_url:
            return "github", github_url
        return (kind or None), None
    if not kind and github_url:
        return "github", github_url
    return (kind or None), (url or None)


class PluginCatalog:
    def __init__(self, adapter) -> None:
        self.adapter = adapter

    async def scan(self) -> tuple[CatalogItem, ...]:
        items = []
        for snap in await self.adapter.snapshot_plugins():
            plugin_id = snap.name or snap.root_dir_name or ""
            source_kind, source_url = normalize_source(snap)
            reasons: list[str] = []
            if not plugin_id or not snap.root_dir_name or not snap.metadata_complete:
                reasons.append("IDENTITY_REQUIRED")
            if not snap.loaded:
                reasons.append("PLUGIN_NOT_LOADED")
            if plugin_id == SELF_PLUGIN_NAME:
                reasons.append("SELF_UPDATE_BLOCKED")
            if snap.reserved:
                reasons.append("RESERVED_PLUGIN")
            if parse_version(snap.version) is None:
                reasons.append("VERSION_UNPARSEABLE")
            if source_kind not in _ALLOWED_SOURCE_KINDS or not source_url:
                reasons.append("SOURCE_REQUIRED")
            evidence = {
                "plugin_id": plugin_id,
                "root": snap.root_dir_name,
                "version": snap.version,
                "source_kind": source_kind,
                "source_url": source_url,
                "reserved": snap.reserved,
                "activated": snap.activated,
                "loaded": snap.loaded,
                "metadata_complete": snap.metadata_complete,
            }
            items.append(
                CatalogItem(
                    plugin_id=plugin_id,
                    root_dir_name=snap.root_dir_name or "",
                    display_name=resolve_display_name(
                        (snap.display_name,), plugin_id or snap.root_dir_name or ""
                    ),
                    current_version=snap.version,
                    source_kind=source_kind,
                    source_url=source_url,
                    reserved=snap.reserved,
                    activated=snap.activated,
                    loaded=snap.loaded,
                    eligible=not reasons,
                    reasons=tuple(reasons),
                    fingerprint=stable_hash(evidence),
                )
            )
        return tuple(sorted(items, key=lambda item: item.plugin_id))
