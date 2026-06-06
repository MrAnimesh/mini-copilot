from __future__ import annotations

from sqlmodel import Session, SQLModel, create_engine

from ..config import settings
from . import models  # noqa: F401 - ensure tables register


_engine = create_engine(
    f"sqlite:///{settings.db_path}",
    echo=False,
)


def init_db() -> None:
    SQLModel.metadata.create_all(_engine)


def get_session() -> Session:
    return Session(_engine)