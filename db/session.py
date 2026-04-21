"""Async SQLAlchemy engine and session factory.

Reads ``DATABASE_URL`` from the environment (``.env`` is loaded on import).
The URL scheme is normalised to the ``postgresql+asyncpg://`` driver so the
same value works for both SQLAlchemy and bare ``psycopg``-style strings.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import AsyncIterator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Load .env from the project root (one level above this file's parent)
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_PROJECT_ROOT / ".env")


def _normalise_url(url: str) -> str:
    """Ensure the URL uses the asyncpg driver."""
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://"):]
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Copy .env.example to .env and fill it in."
    )

DATABASE_URL = _normalise_url(DATABASE_URL)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI-compatible dependency that yields an ``AsyncSession``."""
    async with AsyncSessionLocal() as session:
        yield session
