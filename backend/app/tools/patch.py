from __future__ import annotations

from pydantic import BaseModel, Field

from .base import Tool, ToolContext, registry
from .sandbox import resolve_in_workspace


class ApplyPatchInput(BaseModel):
    path: str = Field(
        ...,
        description="File to edit, relative to workspace."
    )

    old_str: str = Field(
        ...,
        description="Exact existing substring to replace. Must be unique."
    )

    new_str: str = Field(
        ...,
        description="Replacement text."
    )

    create_if_missing: bool = Field(
        False,
        description="If true and file does not exist, create it."
    )


async def apply_patch(ctx: ToolContext, inp: ApplyPatchInput) -> dict:
    target = resolve_in_workspace(ctx.workspace, inp.path)

    if not target.exists():
        if not inp.create_if_missing or inp.old_str:
            return {
                "ok": False,
                "error": f"File not found: {inp.path}"
            }

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(inp.new_str, encoding="utf-8")

        return {
            "ok": True,
            "path": inp.path,
            "created": True
        }

    content = target.read_text(encoding="utf-8")

    if inp.old_str not in content:
        return {
            "ok": False,
            "error": "old_str not found in file"
        }

    updated_content = content.replace(inp.old_str, inp.new_str, 1)

    target.write_text(updated_content, encoding="utf-8")

    return {
    "ok": True,
    "path": inp.path,
    "bytes_written": len(updated.encode("utf-8")),
}

registry.register(
    Tool(
        name="apply_patch",
        description="Replace a unique substring in a workspace file. Requires approval in manual mode.",
        permission="write",
        input_model=ApplyPatchInput,
        handler=apply_patch,
    )
)