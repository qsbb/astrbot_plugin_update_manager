"""异步市场/GitHub 候选读取，含条件缓存、限流与退避。"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

import aiohttp

from ..models import Candidate


class RegistryError(RuntimeError):
    pass


def normalize_optional_setting(value: Any) -> str | None:
    """Normalize optional values returned by AstrBot's config wrappers."""
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized or normalized.lower() in {"none", "null"}:
        return None
    return normalized


class CandidateRegistry:
    def __init__(
        self,
        *,
        timeout_seconds: int = 15,
        cache_ttl_seconds: int = 300,
        proxy: str | None = None,
        github_token: str | None = None,
    ) -> None:
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self.cache_ttl = cache_ttl_seconds
        self.proxy = normalize_optional_setting(proxy)
        self.token = normalize_optional_setting(github_token)
        self._session: aiohttp.ClientSession | None = None
        self._cache: dict[str, tuple[float, str | None, Any]] = {}

    async def _client(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout, trust_env=True)
        return self._session

    async def close(self) -> None:
        session, self._session = self._session, None
        if session is not None and not session.closed:
            await session.close()

    async def fetch_json(self, url: str, *, force_refresh: bool = False) -> Any:
        cached = self._cache.get(url)
        if (
            not force_refresh
            and cached
            and time.monotonic() - cached[0] < self.cache_ttl
        ):
            return cached[2]
        headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if cached and cached[1]:
            headers["If-None-Match"] = cached[1]
        client = await self._client()
        for attempt in range(3):
            try:
                async with client.get(
                    url, headers=headers, proxy=self.proxy, allow_redirects=False
                ) as response:
                    if response.status == 304 and cached:
                        self._cache[url] = (time.monotonic(), cached[1], cached[2])
                        return cached[2]
                    if response.status in {301, 302, 307, 308}:
                        raise RegistryError("SOURCE_REDIRECT_BLOCKED")
                    if response.status in {403, 429} or response.status >= 500:
                        if attempt < 2:
                            await asyncio.sleep(min(2**attempt, 4))
                            continue
                        raise RegistryError(f"REGISTRY_HTTP_{response.status}")
                    if response.status == 404:
                        raise RegistryError("REGISTRY_HTTP_404")
                    if response.status >= 400:
                        raise RegistryError(f"REGISTRY_HTTP_{response.status}")
                    try:
                        payload = await response.json(content_type=None)
                    except (aiohttp.ClientError, ValueError) as exc:
                        raise RegistryError("REGISTRY_JSON_INVALID") from exc
                    self._cache[url] = (
                        time.monotonic(),
                        response.headers.get("ETag"),
                        payload,
                    )
                    return payload
            except asyncio.TimeoutError as exc:
                if attempt == 2:
                    raise RegistryError("REGISTRY_TIMEOUT") from exc
            except aiohttp.ClientError as exc:
                raise RegistryError("REGISTRY_NETWORK_ERROR") from exc
        raise RegistryError("REGISTRY_UNAVAILABLE")

    @staticmethod
    def market_candidate(
        plugin_id: str,
        current_version: str,
        source_url: str,
        source_record: dict[str, Any],
    ) -> Candidate:
        """只消费 AstrBot 已记录的市场候选证据，不猜测市场端点。"""
        target = str(
            source_record.get("latest_version")
            or source_record.get("target_version")
            or ""
        ).removeprefix("v")
        if not target:
            raise RegistryError("MARKET_CANDIDATE_UNAVAILABLE")
        archive_url = str(
            source_record.get("download_url") or source_record.get("archive_url") or ""
        )
        return Candidate(
            plugin_id,
            current_version,
            target,
            source_url,
            "market",
            astrbot_spec=str(source_record.get("astrbot_version") or "") or None,
            digest=str(source_record.get("sha256") or "") or None,
            tag=str(source_record.get("tag") or "") or None,
            commit=str(source_record.get("commit") or "") or None,
            published_at=str(source_record.get("published_at") or "") or None,
            archive_url=archive_url or None,
            evidence={
                "api": "astrbot_install_source_record",
                "observed_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def github_latest(
        self,
        plugin_id: str,
        current_version: str,
        source_url: str,
        *,
        force_refresh: bool = False,
    ) -> Candidate:
        try:
            parsed = urlsplit(source_url)
        except ValueError as exc:
            raise RegistryError("SOURCE_REQUIRED") from exc
        parts = parsed.path.strip("/").split("/")
        if (
            parsed.scheme != "https"
            or parsed.hostname != "github.com"
            or parsed.username
            or parsed.password
            or len(parts) != 2
            or not all(parts)
        ):
            raise RegistryError("SOURCE_REQUIRED")
        repo = "/".join(parts)
        release_url = f"https://api.github.com/repos/{repo}/releases/latest"
        try:
            payload = await self.fetch_json(
                release_url, force_refresh=force_refresh
            )
        except RegistryError as exc:
            if str(exc) != "REGISTRY_HTTP_404":
                raise
            tags_url = f"https://api.github.com/repos/{repo}/tags?per_page=1"
            tags = await self.fetch_json(tags_url, force_refresh=force_refresh)
            if not isinstance(tags, list) or not tags or not isinstance(tags[0], dict):
                raise RegistryError("GITHUB_TAG_SCHEMA_INVALID")
            tag = tags[0]
            tag_name = str(tag.get("name") or "").strip()
            commit_data = tag.get("commit")
            commit = (
                str(commit_data.get("sha") or "").strip()
                if isinstance(commit_data, dict)
                else ""
            )
            zipball = str(tag.get("zipball_url") or "").strip()
            if not tag_name:
                raise RegistryError("GITHUB_TAG_SCHEMA_INVALID")
            return Candidate(
                plugin_id,
                current_version,
                tag_name.removeprefix("v"),
                source_url,
                "github",
                tag=tag_name,
                commit=commit or None,
                archive_url=zipball or None,
                evidence={
                    "api": "github_latest_tag",
                    "observed_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        if not isinstance(payload, dict):
            raise RegistryError("GITHUB_RELEASE_SCHEMA_INVALID")
        target = str(payload.get("tag_name") or "").removeprefix("v")
        published = payload.get("published_at")
        return Candidate(
            plugin_id,
            current_version,
            target,
            source_url,
            "github",
            tag=str(payload.get("tag_name") or ""),
            published_at=str(published) if published else None,
            archive_url=str(payload.get("zipball_url") or "") or None,
            evidence={
                "api": "github_latest_release",
                "observed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
