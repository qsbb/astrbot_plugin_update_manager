"""异步市场/GitHub 候选读取，含条件缓存、限流与退避。"""

from __future__ import annotations

import asyncio
import base64
import binascii
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote, urlsplit

import aiohttp
import yaml
from packaging.version import InvalidVersion, Version

from ..models import Candidate

#: 版本检查优先读取 raw 域，该域不计入 GitHub REST API 配额。
GITHUB_API_HOST = "api.github.com"
GITHUB_RAW_HOST = "raw.githubusercontent.com"
#: raw 读取无法先查询默认分支，按社区惯例顺序探测；失败才回退 API。
DEFAULT_BRANCH_CANDIDATES = ("main", "master")
RATE_LIMIT_MIN_BACKOFF_SECONDS = 60.0
RATE_LIMIT_MAX_BACKOFF_SECONDS = 3600.0
#: 成功结果缓存默认 30 分钟，减少匿名 60 次/小时配额的消耗。
DEFAULT_CACHE_TTL_SECONDS = 1800
#: raw 域实测单请求可达 ~19s；探测用独立短超时，超时即回退 API，不拖垮整批检查。
DEFAULT_RAW_TIMEOUT_SECONDS = 8.0
#: 仓库默认分支极少变动，记住它即可让后续检查只探测一个分支。
DEFAULT_BRANCH_CACHE_TTL_SECONDS = 86400.0
RATE_LIMITED = "REGISTRY_RATE_LIMITED"


def _header_int(value: Any) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _lowered_headers(headers: Any) -> dict[str, str]:
    """aiohttp 用 CIMultiDict，测试与部分代理用普通 dict，统一小写键。"""
    try:
        items = headers.items()
    except AttributeError:
        return {}
    return {str(key).lower(): str(value) for key, value in items}


def _epoch_to_iso(epoch: float | None) -> str | None:
    if epoch is None:
        return None
    try:
        return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


class RegistryError(RuntimeError):
    """Stable registry failure with safe request context for UI diagnostics."""

    def __init__(
        self,
        code: str,
        *,
        http_status: int | None = None,
        repo: str | None = None,
        default_branch: str | None = None,
        rate_limited: bool = False,
        retry_after_seconds: float | None = None,
        reset_at: str | None = None,
        token_configured: bool | None = None,
    ) -> None:
        self.code = code
        self.http_status = http_status
        self.repo = repo
        self.default_branch = default_branch
        self.rate_limited = rate_limited
        self.retry_after_seconds = retry_after_seconds
        self.reset_at = reset_at
        self.token_configured = token_configured
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
        if self.rate_limited:
            context["rate_limited"] = True
            if self.retry_after_seconds is not None:
                context["retry_after_seconds"] = max(
                    0, int(round(self.retry_after_seconds))
                )
            if self.reset_at:
                context["reset_at"] = self.reset_at
            if self.token_configured is not None:
                context["token_configured"] = self.token_configured
        return {"code": self.code, "context": context}


@dataclass
class RateLimitWindow:
    """单个域名最近一次观测到的配额与退避窗口。"""

    limit: int | None = None
    remaining: int | None = None
    reset_epoch: float | None = None
    retry_after_seconds: float | None = None
    blocked_until: float | None = None

    def wait_seconds(self, now: float) -> float | None:
        if self.blocked_until is None:
            return None
        remaining = self.blocked_until - now
        if remaining <= 0:
            self.blocked_until = None
            return None
        return remaining


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
        cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
        proxy: str | None = None,
        github_token: str | None = None,
        raw_timeout_seconds: float = DEFAULT_RAW_TIMEOUT_SECONDS,
    ) -> None:
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self.cache_ttl = cache_ttl_seconds
        self.raw_timeout_seconds = max(1.0, float(raw_timeout_seconds))
        self.proxy = normalize_optional_setting(proxy)
        self.token = normalize_optional_setting(github_token)
        self._session: aiohttp.ClientSession | None = None
        self._cache: dict[str, tuple[float, str | None, Any]] = {}
        self._text_cache: dict[str, tuple[float, str | None, str]] = {}
        self._rate_limits: dict[str, RateLimitWindow] = {}
        #: repo -> (记录时刻, 默认分支)，让后续检查跳过无用的第二次分支探测。
        self._default_branches: dict[str, tuple[float, str]] = {}

    async def _client(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout, trust_env=True)
        return self._session

    async def close(self) -> None:
        session, self._session = self._session, None
        if session is not None and not session.closed:
            await session.close()

    # ---------------------------------------------------------------- 限流状态

    @staticmethod
    def _host(url: str) -> str:
        try:
            return (urlsplit(url).hostname or "").lower()
        except ValueError:
            return ""

    def _window(self, host: str) -> RateLimitWindow:
        window = self._rate_limits.get(host)
        if window is None:
            window = RateLimitWindow()
            self._rate_limits[host] = window
        return window

    def _remember_rate_limit(
        self, url: str, status: int, headers: Any
    ) -> tuple[RateLimitWindow, bool]:
        """记录 x-ratelimit-* 与 retry-after；返回窗口与是否判定为限流。"""
        lowered = _lowered_headers(headers)
        window = self._window(self._host(url))
        limit = _header_int(lowered.get("x-ratelimit-limit"))
        if limit is not None:
            window.limit = limit
        remaining = _header_int(lowered.get("x-ratelimit-remaining"))
        if remaining is not None:
            window.remaining = remaining
        reset = _header_int(lowered.get("x-ratelimit-reset"))
        if reset is not None:
            window.reset_epoch = float(reset)
        retry_after = _header_int(lowered.get("retry-after"))
        if retry_after is not None:
            window.retry_after_seconds = float(retry_after)
        # 403 也用于权限不足；仅当配额耗尽或明确给出 retry-after 时才算限流，
        # 否则会把"私有仓库无权访问"误判成限流并进入长时间退避。
        rate_limited = status == 429 or (
            status == 403 and (remaining == 0 or retry_after is not None)
        )
        if not rate_limited:
            return window, False
        window.blocked_until = time.monotonic() + self._backoff_seconds(window)
        return window, True

    @staticmethod
    def _backoff_seconds(window: RateLimitWindow) -> float:
        """retry-after 优先，其次按 x-ratelimit-reset 推算，最后落到下限。"""
        if window.retry_after_seconds is not None:
            wait = window.retry_after_seconds
        elif window.reset_epoch is not None:
            wait = window.reset_epoch - time.time()
        else:
            wait = RATE_LIMIT_MIN_BACKOFF_SECONDS
        return min(
            max(wait, RATE_LIMIT_MIN_BACKOFF_SECONDS), RATE_LIMIT_MAX_BACKOFF_SECONDS
        )

    def _rate_limit_error(self, url: str, window: RateLimitWindow) -> RegistryError:
        wait = window.wait_seconds(time.monotonic())
        return RegistryError(
            RATE_LIMITED,
            http_status=429 if self._host(url) == GITHUB_RAW_HOST else 403,
            rate_limited=True,
            retry_after_seconds=wait,
            reset_at=_epoch_to_iso(window.reset_epoch),
            token_configured=bool(self.token),
        )

    def rate_limit_status(self) -> dict[str, Any]:
        """给页面用的只读快照，不含任何 token 信息本体。"""
        now = time.monotonic()
        window = self._rate_limits.get(GITHUB_API_HOST)
        wait = window.wait_seconds(now) if window else None
        return {
            "limited": wait is not None,
            "retry_after_seconds": None if wait is None else max(0, int(round(wait))),
            "reset_at": _epoch_to_iso(window.reset_epoch) if window else None,
            "remaining": window.remaining if window else None,
            "limit": window.limit if window else None,
            "token_configured": bool(self.token),
        }

    def _blocked(self, url: str) -> RegistryError | None:
        """限流窗口内直接失败，不再重复发起请求。"""
        window = self._rate_limits.get(self._host(url))
        if window is None or window.wait_seconds(time.monotonic()) is None:
            return None
        return self._rate_limit_error(url, window)

    # ------------------------------------------------------------ 默认分支缓存

    def remembered_default_branch(self, repo: str) -> str | None:
        """返回仍在有效期内的已知默认分支；过期即淘汰。"""
        entry = self._default_branches.get(repo)
        if entry is None:
            return None
        recorded_at, branch = entry
        if time.monotonic() - recorded_at >= DEFAULT_BRANCH_CACHE_TTL_SECONDS:
            self._default_branches.pop(repo, None)
            return None
        return branch

    def _remember_default_branch(self, repo: str, branch: str) -> None:
        if repo and branch:
            self._default_branches[repo] = (time.monotonic(), branch)

    def _branch_probe_order(self, repo: str) -> tuple[str, ...]:
        """已知默认分支时只探测它一个，避免第二次注定 404 的 raw 请求。"""
        known = self.remembered_default_branch(repo)
        if known is None:
            return DEFAULT_BRANCH_CANDIDATES
        return (known,)

    # ------------------------------------------------------------------ 读取

    async def fetch_json(self, url: str, *, force_refresh: bool = False) -> Any:
        cached = self._cache.get(url)
        if (
            not force_refresh
            and cached
            and time.monotonic() - cached[0] < self.cache_ttl
        ):
            return cached[2]
        blocked = self._blocked(url)
        if blocked is not None:
            # 退避期内复用过期缓存，宁可稍旧也不再消耗配额。
            if cached:
                return cached[2]
            raise blocked
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
                    window, rate_limited = self._remember_rate_limit(
                        url, response.status, getattr(response, "headers", {})
                    )
                    if response.status == 304 and cached:
                        self._cache[url] = (time.monotonic(), cached[1], cached[2])
                        return cached[2]
                    if response.status in {301, 302, 307, 308}:
                        raise RegistryError(
                            "SOURCE_REDIRECT_BLOCKED", http_status=response.status
                        )
                    if rate_limited:
                        # 重试只会加速耗尽配额；直接给出可重试时间。
                        if cached:
                            return cached[2]
                        raise self._rate_limit_error(url, window)
                    if response.status >= 500:
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
                        _lowered_headers(getattr(response, "headers", {})).get("etag"),
                        payload,
                    )
                    return payload
            except asyncio.TimeoutError as exc:
                if attempt == 2:
                    raise RegistryError("REGISTRY_TIMEOUT") from exc
            except aiohttp.ClientError as exc:
                raise RegistryError("REGISTRY_NETWORK_ERROR") from exc
        raise RegistryError("REGISTRY_UNAVAILABLE")

    async def fetch_text(
        self,
        url: str,
        *,
        force_refresh: bool = False,
        timeout_seconds: float | None = None,
        attempts: int = 3,
    ) -> str | None:
        """读取纯文本；404 返回 None 供调用方继续探测其他分支。

        ``timeout_seconds`` 用于给 raw 探测一个比全局超时更短的独立预算，
        ``attempts`` 限制重试次数——探测失败本来就要回退 API，重试只会累加延迟。
        """
        cached = self._text_cache.get(url)
        if (
            not force_refresh
            and cached
            and time.monotonic() - cached[0] < self.cache_ttl
        ):
            return cached[2]
        if self._blocked(url) is not None:
            return cached[2] if cached else None
        headers = {"Accept": "text/plain"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if cached and cached[1]:
            headers["If-None-Match"] = cached[1]
        request_kwargs: dict[str, Any] = {}
        if timeout_seconds is not None:
            request_kwargs["timeout"] = aiohttp.ClientTimeout(total=timeout_seconds)
        budget = max(1, attempts)
        client = await self._client()
        for attempt in range(budget):
            try:
                async with client.get(
                    url,
                    headers=headers,
                    proxy=self.proxy,
                    allow_redirects=False,
                    **request_kwargs,
                ) as response:
                    window, rate_limited = self._remember_rate_limit(
                        url, response.status, getattr(response, "headers", {})
                    )
                    if response.status == 304 and cached:
                        self._text_cache[url] = (time.monotonic(), cached[1], cached[2])
                        return cached[2]
                    if response.status == 404:
                        return None
                    if rate_limited:
                        if cached:
                            return cached[2]
                        raise self._rate_limit_error(url, window)
                    if response.status >= 500:
                        if attempt < budget - 1:
                            await asyncio.sleep(min(2**attempt, 4))
                            continue
                        raise RegistryError(
                            f"REGISTRY_HTTP_{response.status}",
                            http_status=response.status,
                        )
                    if response.status >= 400 or response.status in {
                        301,
                        302,
                        307,
                        308,
                    }:
                        raise RegistryError(
                            f"REGISTRY_HTTP_{response.status}",
                            http_status=response.status,
                        )
                    text = await response.text()
                    self._text_cache[url] = (
                        time.monotonic(),
                        _lowered_headers(getattr(response, "headers", {})).get("etag"),
                        text,
                    )
                    return text
            except asyncio.TimeoutError as exc:
                if attempt == budget - 1:
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

    @classmethod
    def _github_metadata_version(cls, payload: Any, plugin_id: str) -> str:
        if not isinstance(payload, dict):
            raise RegistryError("GITHUB_METADATA_SCHEMA_INVALID")
        encoded = payload.get("content")
        if not isinstance(encoded, str) or payload.get("encoding") != "base64":
            raise RegistryError("GITHUB_METADATA_SCHEMA_INVALID")
        try:
            compact = "".join(encoded.split())
            decoded = base64.b64decode(compact, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise RegistryError("GITHUB_METADATA_SCHEMA_INVALID") from exc
        return cls._metadata_yaml_version(decoded, plugin_id)

    @staticmethod
    def _metadata_yaml_version(document: str | bytes, plugin_id: str) -> str:
        """metadata.yaml 权威版本解析，raw 文本与 API base64 共用同一校验。"""
        try:
            metadata = yaml.safe_load(document)
        except yaml.YAMLError as exc:
            raise RegistryError("GITHUB_METADATA_SCHEMA_INVALID") from exc
        if not isinstance(metadata, dict):
            raise RegistryError("GITHUB_METADATA_SCHEMA_INVALID")
        if str(metadata.get("name") or "") != plugin_id:
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

    async def _raw_metadata_version(
        self, repo: str, plugin_id: str, *, force_refresh: bool
    ) -> tuple[str | None, str | None, RegistryError | None]:
        """从 raw 域读取 metadata.yaml，完全不消耗 API 配额。

        已知默认分支时只探测该分支；否则按 main/master 顺序探测。每次探测使用
        独立的短超时且不重试，超时即视为探测失败并交给 API 回退。

        返回 (命中的分支, 权威版本, 权威源错误)。三者均为 None 表示候选分支
        都不存在该文件，调用方需要回退 API 查询真实默认分支。
        """
        for branch in self._branch_probe_order(repo):
            url = (
                f"https://{GITHUB_RAW_HOST}/{repo}/"
                f"{quote(branch, safe='')}/metadata.yaml"
            )
            try:
                document = await self.fetch_text(
                    url,
                    force_refresh=force_refresh,
                    timeout_seconds=self.raw_timeout_seconds,
                    attempts=1,
                )
            except RegistryError as exc:
                # 网络/限流类问题对其他分支同样成立，直接交给 API 回退判定。
                return None, None, exc.with_context(repo=repo, default_branch=branch)
            if document is None:
                continue
            try:
                version = self._metadata_yaml_version(document, plugin_id)
            except RegistryError as exc:
                # 权威源存在但不可信：记录原因，交由 Release/Tag 回退处理。
                return None, None, exc.with_context(repo=repo, default_branch=branch)
            self._remember_default_branch(repo, branch)
            return branch, version, None
        return None, None, None

    async def _default_branch(self, repo: str, *, force_refresh: bool) -> str:
        payload = await self.fetch_json(
            f"https://api.github.com/repos/{repo}", force_refresh=force_refresh
        )
        if not isinstance(payload, dict):
            raise RegistryError("GITHUB_REPOSITORY_SCHEMA_INVALID")
        branch = payload.get("default_branch")
        if not isinstance(branch, str) or not branch.strip():
            raise RegistryError("GITHUB_REPOSITORY_SCHEMA_INVALID")
        branch = branch.strip()
        self._remember_default_branch(repo, branch)
        return branch

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
        raw_branch, raw_target, raw_error = await self._raw_metadata_version(
            repo, plugin_id, force_refresh=force_refresh
        )
        if raw_target is not None and raw_branch is not None:
            return await self._metadata_candidate(
                plugin_id,
                current_version,
                source_url,
                repo,
                raw_target,
                raw_branch,
                force_refresh=force_refresh,
                evidence_api="github_raw_default_branch_metadata",
            )
        # 仅"权威源不可信"才跳过 API 重读；raw 侧的网络/限流问题不应否定 API。
        untrusted_metadata = (
            raw_error
            if raw_error and str(raw_error) in _METADATA_FALLBACK_ERRORS
            else None
        )
        try:
            default_branch = await self._default_branch(repo, force_refresh=force_refresh)
        except RegistryError as exc:
            # raw 已证明权威源不可信，且 API 也不可用时，暴露更准确的 raw 原因。
            if untrusted_metadata is not None and not exc.rate_limited:
                raise untrusted_metadata.with_context(repo=repo)
            raise exc.with_context(repo=repo)
        try:
            if untrusted_metadata is not None:
                raise untrusted_metadata
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
        evidence_api: str = "github_default_branch_metadata",
    ) -> Candidate:
        """metadata.yaml 已给出权威版本，仅补齐归档/提交/发布时间等证据。

        证据补齐走 API，因此在限流退避窗口内会被 fetch_json 直接拦下；此时版本
        仍然有效，只是缺少 tag/published_at，不会额外消耗配额。
        """
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
                "api": evidence_api,
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "version_source": "metadata.yaml",
                "matching_tag": bool(tag_name),
                "quota_free_version_check": evidence_api
                == "github_raw_default_branch_metadata",
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
