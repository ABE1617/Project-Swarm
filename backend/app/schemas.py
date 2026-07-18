from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[\w.-]+$")
    email: EmailStr = Field(max_length=120)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    id: int
    username: str
    email: str


class NodeDef(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1, max_length=128)
    type: str = Field(min_length=1, max_length=64)
    label: str | None = Field(default=None, max_length=128)
    position: dict[str, float] | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class EdgeDef(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    sourceHandle: str | None = None
    targetHandle: str | None = None


class WorkflowDefinition(BaseModel):
    model_config = ConfigDict(extra="allow")

    nodes: list[NodeDef] = Field(default_factory=list, max_length=500)
    edges: list[EdgeDef] = Field(default_factory=list, max_length=2000)

    def to_engine(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class WorkflowSave(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    definition: WorkflowDefinition


class WorkflowOut(BaseModel):
    id: int
    name: str
    created_at: str
    updated_at: str


class RunRequest(BaseModel):
    definition: WorkflowDefinition
    workflow_id: int | None = None
    workflow_name: str = Field(default="", max_length=128)
    input: Any = None
    target_node_id: str | None = Field(default=None, max_length=128)
    """When set, only this node and its ancestors execute ('Execute step')."""
    exclude_target: bool = False
    """With target_node_id: run only the ancestors ('Execute previous nodes')."""
