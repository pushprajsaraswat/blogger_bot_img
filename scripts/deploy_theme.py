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

import os
import sys

# Load .env so BLOGGER_* credentials are available even when run outside the
# shell that exported them (dotenv never overwrites an already-set var).
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from publish.client import BloggerClient  # noqa: E402

BLOG_ID = os.getenv("BLOGGER_BLOG_ID", "")
THEME_PATH = os.path.join(os.path.dirname(__file__), "..", "blogger_theme.xml")
HOMEPAGE = "https://anime-archive-fan.blogspot.com/"


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

    client = BloggerClient(dry_run=False)
    print(f"  credentials: {'present' if client._has_credentials() else 'MISSING'}")
    if not client.is_configured():
        print("FATAL: Blogger client not configured (missing blog id or credentials).")
        return 1

    result = client.set_theme(theme_xml)
    print(f"  deploy ok={result.ok} status={result.status} error={result.error}")
    if not result.ok:
        print("FATAL: theme deployment failed.")
        return 1

    # Verify: fetch the theme back from the API.
    get_url = (
        "https://www.googleapis.com/blogger/v3/blogs/"
        + BLOG_ID + "/theme"
    )
    import httpx
    try:
        token = client._current_token()
        r = httpx.get(get_url, headers={"Authorization": "Bearer " + str(token)}, timeout=30)
        print(f"  theme GET status={r.status_code} bytes={len(r.text or '')}")
        if r.status_code == 200:
            data = r.json()
            stored = data.get("xml", "")
            print(f"  stored theme bytes={len(stored)} match={stored == theme_xml}")
    except Exception as exc:
        print(f"  theme verify GET failed: {type(exc).__name__} {exc}")

    # Verify: fetch the live homepage and check for post-rendering signals.
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
