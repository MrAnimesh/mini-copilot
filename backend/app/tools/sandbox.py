"""workspace jail: every tool path goes through resolve_in workspace.""" 
from __future__ import annotations
from pathlib import Path

class WorkspaceError(Exception):
    pass
def resolve_in_workspace(workspace: str | Path, relative_or_abs: str) -> Path:
    ws = Path(workspace).resolve()
    if not ws.is_dir():
        raise WorkspaceError (f"workspace is not a directory: {ws}")
    candidate = Path(relative_or_abs)
    target = (ws / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    try:
        target.relative_to(ws)
    except ValueError as e:
        raise WorkspaceError(
            f"Path escapes workspace: {target} not under {ws}"
        ) from e
    return target