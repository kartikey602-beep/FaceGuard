"""Small wrapper for recording access decisions in SQLite."""

from backend import database


def record_access_attempt(
    area_id: int,
    result: str,
    personnel_id: int | None = None,
    match_score: float | None = None,
    reason: str | None = None,
) -> dict[str, object]:
    """Store one decision and return its ID and database timestamp."""
    return database.create_access_log(
        area_id=area_id,
        result=result,
        personnel_id=personnel_id,
        match_score=match_score,
        reason=reason,
    )

