"""Read-only API routes for the access audit log."""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from backend import database


router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("")
def list_logs(
    area_id: int | None = None,
    result: Annotated[str | None, Query(pattern="^(ACCESS_GRANTED|ACCESS_DENIED)$")] = None,
    date: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")] = None,
    personnel_id: int | None = None,
) -> list[dict[str, object]]:
    """List access events with optional area, result, date, or person filters."""
    try:
        return database.list_access_logs(area_id, result, date, personnel_id)
    except sqlite3.Error as error:
        raise HTTPException(status_code=500, detail="DATABASE_ERROR") from error


@router.get("/{log_id}")
def get_log(log_id: int) -> dict[str, object]:
    """Read one access event by its database ID."""
    try:
        log = database.get_access_log(log_id)
    except sqlite3.Error as error:
        raise HTTPException(status_code=500, detail="DATABASE_ERROR") from error
    if log is None:
        raise HTTPException(status_code=404, detail="ACCESS_LOG_NOT_FOUND")
    return log

