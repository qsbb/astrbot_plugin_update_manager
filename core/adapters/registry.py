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
        self.proxy = proxy or None
        self.token = github_token or None
        self._session: aiohttp.ClientSession | None = None
        self._cache: dict[str, tuple[float, str | None, dict[str, Any]]] = {}

    async def _client(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout, trust_env=True)
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def fetch_json(self, url: str) -> dict[str, Any]:
        cached = self._cache.get(url)
        if cached and time.monotonic() - cached[0] < self.cache_ttl:
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
                    response.raise_for_status()
                    payload = await response.json(content_type=None)
                    if not isinstance(payload, dict):
                        raise RegistryError("REGISTRY_SCHEMA_INVALID")
                    self._cache[url] = (
                        time.monotonic(),
                        response.headers.get("ETag"),
                        payload,
                    )
                    return payload
            except asyncio.TimeoutError as exc:
                if attempt == 2:
                    raise RegistryError("REGISTRY_TIMEOUT") from exc
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
        self, plugin_id: str, current_version: str, source_url: str
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
        payload = await self.fetch_json(
            f"https://api.github.com/repos/{repo}/releases/latest"
        )
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
