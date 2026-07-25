"""异步市场/GitHub 候选读取，含条件缓存、限流与退避。"""

from __future__ import annotations

import asyncio
import base64
import binascii
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote, urlsplit

import aiohttp
import yaml
from packaging.version import InvalidVersion, Version

from ..models import Candidate


class RegistryError(RuntimeError):
    """Stable registry failure with safe request context for UI diagnostics."""

    def __init__(
        self,
        code: str,
        *,
        http_status: int | None = None,
        repo: str | None = None,
        default_branch: str | None = None,
    ) -> None:
        self.code = code
        self.http_status = http_status
        self.repo = repo
        self.default_branch = default_branch
        super().__init__(code)

    def with_context(
        self, *, repo: str | None = None, default_branch: str | None = None
    ) -> "RegistryError":
        if repo and not self.repo:
            self.repo = repo
        if default_branch and not self.default_branch:
            self.default_branch = default_branch
        return self

    def to_dict(self) -> dict[str, Any]:
        context = {"repo": self.repo} if self.repo else {}
        if self.default_branch:
            context["default_branch"] = self.default_branch
        if self.http_status is not None:
            context["http_status"] = self.http_status
        return {"code": self.code, "context": context}


#: metadata.yaml 是版本权威来源；仅当权威源"确实缺失或不可信"时才允许回退到
#: Release/Tag。网络类错误（超时、连接失败、限流）不在此列——那种情况下宁可
#: 让检查失败，也不要用可能陈旧的标签冒充最新版。
_METADATA_FALLBACK_ERRORS = frozenset(
    {
        "REGISTRY_HTTP_404",
        "REGISTRY_JSON_INVALID",
        "GITHUB_REPOSITORY_SCHEMA_INVALID",
        "GITHUB_METADATA_SCHEMA_INVALID",
        "GITHUB_METADATA_ID_MISMATCH",
        "GITHUB_METADATA_VERSION_INVALID",
    }
)


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
                        raise RegistryError(
                            "SOURCE_REDIRECT_BLOCKED", http_status=response.status
                        )
                    if response.status in {403, 429} or response.status >= 500:
                        if attempt < 2:
                            await asyncio.sleep(min(2**attempt, 4))
                            continue
                        raise RegistryError(
                            f"REGISTRY_HTTP_{response.status}",
                            http_status=response.status,
                        )
                    if response.status == 404:
                        raise RegistryError("REGISTRY_HTTP_404", http_status=404)
                    if response.status >= 400:
                        raise RegistryError(
                            f"REGISTRY_HTTP_{response.status}",
                            http_status=response.status,
                        )
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

    @staticmethod
    def _github_metadata_version(payload: Any, plugin_id: str) -> str:
        if not isinstance(payload, dict):
            raise RegistryError("GITHUB_METADATA_SCHEMA_INVALID")
        encoded = payload.get("content")
        if not isinstance(encoded, str) or payload.get("encoding") != "base64":
            raise RegistryError("GITHUB_METADATA_SCHEMA_INVALID")
        try:
            compact = "".join(encoded.split())
            metadata = yaml.safe_load(base64.b64decode(compact, validate=True))
        except (ValueError, binascii.Error, yaml.YAMLError) as exc:
            raise RegistryError("GITHUB_METADATA_SCHEMA_INVALID") from exc
        if not isinstance(metadata, dict) or str(metadata.get("name") or "") != plugin_id:
            raise RegistryError("GITHUB_METADATA_ID_MISMATCH")
        version = str(metadata.get("version") or "").strip().removeprefix("v")
        try:
            Version(version)
        except InvalidVersion as exc:
            raise RegistryError("GITHUB_METADATA_VERSION_INVALID") from exc
        return version

    @staticmethod
    def _parse_version(value: Any) -> Version | None:
        try:
            return Version(str(value).strip().removeprefix("v"))
        except (InvalidVersion, AttributeError):
            return None

    @classmethod
    def _semver_sorted_tags(cls, payload: Any) -> list[tuple[Version, dict[str, Any]]]:
        """按语义化版本降序返回标签，而不是依赖 GitHub 的创建时间顺序。"""
        if not isinstance(payload, list):
            raise RegistryError("GITHUB_TAG_SCHEMA_INVALID")
        ranked = [
            (version, entry)
            for entry in payload
            if isinstance(entry, dict)
            and (version := cls._parse_version(entry.get("name"))) is not None
        ]
        if not ranked:
            raise RegistryError("GITHUB_TAG_SCHEMA_INVALID")
        return sorted(ranked, key=lambda item: item[0], reverse=True)

    @staticmethod
    def _tag_details(entry: dict[str, Any] | None) -> tuple[str, str, str]:
        if not isinstance(entry, dict):
            return "", "", ""
        commit = entry.get("commit")
        return (
            str(entry.get("name") or "").strip(),
            str(commit.get("sha") or "").strip() if isinstance(commit, dict) else "",
            str(entry.get("zipball_url") or "").strip(),
        )

    async def _tags(self, repo: str, *, force_refresh: bool) -> Any:
        return await self.fetch_json(
            f"https://api.github.com/repos/{repo}/tags?per_page=100",
            force_refresh=force_refresh,
        )

    async def _default_branch(self, repo: str, *, force_refresh: bool) -> str:
        payload = await self.fetch_json(
            f"https://api.github.com/repos/{repo}", force_refresh=force_refresh
        )
        if not isinstance(payload, dict):
            raise RegistryError("GITHUB_REPOSITORY_SCHEMA_INVALID")
        branch = payload.get("default_branch")
        if not isinstance(branch, str) or not branch.strip():
            raise RegistryError("GITHUB_REPOSITORY_SCHEMA_INVALID")
        return branch.strip()

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
        try:
            default_branch = await self._default_branch(repo, force_refresh=force_refresh)
        except RegistryError as exc:
            raise exc.with_context(repo=repo)
        try:
            metadata_url = (
                f"https://api.github.com/repos/{repo}/contents/metadata.yaml"
                f"?ref={quote(default_branch, safe='')}"
            )
            metadata_payload = await self.fetch_json(
                metadata_url, force_refresh=force_refresh
            )
            target = self._github_metadata_version(metadata_payload, plugin_id)
        except RegistryError as exc:
            exc.with_context(repo=repo, default_branch=default_branch)
            if str(exc) not in _METADATA_FALLBACK_ERRORS:
                raise
            try:
                return await self._release_or_tag_candidate(
                    plugin_id,
                    current_version,
                    source_url,
                    repo,
                    default_branch=default_branch,
                    fallback_reason=str(exc),
                    force_refresh=force_refresh,
                )
            except RegistryError as fallback_exc:
                raise fallback_exc.with_context(
                    repo=repo, default_branch=default_branch
                )
        return await self._metadata_candidate(
            plugin_id,
            current_version,
            source_url,
            repo,
            target,
            default_branch,
            force_refresh=force_refresh,
        )

    async def _metadata_candidate(
        self,
        plugin_id: str,
        current_version: str,
        source_url: str,
        repo: str,
        target: str,
        default_branch: str,
        *,
        force_refresh: bool,
    ) -> Candidate:
        """metadata.yaml 已给出权威版本，仅补齐归档/提交/发布时间等证据。"""
        wanted = self._parse_version(target)
        tag_name = commit = archive_url = ""
        published_at: str | None = None
        try:
            release = await self.fetch_json(
                f"https://api.github.com/repos/{repo}/releases/latest",
                force_refresh=force_refresh,
            )
        except RegistryError:
            release = None
        if isinstance(release, dict) and self._parse_version(
            release.get("tag_name")
        ) == wanted:
            tag_name = str(release.get("tag_name") or "").strip()
            archive_url = str(release.get("zipball_url") or "").strip()
            published = release.get("published_at")
            published_at = str(published) if published else None
        else:
            try:
                ranked = self._semver_sorted_tags(
                    await self._tags(repo, force_refresh=force_refresh)
                )
            except RegistryError:
                ranked = []
            matched = next(
                (entry for version, entry in ranked if version == wanted), None
            )
            tag_name, commit, archive_url = self._tag_details(matched)
        if not archive_url:
            archive_url = (
                f"https://api.github.com/repos/{repo}/zipball/"
                f"{quote(default_branch, safe='')}"
            )
        return Candidate(
            plugin_id,
            current_version,
            target,
            source_url,
            "github",
            tag=tag_name or None,
            commit=commit or None,
            published_at=published_at,
            archive_url=archive_url,
            default_branch=default_branch,
            evidence={
                "api": "github_default_branch_metadata",
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "version_source": "metadata.yaml",
                "matching_tag": bool(tag_name),
            },
        )

    async def _release_or_tag_candidate(
        self,
        plugin_id: str,
        current_version: str,
        source_url: str,
        repo: str,
        *,
        default_branch: str,
        fallback_reason: str,
        force_refresh: bool,
    ) -> Candidate:
        """权威源缺失时的回退：先 Release，再按语义化版本排序的标签。"""
        observed_at = datetime.now(timezone.utc).isoformat()
        try:
            payload = await self.fetch_json(
                f"https://api.github.com/repos/{repo}/releases/latest",
                force_refresh=force_refresh,
            )
        except RegistryError as exc:
            if str(exc) != "REGISTRY_HTTP_404":
                raise
            version, entry = self._semver_sorted_tags(
                await self._tags(repo, force_refresh=force_refresh)
            )[0]
            tag_name, commit, archive_url = self._tag_details(entry)
            archive_url = archive_url or (
                f"https://api.github.com/repos/{repo}/zipball/"
                f"{quote(default_branch, safe='')}"
            )
            return Candidate(
                plugin_id,
                current_version,
                str(version),
                source_url,
                "github",
                tag=tag_name or None,
                commit=commit or None,
                archive_url=archive_url,
                default_branch=default_branch,
                evidence={
                    "api": "github_latest_tag",
                    "observed_at": observed_at,
                    "version_source": "tag_semver_max",
                    "metadata_fallback_reason": fallback_reason,
                },
            )
        if not isinstance(payload, dict):
            raise RegistryError("GITHUB_RELEASE_SCHEMA_INVALID")
        tag_name = str(payload.get("tag_name") or "").strip()
        version = self._parse_version(tag_name)
        if version is None:
            raise RegistryError("GITHUB_RELEASE_SCHEMA_INVALID")
        published = payload.get("published_at")
        archive_url = str(payload.get("zipball_url") or "").strip() or (
            f"https://api.github.com/repos/{repo}/zipball/"
            f"{quote(default_branch, safe='')}"
        )
        return Candidate(
            plugin_id,
            current_version,
            str(version),
            source_url,
            "github",
            tag=tag_name,
            published_at=str(published) if published else None,
            archive_url=archive_url,
            default_branch=default_branch,
            evidence={
                "api": "github_latest_release",
                "observed_at": observed_at,
                "version_source": "release_tag_name",
                "metadata_fallback_reason": fallback_reason,
            },
        )
