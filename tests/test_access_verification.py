"""Focused tests for area-scoped access verification and access logging."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from backend import database
from backend.services.access_service import (
    AccessVerificationService,
    AreaDoesNotExistError,
)
from backend.services.face_engine import (
    InvalidImageError,
    MultipleFacesDetectedError,
    NoFaceDetectedError,
)


class FakeFaceEngine:
    """Avoid downloading/running ArcFace weights in database/service tests."""

    def __init__(self, image_embeddings=None, error=None):
        self.image_embeddings = image_embeddings or {b"kartikey": [1.0, 0.0]}
        self.error = error
        self.compared_references = []

    def generate_embedding_from_bytes(self, image_bytes):
        if self.error:
            raise self.error("test image error")
        return self.image_embeddings[image_bytes]

    def compare_embeddings(self, query, reference):
        self.compared_references.append(reference)
        is_match = query == reference
        distance = 0.08 if is_match else 0.75
        return SimpleNamespace(is_match=is_match, distance=distance)


class AccessVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_faceguard.db"
        self.old_path = database.DATABASE_PATH
        self.old_dir = database.DATABASE_DIR
        database.DATABASE_PATH = self.db_path
        database.DATABASE_DIR = self.db_path.parent
        database.initialize_database()

        # Keep the sample IDs used in the project specification: area 1 and
        # Kartikey Test (personnel 2 / EMP-001).
        database.create_personnel("PLACEHOLDER", "Placeholder")
        database.create_personnel("EMP-001", "Kartikey Test", "Testing", "Employee")
        database.create_personnel("EMP-002", "Not Permitted", "Testing", "Employee")
        database.create_personnel("EMP-003", "No Face", "Testing", "Employee")
        database.create_area("Server Room", "Restricted test area")
        database.grant_permission(2, 1)
        database.save_face_embedding(2, [1.0, 0.0], "ArcFace")
        database.save_face_embedding(3, [0.0, 1.0], "ArcFace")

    def tearDown(self):
        database.DATABASE_PATH = self.old_path
        database.DATABASE_DIR = self.old_dir
        self.temp_dir.cleanup()

    def test_permitted_person_is_granted_and_logged(self):
        service = AccessVerificationService(FakeFaceEngine())
        decision = service.verify(1, b"kartikey")

        self.assertEqual(decision.result, "ACCESS_GRANTED")
        self.assertEqual(decision.personnel_id, 2)
        self.assertEqual(decision.employee_id, "EMP-001")
        self.assertEqual(decision.match_score, 0.08)
        self.assertTrue(self._logs()[0]["timestamp"])
        self.assertEqual(self._logs()[0]["result"], "ACCESS_GRANTED")

    def test_unpermitted_person_is_not_searched(self):
        engine = FakeFaceEngine({b"other-person": [0.0, 1.0]})
        decision = AccessVerificationService(engine).verify(1, b"other-person")

        self.assertEqual(decision.result, "ACCESS_DENIED")
        self.assertIsNone(decision.personnel_id)
        self.assertEqual(engine.compared_references, [[1.0, 0.0]])
        self.assertEqual(self._logs()[0]["reason"], "NO_MATCH")

    def test_inactive_area_is_denied_without_face_processing(self):
        database.update_area(1, {"status": "INACTIVE"})
        engine = FakeFaceEngine(error=InvalidImageError)

        decision = AccessVerificationService(engine).verify(1, b"anything")
        self.assertEqual(decision.reason, "AREA_INACTIVE")
        self.assertEqual(self._logs()[0]["reason"], "AREA_INACTIVE")

    def test_unknown_area_returns_error(self):
        with self.assertRaises(AreaDoesNotExistError):
            AccessVerificationService(FakeFaceEngine()).verify(99, b"kartikey")

    def test_face_input_errors_are_logged_before_being_returned(self):
        for error_type, expected_reason in (
            (InvalidImageError, "INVALID_IMAGE"),
            (NoFaceDetectedError, "NO_FACE_DETECTED"),
            (MultipleFacesDetectedError, "MULTIPLE_FACES_DETECTED"),
        ):
            with self.subTest(error=error_type.__name__):
                engine = FakeFaceEngine(error=error_type)
                with self.assertRaises(error_type):
                    AccessVerificationService(engine).verify(1, b"bad-image")
                self.assertEqual(self._logs()[-1]["reason"], expected_reason)

    @staticmethod
    def _logs():
        with database.database_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM access_logs ORDER BY id"
            ).fetchall()
            return [dict(row) for row in rows]


if __name__ == "__main__":
    unittest.main()
