"""自动更新器领域模型、版本策略与稳定序列化。"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

SELF_PLUGIN_NAME = "astrbot_plugin_update_manager"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_version(value: str) -> Version | None:
    try:
        return Version(value.strip())
    except (InvalidVersion, AttributeError):
        return None


def compatible(spec: str | None, astrbot_version: str) -> bool:
    if not spec:
        return True
    try:
        return Version(astrbot_version) in SpecifierSet(spec)
    except (InvalidVersion, InvalidSpecifier):
        return False


class Policy(str, Enum):
    CHECK_ONLY = "check_only"
    PATCH = "patch"
    MINOR = "minor"
    STABLE = "stable"


class FailurePolicy(str, Enum):
    CONTINUE = "rollback_continue"
    STOP = "rollback_stop"


class TxState(str, Enum):
    PLANNED = "PLANNED"
    LOCKED = "LOCKED"
    BACKED_UP = "BACKED_UP"
    CORE_UPDATE_RUNNING = "CORE_UPDATE_RUNNING"
    HEALTHY = "HEALTHY"
    COMMITTED = "COMMITTED"
    FAILED = "FAILED"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"
    ROLLBACK_FAILED = "ROLLBACK_FAILED"
    INTERRUPTED = "INTERRUPTED"


TERMINAL_STATES = {TxState.COMMITTED, TxState.ROLLED_BACK, TxState.ROLLBACK_FAILED}


@dataclass(frozen=True, slots=True)
class Candidate:
    plugin_id: str
    current_version: str
    target_version: str
    source_url: str
    source_kind: str
    astrbot_spec: str | None = None
    digest: str | None = None
    tag: str | None = None
    commit: str | None = None
    published_at: str | None = None
    archive_url: str | None = None
    default_branch: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CatalogItem:
    plugin_id: str
    root_dir_name: str
    display_name: str
    current_version: str
    source_kind: str | None
    source_url: str | None
    reserved: bool
    activated: bool
    loaded: bool
    eligible: bool
    reasons: tuple[str, ...]
    fingerprint: str


@dataclass(frozen=True, slots=True)
class PlanItem:
    plugin_id: str
    root_dir_name: str
    from_version: str
    to_version: str
    source_kind: str
    source_url: str
    activated: bool
    fingerprint: str
    digest: str | None = None
    tag: str | None = None
    commit: str | None = None
    published_at: str | None = None
    archive_url: str | None = None


@dataclass(frozen=True, slots=True)
class UpdatePlan:
    plan_id: str
    created_at: str
    expires_at: str
    astrbot_version: str
    catalog_fingerprint: str
    rule_revision: int | None
    policy: str
    items: tuple[PlanItem, ...]
    plan_hash: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["items"] = [asdict(item) for item in self.items]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UpdatePlan":
        return cls(
            **{**data, "items": tuple(PlanItem(**item) for item in data["items"])}
        )


@dataclass(frozen=True, slots=True)
class UpdateRule:
    schema_version: int = 1
    enabled: bool = False
    plugin_ids: tuple[str, ...] = ()
    local_time: str = "04:30"
    timezone: str = "Asia/Shanghai"
    jitter_minutes: int = 10
    policy: str = Policy.CHECK_ONLY.value
    prerelease: bool = False
    minimum_release_age_hours: int = 24
    on_failure: str = FailurePolicy.CONTINUE.value
    misfire_grace_minutes: int = 30
    revision: int = 0
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["plugin_ids"] = list(self.plugin_ids)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UpdateRule":
        return cls(**{**data, "plugin_ids": tuple(data.get("plugin_ids", ()))})


def stable_hash(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def policy_allows(
    current: str, target: str, policy: Policy, *, prerelease: bool = False
) -> tuple[bool, str]:
    cur, new = parse_version(current), parse_version(target)
    if cur is None or new is None:
        return False, "VERSION_UNPARSEABLE"
    if new <= cur:
        return False, "NOT_NEWER"
    if new.is_prerelease and not prerelease:
        return False, "PRERELEASE_BLOCKED"
    if cur.major == 0 and policy is not Policy.CHECK_ONLY:
        return False, "PRE_1_0_MANUAL_ONLY"
    if policy is Policy.CHECK_ONLY:
        return False, "CHECK_ONLY"
    if policy is Policy.PATCH and (new.major, new.minor) != (cur.major, cur.minor):
        return False, "POLICY_BLOCKED"
    if policy is Policy.MINOR and new.major != cur.major:
        return False, "POLICY_BLOCKED"
    return True, "ELIGIBLE"
