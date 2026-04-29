"""A2A (Agent-to-Agent Protocol) message models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class A2ASkill(BaseModel):
    id: str
    name: str
    description: str
    input_modes: list[str] = Field(default_factory=lambda: ["text"])
    output_modes: list[str] = Field(default_factory=lambda: ["text", "data"])


class A2AAgentCard(BaseModel):
    """Seller's public capability manifest — the A2A equivalent of a landing page."""

    name: str
    description: str
    url: str
    version: str = Field(default="1.0")
    capabilities: dict[str, bool] = Field(
        default_factory=lambda: {"streaming": True, "push_notifications": False}
    )
    skills: list[A2ASkill] = Field(default_factory=list)
    default_input_mode: str = "text"
    default_output_mode: str = "data"


class A2AMessage(BaseModel):
    role: str  # user | agent
    parts: list[dict[str, Any]]  # {type: text|data|file, content: ...}


class A2ATask(BaseModel):
    id: str
    session_id: str | None = None
    status: str = "submitted"  # submitted | working | completed | failed | cancelled
    messages: list[A2AMessage] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class A2ATaskUpdate(BaseModel):
    task_id: str
    status: str
    message: A2AMessage | None = None
    artifact: dict[str, Any] | None = None
    final: bool = False
