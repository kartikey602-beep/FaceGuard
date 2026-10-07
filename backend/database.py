"""SQLite setup and small query helpers for FaceGuard."""

import json
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from backend.config import DATABASE_DIR, DATABASE_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS personnel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    department TEXT,
    role TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'INACTIVE')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS face_embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    personnel_id INTEGER NOT NULL,
    embedding BLOB NOT NULL,
    model_name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (personnel_id) REFERENCES personnel(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS areas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'INACTIVE')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    personnel_id INTEGER NOT NULL,
    area_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (personnel_id, area_id),
    FOREIGN KEY (personnel_id) REFERENCES personnel(id) ON DELETE CASCADE,
    FOREIGN KEY (area_id) REFERENCES areas(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS access_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    personnel_id INTEGER,
    area_id INTEGER NOT NULL,
    match_score REAL,
    result TEXT NOT NULL,
    reason TEXT,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (personnel_id) REFERENCES personnel(id) ON DELETE SET NULL,
    FOREIGN KEY (area_id) REFERENCES areas(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_face_embeddings_personnel_id
    ON face_embeddings(personnel_id);
CREATE INDEX IF NOT EXISTS idx_permissions_area_id
    ON permissions(area_id);
CREATE INDEX IF NOT EXISTS idx_access_logs_timestamp
    ON access_logs(timestamp);
"""


def get_connection() -> sqlite3.Connection:
    """Open a configured connection to the project's SQLite database."""
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def database_connection() -> Iterator[sqlite3.Connection]:
    """Provide a connection that commits on success and always closes."""
    connection = get_connection()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database() -> None:
    """Create the database file, tables, and indexes if they are missing."""
    with database_connection() as connection:
        connection.executescript(SCHEMA)


def create_personnel(
    employee_id: str,
    name: str,
    department: str | None = None,
    role: str | None = None,
    status: str = "ACTIVE",
) -> int:
    """Insert a personnel record and return its new database ID."""
    with database_connection() as connection:
        cursor = connection.execute(
            """INSERT INTO personnel (employee_id, name, department, role, status)
               VALUES (?, ?, ?, ?, ?)""",
            (employee_id, name, department, role or None, status),
        )
        return int(cursor.lastrowid)


def list_personnel() -> list[dict[str, object]]:
    """Return all personnel records without biometric data."""
    with database_connection() as connection:
        rows = connection.execute(
            """SELECT id, employee_id, name, department, role, status, created_at
               FROM personnel ORDER BY id"""
        ).fetchall()
        return [dict(row) for row in rows]


def get_personnel(personnel_id: int) -> dict[str, object] | None:
    """Return one personnel record, or None when it does not exist."""
    with database_connection() as connection:
        row = connection.execute(
            """SELECT id, employee_id, name, department, role, status, created_at
               FROM personnel WHERE id = ?""",
            (personnel_id,),
        ).fetchone()
        return dict(row) if row is not None else None


def update_personnel(
    personnel_id: int, updates: dict[str, object]
) -> dict[str, object] | None:
    """Update supplied personnel fields and return the safe public record."""
    allowed_fields = {"employee_id", "name", "department", "role", "status"}
    if not updates or not set(updates).issubset(allowed_fields):
        raise ValueError("No valid personnel fields were provided.")

    columns = ", ".join(f"{field} = ?" for field in updates)
    values = list(updates.values()) + [personnel_id]
    with database_connection() as connection:
        cursor = connection.execute(
            f"UPDATE personnel SET {columns} WHERE id = ?", values
        )
        if cursor.rowcount == 0:
            return None
        row = connection.execute(
            """SELECT id, employee_id, name, department, role, status, created_at
               FROM personnel WHERE id = ?""",
            (personnel_id,),
        ).fetchone()
        return dict(row)


def delete_personnel(personnel_id: int) -> bool:
    """Delete a person; SQLite removes linked embeddings through the foreign key."""
    with database_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM personnel WHERE id = ?", (personnel_id,)
        )
        return cursor.rowcount > 0


def create_area(
    name: str,
    description: str | None = None,
    status: str = "ACTIVE",
) -> int:
    """Insert an area and return its new database ID."""
    with database_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO areas (name, description, status) VALUES (?, ?, ?)",
            (name, description, status),
        )
        return int(cursor.lastrowid)


def list_areas() -> list[dict[str, object]]:
    """Return all areas."""
    with database_connection() as connection:
        rows = connection.execute(
            "SELECT id, name, description, status, created_at FROM areas ORDER BY id"
        ).fetchall()
        return [dict(row) for row in rows]


def get_area(area_id: int) -> dict[str, object] | None:
    """Return one area, or None when it does not exist."""
    with database_connection() as connection:
        row = connection.execute(
            "SELECT id, name, description, status, created_at FROM areas WHERE id = ?",
            (area_id,),
        ).fetchone()
        return dict(row) if row is not None else None


def update_area(area_id: int, updates: dict[str, object]) -> dict[str, object] | None:
    """Update supplied area fields and return the updated record."""
    allowed_fields = {"name", "description", "status"}
    if not updates or not set(updates).issubset(allowed_fields):
        raise ValueError("No valid area fields were provided.")

    columns = ", ".join(f"{field} = ?" for field in updates)
    values = list(updates.values()) + [area_id]
    with database_connection() as connection:
        cursor = connection.execute(
            f"UPDATE areas SET {columns} WHERE id = ?", values
        )
        if cursor.rowcount == 0:
            return None
        row = connection.execute(
            "SELECT id, name, description, status, created_at FROM areas WHERE id = ?",
            (area_id,),
        ).fetchone()
        return dict(row)


def delete_area(area_id: int) -> bool:
    """Delete an area; SQLite rejects deletion if access logs reference it."""
    with database_connection() as connection:
        cursor = connection.execute("DELETE FROM areas WHERE id = ?", (area_id,))
        return cursor.rowcount > 0


def grant_permission(personnel_id: int, area_id: int) -> dict[str, object]:
    """Create one personnel-to-area link and return its metadata."""
    with database_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO permissions (personnel_id, area_id) VALUES (?, ?)",
            (personnel_id, area_id),
        )
        row = connection.execute(
            """SELECT id, personnel_id, area_id, created_at
               FROM permissions WHERE id = ?""",
            (cursor.lastrowid,),
        ).fetchone()
        return dict(row)


def revoke_permission(personnel_id: int, area_id: int) -> bool:
    """Remove a permission; return True if a row was removed."""
    with database_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM permissions WHERE personnel_id = ? AND area_id = ?",
            (personnel_id, area_id),
        )
        return cursor.rowcount > 0


def list_area_permissions(area_id: int) -> list[dict[str, object]]:
    """List personnel connected to an area, without retrieving embeddings."""
    with database_connection() as connection:
        rows = connection.execute(
            """SELECT p.id AS personnel_id, p.employee_id, p.name,
                      p.department, p.role, p.status,
                      permissions.created_at AS permission_created_at
               FROM permissions
               JOIN personnel AS p ON p.id = permissions.personnel_id
               WHERE permissions.area_id = ?
               ORDER BY p.name, p.id""",
            (area_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_active_area_gallery_rows(area_id: int) -> list[dict[str, object]]:
    """Read embeddings only for active people permitted in an active area."""
    with database_connection() as connection:
        rows = connection.execute(
            """SELECT p.id AS personnel_id, p.employee_id, p.name,
                      fe.id AS embedding_id, fe.embedding, fe.model_name
               FROM permissions AS perm
               JOIN areas AS a ON a.id = perm.area_id
               JOIN personnel AS p ON p.id = perm.personnel_id
               JOIN face_embeddings AS fe ON fe.personnel_id = p.id
               WHERE perm.area_id = ?
                 AND a.status = 'ACTIVE'
                 AND p.status = 'ACTIVE'
               ORDER BY p.id, fe.id""",
            (area_id,),
        ).fetchall()
        return [dict(row) for row in rows]

def save_face_embedding(
    personnel_id: int, embedding: list[float], model_name: str
) -> dict[str, object]:
    """Serialize and save an embedding; return metadata but never the vector."""
    serialized_embedding = json.dumps(embedding, separators=(",", ":")).encode("utf-8")
    with database_connection() as connection:
        cursor = connection.execute(
            """INSERT INTO face_embeddings (personnel_id, embedding, model_name)
               VALUES (?, ?, ?)""",
            (personnel_id, sqlite3.Binary(serialized_embedding), model_name),
        )
        row = connection.execute(
            """SELECT id, personnel_id, model_name, created_at
               FROM face_embeddings WHERE id = ?""",
            (cursor.lastrowid,),
        ).fetchone()
        return dict(row)


def create_access_log(
    area_id: int,
    result: str,
    personnel_id: int | None = None,
    match_score: float | None = None,
    reason: str | None = None,
) -> dict[str, object]:
    """Record an access attempt and return its public log metadata."""
    with database_connection() as connection:
        cursor = connection.execute(
            """INSERT INTO access_logs
               (personnel_id, area_id, match_score, result, reason)
               VALUES (?, ?, ?, ?, ?)""",
            (personnel_id, area_id, match_score, result, reason),
        )
        row = connection.execute(
            "SELECT id, timestamp FROM access_logs WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return dict(row)


def list_access_logs(
    area_id: int | None = None,
    result: str | None = None,
    date: str | None = None,
    personnel_id: int | None = None,
) -> list[dict[str, object]]:
    """Return access logs with display names, never biometric data."""
    conditions: list[str] = []
    values: list[object] = []
    if area_id is not None:
        conditions.append("logs.area_id = ?")
        values.append(area_id)
    if result is not None:
        conditions.append("logs.result = ?")
        values.append(result)
    if date is not None:
        conditions.append("date(logs.timestamp) = ?")
        values.append(date)
    if personnel_id is not None:
        conditions.append("logs.personnel_id = ?")
        values.append(personnel_id)

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    with database_connection() as connection:
        rows = connection.execute(
            """SELECT logs.id, logs.personnel_id,
                      COALESCE(personnel.name, 'Unknown') AS person_name,
                      personnel.employee_id, logs.area_id, areas.name AS area_name,
                      logs.match_score, logs.result, logs.reason, logs.timestamp
               FROM access_logs AS logs
               LEFT JOIN personnel ON personnel.id = logs.personnel_id
               JOIN areas ON areas.id = logs.area_id"""
            + where_clause
            + " ORDER BY logs.timestamp DESC, logs.id DESC",
            values,
        ).fetchall()
        return [dict(row) for row in rows]


def get_access_log(log_id: int) -> dict[str, object] | None:
    """Return one access log with display names, or None if absent."""
    with database_connection() as connection:
        row = connection.execute(
            """SELECT logs.id, logs.personnel_id,
                      COALESCE(personnel.name, 'Unknown') AS person_name,
                      personnel.employee_id, logs.area_id, areas.name AS area_name,
                      logs.match_score, logs.result, logs.reason, logs.timestamp
               FROM access_logs AS logs
               LEFT JOIN personnel ON personnel.id = logs.personnel_id
               JOIN areas ON areas.id = logs.area_id
               WHERE logs.id = ?""",
            (log_id,),
        ).fetchone()
        return dict(row) if row is not None else None



