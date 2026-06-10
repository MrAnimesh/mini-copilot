from __future__ import annotations

from pydantic import BaseModel, Field

from .base import Tool, ToolContext, registry
from .sandbox import resolve_in_workspace


class CreateFileInput(BaseModel):
    path: str = Field(
        ...,
        description=(
            "File path relative to workspace. "
            "Parent directories will be created."
        ),
    )

    content: str = Field(
        ...,
        description="Full UTF-8 file content.",
    )

    overwrite: bool = Field(
        False,
        description=(
            "If true, replaces an existing file. "
            "If false and file exists, fails."
        ),
    )


async def create_file(
    ctx: ToolContext,
    inp: CreateFileInput,
) -> dict:
    target = resolve_in_workspace(
        ctx.workspace,
        inp.path,
    )

    if target.exists and not inp.overwrite:
        return {
            "ok": False,
            "error": (
                "File already exists "
                "(set overwrite=true to replace): "
                f"{inp.path}"
            ),
        }

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    target.write_text(
        inp.content,
        encoding="utf-8",
    )

    return {
        "ok": True,
        "path": inp.path,
        "bytes_written": len(
            inp.content.encode("utf-8")
        ),
        "created": not target.exists() or not inp.overwrite,
    }


registry.register(
    Tool(
        name="create_file",
        description=(
            "Create a new UTF-8 text file "
            "(or overwrite an existing one "
            "when overwrite=true). "
            "Use this whenever the user asks "
            "you to create / add / generate "
            "a NEW file. "
            'Always provide the FULL file '
            'content in "content".'
        ),
        permission="write",
        input_model=CreateFileInput,
        handler=create_file,
    )
)