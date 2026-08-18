"""High-level CRUD — all async, return dicts."""
from __future__ import annotations
from database.db import Database
from uuid import uuid4
from datetime import datetime
from typing import Any
import json

def _now() -> str:
    return datetime.utcnow().isoformat()

# ---------- Providers ----------
async def list_providers(active_only=True) -> list[dict]:
    db = Database.get()
    sql = "SELECT * FROM providers"
    if active_only:
        sql += " WHERE is_active=1"
    sql += " ORDER BY sort_order, name"
    cur = await db.execute(sql)
    return [dict(r) for r in await cur.fetchall()]

async def get_provider(pid: str) -> dict | None:
    cur = await Database.get().execute("SELECT * FROM providers WHERE id=?", (pid,))
    r = await cur.fetchone()
    return dict(r) if r else None

async def upsert_provider(p: dict) -> str:
    db = Database.get()
    pid = p.get("id") or str(uuid4())[:8]
    await db.execute("""
        INSERT INTO providers (id,name,base_url,auth_type,api_key_encrypted,is_active,sort_order)
        VALUES (?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name, base_url=excluded.base_url, auth_type=excluded.auth_type,
            api_key_encrypted=excluded.api_key_encrypted, is_active=excluded.is_active,
            sort_order=excluded.sort_order
    """, (pid, p["name"], p["base_url"], p.get("auth_type","bearer"),
          p.get("api_key_encrypted"), p.get("is_active",1), p.get("sort_order",0)))
    await db.commit()
    return pid

# ---------- Models ----------
async def list_models(provider_id: str | None = None, enabled_only=True) -> list[dict]:
    db = Database.get()
    sql = "SELECT * FROM models"
    params = []
    if provider_id or enabled_only:
        sql += " WHERE"
        clauses = []
        if provider_id:
            clauses.append("provider_id=?")
            params.append(provider_id)
        if enabled_only:
            clauses.append("is_enabled=1")
        sql += " AND ".join(clauses)
    sql += " ORDER BY provider_id, display_name"
    cur = await db.execute(sql, params)
    return [dict(r) for r in await cur.fetchall()]

async def upsert_model(m: dict) -> str:
    db = Database.get()
    mid = m["id"]  # provider_model
    await db.execute("""
        INSERT INTO models (id,provider_id,model_id,display_name,context_length,max_output,
            supports_vision,supports_tools,supports_streaming,input_cost_per_1k,output_cost_per_1k,is_enabled)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
            display_name=excluded.display_name, context_length=excluded.context_length,
            max_output=excluded.max_output, supports_vision=excluded.supports_vision,
            supports_tools=excluded.supports_tools, supports_streaming=excluded.supports_streaming,
            input_cost_per_1k=excluded.input_cost_per_1k, output_cost_per_1k=excluded.output_cost_per_1k,
            is_enabled=excluded.is_enabled
    """, (mid, m["provider_id"], m["model_id"], m["display_name"],
          m.get("context_length",4096), m.get("max_output",4096),
          int(m.get("supports_vision",0)), int(m.get("supports_tools",0)),
          int(m.get("supports_streaming",1)), m.get("input_cost_per_1k",0),
          m.get("output_cost_per_1k",0), int(m.get("is_enabled",1))))
    await db.commit()
    return mid

# ---------- Conversations ----------
async def create_conversation(
    provider_id: str, model_id: str, title: str = "New chat", system_prompt: str | None = None
) -> str:
    db = Database.get()
    cid = str(uuid4())
    await db.execute("""
        INSERT INTO conversations (id,title,provider_id,model_id,system_prompt,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?)
    """, (cid, title, provider_id, model_id, system_prompt, _now(), _now()))
    await db.commit()
    return cid

async def list_conversations(archived=False, limit=100) -> list[dict]:
    db = Database.get()
    sql = """SELECT c.*, m.content as last_msg, m.role as last_role
             FROM conversations c
             LEFT JOIN (
                 SELECT conversation_id, content, role, MAX(created_at) as max_dt
                 FROM messages GROUP BY conversation_id
             ) m ON c.id = m.conversation_id
             WHERE c.is_archived=?
             ORDER BY c.is_pinned DESC, c.updated_at DESC LIMIT ?"""
    cur = await db.execute(sql, (int(archived), limit))
    return [dict(r) for r in await cur.fetchall()]

async def get_conversation(cid: str) -> dict | None:
    cur = await Database.get().execute("SELECT * FROM conversations WHERE id=?", (cid,))
    r = await cur.fetchone()
    return dict(r) if r else None

async def update_conversation(cid: str, **fields):
    if not fields: return
    db = Database.get()
    fields["updated_at"] = _now()
    cols = ", ".join(f"{k}=?" for k in fields)
    await db.execute(f"UPDATE conversations SET {cols} WHERE id=?", (*fields.values(), cid))
    await db.commit()

# ---------- Messages ----------
async def add_message(
    conversation_id: str, role: str, content: str = "",
    tool_calls: list | None = None, tool_call_id: str | None = None,
    status: str = "complete"
) -> str:
    db = Database.get()
    mid = str(uuid4())
    await db.execute("""
        INSERT INTO messages (id,conversation_id,role,content,tool_calls,tool_call_id,status,created_at)
        VALUES (?,?,?,?,?,?,?,?)
    """, (mid, conversation_id, role, content,
          json.dumps(tool_calls) if tool_calls else None, tool_call_id, status, _now()))
    await db.execute("UPDATE conversations SET updated_at=? WHERE id=?", (_now(), conversation_id))
    await db.commit()
    return mid

async def update_message(mid: str, **fields):
    if not fields: return
    db = Database.get()
    cols = ", ".join(f"{k}=?" for k in fields)
    await db.execute(f"UPDATE messages SET {cols} WHERE id=?", (*fields.values(), mid))
    await db.commit()

async def get_messages(conversation_id: str) -> list[dict]:
    cur = await Database.get().execute(
        "SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at", (conversation_id,))
    return [dict(r) for r in await cur.fetchall()]

# ---------- Settings ----------
async def get_setting(key: str, default: str = "") -> str:
    cur = await Database.get().execute("SELECT value FROM settings WHERE key=?", (key,))
    r = await cur.fetchone()
    return r[0] if r else default

async def set_setting(key: str, value: str):
    db = Database.get()
    await db.execute("""
        INSERT INTO settings (key,value) VALUES (?,?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (key, value))
    await db.commit()
