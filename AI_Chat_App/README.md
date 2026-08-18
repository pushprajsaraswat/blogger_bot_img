# Phase 1 Scaffold — Pydroid 3 AI Chat App

Single-folder, copy-paste runnable.
Tested on Pydroid 3 (Python 3.11+, Kivy 2.3, `aiohttp`, `aiosqlite`, `markdown`, `pygments`).

## 1. Install in Pydroid Terminal
```bash
pip install aiohttp aiosqlite markdown pygments
```
(Kivy, asyncio, sqlite3, json, pathlib, dataclasses, datetime, typing are built-in.)

## 2. Run in Pydroid
1. Copy this `AI_Chat_App` folder onto your device (e.g. `/sdcard/AI_Chat_App`).
2. Open Pydroid 3 → Terminal → `cd /sdcard/AI_Chat_App && pip install aiohttp aiosqlite markdown pygments`
3. Run `python main.py`.
4. App launches:
   - Chat tab works (creates conversation, streams from OpenRouter if you add a key).
   - Settings tab lists providers; tap "Edit Key" → prints to console (popup TODO).

## 3. Add Your API Key (OpenRouter example)

In Pydroid terminal (or a one-off script placed in this folder):
```python
import asyncio, aiosqlite
async def set_key():
    db = await aiosqlite.connect("app.db")
    await db.execute("UPDATE providers SET api_key_encrypted=? WHERE id='openrouter'", ("sk-or-xxxxx",))
    await db.commit()
asyncio.run(set_key())
```
Restart the app → chat works.

## 4. What's Next (Phase 2+ hooks already in place)

| Feature | Where to extend |
|---------|-----------------|
| Markdown polish | `ui/widgets/markdown_view.py` → use `markdown_it_py` + custom Kivy renderer |
| Conversation list / sidebar | New screen + `list_conversations` repo |
| Model picker | `SettingsScreen` → show `list_models(provider_id)` |
| System prompt / params per chat | Add edit dialog → `update_conversation` |
| Encrypted keys | `utils/secure_store.py` using `cryptography.fernet` + Android Keystore |
| Artifacts / code blocks | Detect fenced blocks in `MessageBubble` → "Run / Save" buttons |
| Agents / Tools | New `core/agent.py` + tool registry in `tools/` |

## Notes on this build

A couple of small syntax slips in the original spec were fixed while assembling this
zip so the app actually imports cleanly:
- `providers/openai_compat.py`: the module docstring needed its own line.
- `ui/widgets/markdown_view.py`: `size_hint_y(None)` → `size_hint_y=None`.

Everything else matches the original scaffold as written, including the stub
`utils/secure_store.py` and `utils/helpers.py` placeholders referenced by the
file tree (kept empty for you to fill in during Phase 2).
