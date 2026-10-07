"""Tests for temporary, permission-derived area galleries."""

import tempfile
import unittest
from pathlib import Path

from backend import database
from backend.services.gallery_service import (
    AreaNotFoundError,
    GalleryEntry,
    InactiveAreaError,
    get_area_gallery,
)


class AreaGalleryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_database_dir = database.DATABASE_DIR
        self.original_database_path = database.DATABASE_PATH
        database.DATABASE_DIR = Path(self.temp_directory.name)
        database.DATABASE_PATH = database.DATABASE_DIR / "test_faceguard.db"
        database.initialize_database()

        self.active_area_id = database.create_area("Active Lab")
        self.inactive_area_id = database.create_area("Closed Lab", status="INACTIVE")
        self.person_id = database.create_personnel("EMP-100", "Authorized Person")
        self.unauthorized_person_id = database.create_personnel(
            "EMP-200", "No Permission"
        )
        self.inactive_person_id = database.create_personnel(
            "EMP-300", "Inactive Person", status="INACTIVE"
        )
        self.no_face_person_id = database.create_personnel("EMP-400", "No Face")

    def tearDown(self) -> None:
        database.DATABASE_DIR = self.original_database_dir
        database.DATABASE_PATH = self.original_database_path
        self.temp_directory.cleanup()

    def test_gallery_includes_only_permitted_active_people_with_faces(self) -> None:
        database.grant_permission(self.person_id, self.active_area_id)
        database.grant_permission(self.inactive_person_id, self.active_area_id)
        database.grant_permission(self.no_face_person_id, self.active_area_id)
        database.save_face_embedding(self.person_id, [0.1, 0.2, 0.3], "ArcFace")
        database.save_face_embedding(
            self.unauthorized_person_id, [0.4, 0.5, 0.6], "ArcFace"
        )
        database.save_face_embedding(
            self.inactive_person_id, [0.7, 0.8, 0.9], "ArcFace"
        )

        gallery = get_area_gallery(self.active_area_id)

        self.assertEqual(len(gallery), 1)
        self.assertIsInstance(gallery[0], GalleryEntry)
        self.assertEqual(gallery[0].personnel_id, self.person_id)
        self.assertEqual(gallery[0].employee_id, "EMP-100")
        self.assertEqual(gallery[0].name, "Authorized Person")
        self.assertEqual(gallery[0].embedding, [0.1, 0.2, 0.3])
        self.assertEqual(gallery[0].model_name, "ArcFace")

    def test_permission_changes_are_visible_on_the_next_call(self) -> None:
        database.save_face_embedding(self.person_id, [0.1, 0.2], "ArcFace")

        self.assertEqual(get_area_gallery(self.active_area_id), [])
        database.grant_permission(self.person_id, self.active_area_id)
        self.assertEqual(len(get_area_gallery(self.active_area_id)), 1)
        database.revoke_permission(self.person_id, self.active_area_id)
        self.assertEqual(get_area_gallery(self.active_area_id), [])

    def test_inactive_and_missing_areas_do_not_return_galleries(self) -> None:
        with self.assertRaises(InactiveAreaError):
            get_area_gallery(self.inactive_area_id)
        with self.assertRaises(AreaNotFoundError):
            get_area_gallery(99999)

    def test_multiple_embeddings_are_returned_without_database_copies(self) -> None:
        database.grant_permission(self.person_id, self.active_area_id)
        database.save_face_embedding(self.person_id, [0.1, 0.2], "ArcFace")
        database.save_face_embedding(self.person_id, [0.2, 0.3], "ArcFace")

        connection = database.get_connection()
        try:
            before_count = connection.execute(
                "SELECT COUNT(*) FROM face_embeddings WHERE personnel_id = ?",
                (self.person_id,),
            ).fetchone()[0]
            gallery_tables = connection.execute(
                """SELECT name FROM sqlite_master
                   WHERE type = 'table' AND lower(name) = 'gallery'"""
            ).fetchall()
        finally:
            connection.close()

        gallery = get_area_gallery(self.active_area_id)

        connection = database.get_connection()
        try:
            after_count = connection.execute(
                "SELECT COUNT(*) FROM face_embeddings WHERE personnel_id = ?",
                (self.person_id,),
            ).fetchone()[0]
        finally:
            connection.close()

        self.assertEqual(len(gallery), 2)
        self.assertEqual(before_count, 2)
        self.assertEqual(after_count, before_count)
        self.assertEqual(gallery_tables, [])


if __name__ == "__main__":
    unittest.main()
