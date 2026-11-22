#!/usr/bin/env python3
"""Local Android share receiver. Binds to loopback only."""
import html, json, os, re, secrets, subprocess, sys, uuid
from pathlib import Path
from typing import Annotated
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response

ROOT = Path(os.environ.get("BLOGGER_BOT_REPO", str(Path.home() / "blogger_bot_img"))).resolve()
BRANCH = os.environ.get("GIT_BRANCH", "main")
MAX_BYTES = int(os.environ.get("MAX_IMAGE_BYTES", str(15 * 1024 * 1024)))
SHARE_SECRET = os.environ.get("SHARE_SECRET", "")
INBOX = Path(os.environ.get("IMAGE_INBOX", str(Path.home() / ".blogger-image-inbox"))).resolve()
app = FastAPI(title="Blogger Artwork Inbox", docs_url=None, redoc_url=None)

def git(*args):
    p = subprocess.run(["git", "-C", str(ROOT), *args], text=True, capture_output=True, timeout=120)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout or "git failed").strip())
    return p.stdout.strip()

def check_secret(value):
    if not SHARE_SECRET or not secrets.compare_digest(value, SHARE_SECRET):
        raise HTTPException(404, "Not found")

def image_ext(data):
    if data.startswith(b"\x89PNG\r\n\x1a\n"): return ".png"
    if data.startswith(b"\xff\xd8\xff"): return ".jpg"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP": return ".webp"
    raise HTTPException(415, "Only PNG, JPEG and WebP images are accepted")

def requests():
    rows = []
    for platform in ("blogger", "telegram"):
        base = ROOT / platform
        if not base.is_dir(): continue
        for folder in sorted(base.iterdir()):
            path = folder / "request.json"
            if not folder.is_dir() or not path.is_file(): continue
            try: req = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError): continue
            if req.get("request_status") not in ("pending", "in_progress"): continue
            ident = req.get("content_identity") or {}
            rows.append({"id": str(ident.get("platform_content_id", "")),
                         "platform": platform, "folder": folder.name,
                         "title": str(ident.get("title", folder.name)),
                         "categories": req.get("required_artwork_categories", ["featured", "inline"]),
                         "counts": req.get("artwork_count_requirements", {})})
    return rows

@app.get("/health")
def health():
    return {"ok": True, "repo_exists": ROOT.is_dir(), "branch": BRANCH}

@app.get("/manifest.webmanifest")
def manifest():
    return Response(json.dumps({
        "name": "Blogger Artwork Inbox", "short_name": "Artwork",
        "start_url": "/", "display": "standalone",
        "background_color": "#10131a", "theme_color": "#10131a",
        "share_target": {"action": f"/share/{SHARE_SECRET}", "method": "POST",
          "enctype": "multipart/form-data",
          "params": {"title": "title", "text": "text", "url": "url",
            "files": [{"name": "file", "accept": ["image/png", "image/jpeg", "image/webp"]}]}}
    }), media_type="application/manifest+json")

@app.get("/", response_class=HTMLResponse)
def home():
    rows = requests()
    opts = "".join(f'<option value="{html.escape(r["id"])}">{html.escape(r["platform"])} · {html.escape(r["title"])}</option>' for r in rows)
    return f"""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
    <link rel="manifest" href="/manifest.webmanifest"><title>Blogger Artwork Inbox</title>
    <style>body{{font:16px system-ui;max-width:720px;margin:28px auto;padding:0 16px;background:#10131a;color:#f4f4f5}}
    section{{background:#202631;padding:18px;border-radius:14px;margin:14px 0}}select,input,button{{font:inherit;padding:12px;width:100%;margin:8px 0;box-sizing:border-box}}</style>
    </head><body><h1>Blogger Artwork Inbox</h1><p>Share a generated image to this installed app, then select its post and category.</p>
    <section><b>Pending requests: {len(rows)}</b><form method="post" action="/publish/{html.escape(SHARE_SECRET)}">
    <label>Post</label><select name="content_id" required>{opts}</select>
    <label>Category</label><select name="category"><option>featured</option><option>inline</option><option>character</option><option>scene</option><option>promotional</option></select>
    <label>Inbox image ID (shown after sharing)</label><input name="inbox_id" required>
    <button>Publish one image to GitHub</button></form></section>
    <p>Install this page from Android Chrome menu → Add to Home screen. Then share an image from ChatGPT or Gallery to Blogger Artwork Inbox.</p></body></html>"""

@app.post("/share/{secret}", response_class=HTMLResponse)
async def receive(secret: str, file: Annotated[UploadFile, File()],
                  title: str = Form(""), text: str = Form(""), url: str = Form("")):
    check_secret(secret)
    data = await file.read(MAX_BYTES + 1)
    if not data or len(data) > MAX_BYTES: raise HTTPException(413, "Image too large or empty")
    ext = image_ext(data)
    INBOX.mkdir(parents=True, exist_ok=True)
    ident = uuid.uuid4().hex
    (INBOX / (ident + ext)).write_bytes(data)
    return f"""<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1">
    <body style="font:16px system-ui;max-width:600px;margin:30px auto;padding:16px">
    <h2>Image received</h2><p>{html.escape(title or file.filename or "Shared image")}</p>
    <p>Inbox ID: <b>{ident}</b></p><p>Open the Artwork Inbox app, select the post and category, and enter this ID.</p><a href="/">Open publisher</a></body>"""

@app.post("/publish/{secret}", response_class=HTMLResponse)
def publish(secret: str, content_id: str = Form(...), category: str = Form(...), inbox_id: str = Form(...)):
    check_secret(secret)
    if not re.fullmatch(r"[a-f0-9]{32}", inbox_id): raise HTTPException(400, "Invalid inbox ID")
    selected = [r for r in requests() if r["id"] == content_id]
    if len(selected) != 1: raise HTTPException(404, "Pending request not found")
    row = selected[0]
    if category not in row["categories"]: raise HTTPException(400, "Category not requested")
    candidates = list(INBOX.glob(inbox_id + ".*"))
    if len(candidates) != 1: raise HTTPException(404, "Inbox image not found")
    source = candidates[0]
    data = source.read_bytes()
    ext = image_ext(data)
    if len(data) > MAX_BYTES: raise HTTPException(413, "Image too large")
    try:
        git("pull", "--ff-only", "origin", BRANCH)
        folder = ROOT / row["platform"] / row["folder"]
        req = json.loads((folder / "request.json").read_text(encoding="utf-8"))
        needed = int((req.get("artwork_count_requirements") or {}).get(category, 1))
        target = folder / "artwork" / category
        target.mkdir(parents=True, exist_ok=True)
        existing = [p for p in target.iterdir() if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}]
        if len(existing) >= needed: raise HTTPException(409, f"Category is full ({len(existing)}/{needed})")
        if category == "featured" and not existing: name = "featured" + ext
        else:
            i = 1
            while (target / f"{category}_{i:02d}{ext}").exists(): i += 1
            name = f"{category}_{i:02d}{ext}"
        dest = target / name
        dest.write_bytes(data)
        validator = ROOT / "discovery_validate.py"
        if validator.is_file():
            p = subprocess.run([sys.executable, str(validator)], cwd=ROOT, text=True, capture_output=True, timeout=180)
            if p.returncode: raise RuntimeError("Artwork validator failed: " + (p.stderr or p.stdout)[-1500:])
        git("add", dest.relative_to(ROOT).as_posix())
        status = folder / "status.json"
        if status.exists(): git("add", status.relative_to(ROOT).as_posix())
        git("commit", "-m", f"Add {category} artwork for {content_id}")
        git("push", "origin", BRANCH)
        source.unlink(missing_ok=True)
        return HTMLResponse(f"<h2>Published successfully</h2><p>{html.escape(dest.relative_to(ROOT).as_posix())}</p><p>Git commit pushed to {html.escape(BRANCH)}.</p><a href='/'>Back</a>")
    except HTTPException: raise
    except Exception as exc: raise HTTPException(500, f"Publish failed; inbox retained. {str(exc)[:900]}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8765")))
