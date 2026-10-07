"""Build temporary area galleries from existing SQLite relationships."""

import json
from dataclasses import dataclass

from backend import database


class AreaNotFoundError(Exception):
    """Raised when a requested area does not exist."""


class InactiveAreaError(Exception):
    """Raised when a gallery is requested for an inactive area."""


class GalleryDataError(Exception):
    """Raised when a stored embedding cannot be read."""


@dataclass(frozen=True)
class GalleryEntry:
    """One authorized person and one of their stored face embeddings."""

    personnel_id: int
    employee_id: str
    name: str
    embedding_id: int
    embedding: list[float]
    model_name: str


def get_area_gallery(area_id: int) -> list[GalleryEntry]:
    """Build an in-memory gallery for one active area.

    The database query follows permission links and only returns rows for
    active personnel with existing embeddings. Nothing is written to SQLite.
    """
    area = database.get_area(area_id)
    if area is None:
        raise AreaNotFoundError(f"Area {area_id} does not exist.")
    if area["status"] != "ACTIVE":
        raise InactiveAreaError(f"Area {area_id} is inactive.")

    rows = database.get_active_area_gallery_rows(area_id)
    gallery: list[GalleryEntry] = []
    for row in rows:
        try:
            raw_embedding = row["embedding"]
            if isinstance(raw_embedding, (bytes, bytearray, memoryview)):
                raw_embedding = bytes(raw_embedding).decode("utf-8")
            values = json.loads(raw_embedding)
            if not isinstance(values, list) or not values:
                raise ValueError("Embedding must be a non-empty list.")
            embedding = [float(value) for value in values]
            gallery.append(
                GalleryEntry(
                    personnel_id=int(row["personnel_id"]),
                    employee_id=str(row["employee_id"]),
                    name=str(row["name"]),
                    embedding_id=int(row["embedding_id"]),
                    embedding=embedding,
                    model_name=str(row["model_name"]),
                )
            )
        except (KeyError, TypeError, ValueError, UnicodeDecodeError) as error:
            raise GalleryDataError(
                f"Stored embedding data for area {area_id} could not be read."
            ) from error

    return gallery

