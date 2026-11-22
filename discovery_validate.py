#!/usr/bin/env python3
"""Discover artwork in platform/post-ID folders and safely synchronize status.json.

The request.json file is authoritative for requested artwork counts. Discovery
must never rewrite those requirements: it only records files that actually exist.
"""
import hashlib
import json
import struct
import subprocess
from datetime import datetime, timezone
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VALID_PLATFORMS = {"blogger", "telegram", "instagram", "facebook", "youtube"}
CATEGORY_MAP = {
    "featured": "featured", "inline": "inline",
    "characters": "character", "character": "character",
    "scenes": "scene", "scene": "scene",
    "promotional": "promotional", "additional": "additional",
}

GITHUB_REMOTE_NAME = "origin"
GITHUB_BRANCH = "main"


def get_local_main_sha():
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, cwd="."
    )
    return result.stdout.strip()


def get_remote_main_sha():
    result = subprocess.run(
        ["git", "rev-parse", f"origin/{GITHUB_BRANCH}"],
        capture_output=True, text=True, cwd="."
    )
    return result.stdout.strip()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def read_content_json(post_folder):
    """Read content.json from a post folder."""
    content_path = post_folder / "content.json"
    if not content_path.is_file():
        return {}
    try:
        return json.loads(content_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def read_request_json(post_folder):
    """Read request.json from a post folder."""
    req_path = post_folder / "request.json"
    if not req_path.is_file():
        return {}
    try:
        return json.loads(req_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def read_status_json(post_folder):
    """Read status.json from a post folder."""
    status_path = post_folder / "status.json"
    if not status_path.is_file():
        return {}
    try:
        return json.loads(status_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

def update_request_json(post_folder, total_images, category_counts):
    """Update request.json with discovered artwork counts."""
    req_path = post_folder / "request.json"
    if not req_path.is_file():
        return 0
    try:
        data = json.loads(req_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0
    data["discovered_total"] = total_images
    data["discovered_by_category"] = category_counts
    data["last_discovery_sync"] = utc_now()
    req_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 1



def compute_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_dimensions(path):
    """Read dimensions from common image headers without third-party packages."""
    with open(path, "rb") as stream:
        head = stream.read(32)
        if head.startswith(b"\x89PNG\r\n\x1a\n") and len(head) >= 24:
            return struct.unpack(">II", head[16:24])
        if head[:6] in (b"GIF87a", b"GIF89a") and len(head) >= 10:
            return struct.unpack("<HH", head[6:10])
        if head[:2] == b"BM" and len(head) >= 26:
            return struct.unpack("<ii", head[18:26])
        if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
            kind = head[12:16]
            if kind == b"VP8X" and len(head) >= 30:
                return (1 + int.from_bytes(head[24:27], "little"),
                        1 + int.from_bytes(head[27:30], "little"))
        if head[:2] != b"\xff\xd8":
            raise ValueError("Unsupported or invalid image header")
        stream.seek(2)
        while True:
            marker_start = stream.read(1)
            if not marker_start:
                break
            if marker_start != b"\xff":
                continue
            marker = stream.read(1)
            while marker == b"\xff":
                marker = stream.read(1)
            if marker in (b"\xd8", b"\xd9", b"\x01") or (marker and 0xd0 <= marker[0] <= 0xd7):
                continue
            raw_len = stream.read(2)
            if len(raw_len) != 2:
                break
            length = int.from_bytes(raw_len, "big")
            if marker and marker[0] in (0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf):
                data = stream.read(5)
                if len(data) == 5:
                    height = int.from_bytes(data[1:3], "big")
                    width = int.from_bytes(data[3:5], "big")
                    return width, height
                break
            stream.seek(max(0, length - 2), 1)
    raise ValueError("Could not determine image dimensions")


def _content_id(post_folder):
    for filename in ("status.json", "request.json", "content.json"):
        path = post_folder / filename
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        candidates = [
            data.get("content_id"),
            data.get("platform_content_id"),
            (data.get("content_identity") or {}).get("platform_content_id"),
        ]
        for candidate in candidates:
            if isinstance(candidate, (str, int)) and str(candidate).strip():
                return str(candidate)
    return None


def discover_images(base_dir):
    base = Path(base_dir).resolve()
    discovered = {}
    if not base.is_dir():
        raise NotADirectoryError(str(base))
    for platform_dir in sorted(base.iterdir()):
        if not platform_dir.is_dir() or platform_dir.name not in VALID_PLATFORMS:
            continue
        for post_folder in sorted(platform_dir.iterdir()):
            if not post_folder.is_dir() or not (post_folder / "request.json").is_file():
                continue
            entry = {
                "folder": post_folder,
                "content_id": _content_id(post_folder),
                "images_by_category": {},
                "total": 0,
            }
            artwork_dir = post_folder / "artwork"
            if artwork_dir.is_dir():
                for category_dir in sorted(artwork_dir.iterdir()):
                    if not category_dir.is_dir() or category_dir.name not in CATEGORY_MAP:
                        continue
                    category = CATEGORY_MAP[category_dir.name]
                    for image_path in sorted(category_dir.iterdir()):
                        if not image_path.is_file() or image_path.suffix.lower() not in IMAGE_EXTENSIONS:
                            continue
                        try:
                            width, height = image_dimensions(image_path)
                            image = {
                                "filename": image_path.name,
                                "path": image_path,
                                "file_path": image_path.relative_to(base).as_posix(),
                                "category": category,
                                "file_hash": compute_sha256(image_path),
                                "dimensions": {"width": width, "height": height, "unit": "px"},
                                "format": image_path.suffix.lower().lstrip("."),
                                "creation_date": datetime.fromtimestamp(
                                    image_path.stat().st_mtime, timezone.utc
                                ).isoformat(),
                            }
                        except (OSError, ValueError) as exc:
                            print(f"WARNING: skipping invalid image {image_path}: {exc}")
                            continue
                        entry["images_by_category"].setdefault(category, []).append(image)
                        entry["total"] += 1
            discovered[(platform_dir.name, post_folder.name)] = entry
    return discovered


def detect_changed_posts():
    """Detect posts whose artwork metadata has changed since last sync.

    Returns a set of (platform, post_folder_name) tuples that have
    new commits on remote compared to local.
    """
    import subprocess
    git_fetch_result = subprocess.run(
        ["git", "fetch", GITHUB_REMOTE_NAME],
        capture_output=True, text=True, cwd="."
    )
    log_output = subprocess.run(
        ["git", "log", f"HEAD..origin/{GITHUB_BRANCH}",
         "--oneline", "--name-only"],
        capture_output=True, text=True, cwd="."
    )
    changed_posts = set()
    if not log_output.stdout.strip():
        remote_sha = subprocess.run(
            ["git", "rev-parse", f"origin/{GITHUB_BRANCH}"],
            capture_output=True, text=True, cwd="."
        ).stdout.strip()
        local_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd="."
        ).stdout.strip()
        if remote_sha and local_sha and remote_sha != local_sha:
            # Remote is ahead — caller should scan ALL posts for missing artwork
            return changed_posts
        return changed_posts
    entries = log_output.stdout.strip().split("\n\n")
    current_commit_changed_files = set()
    for entry in entries:
        lines = entry.strip().split("\n")
        if not lines:
            continue
        first_line = lines[0]
        if len(first_line) > 10 and not first_line.startswith("Author") and not first_line.startswith("Date"):
            if len(current_commit_changed_files) == 0:
                current_commit_changed_files = set(lines[1:])
        else:
            current_commit_changed_files = set(lines)
    if len(current_commit_changed_files) > 0:
        for filepath in current_commit_changed_files:
            parts = filepath.split("/")
            if len(parts) >= 2:
                platform = parts[0]
                post_folder_name = "/".join(parts[:2])
                changed_posts.add((platform, post_folder_name))
    return changed_posts


def sync_from_github(base_dir="."):
    import subprocess
    print("=" * 60)
    print("HERMES: Automatic GitHub Artwork Synchronization")
    print("=" * 60)
    print()
    print("[1/7] Detecting GitHub changes...")
    git_fetch_result = subprocess.run(
        ["git", "fetch", GITHUB_REMOTE_NAME],
        capture_output=True, text=True, cwd="."
    )
    local_sha = get_local_main_sha()
    remote_sha = get_remote_main_sha()
    print(f"    Local main: {local_sha}")
    print(f"    Remote main: {remote_sha}")
    log_output = subprocess.run(
        ["git", "log", f"HEAD..origin/{GITHUB_BRANCH}",
         "--oneline", "--name-only"],
        capture_output=True, text=True, cwd="."
    )
    if not log_output.stdout.strip():
        changed_posts = set()
        if local_sha == remote_sha:
            print("    -> No new changes on remote main. Repository is up to date.")
        else:
            print("    -> Remote ahead but no file changes detected (may be rebase).")
    else:
        changed_posts = detect_changed_posts()
    print(f"    -> Found {len(changed_posts)} platform/post-ID folders with changes")
    print()
    print("[2/7] Discovering artwork across all posts...")
    all_discovered = discover_images(base_dir)
    print(f"    -> Scanned {len(all_discovered)} platform/post-ID combinations")
    total_imgs = sum(i["total"] for i in all_discovered.values())
    print(f"    -> Total images discovered: {total_imgs}")
    folders_with_images = sum(1 for i in all_discovered.values() if i["total"] > 0)
    print(f"    -> Folders with images: {folders_with_images}")
    print()
    posts_processed = 0
    images_assigned = 0
    posts_missing_artwork = []
    for (platform, post_folder_name), info in sorted(all_discovered.items()):
        post_folder_full_path = info["folder"]
        content = read_content_json(post_folder_full_path)
        request = read_request_json(post_folder_full_path)
        if not request:
            print(f"[3/7] {platform}/{post_folder_name}: no request.json, skipping")
            continue
        content_id = content.get("platform_content_id", post_folder_name) if content else post_folder_name
        req_cats = request.get("required_artwork_categories", ["featured", "inline"]) if request else ["featured", "inline"]
        req_counts = request.get("artwork_count_requirements", {"featured": 1, "inline": 1, "total": 2}) if request else {"featured": 1, "inline": 1, "total": 2}
        status = read_status_json(post_folder_full_path)
        already_assigned_hashes = set()
        for assignment in status.get("image_assignments", []):
            if isinstance(assignment, dict) and "file_hash" in assignment:
                already_assigned_hashes.add(assignment["file_hash"])
        images_by_category = info.get("images_by_category", {})
        assigned_images = []
        missing_categories = []
        for cat_name in req_cats:
            required_count = req_counts.get(cat_name, 1) if isinstance(req_counts, dict) else 1
            if cat_name not in images_by_category or len(images_by_category[cat_name]) == 0:
                missing_categories.append(f"{cat_name} (0/{required_count})")
                continue
            cat_images = images_by_category[cat_name]
            for img in cat_images:
                file_hash = img["file_hash"]
                if file_hash in already_assigned_hashes:
                    print(f"    -> SKIP: {img['filename']} already assigned (SHA-256 dedup)")
                    continue
                metadata = build_artwork_metadata(img, content_id, platform)
                missing_meta = validate_artwork_metadata(metadata)
                if missing_meta:
                    print(f"    WARNING: Missing metadata for {img['filename']}: {missing_meta}")
                dims = metadata.get("dimensions", {})
                if not dims.get("width") or not dims.get("height"):
                    print(f"    WARNING: Missing dimensions for {img['filename']}")
                assignment = {
                    "image_hash": file_hash,
                    "platform_assignment": platform,
                    "status": "assigned",
                    "category": cat_name,
                    "filename": img["filename"],
                    "file_url": img.get("file_url", img.get("filepath", ""))
                }
                assigned_images.append(assignment)
                already_assigned_hashes.add(file_hash)
                images_assigned += 1
                print(f"    -> Assigned: {img['filename']} ({cat_name}) [{img.get('width','?')}x{img.get('height','?')}]")
        if assigned_images:
            updated = update_status_json(post_folder_full_path, assigned_images, platform_identifier=platform)
            if updated:
                print(f"    -> status.json updated: {len(assigned_images)} new assignments")
            else:
                print(f"    -> status.json: no changes needed")
        request = read_request_json(post_folder_full_path)
        if request:
            updated_req = update_request_json(post_folder_full_path, info["total"], {cat: len(images_by_category.get(cat, [])) for cat in req_cats})
            if updated_req:
                print(f"    -> request.json counts updated")
        # Track posts with missing artwork for retry
        if missing_categories:
            posts_missing_artwork.append({
                "platform": platform,
                "post_folder_name": post_folder_name,
                "missing": missing_categories
            })
        posts_processed += 1
        print(f"[6/7] Consuming artwork for {platform}/{post_folder_name}...")
        if platform == "blogger":
            consume_blogger_artwork(post_folder_full_path, content, request)
        elif platform == "telegram":
            consume_telegram_artwork(post_folder_full_path, content, request)
        else:
            print(f"    -> Platform '{platform}': general synchronization complete")
        print()
    print("[7/7] Synchronization Summary:")
    print(f"    Posts processed: {posts_processed}")
    print(f"    Images assigned: {images_assigned}")
    print(f"    Total folders scanned: {len(all_discovered)}")
    if posts_missing_artwork:
        print(f"    Posts missing artwork: {len(posts_missing_artwork)}")
        for m in posts_missing_artwork:
            print(f"      {m['platform']}/{m['post_folder_name']}: {', '.join(m['missing'])}")
    else:
        print(f"    Posts missing artwork: 0")
    for (platform, post_folder_name), info in sorted(all_discovered.items()):
        status = read_status_json(info["folder"])
        assigned_count = len(status.get("image_assignments", []))
        print(f"    {platform}/{post_folder_name}: {assigned_count} assigned images")
    print()
    print("=" * 60)
    print("AUTOMATIC SYNCHRONIZATION COMPLETE")
    print("=" * 60)
    print()
    # Auto-commit and push the metadata changes to GitHub
    import subprocess
    git_status = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd="."
    )
    changed_files = [line.split()[1] for line in git_status.stdout.strip().split("\n") if line.strip()]
    if not changed_files:
        print("[INFO] No local changes to commit (all images already assigned or up to date)")
        print()
        print("=" * 60)
        print("AUTOMATIC SYNCHRONIZATION COMPLETE - No changes pushed")
        print("=" * 60)
        print()
        return True
    # Prepare commit message with summary
    commit_msg = f"chore: synchronize artwork and metadata ({posts_processed} posts, {images_assigned} images assigned)"
    # Add only the modified metadata files, not discovered images themselves
    import os as _os
    metadata_files = {"content.json", "request.json", "status.json", "discovery_validate.py"}
    files_to_add = [f for f in changed_files if _os.path.basename(f) in metadata_files]
    if files_to_add:
        add_result = subprocess.run(
            ["git", "add"] + files_to_add,
            capture_output=True, text=True, cwd="."
        )
        if add_result.returncode != 0:
            print(f"[WARN] git add partially failed: {add_result.stderr.strip()}")
    # Try to commit
    commit_result = subprocess.run(
        ["git", "commit", "-m", commit_msg],
        capture_output=True, text=True, cwd="."
    )
    if commit_result.returncode != 0 and "nothing to commit" not in commit_result.stderr:
        print(f"[INFO] Commit skipped (may already be committed): {commit_result.stderr.strip()[:100]}")
    # Try to push - handle non-fast-forward gracefully (no force-push)
    push_result = subprocess.run(
        ["git", "push", GITHUB_REMOTE_NAME, GITHUB_BRANCH],
        capture_output=True, text=True, cwd="."
    )
    if push_result.returncode == 0:
        print(f"[INFO] Successfully pushed to {GITHUB_REMOTE_NAME}/{GITHUB_BRANCH}")
    elif "Everything up-to-date" in push_result.stderr:
        print(f"[INFO] Push: {GITHUB_REMOTE_NAME}/{GITHUB_BRANCH} already up to date")
    elif "rejected" in push_result.stderr.lower() or "non-fast-forward" in push_result.stderr.lower():
        # Non-fast-forward: remote has ahead commits we don't have
        # Per safety: never force-push or overwrite remote changes
        print(f"[INFO] Push to {GITHUB_REMOTE_NAME}/{GITHUB_BRANCH} rejected (non-fast-forward)")
        print(f"    Remote has ahead commits not in local repo")
        print(f"    Per safety: not overwriting remote history")
        print(f"    To sync: run 'git pull' then re-run Hermes sync")
        print(f"    Or: git pull --rebase {GITHUB_REMOTE_NAME} {GITHUB_BRANCH} && git push {GITHUB_REMOTE_NAME} {GITHUB_BRANCH}")
    else:
        print(f"[INFO] Push status: {push_result.stdout.strip()[:120]}{push_result.stderr.strip()[:120] if push_result.stderr else ''}")
    print()
    print("=" * 60)
    print("AUTOMATIC SYNCHRONIZATION COMPLETE")
    print("=" * 60)
    print()
    return True


def build_artwork_metadata(image, content_id, platform):
    if not content_id:
        raise ValueError("Cannot assign artwork without a verified content ID")
    return {
        "artwork_id": image["file_hash"],
        "content_id": content_id,
        "platform": platform,
        "file_path": image["file_path"],
        "file_hash": image["file_hash"],
        "category": image["category"],
        "dimensions": image["dimensions"],
        "format": image["format"],
        "contributor_info": {"provider": "unknown", "model_name": None},
        "creation_date": image["creation_date"],
        "approval_status": "pending",
    }


def update_status_json(post_folder, assignments):
    status_path = post_folder / "status.json"
    if not status_path.is_file():
        print(f"WARNING: status.json missing: {status_path}")
        return 0
    status = json.loads(status_path.read_text(encoding="utf-8"))
    existing = status.get("image_assignments")
    if not isinstance(existing, list):
        existing = []
    known_hashes = {
        item.get("file_hash") for item in existing
        if isinstance(item, dict) and item.get("file_hash")
    }
    added = 0
    for assignment in assignments:
        digest = assignment["file_hash"]
        if digest not in known_hashes:
            existing.append(assignment)
            known_hashes.add(digest)
            added += 1
    status["image_assignments"] = existing
    status["last_verified"] = utc_now()
    # Discovery is not proof of backup, approval, or publication. Preserve
    # distribution_history and overall_status exactly as they were.
    status_path.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return added


def consume_blogger_artwork(post_folder_full_path, content, request):
    """Sync blogger-specific artwork assignments.

    Per the workflow: blogger platform assigns images from the local
    discovered set into status.json and updates request.json counts.
    No AI generation, no external search — only local artwork discovery.
    """
    import json
    from pathlib import Path
    status_path = post_folder_full_path / "status.json"
    content_path = post_folder_full_path / "content.json"
    assigned = []
    already_assigned = set()
    if status_path.is_file():
        existing = json.loads(status_path.read_text(encoding="utf-8")).get("image_assignments", [])
        for a in existing:
            if isinstance(a, dict) and "file_hash" in a:
                already_assigned.add(a["file_hash"])
    # Read discovered images from the info dict (passed via request context)
    # request holds the required categories and counts
    req_cats = request.get("required_artwork_categories", ["featured", "inline"]) if request else ["featured", "inline"]
    req_counts = request.get("artwork_count_requirements", {"featured": 1, "inline": 1, "total": 2}) if request else {"featured": 1, "inline": 1, "total": 2}
    # We need discovered images — they should have been scanned already.
    # Since we don't have the full discover output here, we read the status
    # and request to determine what's still missing.
    if content_path.is_file():
        content_data = json.loads(content_path.read_text(encoding="utf-8"))
        content_id = content_data.get("platform_content_id") or content_data.get("content_id") or ""
    else:
        content_id = ""
    # Read the artwork directory
    artwork_dir = post_folder_full_path / "artwork"
    new_assignments = []
    if artwork_dir.is_dir():
        for category_dir in sorted(artwork_dir.iterdir()):
            if not category_dir.is_dir():
                continue
            cat_name = category_dir.name
            if cat_name not in req_cats:
                continue
            for img_path in sorted(category_dir.iterdir()):
                if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
                    continue
                file_hash = compute_sha256(img_path)
                if file_hash in already_assigned:
                    continue
                if content_id:
                    metadata = build_artwork_metadata(
                        {"file_hash": file_hash, "filename": img_path.name,
                         "category": cat_name},
                        content_id, "blogger"
                    )
                else:
                    metadata = {"artwork_id": file_hash, "content_id": content_id,
                                "platform": "blogger", "file_path": img_path.relative_to(Path(".").resolve()).as_posix(),
                                "file_hash": file_hash, "category": cat_name,
                                "dimensions": {"width": 0, "height": 0, "unit": "px"},
                                "format": img_path.suffix.lower().lstrip("."),
                                "creation_date": utc_now(), "approval_status": "pending"}
                new_assignments.append({"file_hash": file_hash, "platform_assignment": "blogger",
                                        "status": "assigned", "category": cat_name,
                                        "filename": img_path.name,
                                        "file_url": img_path.as_posix()})
                already_assigned.add(file_hash)
    if new_assignments:
        updated = update_status_json(post_folder_full_path, new_assignments)
        print(f"    -> blogger: assigned {updated} new images")
    # Update request.json counts
    current_counts = {}
    req_path = post_folder_full_path / "request.json"
    if req_path.is_file():
        try:
            existing_req = json.loads(req_path.read_text(encoding="utf-8"))
            for cat in req_cats:
                current_counts[cat] = len(existing_req.get("artwork_by_category", {}).get(cat, []))
        except (json.JSONDecodeError, KeyError):
            current_counts = {}
    # Update counts to reflect what we have
    final_counts = {}
    for cat in req_cats:
        img_count = len([a for a in new_assignments if a["category"] == cat])
        final_counts[cat] = img_count
    if req_path.is_file():
        req_data = json.loads(req_path.read_text(encoding="utf-8"))
        for cat in req_cats:
            if cat not in req_data.get("artwork_by_category", {}):
                req_data.setdefault("artwork_by_category", {})[cat] = []
        req_data["artwork_by_category"][cat] = [{"filename": f"synced_{cat}"} for _ in range(final_counts.get(cat, 0))]
        req_path.write_text(json.dumps(req_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"    -> request.json: updated counts for {cat}: {final_counts.get(cat, 0)}")
    else:
        # Create minimal request.json
        req_data = {
            "platform_content_id": content_id,
            "required_artwork_categories": req_cats,
            "artwork_count_requirements": final_counts,
            "artwork_by_category": {cat: [] for cat in req_cats}
        }
        req_path.write_text(json.dumps(req_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"    -> request.json: created with counts {final_counts}")
    return True


def consume_telegram_artwork(post_folder_full_path, content, request):
    """Sync telegram-specific artwork assignments.

    Per the workflow: telegram platform assigns images from the local
    discovered set into status.json and updates request.json counts.
    No AI generation, no external search — only local artwork discovery.
    """
    import json
    from pathlib import Path
    status_path = post_folder_full_path / "status.json"
    content_path = post_folder_full_path / "content.json"
    assigned = []
    already_assigned = set()
    if status_path.is_file():
        existing = json.loads(status_path.read_text(encoding="utf-8")).get("image_assignments", [])
        for a in existing:
            if isinstance(a, dict) and "file_hash" in a:
                already_assigned.add(a["file_hash"])
    req_cats = request.get("required_artwork_categories", ["featured", "inline"]) if request else ["featured", "inline"]
    req_counts = request.get("artwork_count_requirements", {"featured": 1, "inline": 1, "total": 2}) if request else {"featured": 1, "inline": 1, "total": 2}
    if content_path.is_file():
        content_data = json.loads(content_path.read_text(encoding="utf-8"))
        content_id = content_data.get("platform_content_id") or content_data.get("content_id") or ""
    else:
        content_id = ""
    artwork_dir = post_folder_full_path / "artwork"
    new_assignments = []
    if artwork_dir.is_dir():
        for category_dir in sorted(artwork_dir.iterdir()):
            if not category_dir.is_dir():
                continue
            cat_name = category_dir.name
            if cat_name not in req_cats:
                continue
            for img_path in sorted(category_dir.iterdir()):
                if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
                    continue
                file_hash = compute_sha256(img_path)
                if file_hash in already_assigned:
                    continue
                if content_id:
                    metadata = build_artwork_metadata(
                        {"file_hash": file_hash, "filename": img_path.name,
                         "category": cat_name},
                        content_id, "telegram"
                    )
                else:
                    metadata = {"artwork_id": file_hash, "content_id": content_id,
                                "platform": "telegram", "file_path": img_path.relative_to(Path(".").resolve()).as_posix(),
                                "file_hash": file_hash, "category": cat_name,
                                "dimensions": {"width": 0, "height": 0, "unit": "px"},
                                "format": img_path.suffix.lower().lstrip("."),
                                "creation_date": utc_now(), "approval_status": "pending"}
                new_assignments.append({"file_hash": file_hash, "platform_assignment": "telegram",
                                        "status": "assigned", "category": cat_name,
                                        "filename": img_path.name,
                                        "file_url": img_path.as_posix()})
                already_assigned.add(file_hash)
    if new_assignments:
        updated = update_status_json(post_folder_full_path, new_assignments)
        print(f"    -> telegram: assigned {updated} new images")
    # Update request.json counts
    current_counts = {}
    req_path = post_folder_full_path / "request.json"
    if req_path.is_file():
        try:
            existing_req = json.loads(req_path.read_text(encoding="utf-8"))
            for cat in req_cats:
                current_counts[cat] = len(existing_req.get("artwork_by_category", {}).get(cat, []))
        except (json.JSONDecodeError, KeyError):
            current_counts = {}
    final_counts = {}
    for cat in req_cats:
        img_count = len([a for a in new_assignments if a["category"] == cat])
        final_counts[cat] = img_count
    if req_path.is_file():
        req_data = json.loads(req_path.read_text(encoding="utf-8"))
        for cat in req_cats:
            req_data.setdefault("artwork_by_category", {})[cat] = [{"filename": f"synced_{cat}"} for _ in range(final_counts.get(cat, 0))]
        req_path.write_text(json.dumps(req_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"    -> request.json: updated counts for {cat}: {final_counts.get(cat, 0)}")
    else:
        req_data = {
            "platform_content_id": content_id,
            "required_artwork_categories": req_cats,
            "artwork_count_requirements": final_counts,
            "artwork_by_category": {cat: [] for cat in req_cats}
        }
        req_path.write_text(json.dumps(req_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"    -> request.json: created with counts {final_counts}")
    return True


def main():
    base = Path(".").resolve()
    discovered = discover_images(base)
    folders_with_images = 0
    total_images = 0
    for (platform, folder_name), info in sorted(discovered.items()):
        assignments = []
        for images in info["images_by_category"].values():
            for image in images:
                if not info["content_id"]:
                    print(f"WARNING: no verified content ID; not assigning images for {platform}/{folder_name}")
                    continue
                assignments.append(build_artwork_metadata(image, info["content_id"], platform))
        added = update_status_json(info["folder"], assignments)
        total_images += info["total"]
        folders_with_images += int(info["total"] > 0)
        print(f"{platform}/{folder_name}: discovered={info['total']} new_assignments={added}")
    print(f"Folders scanned: {len(discovered)}")
    print(f"Folders with valid images: {folders_with_images}")
    print(f"Valid images discovered: {total_images}")
    print("Request requirements and distribution history were not modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
