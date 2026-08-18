"""Factory + model registry sync."""
from __future__ import annotations
from providers.base import AIProvider
from providers.openai_compat import OpenAICompatProvider
from database.repositories import list_providers, upsert_model, list_models as db_list_models
from database.db import Database
from core.events import bus
import asyncio

_PROVIDER_MAP = {
    "openai": OpenAICompatProvider,
    "openrouter": OpenAICompatProvider,
    "groq": OpenAICompatProvider,
    "together": OpenAICompatProvider,
    "ollama": OpenAICompatProvider,
    "custom": OpenAICompatProvider,
}

_active_instances: dict[str, AIProvider] = {}

def get_provider_class(pid: str) -> type[AIProvider]:
    return _PROVIDER_MAP.get(pid, OpenAICompatProvider)

async def get_provider(provider_id: str) -> AIProvider:
    """Return cached or new instance with DB credentials."""
    if provider_id in _active_instances:
        return _active_instances[provider_id]

    p = await Database.get().execute("SELECT * FROM providers WHERE id=?", (provider_id,))
    row = await p.fetchone()
    if not row:
        raise ValueError(f"Provider {provider_id} not configured")
    row = dict(row)

    # decrypt key if you added secure_store; here plain for Phase 1
    api_key = row["api_key_encrypted"] or None
    extra = {}
    if provider_id == "openrouter":
        extra = {"HTTP-Referer": "http://localhost", "X-Title": "PydroidAI"}

    cls = get_provider_class(provider_id)
    inst = cls(provider_id, row["base_url"], api_key, extra_headers=extra)
    _active_instances[provider_id] = inst
    return inst

async def refresh_all_models():
    """Call on startup / user 'Refresh models'."""
    providers = await list_providers()
    for p in providers:
        try:
            inst = await get_provider(p["id"])
            models = await inst.list_models()
            for m in models:
                await upsert_model({
                    "id": f"{p['id']}_{m.id}",
                    "provider_id": p["id"],
                    "model_id": m.id,
                    "display_name": m.display_name,
                    "context_length": m.context_length,
                    "max_output": m.max_output,
                    "supports_vision": m.supports_vision,
                    "supports_tools": m.supports_tools,
                    "supports_streaming": m.supports_streaming,
                    "input_cost_per_1k": m.input_cost_per_1k,
                    "output_cost_per_1k": m.output_cost_per_1k,
                    "is_enabled": 1,
                })
            print(f"[Registry] Synced {len(models)} models from {p['name']}")
        except Exception as e:
            print(f"[Registry] Failed {p['name']}: {e}")

async def close_all():
    for inst in _active_instances.values():
        await inst.close()
    _active_instances.clear()
