from typing import Any

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str


class WorkflowSave(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    definition: dict[str, Any]


class WorkflowOut(BaseModel):
    id: int
    name: str
    created_at: str
    updated_at: str


class RunRequest(BaseModel):
    definition: dict[str, Any]
    workflow_id: int | None = None
    workflow_name: str = ""
    input: Any = None
