"""Small configuration module for paths and face matching."""

import os
from pathlib import Path

# The project root is the parent of this backend package.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DATABASE_DIR = PROJECT_ROOT / "database"
DATABASE_PATH = DATABASE_DIR / "faceguard.db"

# Optional override. If unset, DeepFace uses its ArcFace/cosine default.
FACE_MATCH_THRESHOLD = os.getenv("FACE_MATCH_THRESHOLD") or None
