"""Fernet-encrypted key storage (optional, Phase 2).

Placeholder — Phase 1 stores API keys in plaintext in the local SQLite DB.
Wire this up with `cryptography.fernet` (and ideally the Android Keystore)
before shipping anything beyond local personal use.
"""
from __future__ import annotations

# TODO(Phase 2): implement encrypt_key(raw: str) -> str and decrypt_key(enc: str) -> str
