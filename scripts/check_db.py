"""Smoke-test DB connectivity.

Usage:
    python scripts/check_db.py

Prints ``OK`` on success, otherwise prints the error and exits with code 1.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Make project root importable when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from db.session import engine


async def main() -> int:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("OK")
        return 0
    except Exception as exc:  # noqa: BLE001 — we want to report anything
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
