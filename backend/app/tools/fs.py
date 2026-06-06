"""Filesystem tools: read_file, list dir.""" 
from __future__ import annotations
from pydantic import BaseModel, Field 
from .base import Tool, ToolContext, registry 
from .sandbox import resolve_in_workspace

class ReadFileInput(BaseModel):
    path: str = Field(..., description="File path relative to the workspace root.")
    start_line: int | None = Field(None, ge=1, description="1-indexed start line (inclusive).")
    end_line: int | None = Field(None, ge=1, description="1-indexed end line (inclusive).")

async def read_file(ctx: ToolContext, inp: ReadFileInput) -> dict:
    target = resolve_in_workspace(ctx.workspace, inp.path)
    if not target.is_file():
        return {"ok": False, "error": f"Not a file: {inp.path} "}
    text = target.read_text(encoding="utf-8", errors="replace")
    if inp.start_line or inp.end_line:
        lines = text.splitlines()
        s = (inp.start_line or 1) - 1
        e = inp.end_line or len(lines)
        text = "\n".join(lines [s:e])
    return {"ok": True, "path": inp.path, "content": text}
    
class ListDirInput(BaseModel):
    path: str = Field(".", description = "Directory path relative to the workspace root")

async def list_dir(ctx: ToolContext, inp: ListDirInput) -> dict:
    target = resolve_in_workspace(ctx.workspace, inp.path)
    if not target.is_dir():
        return {"ok": False, "error": f"not a directory: {inp.path}"}

    entries = []
    for child in sorted(target.iterdir()):
        entries.append(
            {
                "name": child.name,
                "type": "dir" if child.is_dir() else "file",
                "size": child.stat().st_size if child.is_file() else None,
            }
        )
    return {"ok": True, "path": inp.path, "entries": entries}



registry.register(
    Tool(
        name="read_file",
        description="Read a UTF-8 text file from the workspace. optionally restrict to a line range",
        permission="read",
        input_model=ReadFileInput,
        handler=read_file,
    )
)

registry.register(
    Tool(
        name="list_dir",
        description="List immediate children of a directory in the workspace",
        permission="read",
        input_model=ListDirInput,
        handler=list_dir
    )
)