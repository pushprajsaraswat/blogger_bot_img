-- database/schema.sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS providers (
    id TEXT PRIMARY KEY,              -- 'openrouter', 'openai', 'custom-ollama'
    name TEXT NOT NULL,
    base_url TEXT NOT NULL,           -- 'https://openrouter.ai/api/v1'
    auth_type TEXT NOT NULL DEFAULT 'bearer', -- 'bearer', 'none'
    api_key_encrypted TEXT,           -- encrypted at rest
    is_active INTEGER DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS models (
    id TEXT PRIMARY KEY,              -- provider_model e.g. 'openrouter_anthropic/claude-3.5-sonnet'
    provider_id TEXT NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
    model_id TEXT NOT NULL,           -- raw model id from API
    display_name TEXT NOT NULL,
    context_length INTEGER DEFAULT 4096,
    max_output INTEGER DEFAULT 4096,
    supports_vision INTEGER DEFAULT 0,
    supports_tools INTEGER DEFAULT 0,
    supports_streaming INTEGER DEFAULT 1,
    input_cost_per_1k REAL DEFAULT 0,
    output_cost_per_1k REAL DEFAULT 0,
    is_enabled INTEGER DEFAULT 1,
    UNIQUE(provider_id, model_id)
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,              -- uuid
    title TEXT NOT NULL DEFAULT 'New chat',
    provider_id TEXT REFERENCES providers(id),
    model_id TEXT REFERENCES models(id),
    system_prompt TEXT,
    temperature REAL DEFAULT 0.7,
    top_p REAL DEFAULT 1.0,
    max_tokens INTEGER DEFAULT 4096,
    is_pinned INTEGER DEFAULT 0,
    is_archived INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,              -- uuid
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('system','user','assistant','tool')),
    content TEXT NOT NULL DEFAULT '',
    tool_calls TEXT,                  -- JSON array
    tool_call_id TEXT,                -- for tool responses
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0,
    status TEXT DEFAULT 'complete' CHECK (status IN ('streaming','complete','error')),
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id, created_at);

CREATE TABLE IF NOT EXISTS attachments (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    mime_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    text_content TEXT,                -- extracted text for RAG later
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
