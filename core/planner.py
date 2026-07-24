"""不可变更新计划生成与执行前冻结校验。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from .models import (
    Candidate,
    CatalogItem,
    PlanItem,
    Policy,
    UpdatePlan,
    compatible,
    policy_allows,
    stable_hash,
    utc_now,
)


class PlanError(ValueError):
    pass


class PlanStaleError(PlanError):
    pass


class UpdatePlanner:
    def __init__(self, *, ttl_seconds: int = 900) -> None:
        self.ttl_seconds = ttl_seconds

    def create(
        self,
        catalog: tuple[CatalogItem, ...],
        candidates: dict[str, Candidate],
        *,
        selected: tuple[str, ...],
        astrbot_version: str,
        policy: Policy,
        rule_revision: int | None = None,
        prerelease: bool = False,
        minimum_release_age_hours: int = 0,
    ) -> UpdatePlan:
        by_id = {item.plugin_id: item for item in catalog}
        items: list[PlanItem] = []
        for plugin_id in dict.fromkeys(selected):
            item = by_id.get(plugin_id)
            candidate = candidates.get(plugin_id)
            if item is None or candidate is None:
                raise PlanError(f"{plugin_id}: CANDIDATE_REQUIRED")
            if not item.eligible:
                raise PlanError(f"{plugin_id}: {','.join(item.reasons)}")
            if (
                candidate.source_url != item.source_url
                or candidate.source_kind != item.source_kind
            ):
                raise PlanError(f"{plugin_id}: SOURCE_CHANGED")
            if not compatible(candidate.astrbot_spec, astrbot_version):
                raise PlanError(f"{plugin_id}: ASTRBOT_INCOMPATIBLE")
            allowed, reason = policy_allows(
                item.current_version,
                candidate.target_version,
                policy,
                prerelease=prerelease,
            )
            if not allowed:
                raise PlanError(f"{plugin_id}: {reason}")
            if minimum_release_age_hours:
                if not candidate.published_at:
                    raise PlanError(f"{plugin_id}: RELEASE_AGE_UNKNOWN")
                try:
                    published = datetime.fromisoformat(
                        candidate.published_at.replace("Z", "+00:00")
                    )
                    if published.tzinfo is None:
                        published = published.replace(tzinfo=timezone.utc)
                except ValueError as exc:
                    raise PlanError(f"{plugin_id}: RELEASE_DATE_INVALID") from exc
                age = utc_now() - published.astimezone(timezone.utc)
                if age < timedelta(hours=minimum_release_age_hours):
                    raise PlanError(f"{plugin_id}: RELEASE_TOO_NEW")
            items.append(
                PlanItem(
                    plugin_id,
                    item.root_dir_name,
                    item.current_version,
                    candidate.target_version,
                    candidate.source_kind,
                    candidate.source_url,
                    item.activated,
                    item.fingerprint,
                    candidate.digest,
                    candidate.tag,
                    candidate.commit,
                    candidate.published_at,
                    candidate.archive_url,
                )
            )
        if not items:
            raise PlanError("EMPTY_PLAN")
        now = utc_now()
        plan_id = str(uuid4())
        core = {
            "plan_id": plan_id,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=self.ttl_seconds)).isoformat(),
            "astrbot_version": astrbot_version,
            "catalog_fingerprint": stable_hash([item.fingerprint for item in catalog]),
            "rule_revision": rule_revision,
            "policy": policy.value,
            "items": [
                item.__dict__
                if hasattr(item, "__dict__")
                else {slot: getattr(item, slot) for slot in item.__slots__}
                for item in items
            ],
        }
        digest = stable_hash(core)
        return UpdatePlan(
            plan_id,
            core["created_at"],
            core["expires_at"],
            astrbot_version,
            core["catalog_fingerprint"],
            rule_revision,
            policy.value,
            tuple(items),
            digest,
        )

    def validate(
        self,
        plan: UpdatePlan,
        catalog: tuple[CatalogItem, ...],
        *,
        astrbot_version: str,
        rule_revision: int | None,
    ) -> None:
        now = utc_now()
        from datetime import datetime

        if now >= datetime.fromisoformat(plan.expires_at):
            raise PlanStaleError("PLAN_EXPIRED")
        if plan.astrbot_version != astrbot_version:
            raise PlanStaleError("ASTRBOT_VERSION_CHANGED")
        if plan.rule_revision != rule_revision:
            raise PlanStaleError("RULE_REVISION_CHANGED")
        if plan.catalog_fingerprint != stable_hash(
            [item.fingerprint for item in catalog]
        ):
            raise PlanStaleError("CATALOG_CHANGED")
        by_id = {item.plugin_id: item for item in catalog}
        for planned in plan.items:
            current = by_id.get(planned.plugin_id)
            if current is None or current.fingerprint != planned.fingerprint:
                raise PlanStaleError(f"{planned.plugin_id}: CATALOG_CHANGED")
