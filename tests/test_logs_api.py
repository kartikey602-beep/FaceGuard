"""API tests for the read-only access-log endpoints used by the UI."""

import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

from backend import database
from backend.config import FRONTEND_DIR
from backend.routes.logs import get_log, list_logs


class AccessLogApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_path, self.old_dir = database.DATABASE_PATH, database.DATABASE_DIR
        database.DATABASE_PATH = Path(self.temp_dir.name) / "api_test.db"
        database.DATABASE_DIR = Path(self.temp_dir.name)
        database.initialize_database()
        person_id = database.create_personnel("EMP-LOG", "Log Test", "IT", "Staff")
        area_id = database.create_area("Log Test Area")
        self.log_id = database.create_access_log(
            area_id, "ACCESS_GRANTED", person_id, 0.1234, "AUTHORIZED_MATCH"
        )["id"]

    def tearDown(self):
        database.DATABASE_PATH, database.DATABASE_DIR = self.old_path, self.old_dir
        self.temp_dir.cleanup()

    def test_list_and_filter_logs(self):
        rows = list_logs()
        row = rows[0]
        self.assertEqual(row["person_name"], "Log Test")
        self.assertEqual(row["area_name"], "Log Test Area")
        self.assertEqual(row["result"], "ACCESS_GRANTED")
        self.assertNotIn("embedding", row)

        self.assertEqual(list_logs(result="ACCESS_DENIED"), [])

    def test_read_one_and_not_found(self):
        self.assertEqual(get_log(self.log_id)["id"], self.log_id)
        with self.assertRaises(HTTPException) as context:
            get_log(999)
        self.assertEqual(context.exception.status_code, 404)

    def test_frontend_pages_are_served_by_fastapi(self):
        dashboard = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
        personnel = (FRONTEND_DIR / "personnel.html").read_text(encoding="utf-8")
        self.assertIn("/js/dashboard.js", dashboard)
        self.assertIn("personnel-table", personnel)


if __name__ == "__main__":
    unittest.main()
