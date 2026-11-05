#!/usr/bin/env python3
"""Deploy the custom Anime Archive theme to the live Blogger blog.

Fix: live blog `anime-archive-fan.blogspot.com` was running a default/minimal
theme with no post-rendering widget, so `data:posts` was empty and no post
cards rendered on homepage/label/single-post pages.

Deploys blogger_theme.xml via the Blogger API v3 themes PUT endpoint:
  PUT https://www.googleapis.com/blogger/v3/blogs/{blogId}/theme
  Body: {"kind": "blogger#theme", "xml": "<xml>"}

Then verifies by fetching the theme back from the API and the live homepage.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import time

import httpx

THEME_PATH = os.path.join(os.path.dirname(__file__), "..", "blogger_theme.xml")
BLOG_ID = os.getenv("BLOGGER_BLOG_ID", "")
HOMEPAGE = "https://anime-archive-fan.blogspot.com/"


def _refresh_access_token() -> str:
    """Use refresh token to get a fresh access token from Google OAuth."""
    client_id = os.getenv("BLOGGER_CLIENT_ID", "")
    client_secret = os.getenv("BLOGGER_CLIENT_SECRET", "")
    refresh_token = os.getenv("BLOGGER_REFRESH_TOKEN", "")
    if not all([client_id, client_secret, refresh_token]):
        raise RuntimeError("Missing OAuth credentials (client_id, client_secret, refresh_token)")
    r = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"OAuth refresh failed: HTTP {r.status_code} {r.text[:200]}")
    tok = r.json().get("access_token")
    if not tok:
        raise RuntimeError("OAuth refresh returned no access_token")
    return tok


def main() -> int:
    print("=" * 60)
    print("Deploy custom theme to live Blogger blog")
    print("=" * 60)
    print(f"  blog_id: {BLOG_ID or '(unset)'}")
    if not BLOG_ID:
        print("FATAL: BLOGGER_BLOG_ID not set in environment.")
        return 1

    if not os.path.exists(THEME_PATH):
        print(f"FATAL: theme file not found: {THEME_PATH}")
        return 1

    with open(THEME_PATH, "r", encoding="utf-8") as fh:
        theme_xml = fh.read()
    print(f"  theme file: {THEME_PATH} ({len(theme_xml)} bytes)")

    # Get access token via OAuth refresh
    try:
        token = _refresh_access_token()
        print("  credentials: OAuth refresh OK")
    except Exception as exc:
        print(f"  credentials: FAILED — {exc}")
        return 1

    # Deploy theme via Blogger API v3 themes PUT endpoint
    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/theme"
    body = {"kind": "blogger#theme", "xml": theme_xml}
    try:
        r = httpx.put(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json=body,
            timeout=60,
        )
        print(f"  deploy status={r.status_code}")
        if r.status_code >= 400:
            print(f"FATAL: theme deployment failed: {r.text[:500]}")
            return 1
        print("  deploy OK")
    except Exception as exc:
        print(f"FATAL: theme deployment error: {type(exc).__name__} {exc}")
        return 1

    # Verify: fetch the theme back from the API
    try:
        r = httpx.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        print(f"  theme GET status={r.status_code}")
        if r.status_code == 200:
            data = r.json()
            stored = data.get("xml", "")
            print(f"  stored theme bytes={len(stored)} match={stored == theme_xml}")
    except Exception as exc:
        print(f"  theme verify GET failed: {type(exc).__name__} {exc}")

    # Verify: fetch the live homepage
    try:
        r = httpx.get(HOMEPAGE, timeout=30, follow_redirects=True)
        html = r.text or ""
        print(f"  homepage status={r.status_code} bytes={len(html)} url={r.url}")
        has_posts = ("data:posts" in html) or ("<article" in html) or ("ledger-sheet" in html)
        has_no_items = "no-items" in html and "No articles found" in html
        print(f"  homepage renders posts={has_posts} empty-grid={has_no_items}")
    except Exception as exc:
        print(f"  homepage fetch failed: {type(exc).__name__} {exc}")

    print("\nTheme deployment complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
