"""Pydantic request and response shapes for the personnel API."""

from typing import Literal

from pydantic import BaseModel, Field


PersonnelStatus = Literal["ACTIVE", "INACTIVE"]


class PersonnelCreate(BaseModel):
    employee_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    department: str | None = None
    role: str | None = None
    status: PersonnelStatus = "ACTIVE"


class PersonnelUpdate(BaseModel):
    employee_id: str | None = Field(default=None, min_length=1)
    name: str | None = Field(default=None, min_length=1)
    department: str | None = None
    role: str | None = None
    status: PersonnelStatus | None = None


class PersonnelResponse(BaseModel):
    id: int
    employee_id: str
    name: str
    department: str | None
    role: str | None
    status: PersonnelStatus
    created_at: str


class FaceRegistrationResponse(BaseModel):
    id: int
    personnel_id: int
    model_name: str
    created_at: str
    message: str


class AreaCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    status: PersonnelStatus = "ACTIVE"


class AreaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    status: PersonnelStatus | None = None


class AreaResponse(BaseModel):
    id: int
    name: str
    description: str | None
    status: PersonnelStatus
    created_at: str


class PermissionResponse(BaseModel):
    id: int
    personnel_id: int
    area_id: int
    created_at: str


class AreaPersonnelResponse(BaseModel):
    personnel_id: int
    employee_id: str
    name: str
    department: str | None
    role: str | None
    status: PersonnelStatus
    permission_created_at: str


class AccessPersonResponse(BaseModel):
    personnel_id: int
    employee_id: str
    name: str


class AccessAreaResponse(BaseModel):
    area_id: int
    name: str


class AccessVerifyResponse(BaseModel):
    result: Literal["ACCESS_GRANTED", "ACCESS_DENIED"]
    area: AccessAreaResponse
    person: AccessPersonResponse | None = None
    match_score: float | None = None
    reason: str
    timestamp: str
