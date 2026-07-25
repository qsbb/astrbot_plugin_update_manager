"""插件目录发现与自动更新资格解释。"""

from __future__ import annotations

from urllib.parse import urlsplit

from .adapters.astrbot import PluginSnapshot
from .models import CatalogItem, SELF_PLUGIN_NAME, parse_version, stable_hash

_ALLOWED_SOURCE_KINDS = {"market", "github"}


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
    if kind == "github" and url:
        try:
            parsed = urlsplit(url.removesuffix(".git").rstrip("/"))
        except ValueError:
            return kind, None
        if parsed.scheme != "https" or parsed.hostname != "github.com":
            return kind, None
        parts = parsed.path.strip("/").split("/")
        if len(parts) != 2 or not all(parts) or parsed.username or parsed.password:
            return kind, None
        url = f"https://github.com/{parts[0]}/{parts[1]}"
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
                    display_name=snap.display_name or plugin_id,
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
