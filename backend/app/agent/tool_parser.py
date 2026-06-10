from __future__ import annotations
import json
import re
from typing import Any

_FENCE = re.compile(
    r"```(?:json|tool_call|tool|function)?\s*\n?(.*?)```",
    re.DOTALL | re.IGNORECASE
)


def extract_tool_calls_from_text(text: str) -> list[dict[str, Any]]:
    if not text or not text.strip():
        return []

    candidates: list[str] = []

    # 1. fenced blocks
    for m in _FENCE.finditer(text):
        candidates.append(m.group(1).strip())

    # 2. whole text as JSON fallback
    candidates.append(text.strip())

    # 3. all balanced top-level {...} blobs in the text
    candidates.extend(_find_balanced_objects(text))

    seen: set[str] = set()
    out: list[dict[str, Any]] = []

    for c in candidates:
        c = c.strip()
        if not c or c in seen:
            continue

        seen.add(c)

        obj = _safe_loads(c)
        if obj is None:
            continue

        for call in _normalize(obj):
            out.append(call)

    return _dedupe(out)


def _safe_loads(s: str) -> Any:
    try:
        return json.loads(s)
    except Exception:
        return None


def _find_balanced_objects(text: str) -> list[str]:
    out: list[str] = []
    depth = 0
    start = -1
    in_str = False
    esc = False

    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue

        if ch == '"':
            in_str = True
            continue

        if ch == "{":
            if depth == 0:
                start = i
            depth += 1

        elif ch == "}":
            if depth > 0:
                depth -= 1

            if depth == 0 and start >= 0:
                out.append(text[start:i + 1])
                start = -1

    return out



def _normalize(obj: Any) -> list[dict[str, Any]]:
    """Coerce a parsed object into a list of function calls (name + arguments)."""

    if isinstance(obj, list):
        out: list[dict[str, Any]] = []
        for item in obj:
            out.extend(_normalize(item))
        return out

    if not isinstance(obj, dict):
        return []

    # already in ollama/openai-like shape
    if (
        "function" in obj
        and isinstance(obj["function"], dict)
        and "name" in obj["function"]
    ):
        fn = obj["function"]
        return [{
            "function": {
                "name": fn["name"],
                "arguments": fn.get("arguments", {})
            }
        }]

    # tool_calls format
    if "tool_calls" in obj and isinstance(obj["tool_calls"], list):
        out: list[dict[str, Any]] = []
        for c in obj["tool_calls"]:
            out.extend(_normalize(c))
        return out

    name = (
        obj.get("name")
        or obj.get("tool")
        or obj.get("tool_name")
        or obj.get("function_name")
    )

    if not isinstance(name, str):
        return []

    args = (
        obj.get("arguments")
        if "arguments" in obj
        else obj.get("parameters")
        if "parameters" in obj
        else obj.get("args")
        if "args" in obj
        else {}
    )

    if isinstance(args, str):
        parsed = _safe_loads(args)
        args = parsed if isinstance(parsed, dict) else {}
    
    if not isinstance(args, dict):
        args = {}
    
    return [{"function": {"name": name, "arguments": args}}]

def _dedupe(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:

    seen: set[str] = set()

    out: list[dict[str, Any]] = []

    for c in calls:

        key = json.dumps(c, sort_keys=True)

        if key in seen:

            continue

        seen.add(key)

        out.append(c)

    return out