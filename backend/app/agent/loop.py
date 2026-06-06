from __future__ import annotations

import json
from typing import Any, AsyncIterator

from pydantic import ValidationError

from .approvals import (
    Mode,
    needs_approval,
    new_approval_id,
    wait_for_approval,
)

from ..config import settings
from ..ollama_client import OllamaClient
from ..tools import registry
from ..tools.base import ToolContext
from .events import AgentEvent
from .tool_parser import extract_tool_calls_from_text


SYSTEM_PROMPT = """
You are a local coding agent operating inside a single workspace folder.

You MUST accomplish tasks by CALLING tools, not by describing code in chat.

Available tools:
- list_dir(path)
  -> inspect a directory

- read_file(path, start_line?, end_line?)
  -> read an existing file

- create_file(path, content, overwrite?)
  -> create a NEW file with full content

- apply_patch(path, old_str, new_str)
  -> edit an EXISTING file; old_str must be a unique substring already present

Rules:
1. If the user asks you to CREATE / ADD / GENERATE / WRITE a NEW file,
   you MUST call create_file.
   Do NOT just print the code in chat.

2. If the user asks you to MODIFY an existing file,
   first call read_file, then call apply_patch.

3. Paths are relative to the workspace root.
   Never use absolute paths or "..".

4. Take small, verifiable steps.
   After tool results come back, decide the next tool call.

5. Only when the task is fully done,
   reply with a short confirmation message and NO tool calls.

Example:
User says:
"implement binary search in test.py"

Assistant should call:
create_file(
    path="utils/math.py",
    content="def binary_search(arr, target):\\n    ..."
)
"""


async def run_agent(
    workspace: str,
    task: str,
    model: str | None = None,
    mode: Mode = "manual",
    max_steps: int | None = None,
) -> AsyncIterator[AgentEvent]:

    model = model or settings.default_model
    max_steps = max_steps or settings.max_steps

    ctx = ToolContext(workspace=workspace)

    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": f"Workspace: {workspace}\n\nTask:\n{task}",
        },
    ]

    client = OllamaClient()

    try:
        for step in range(1, max_steps + 1):

            assistant_content_parts: list[str] = []
            tool_calls: list[dict[str, Any]] = []

            async for chunk in client.chat_stream(
                model=model,
                messages=messages,
                tools=registry.schemas(),
            ):
                msg = chunk.get("message")

                if msg and "content" in msg and msg["content"]:
                    assistant_content_parts.append(msg["content"])

                    yield AgentEvent(
                        type="token",
                        step=step,
                        data={"text": msg["content"]},
                    )

                if msg and msg.get("tool_calls"):
                    tool_calls.extend(msg["tool_calls"])

                if chunk.get("done"):
                    break

            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": "".join(assistant_content_parts),
            }

            if not tool_calls and assistant_msg["content"]:
                recovered = extract_tool_calls_from_text(assistant_msg["content"])
                known = {t.name for t in registry.all()}
                if recovered and all(
                    (c.get("function", {}).get("name") in known) for c in recovered
                ):
                    tool_calls = recovered
                    assistant_msg["content"] = ""

            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls

            messages.append(assistant_msg)

            if not tool_calls:
                yield AgentEvent(
                    type="done",
                    step=step,
                    data={"final": assistant_msg["content"]},
                )

                return

            for call in tool_calls:
                fn = call.get("function", {})

                name = fn.get("name", "")
                raw_args = fn.get("arguments", {})

                if isinstance(raw_args, str):
                    try:
                        raw_args = json.loads(raw_args)
                    except json.JSONDecodeError:
                        raw_args = {}

                yield AgentEvent(
                    type="tool_call",
                    step=step,
                    data={
                        "name": name,
                        "arguments": raw_args,
                    },
                )

                try:
                    tool = registry.get(name)

                except KeyError:
                    result = {
                        "ok": False,
                        "error": f"Unknown tool: {name}",
                    }

                    messages.append(tool_result_msg(name, result))

                    yield AgentEvent(
                        type="tool_result",
                        step=step,
                        data={
                            "name": name,
                            "result": result,
                        },
                    )

                    continue

                try:
                    parsed = tool.input_model.model_validate(raw_args)

                except ValidationError as e:
                    result = {
                        "ok": False,
                        "error": f"Invalid arguments: {e.errors()}",
                    }

                    messages.append(tool_result_msg(name, result))

                    yield AgentEvent(
                        type="tool_result",
                        step=step,
                        data={
                            "name": name,
                            "result": result,
                        },
                    )

                    continue

                if needs_approval(tool.permission, mode):
                    approval_id = new_approval_id()

                    yield AgentEvent(
                        type="approval_required",
                        step=step,
                        data={
                            "approval_id": approval_id,
                            "tool": name,
                            "permission": tool.permission,
                            "arguments": raw_args,
                        },
                    )

                    approved = await wait_for_approval(approval_id)

                    if not approved:
                        result = {
                            "ok": False,
                            "error": "User rejected tool call",
                        }

                        messages.append(tool_result_msg(name, result))

                        yield AgentEvent(
                            type="tool_result",
                            step=step,
                            data={
                                "name": name,
                                "result": result,
                            },
                        )

                        continue

                try:
                    result = await tool.handler(ctx, parsed)

                except Exception as e:
                    # noqa: BLE001 - surface any tool failure to the model
                    result = {
                        "ok": False,
                        "error": f"{type(e).__name__}: {e}",
                    }

                messages.append(tool_result_msg(name, result))

                yield AgentEvent(
                    type="tool_result",
                    step=step,
                    data={
                        "name": name,
                        "result": result,
                    },
                )

        yield AgentEvent(
            type="error",
            step=max_steps,
            data={
                "error": "max_steps exhausted",
            },
        )

    finally:
        await client.aclose()


def tool_result_msg(name: str, result: Any) -> dict[str, Any]:
    return {
        "role": "tool",
        "name": name,
        "content": json.dumps(result, ensure_ascii=False),
    }