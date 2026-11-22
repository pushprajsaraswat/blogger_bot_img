#!/usr/bin/env python3
"""Discover artwork in platform/post-ID folders and safely synchronize status.json.

The request.json file is authoritative for requested artwork counts. Discovery
must never rewrite those requirements: it only records files that actually exist.
"""
import hashlib
import json
import struct
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


def utc_now():
    return datetime.now(timezone.utc).isoformat()


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
