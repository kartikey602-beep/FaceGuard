"""Access verification endpoint."""

import sqlite3

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.schemas import (
    AccessAreaResponse,
    AccessPersonResponse,
    AccessVerifyResponse,
)
from backend.services.access_service import (
    AccessVerificationService,
    AreaDoesNotExistError,
)
from backend.services.face_engine import (
    FaceEngineError,
    InvalidImageError,
    MultipleFacesDetectedError,
    NoFaceDetectedError,
)
from backend.services.gallery_service import GalleryDataError


router = APIRouter(prefix="/api/access", tags=["access"])
service = AccessVerificationService()


@router.post("/verify", response_model=AccessVerifyResponse)
async def verify_access(
    area_id: int = Form(..., description="Area being checked"),
    image: UploadFile = File(..., description="Image containing one face"),
) -> AccessVerifyResponse:
    """Check the uploaded face against only this area's authorized gallery."""
    try:
        image_bytes = await image.read()
    except OSError as error:
        raise HTTPException(status_code=422, detail="INVALID_IMAGE") from error
    finally:
        await image.close()
    try:
        decision = service.verify(area_id, image_bytes)
    except AreaDoesNotExistError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except FaceEngineError as error:
        # Image and face-count errors have already been logged by the service.
        if isinstance(
            error,
            (InvalidImageError, NoFaceDetectedError, MultipleFacesDetectedError),
        ):
            raise HTTPException(status_code=422, detail=str(error)) from error
        raise HTTPException(status_code=503, detail=str(error)) from error
    except GalleryDataError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=500, detail="Stored face data could not be compared.") from error
    except sqlite3.Error as error:
        raise HTTPException(status_code=500, detail="Could not record or load access data.") from error

    person = None
    if decision.personnel_id is not None:
        person = AccessPersonResponse(
            personnel_id=decision.personnel_id,
            employee_id=str(decision.employee_id),
            name=str(decision.person_name),
        )
    return AccessVerifyResponse(
        result=decision.result,
        area=AccessAreaResponse(area_id=decision.area_id, name=decision.area_name),
        person=person,
        match_score=decision.match_score,
        reason=decision.reason,
        timestamp=decision.timestamp,
    )

