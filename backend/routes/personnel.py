"""Personnel CRUD and face-registration API routes."""

import sqlite3

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import Response

from backend import database
from backend.schemas import (
    FaceRegistrationResponse,
    PersonnelCreate,
    PersonnelResponse,
    PersonnelUpdate,
)
from backend.services.face_engine import (
    MODEL_NAME,
    FaceEngine,
    FaceEngineError,
    InvalidImageError,
    MultipleFacesDetectedError,
    NoFaceDetectedError,
)


router = APIRouter(prefix="/api/personnel", tags=["personnel"])


def _database_error() -> HTTPException:
    """Return a safe error without exposing SQLite's internal message."""
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="DATABASE_ERROR",
    )


@router.post("", response_model=PersonnelResponse, status_code=status.HTTP_201_CREATED)
def create_personnel(person: PersonnelCreate) -> dict[str, object]:
    """Create one personnel record."""
    try:
        personnel_id = database.create_personnel(
            employee_id=person.employee_id,
            name=person.name,
            department=person.department,
            role=person.role,
            status=person.status,
        )
        record = database.get_personnel(personnel_id)
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="EMPLOYEE_ID_ALREADY_EXISTS",
        ) from error
    except sqlite3.Error as error:
        raise _database_error() from error
    return record  # type: ignore[return-value]


@router.get("", response_model=list[PersonnelResponse])
def list_personnel() -> list[dict[str, object]]:
    """List personnel without returning stored face embeddings."""
    try:
        return database.list_personnel()
    except sqlite3.Error as error:
        raise _database_error() from error


@router.get("/{personnel_id}", response_model=PersonnelResponse)
def get_personnel(personnel_id: int) -> dict[str, object]:
    """Get one personnel record by its database ID."""
    try:
        record = database.get_personnel(personnel_id)
    except sqlite3.Error as error:
        raise _database_error() from error
    if record is None:
        raise HTTPException(status_code=404, detail="PERSONNEL_NOT_FOUND")
    return record


@router.put("/{personnel_id}", response_model=PersonnelResponse)
def update_personnel(
    personnel_id: int, changes: PersonnelUpdate
) -> dict[str, object]:
    """Update the fields supplied in the request body."""
    updates = changes.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="NO_FIELDS_TO_UPDATE")
    for required_field in ("employee_id", "name", "status"):
        if required_field in updates and updates[required_field] is None:
            raise HTTPException(
                status_code=422,
                detail=f"{required_field.upper()}_CANNOT_BE_NULL",
            )

    try:
        record = database.update_personnel(personnel_id, updates)
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="EMPLOYEE_ID_ALREADY_EXISTS_OR_INVALID_STATUS",
        ) from error
    except sqlite3.Error as error:
        raise _database_error() from error
    if record is None:
        raise HTTPException(status_code=404, detail="PERSONNEL_NOT_FOUND")
    return record


@router.delete("/{personnel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_personnel(personnel_id: int) -> Response:
    """Delete personnel and their linked embeddings from SQLite."""
    try:
        deleted = database.delete_personnel(personnel_id)
    except sqlite3.Error as error:
        raise _database_error() from error
    if not deleted:
        raise HTTPException(status_code=404, detail="PERSONNEL_NOT_FOUND")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{personnel_id}/register-face",
    response_model=FaceRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_face(
    personnel_id: int,
    image: UploadFile = File(..., description="Image containing exactly one face"),
) -> dict[str, object]:
    """Generate and store one ArcFace embedding for an active person."""
    try:
        person = database.get_personnel(personnel_id)
    except sqlite3.Error as error:
        raise _database_error() from error
    if person is None:
        raise HTTPException(status_code=404, detail="PERSONNEL_NOT_FOUND")
    if person["status"] != "ACTIVE":
        raise HTTPException(status_code=409, detail="PERSONNEL_INACTIVE")

    try:
        image_bytes = image.file.read()
    except OSError as error:
        raise HTTPException(status_code=422, detail="INVALID_IMAGE") from error
    finally:
        image.file.close()

    face_engine = FaceEngine()
    try:
        embedding = face_engine.generate_embedding_from_bytes(image_bytes)
    except InvalidImageError as error:
        raise HTTPException(status_code=422, detail="INVALID_IMAGE") from error
    except NoFaceDetectedError as error:
        raise HTTPException(status_code=422, detail="NO_FACE_DETECTED") from error
    except MultipleFacesDetectedError as error:
        raise HTTPException(status_code=422, detail="MULTIPLE_FACES_DETECTED") from error
    except FaceEngineError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FACE_ENGINE_UNAVAILABLE",
        ) from error

    try:
        saved_embedding = database.save_face_embedding(
            personnel_id=personnel_id,
            embedding=embedding,
            model_name=MODEL_NAME,
        )
    except sqlite3.Error as error:
        raise _database_error() from error

    return {
        **saved_embedding,
        "message": "Face embedding registered successfully.",
    }
