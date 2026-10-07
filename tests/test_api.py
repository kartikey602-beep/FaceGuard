"""FastAPI route/schema and frontend integration smoke checks."""

import unittest

from backend.config import FRONTEND_DIR
from backend.main import app


class ApiIntegrationTests(unittest.TestCase):
    def test_required_api_routes_are_registered(self):
        paths = app.openapi()["paths"]
        self.assertIn("/api/access/verify", paths)
        self.assertIn("/api/logs", paths)
        self.assertIn("/api/logs/{log_id}", paths)
        self.assertIn("/api/personnel", paths)
        self.assertIn("/api/areas", paths)

    def test_public_response_schemas_do_not_include_embeddings(self):
        schemas = app.openapi()["components"]["schemas"]
        for name in ("PersonnelResponse", "FaceRegistrationResponse", "AccessVerifyResponse"):
            with self.subTest(schema=name):
                self.assertNotIn("embedding", schemas[name]["properties"])

    def test_all_dashboard_pages_reference_shared_styles_and_scripts(self):
        pages = ("index.html", "personnel.html", "verification.html", "areas.html", "logs.html")
        for page_name in pages:
            with self.subTest(page=page_name):
                content = (FRONTEND_DIR / page_name).read_text(encoding="utf-8")
                self.assertIn("/css/style.css", content)
                self.assertIn("/js/app.js", content)


if __name__ == "__main__":
    unittest.main()
