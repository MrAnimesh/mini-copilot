"""sync streaming o11ama client (subset needed for agent 100p).""" 
from __future__ import annotations
import json
from typing import Any, AsyncIterator
import httpx
from .config import settings
class OllamaClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(None, connect=10.0))

    async def aclose(self) -> None:
        await self._client.aclose()

    async def list_models(self) -> list[dict[str, Any]]:
        r = await self._client.get(f"{self.base_url}/api/tags")
        r.raise_for_status()
        return r.json().get("models", [])
    
    async def chat_stream( self, 
                          model: str, 
                          messages: list[dict[str, Any]],
                          tools: list[dict[str, Any]] | None = None,
                          options: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """yields raw streamed JSON chunks from /api/chat."""
        want_stream = tools is None
        payload: dict[str, Any] = {
            "model": model, 
            "messages": messages,
            "stream": want_stream,
        }
        if tools:
            payload["tools"] = tools
        if options:
            payload["options"] = options

        
        # if not stream:
        #     r = await self._client.post(
        #         f"{self.base_url}/api/chat", json = payload, timeout = httpx.Timeout(None, connect = 10.0)
        #     )
        #     r.raise_for_status()
        #     yield r.json()
        #     return

        async with self._client.stream(
            "POST", f"{self.base_url}/api/chat", json=payload
        ) as resp:
            resp.raise_for_status()
            frames: list[dict[str, any]] = []
            
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if want_stream:
                    yield obj
                else:
                    frames.append(obj)
            if not want_stream:
                yield _merge_frames(frames)

from typing import Any


def _merge_frames(
    frames: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Collapse NDJSON frames from a non-streamed /api/chat
    response into a single message dict that matches the
    streamed final chunk shape.

    Concatenates message.content across frames and preserves
    the last non-empty message.tool_calls
    (Ollama emits tool calls in the final frame).
    """

    if not frames:
        return {
            "message": {
                "role": "assistant",
                "content": "",
            },
            "done": True,
        }

    if len(frames) == 1:
        return frames[0]

    content_parts: list[str] = []
    tool_calls: list[dict[str, Any]] | None = None
    role = "assistant"

    last = frames[-1]

    for f in frames:
        msg = f.get("message") or {}

        if msg.get("role"):
            role = msg["role"]

        if msg.get("content"):
            content_parts.append(msg["content"])

        if msg.get("tool_calls"):
            tool_calls = msg["tool_calls"]

    merged: dict[str, Any] = dict(last)

    merged["message"] = {
        "role": role,
        "content": "".join(content_parts),
    }

    if tool_calls:
        merged["message"]["tool_calls"] = tool_calls

    merged["done"] = True

    return merged