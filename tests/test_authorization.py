"""Authorization permission route tests with isolated SQLite state."""

import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

from backend import database
from backend.routes.areas import create_permission, delete_permission, list_area_permissions


class PermissionApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_path, self.old_dir = database.DATABASE_PATH, database.DATABASE_DIR
        database.DATABASE_PATH = Path(self.temp_dir.name) / "permission_test.db"
        database.DATABASE_DIR = Path(self.temp_dir.name)
        database.initialize_database()
        self.active_person = database.create_personnel("EMP-A", "Active Person")
        self.inactive_person = database.create_personnel(
            "EMP-I", "Inactive Person", status="INACTIVE"
        )
        self.active_area = database.create_area("Active Room")
        self.inactive_area = database.create_area("Inactive Room", status="INACTIVE")

    def tearDown(self):
        database.DATABASE_PATH, database.DATABASE_DIR = self.old_path, self.old_dir
        self.temp_dir.cleanup()

    def test_grant_list_revoke_and_duplicate_prevention(self):
        permission = create_permission(self.active_area, self.active_person)
        self.assertEqual(permission["personnel_id"], self.active_person)
        self.assertEqual(
            list_area_permissions(self.active_area)[0]["name"], "Active Person"
        )
        with self.assertRaises(HTTPException) as context:
            create_permission(self.active_area, self.active_person)
        self.assertEqual(context.exception.status_code, 409)
        response = delete_permission(self.active_area, self.active_person)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(list_area_permissions(self.active_area), [])

    def test_inactive_and_missing_records_are_rejected(self):
        cases = (
            (self.active_area, self.inactive_person, 409),
            (self.inactive_area, self.active_person, 409),
            (999, self.active_person, 404),
            (self.active_area, 999, 404),
        )
        for area_id, person_id, status_code in cases:
            with self.subTest(area_id=area_id, person_id=person_id):
                with self.assertRaises(HTTPException) as context:
                    create_permission(area_id, person_id)
                self.assertEqual(context.exception.status_code, status_code)


if __name__ == "__main__":
    unittest.main()
