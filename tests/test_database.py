"""SQLite schema, relationship, and privacy checks."""

import tempfile
import sqlite3
import unittest
from pathlib import Path

from backend import database


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_path, self.old_dir = database.DATABASE_PATH, database.DATABASE_DIR
        database.DATABASE_PATH = Path(self.temp_dir.name) / "database_test.db"
        database.DATABASE_DIR = Path(self.temp_dir.name)
        database.initialize_database()

    def tearDown(self):
        database.DATABASE_PATH, database.DATABASE_DIR = self.old_path, self.old_dir
        self.temp_dir.cleanup()

    def test_required_tables_exist_without_gallery_table(self):
        with database.database_connection() as connection:
            names = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        self.assertTrue(
            {"personnel", "face_embeddings", "areas", "permissions", "access_logs"}
            .issubset(names)
        )
        self.assertNotIn("gallery", names)

    def test_foreign_keys_are_enabled_and_enforced(self):
        with database.database_connection() as connection:
            self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO face_embeddings (personnel_id, embedding, model_name) VALUES (999, ?, 'ArcFace')",
                    (b"[]",),
                )

    def test_person_and_area_log_relationships(self):
        person_id = database.create_personnel("DB-1", "Database Test")
        area_id = database.create_area("Database Area")
        database.grant_permission(person_id, area_id)
        embedding = database.save_face_embedding(person_id, [0.1, 0.2], "ArcFace")
        log = database.create_access_log(area_id, "ACCESS_GRANTED", person_id, 0.1)

        self.assertEqual(embedding["personnel_id"], person_id)
        self.assertEqual(database.get_access_log(log["id"])["area_name"], "Database Area")
        self.assertTrue(database.revoke_permission(person_id, area_id))


if __name__ == "__main__":
    unittest.main()
