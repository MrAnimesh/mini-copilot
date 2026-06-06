"""Approval gate: write/exec tool calls pause the loop until approved in manual mode."""

from __future__ import annotations

import asyncio
import uuid
from typing import Literal

Mode = Literal["manual", "auto-edit", "yolo"]

_pending: dict[str, asyncio.Future[bool]] = {}


def needs_approval(permission: str, mode: Mode) -> bool:
    if mode == "yolo":
        return False

    if mode == "auto-edit":
        return permission == "exec"

    return permission in ("write", "exec")


def new_approval_id() -> str:
    return uuid.uuid4().hex


async def wait_for_approval(approval_id: str) -> bool:
    loop = asyncio.get_running_loop()

    fut: asyncio.Future[bool] = loop.create_future()
    _pending[approval_id] = fut

    try:
        return await fut
    finally:
        _pending.pop(approval_id, None)


def resolve_approval(approval_id: str, approved: bool) -> bool:
    fut = _pending.get(approval_id)

    if fut is None or fut.done():
        return False

    fut.set_result(approved)
    return True