"""Personnel route tests using a temporary SQLite database."""

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException, UploadFile

from backend import database
from backend.routes import personnel as personnel_routes
from backend.schemas import PersonnelCreate, PersonnelUpdate


class FakeRegistrationEngine:
    def generate_embedding_from_bytes(self, _image_bytes):
        return [0.25, 0.5, 0.75]


class PersonnelApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_path, self.old_dir = database.DATABASE_PATH, database.DATABASE_DIR
        database.DATABASE_PATH = Path(self.temp_dir.name) / "personnel_test.db"
        database.DATABASE_DIR = Path(self.temp_dir.name)
        database.initialize_database()

    def tearDown(self):
        database.DATABASE_PATH, database.DATABASE_DIR = self.old_path, self.old_dir
        self.temp_dir.cleanup()

    def test_create_read_update_list_and_reject_duplicate_id(self):
        person = personnel_routes.create_personnel(
            PersonnelCreate(employee_id="EMP-T1", name="Test Person")
        )
        person_id = person["id"]
        self.assertEqual(personnel_routes.get_personnel(person_id)["name"], "Test Person")
        updated = personnel_routes.update_personnel(
            person_id, PersonnelUpdate(status="INACTIVE", department="Operations")
        )
        self.assertEqual(updated["status"], "INACTIVE")
        self.assertEqual(updated["department"], "Operations")
        self.assertNotIn("embedding", personnel_routes.list_personnel()[0])

        with self.assertRaises(HTTPException) as context:
            personnel_routes.create_personnel(
                PersonnelCreate(employee_id="EMP-T1", name="Duplicate")
            )
        self.assertEqual(context.exception.status_code, 409)

    def test_face_registration_stores_arcface_vector_without_returning_it(self):
        person_id = database.create_personnel("EMP-FACE", "Face Test")
        upload = UploadFile(file=io.BytesIO(b"image-bytes"), filename="face.jpg")
        with patch.object(personnel_routes, "FaceEngine", FakeRegistrationEngine):
            response = personnel_routes.register_face(person_id, upload)

        self.assertEqual(response["model_name"], "ArcFace")
        self.assertNotIn("embedding", response)
        with database.database_connection() as connection:
            rows = connection.execute(
                "SELECT personnel_id, model_name, embedding FROM face_embeddings WHERE personnel_id = ?",
                (person_id,),
            ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["model_name"], "ArcFace")
        self.assertGreater(len(rows[0]["embedding"]), 0)

    def test_inactive_or_missing_person_cannot_register_face(self):
        inactive_id = database.create_personnel("EMP-INACTIVE", "Inactive", status="INACTIVE")
        for person_id, expected_status in ((inactive_id, 409), (999, 404)):
            upload = UploadFile(file=io.BytesIO(b"image-bytes"), filename="face.jpg")
            with self.subTest(person_id=person_id), self.assertRaises(HTTPException) as context:
                personnel_routes.register_face(person_id, upload)
            self.assertEqual(context.exception.status_code, expected_status)
        with database.database_connection() as connection:
            count = connection.execute("SELECT COUNT(*) FROM face_embeddings").fetchone()[0]
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
