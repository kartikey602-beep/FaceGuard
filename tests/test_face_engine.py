"""Small command-line check for the isolated FaceGuard face engine.

Run as a module from the project root and pass one or two face image paths.
"""

import argparse
import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

from backend.services.face_engine import FaceEngine, FaceEngineError


def main() -> int:
    # DeepFace may print Unicode startup messages; use UTF-8 in Windows consoles.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Try the FaceGuard ArcFace engine.")
    parser.add_argument("image_one", type=Path, help="First image with one face")
    parser.add_argument(
        "image_two",
        type=Path,
        nargs="?",
        help="Optional second image to compare with the first",
    )
    expected = parser.add_mutually_exclusive_group()
    expected.add_argument(
        "--expect-match", action="store_true", help="Require a match result"
    )
    expected.add_argument(
        "--expect-no-match", action="store_true", help="Require a non-match result"
    )
    args = parser.parse_args()

    engine = FaceEngine()
    try:
        first_embedding = engine.generate_embedding(args.image_one)
        print(f"First image: one face detected; embedding length={len(first_embedding)}")
        if args.image_two is None:
            return 0

        second_embedding = engine.generate_embedding(args.image_two)
        result = engine.compare_embeddings(first_embedding, second_embedding)
        print(f"Distance: {result.distance:.6f}")
        print(f"Threshold: {result.threshold:.6f}")
        print(f"Match: {result.is_match}")

        if args.expect_match and not result.is_match:
            print("Expected these images to match, but they did not.")
            return 1
        if args.expect_no_match and result.is_match:
            print("Expected these images not to match, but they did.")
            return 1
        return 0
    except FaceEngineError as error:
        print(f"Face engine error: {error}")
        return 2


class FakeDeepFace:
    """A predictable DeepFace substitute for fast unit tests."""

    faces = [{"embedding": [0.1, 0.2], "facial_area": {"x": 1, "y": 2, "w": 3, "h": 4}}]

    @classmethod
    def represent(cls, **_kwargs):
        return cls.faces

    @staticmethod
    def verify(**_kwargs):
        return {"verified": True, "distance": 0.12, "threshold": 0.4}


class FaceEngineUnitTests(unittest.TestCase):
    def setUp(self):
        self.engine = FaceEngine(threshold=0.4)
        self.engine._deepface = FakeDeepFace
        ok, encoded = cv2.imencode(".jpg", np.zeros((32, 32, 3), dtype=np.uint8))
        self.assertTrue(ok)
        self.image_bytes = encoded.tobytes()

    def test_generates_embedding_for_one_detected_face(self):
        FakeDeepFace.faces = [{"embedding": [0.1, 0.2], "facial_area": {"x": 1, "y": 2, "w": 3, "h": 4}}]
        self.assertEqual(self.engine.generate_embedding_from_bytes(self.image_bytes), [0.1, 0.2])

    def test_rejects_no_face_and_multiple_faces(self):
        from backend.services.face_engine import MultipleFacesDetectedError, NoFaceDetectedError

        FakeDeepFace.faces = []
        with self.assertRaises(NoFaceDetectedError):
            self.engine.generate_embedding_from_bytes(self.image_bytes)
        FakeDeepFace.faces = [{"embedding": [0.1]}, {"embedding": [0.2]}]
        with self.assertRaises(MultipleFacesDetectedError):
            self.engine.generate_embedding_from_bytes(self.image_bytes)

    def test_rejects_unreadable_image(self):
        from backend.services.face_engine import InvalidImageError

        with self.assertRaises(InvalidImageError):
            self.engine.generate_embedding_from_bytes(b"not an image")

    def test_comparison_uses_threshold_and_returns_distance(self):
        result = self.engine.compare_embeddings([0.1, 0.2], [0.2, 0.1])
        self.assertTrue(result.is_match)
        self.assertEqual(result.distance, 0.12)
        self.assertEqual(result.threshold, 0.4)

    def test_threshold_validation(self):
        with self.assertRaises(ValueError):
            FaceEngine(threshold=2.1)


if __name__ == "__main__":
    raise SystemExit(main())
