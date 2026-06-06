from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


EventType = Literal[
    "token",
    "tool_call",
    "tool_result",
    "approval_required",
    "done",
    "error",
]


class AgentEvent(BaseModel):
    type: EventType
    step: int
    data: dict[str, Any]

    def to_sse(self) -> dict[str, str]:
        return {
            "event": self.type,
            "data": self.model_dump_json(),
        }