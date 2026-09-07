from datetime import datetime, timezone
from typing import Optional

from .. import config


_STALE_TAGS = {"stale", "obsolete", "deprecated", "superseded"}


def annotate_item(row: dict) -> dict:
    annotated = dict(row)
    annotated.update(evaluate_item(row))
    return annotated


def evaluate_item(row: dict, stale_after_days: Optional[int] = None) -> dict:
    threshold = _threshold_days(stale_after_days)
    updated_at = _parse_time(row.get("updated_at"))
    age_days = _age_days(updated_at)
    tags = {str(tag).strip().lower() for tag in row.get("tags") or []}
    stale_tag = next((tag for tag in sorted(tags) if tag in _STALE_TAGS), "")

    stale = False
    reason = None
    if row.get("pinned"):
        reason = "pinned"
    elif stale_tag:
        stale = True
        reason = f"tag:{stale_tag}"
    elif age_days is not None and threshold > 0 and age_days >= threshold:
        stale = True
        reason = f"older_than_{threshold}_days"

    return {
        "stale": stale,
        "stale_reason": reason,
        "age_days": round(age_days, 1) if age_days is not None else None,
        "stale_after_days": threshold,
        "last_attached_at": row.get("last_attached_at"),
    }


def is_stale(row: dict) -> bool:
    if "stale" in row:
        return bool(row.get("stale"))
    return bool(evaluate_item(row)["stale"])


def _threshold_days(value: Optional[int]) -> int:
    if value is None:
        value = config.MEMORY_STALE_AFTER_DAYS
    return max(0, int(value))


def _age_days(value: Optional[datetime]) -> Optional[float]:
    if value is None:
        return None
    return max(0.0, (datetime.now(timezone.utc) - value).total_seconds() / 86400)


def _parse_time(value) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
