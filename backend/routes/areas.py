"""Area and personnel-area permission API routes."""

import sqlite3

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from backend import database
from backend.schemas import (
    AreaCreate,
    AreaPersonnelResponse,
    AreaResponse,
    AreaUpdate,
    PermissionResponse,
)


router = APIRouter(prefix="/api/areas", tags=["areas"])


def _database_error() -> HTTPException:
    """Return a safe error without exposing SQLite's internal message."""
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="DATABASE_ERROR",
    )


def _clean_area_name(name: str) -> str:
    """Trim an area name and reject values that are only whitespace."""
    cleaned_name = name.strip()
    if not cleaned_name:
        raise HTTPException(status_code=422, detail="AREA_NAME_REQUIRED")
    return cleaned_name


@router.post("", response_model=AreaResponse, status_code=status.HTTP_201_CREATED)
def create_area(area: AreaCreate) -> dict[str, object]:
    """Create a restricted area."""
    name = _clean_area_name(area.name)
    try:
        area_id = database.create_area(name, area.description, area.status)
        record = database.get_area(area_id)
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="AREA_NAME_ALREADY_EXISTS_OR_INVALID_STATUS",
        ) from error
    except sqlite3.Error as error:
        raise _database_error() from error
    return record  # type: ignore[return-value]


@router.get("", response_model=list[AreaResponse])
def list_areas() -> list[dict[str, object]]:
    """List areas without returning personnel or embedding data."""
    try:
        return database.list_areas()
    except sqlite3.Error as error:
        raise _database_error() from error


@router.get("/{area_id}", response_model=AreaResponse)
def get_area(area_id: int) -> dict[str, object]:
    """Get one area by its database ID."""
    try:
        record = database.get_area(area_id)
    except sqlite3.Error as error:
        raise _database_error() from error
    if record is None:
        raise HTTPException(status_code=404, detail="AREA_NOT_FOUND")
    return record


@router.put("/{area_id}", response_model=AreaResponse)
def update_area(area_id: int, changes: AreaUpdate) -> dict[str, object]:
    """Update supplied area fields."""
    updates = changes.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="NO_FIELDS_TO_UPDATE")
    for field in ("name", "status"):
        if field in updates and updates[field] is None:
            raise HTTPException(status_code=422, detail=f"{field.upper()}_CANNOT_BE_NULL")
    if "name" in updates:
        updates["name"] = _clean_area_name(str(updates["name"]))

    try:
        record = database.update_area(area_id, updates)
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="AREA_NAME_ALREADY_EXISTS_OR_INVALID_STATUS",
        ) from error
    except sqlite3.Error as error:
        raise _database_error() from error
    if record is None:
        raise HTTPException(status_code=404, detail="AREA_NOT_FOUND")
    return record


@router.delete("/{area_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_area(area_id: int) -> Response:
    """Delete an area unless an access log still references it."""
    try:
        if database.get_area(area_id) is None:
            raise HTTPException(status_code=404, detail="AREA_NOT_FOUND")
        database.delete_area(area_id)
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="AREA_HAS_ACCESS_LOGS",
        ) from error
    except sqlite3.Error as error:
        raise _database_error() from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{area_id}/permissions/{personnel_id}",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_permission(area_id: int, personnel_id: int) -> dict[str, object]:
    """Grant an active person permission to enter an active area."""
    try:
        area = database.get_area(area_id)
        if area is None:
            raise HTTPException(status_code=404, detail="AREA_NOT_FOUND")
        person = database.get_personnel(personnel_id)
        if person is None:
            raise HTTPException(status_code=404, detail="PERSONNEL_NOT_FOUND")
        if area["status"] != "ACTIVE":
            raise HTTPException(status_code=409, detail="AREA_INACTIVE")
        if person["status"] != "ACTIVE":
            raise HTTPException(status_code=409, detail="PERSONNEL_INACTIVE")
        return database.grant_permission(personnel_id, area_id)
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="PERMISSION_ALREADY_EXISTS",
        ) from error
    except sqlite3.Error as error:
        raise _database_error() from error


@router.delete(
    "/{area_id}/permissions/{personnel_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_permission(area_id: int, personnel_id: int) -> Response:
    """Remove a permission link between an existing person and area."""
    try:
        if database.get_area(area_id) is None:
            raise HTTPException(status_code=404, detail="AREA_NOT_FOUND")
        if database.get_personnel(personnel_id) is None:
            raise HTTPException(status_code=404, detail="PERSONNEL_NOT_FOUND")
        removed = database.revoke_permission(personnel_id, area_id)
    except sqlite3.Error as error:
        raise _database_error() from error
    if not removed:
        raise HTTPException(status_code=404, detail="PERMISSION_NOT_FOUND")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{area_id}/permissions",
    response_model=list[AreaPersonnelResponse],
)
def list_area_permissions(area_id: int) -> list[dict[str, object]]:
    """List personnel linked to an area through permissions."""
    try:
        if database.get_area(area_id) is None:
            raise HTTPException(status_code=404, detail="AREA_NOT_FOUND")
        return database.list_area_permissions(area_id)
    except sqlite3.Error as error:
        raise _database_error() from error

