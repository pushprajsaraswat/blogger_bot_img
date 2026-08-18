"""Async SQLite connection + migration runner."""
from __future__ import annotations
import aiosqlite
import json
from pathlib import Path
from typing import Any
from core.events import bus

DB_PATH = Path(__file__).parent.parent / "app.db"  # AI_Chat_App/app.db
SCHEMA_SQL = (Path(__file__).parent / "schema.sql").read_text()

class Database:
    _instance: aiosqlite.Connection | None = None

    @classmethod
    async def init(cls):
        if cls._instance:
            return cls._instance
        cls._instance = await aiosqlite.connect(DB_PATH)
        cls._instance.row_factory = aiosqlite.Row
        await cls._instance.executescript(SCHEMA_SQL)
        await cls._instance.commit()
        # seed default provider if empty
        cur = await cls._instance.execute("SELECT COUNT(*) FROM providers")
        if (await cur.fetchone())[0] == 0:
            await cls._instance.execute(
                """INSERT INTO providers (id,name,base_url,auth_type,sort_order)
                   VALUES (?,?,?,?,?)""",
                ("openrouter", "OpenRouter", "https://openrouter.ai/api/v1", "bearer", 0)
            )
            await cls._instance.commit()
        await bus.emit("db_ready")
        return cls._instance

    @classmethod
    def get(cls) -> aiosqlite.Connection:
        if not cls._instance:
            raise RuntimeError("Database not initialized. Call Database.init() first.")
        return cls._instance

    @classmethod
    async def close(cls):
        if cls._instance:
            await cls._instance.close()
            cls._instance = None
