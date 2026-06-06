from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Session(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    workspace: str
    model: str
    mode: str
    task: str

    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )


class Step(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    session_id: int = Field(
        foreign_key="session.id",
        index=True,
    )

    step_index: int
    event_type: str
    payload_json: str

    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )