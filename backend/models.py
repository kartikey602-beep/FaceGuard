"""Simple Python records matching the FaceGuard database tables."""

from dataclasses import dataclass


@dataclass
class Personnel:
    id: int
    employee_id: str
    name: str
    department: str | None
    role: str | None
    status: str
    created_at: str


@dataclass
class FaceEmbedding:
    id: int
    personnel_id: int
    embedding: bytes
    model_name: str
    created_at: str


@dataclass
class Area:
    id: int
    name: str
    description: str | None
    status: str
    created_at: str


@dataclass
class Permission:
    id: int
    personnel_id: int
    area_id: int
    created_at: str


@dataclass
class AccessLog:
    id: int
    personnel_id: int | None
    area_id: int
    match_score: float | None
    result: str
    reason: str | None
    timestamp: str
