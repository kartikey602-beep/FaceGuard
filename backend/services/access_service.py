"""Orchestrate face comparison against an area's authorized gallery."""

from dataclasses import dataclass

from backend import database
from backend.services.face_engine import (
    FaceEngine,
    FaceEngineError,
    InvalidImageError,
    MultipleFacesDetectedError,
    NoFaceDetectedError,
)
from backend.services.gallery_service import (
    AreaNotFoundError,
    GalleryDataError,
    InactiveAreaError,
    GalleryEntry,
    get_area_gallery,
)
from backend.services.logging_service import record_access_attempt


class AreaDoesNotExistError(Exception):
    """Raised when an access check names an unknown area."""


@dataclass(frozen=True)
class AccessDecision:
    """Safe response data for a completed access attempt."""

    result: str
    area_id: int
    area_name: str
    personnel_id: int | None
    employee_id: str | None
    person_name: str | None
    match_score: float | None
    reason: str
    timestamp: str


class AccessVerificationService:
    """Compare one submitted face only with permitted area-gallery entries."""

    def __init__(self, face_engine: FaceEngine | None = None) -> None:
        self.face_engine = face_engine or FaceEngine()

    def verify(self, area_id: int, image_bytes: bytes) -> AccessDecision:
        """Return and log a grant/deny decision for a single uploaded image."""
        area = database.get_area(area_id)
        if area is None:
            # An unknown area cannot be logged because access_logs has an area FK.
            raise AreaDoesNotExistError(f"Area {area_id} does not exist.")

        if area["status"] != "ACTIVE":
            return self._deny(area, "AREA_INACTIVE", None)

        try:
            query_embedding = self.face_engine.generate_embedding_from_bytes(image_bytes)
        except (InvalidImageError, NoFaceDetectedError, MultipleFacesDetectedError) as error:
            # The attempt is logged, while the API reports the specific input error.
            record_access_attempt(area_id, "ACCESS_DENIED", reason=self._error_code(error))
            raise
        except FaceEngineError:
            record_access_attempt(area_id, "ACCESS_DENIED", reason="FACE_ENGINE_ERROR")
            raise

        try:
            gallery = get_area_gallery(area_id)
        except AreaNotFoundError as error:
            raise AreaDoesNotExistError(str(error)) from error
        except InactiveAreaError:
            # The area may have been deactivated while the image was processing.
            current_area = database.get_area(area_id)
            if current_area is None:
                raise AreaDoesNotExistError(f"Area {area_id} does not exist.")
            return self._deny(current_area, "AREA_INACTIVE", None)
        except GalleryDataError:
            record_access_attempt(area_id, "ACCESS_DENIED", reason="GALLERY_DATA_ERROR")
            raise

        # Gallery entries are already restricted to active, permitted people.
        # Skip embeddings from an incompatible model rather than comparing them.
        best_match: tuple[GalleryEntry, float] | None = None
        closest_distance: float | None = None
        try:
            for entry in gallery:
                if entry.model_name != "ArcFace":
                    continue
                comparison = self.face_engine.compare_embeddings(
                    query_embedding, entry.embedding
                )
                distance = float(comparison.distance)
                if closest_distance is None or distance < closest_distance:
                    closest_distance = distance
                if comparison.is_match and (
                    best_match is None or distance < best_match[1]
                ):
                    best_match = (entry, distance)
        except ValueError:
            record_access_attempt(
                area_id, "ACCESS_DENIED", reason="INVALID_GALLERY_EMBEDDING"
            )
            raise
        except FaceEngineError:
            record_access_attempt(area_id, "ACCESS_DENIED", reason="FACE_ENGINE_ERROR")
            raise

        if best_match is not None:
            person, distance = best_match
            log = record_access_attempt(
                area_id,
                "ACCESS_GRANTED",
                personnel_id=person.personnel_id,
                match_score=distance,
                reason="AUTHORIZED_MATCH",
            )
            return AccessDecision(
                result="ACCESS_GRANTED",
                area_id=area_id,
                area_name=str(area["name"]),
                personnel_id=person.personnel_id,
                employee_id=person.employee_id,
                person_name=person.name,
                match_score=distance,
                reason="AUTHORIZED_MATCH",
                timestamp=str(log["timestamp"]),
            )

        return self._deny(area, "NO_MATCH", closest_distance)

    @staticmethod
    def _error_code(error: FaceEngineError) -> str:
        if isinstance(error, InvalidImageError):
            return "INVALID_IMAGE"
        if isinstance(error, NoFaceDetectedError):
            return "NO_FACE_DETECTED"
        if isinstance(error, MultipleFacesDetectedError):
            return "MULTIPLE_FACES_DETECTED"
        return "FACE_ENGINE_ERROR"

    @staticmethod
    def _deny(
        area: dict[str, object], reason: str, match_score: float | None
    ) -> AccessDecision:
        log = record_access_attempt(
            int(area["id"]),
            "ACCESS_DENIED",
            match_score=match_score,
            reason=reason,
        )
        return AccessDecision(
            result="ACCESS_DENIED",
            area_id=int(area["id"]),
            area_name=str(area["name"]),
            personnel_id=None,
            employee_id=None,
            person_name=None,
            match_score=match_score,
            reason=reason,
            timestamp=str(log["timestamp"]),
        )
