from __future__ import annotations

import json

from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from .agent.approvals import Mode, resolve_approval
from .agent.loop import run_agent

from .config import settings
from .ollama_client import OllamaClient

from .store.db import get_session, init_db
from .store.models import Session as SessionRow, Step


app = FastAPI(
    title="mini-copilot backend",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
async def health() -> dict:
    return {
        "ok": True,
        "version": "0.1.0",
    }


@app.get("/models")
async def models() -> dict:
    client = OllamaClient()

    try:
        ms = await client.list_models()

    finally:
        await client.aclose()

    return {
        "default": settings.default_model,
        "models": ms,
    }


class RunRequest(BaseModel):
    workspace: str
    task: str
    model: str | None = None
    mode: Mode = "manual"


@app.post("/agent/run")
async def agent_run(req: RunRequest) -> EventSourceResponse:
    with get_session() as db:
        row = SessionRow(
            workspace=req.workspace,
            model=req.model or settings.default_model,
            mode=req.mode,
            task=req.task,
        )

        db.add(row)
        db.commit()
        db.refresh(row)

        session_id = row.id
    
    async def gen() -> AsyncIterator[dict]:
        async for ev in run_agent(
            workspace=req.workspace,
            task=req.task,
            model=req.model,
            mode=req.mode,
        ):
            with get_session() as db:
                db.add(
                    Step(
                        session_id=session_id,
                        step_index=ev.step,
                        event_type=ev.type,
                        payload_json=json.dumps(
                            ev.data,
                            ensure_ascii=False,
                        ),
                    )
                )

                db.commit()

            yield ev.to_sse()


    return EventSourceResponse(gen())

class ApprovalRequest(BaseModel):
    approval_id: str
    approved: bool


@app.post("/agent/approve")
async def agent_approve(req: ApprovalRequest) -> dict:
    ok = resolve_approval(
        req.approval_id,
        req.approved,
    )

    if not ok:
        raise HTTPException(
            status_code=404,
            detail="approval_id not pending",
        )

    return {"ok": True}