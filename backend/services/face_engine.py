"""Face detection and ArcFace embedding helpers.

This module has no API, authorization, or database responsibilities.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from backend.config import FACE_MATCH_THRESHOLD


MODEL_NAME = "ArcFace"
DETECTOR_BACKEND = "opencv"
DISTANCE_METRIC = "cosine"


class FaceEngineError(Exception):
    """Base error for image or face-processing problems."""


class InvalidImageError(FaceEngineError):
    """The image file is missing, unreadable, or not a supported image."""


class NoFaceDetectedError(FaceEngineError):
    """The image did not contain a detectable face."""


class MultipleFacesDetectedError(FaceEngineError):
    """The image contained more than one detectable face."""


@dataclass(frozen=True)
class FaceDetection:
    """Bounding box for the one face accepted by this engine."""

    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class FaceMatchResult:
    """Result of comparing two face embeddings using cosine distance."""

    is_match: bool
    distance: float
    threshold: float
    model_name: str = MODEL_NAME
    distance_metric: str = DISTANCE_METRIC


class FaceEngine:
    """Use DeepFace's pretrained ArcFace model for face embeddings."""

    def __init__(self, threshold: float | None = None) -> None:
        # An explicit argument takes priority over the environment setting.
        configured_threshold = (
            threshold if threshold is not None else FACE_MATCH_THRESHOLD
        )
        self.threshold = self._parse_threshold(configured_threshold)
        self._deepface: Any | None = None

    @staticmethod
    def _parse_threshold(value: float | str | None) -> float | None:
        """Read the optional cosine-distance threshold and validate its range."""
        if value is None or value == "":
            return None
        try:
            parsed = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError("FACE_MATCH_THRESHOLD must be a number.") from error
        if not np.isfinite(parsed) or not 0 <= parsed <= 2:
            raise ValueError(
                "The ArcFace cosine-distance threshold must be between 0 and 2."
            )
        return parsed

    def _get_deepface(self) -> Any:
        """Import DeepFace only when recognition is first requested."""
        if self._deepface is None:
            try:
                from deepface import DeepFace
            except ImportError as error:
                raise FaceEngineError(
                    "DeepFace is not installed. Install requirements.txt first."
                ) from error
            self._deepface = DeepFace
        return self._deepface

    @staticmethod
    def load_image(image_source: str | Path | bytes | bytearray) -> np.ndarray:
        """Read an image from disk as an OpenCV BGR image."""
        if isinstance(image_source, (bytes, bytearray)):
            if not image_source:
                raise InvalidImageError("The uploaded image is empty.")
            try:
                image = cv2.imdecode(
                    np.frombuffer(image_source, dtype=np.uint8), cv2.IMREAD_COLOR
                )
            except cv2.error as error:
                raise InvalidImageError("The uploaded file is not a readable image.") from error
            if image is None or image.size == 0:
                raise InvalidImageError("The uploaded file is not a readable image.")
            return image

        path = Path(image_source)
        if not path.is_file():
            raise InvalidImageError(f"Image file does not exist: {path}")
        try:
            image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        except (cv2.error, OSError) as error:
            raise InvalidImageError(f"Could not read image: {path}") from error
        if image is None or image.size == 0:
            raise InvalidImageError(f"File is not a readable image: {path}")
        return image

    def _get_single_face(
        self, image_source: str | Path | bytes | bytearray
    ) -> tuple[dict[str, Any], np.ndarray]:
        """Detect faces and create internal ArcFace output for a single image."""
        image = self.load_image(image_source)
        deepface = self._get_deepface()
        try:
            faces = deepface.represent(
                img_path=image,
                model_name=MODEL_NAME,
                detector_backend=DETECTOR_BACKEND,
                enforce_detection=True,
                align=True,
                max_faces=2,
            )
        except Exception as error:
            # DeepFace raises this message when its detector finds no face.
            if "face could not be detected" in str(error).lower():
                raise NoFaceDetectedError(
                    "No face detected. Use a clear image showing one face."
                ) from error
            raise FaceEngineError("DeepFace could not process this image.") from error

        if not faces:
            raise NoFaceDetectedError("No face detected in the image.")
        if len(faces) > 1:
            raise MultipleFacesDetectedError(
                "Multiple faces detected. Please provide one person at a time."
            )

        embedding = np.asarray(faces[0].get("embedding"), dtype=np.float64)
        if embedding.ndim != 1 or embedding.size == 0:
            raise FaceEngineError("ArcFace returned an invalid embedding.")
        if not np.all(np.isfinite(embedding)):
            raise FaceEngineError("ArcFace returned non-finite embedding values.")
        return faces[0], embedding

    def detect_face(self, image_path: str | Path | bytes | bytearray) -> FaceDetection:
        """Validate that exactly one face is present and return its box."""
        face, _ = self._get_single_face(image_path)
        area = face.get("facial_area") or {}
        try:
            return FaceDetection(
                x=int(area["x"]),
                y=int(area["y"]),
                width=int(area["w"]),
                height=int(area["h"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise FaceEngineError("DeepFace returned an invalid face location.") from error

    def generate_embedding(self, image_path: str | Path | bytes | bytearray) -> list[float]:
        """Return the ArcFace vector for the one face in an image."""
        _, embedding = self._get_single_face(image_path)
        return embedding.tolist()

    def generate_embedding_from_bytes(self, image_bytes: bytes) -> list[float]:
        """Generate an embedding from an uploaded image without saving it."""
        _, embedding = self._get_single_face(image_bytes)
        return embedding.tolist()
    def compare_embeddings(
        self,
        first: list[float],
        second: list[float],
        threshold: float | None = None,
    ) -> FaceMatchResult:
        """Compare two ArcFace vectors; smaller cosine distance means closer."""
        first_vector = self._validate_embedding(first, "first")
        second_vector = self._validate_embedding(second, "second")
        if first_vector.shape != second_vector.shape:
            raise ValueError("Face embeddings must have the same dimensions.")

        selected_threshold = (
            self.threshold if threshold is None else self._parse_threshold(threshold)
        )
        deepface = self._get_deepface()
        try:
            result = deepface.verify(
                img1_path=first_vector.tolist(),
                img2_path=second_vector.tolist(),
                model_name=MODEL_NAME,
                distance_metric=DISTANCE_METRIC,
                threshold=selected_threshold,
                enforce_detection=False,
                silent=True,
            )
        except Exception as error:
            raise FaceEngineError("DeepFace could not compare these embeddings.") from error

        return FaceMatchResult(
            is_match=bool(result["verified"]),
            distance=float(result["distance"]),
            threshold=float(result["threshold"]),
        )

    @staticmethod
    def _validate_embedding(values: list[float], label: str) -> np.ndarray:
        """Check that a saved or incoming vector can be compared safely."""
        try:
            vector = np.asarray(values, dtype=np.float64)
        except (TypeError, ValueError) as error:
            raise ValueError(f"The {label} embedding must contain numbers.") from error
        if vector.ndim != 1 or vector.size == 0:
            raise ValueError(f"The {label} embedding must be a non-empty vector.")
        if not np.all(np.isfinite(vector)):
            raise ValueError(f"The {label} embedding must contain finite values.")
        if np.linalg.norm(vector) == 0:
            raise ValueError(f"The {label} embedding cannot be a zero vector.")
        return vector


