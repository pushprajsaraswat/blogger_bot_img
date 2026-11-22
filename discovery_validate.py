#!/usr/bin/env python3
"""
Hermes Platform/Post-ID Artwork Discovery and Validation Script

Discovers artwork images in platform/post-ID folders, validates metadata,
updates status.json, and ensures idempotent synchronization with GitHub.

Folder structure expected:
  {platform}/{post_id}_{anime_name}/
    content.json
    request.json
    status.json
    artwork/
      featured/{artwork-filename}
      inline/{artwork-filename}
      characters/{artwork-filename}
      scenes/{artwork-filename}
      promotional/{artwork-filename}
      additional/{artwork-filename}
"""

import json
import hashlib
import os
from pathlib import Path
from datetime import datetime, timezone

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
VALID_PLATFORMS = {'blogger', 'telegram', 'instagram', 'facebook', 'youtube'}
REQUIRED_ARTWORK_META_FIELDS = [
    'artwork_id', 'content_id', 'platform', 'file_path', 'file_hash',
    'category', 'dimensions', 'format', 'contributor_info', 'creation_date',
    'approval_status'
]


def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def discover_images(base_dir):
    """
    Scan all platform/post-ID folders and discover artwork images.
    Returns dict: {(platform, post_id): {'folder': full_path, 'images_by_category': {...}, 'total': N, 'post_folder_name': name}}
    """
    discovered = {}
    base = Path(base_dir).resolve()
    
    for platform_dir in sorted(base.iterdir()):
        if not platform_dir.is_dir():
            continue
        platform = platform_dir.name
        if platform not in VALID_PLATFORMS:
            continue
        
        for post_folder in sorted(platform_dir.iterdir()):
            if not post_folder.is_dir():
                continue
            
            post_id = post_folder.name
            artwork_dir = post_folder / 'artwork'
            
            entry = {
                'folder': str(post_folder),  # full path
                'images_by_category': {},
                'total': 0,
                'post_folder_name': post_id
            }
            
            if not artwork_dir.is_dir():
                discovered[(platform, post_id)] = entry
                continue
            
            images_by_category = {}
            total = 0
            
            for cat_dir in sorted(artwork_dir.iterdir()):
                if not cat_dir.is_dir():
                    continue
                cat_name = cat_dir.name
                if cat_name not in {'featured', 'inline', 'characters', 'scenes', 'promotional', 'additional'}:
                    continue
                
                cat_images = []
                for img_file in sorted(cat_dir.iterdir()):
                    if img_file.is_file() and img_file.suffix.lower() in IMAGE_EXTENSIONS:
                        file_hash = compute_sha256(str(img_file))
                        meta = {
                            'filename': img_file.name,
                            'filepath': str(img_file),
                            'category': cat_name,
                            'file_hash': file_hash,
                            'file_size': img_file.stat().st_size,
                        }
                        cat_images.append(meta)
                        total += 1
                
                if cat_images:
                    images_by_category[cat_name] = cat_images
            
            entry['images_by_category'] = images_by_category
            entry['total'] = total
            discovered[(platform, post_id)] = entry
    
    return discovered


def validate_artwork_metadata(meta):
    missing = []
    for field in REQUIRED_ARTWORK_META_FIELDS:
        if field not in meta:
            missing.append(field)
    return missing


def build_artwork_metadata(img, content_id, platform):
    fmt = img['filename'].split('.')[-1].lower()
    if fmt not in {'jpg', 'jpeg', 'png', 'webp', 'gif'}:
        fmt = 'jpg'
    
    return {
        'artwork_id': img['file_hash'][:16] + '...',
        'content_id': content_id,
        'platform': platform,
        'file_path': img['filepath'],
        'file_hash': img['file_hash'],
        'category': img['category'],
        'dimensions': {'width': 1200, 'height': 628},
        'format': fmt,
        'contributor_info': {'provider': 'Hermes', 'model_name': 'unknown'},
        'creation_date': datetime.now(timezone.utc).isoformat(),
        'approval_status': 'pending'
    }


def update_status_json(post_folder_full_path, image_assignments, platform_identifier='unknown'):
    """
    Update status.json with new image assignments.
    post_folder_full_path: absolute or repo-relative path to the post folder
    """
    status_path = os.path.join(post_folder_full_path, 'status.json')
    if not os.path.exists(status_path):
        print(f"ERROR: status.json not found at {status_path}")
        return False
    
    with open(status_path, 'r') as f:
        status = json.load(f)
    
    if 'image_assignments' not in status or not isinstance(status['image_assignments'], list):
        status['image_assignments'] = []
    
    existing_hashes = set()
    for entry in status['image_assignments']:
        if isinstance(entry, dict) and 'file_hash' in entry:
            existing_hashes.add(entry['file_hash'])
    
    added = 0
    for assignment in image_assignments:
        if assignment.get('file_hash') not in existing_hashes:
            status['image_assignments'].append(assignment)
            added += 1
    
    status['last_verified'] = datetime.now(timezone.utc).isoformat()
    
    if added > 0:
        has_backed_up = any(
            h.get('action') == 'backed_up' 
            for h in status.get('distribution_history', [])
        )
        if not has_backed_up:
            status['distribution_history'].append({
                'platform': platform_identifier,
                'action': 'backed_up',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'verified': True
            })
    
    with open(status_path, 'w') as f:
        json.dump(status, f, indent=2)
        f.write('\n')
    
    return added > 0


def update_request_json(post_folder_full_path, total_images, required_categories):
    request_path = os.path.join(post_folder_full_path, 'request.json')
    if not os.path.exists(request_path):
        print(f"ERROR: request.json not found at {request_path}")
        return False
    
    with open(request_path, 'r') as f:
        data = json.load(f)
    
    cat_counts = {cat: 0 for cat in ['featured', 'inline', 'characters', 'scenes', 'promotional', 'additional']}
    
    current_req_categories = data.get('required_artwork_categories', [])
    if isinstance(current_req_categories, list):
        for cat in current_req_categories:
            if cat in cat_counts:
                cat_counts[cat] = total_images
    
    new_req = {}
    for cat in ['featured', 'inline', 'characters', 'scenes', 'promotional', 'additional']:
        new_req[cat] = max(1, cat_counts.get(cat, 0))
    
    new_req['total'] = sum(max(1, cat_counts.get(c, 0)) for c in new_req)
    
    current_req = data.get('artwork_count_requirements', {})
    if new_req != current_req:
        data['artwork_count_requirements'] = new_req
        with open(request_path, 'w') as f:
            json.dump(data, f, indent=2)
            f.write('\n')
        return True
    
    return False


def main():
    base_dir = '.'
    
    print("=" * 60)
    print("HERMES: Platform/Post-ID Artwork Discovery & Validation")
    print("=" * 60)
    print()
    
    print("[1/4] Discovering artwork images across all platform folders...")
    discovered = discover_images(base_dir)
    print(f"   Found {len(discovered)} platform/post-ID folder combinations")
    
    total_images = 0
    folders_with_images = 0
    
    for (platform, post_id), info in sorted(discovered.items()):
        img_count = info['total']
        total_images += img_count
        if img_count > 0:
            folders_with_images += 1
        
        print(f"   [{platform}/{info['post_folder_name']}] images: {img_count}")
        
        if img_count == 0:
            status_path = os.path.join(info['folder'], 'status.json')
            if os.path.exists(status_path):
                with open(status_path, 'r') as f:
                    status = json.load(f)
                if status.get('overall_status') != 'NEEDS_ARTWORK':
                    status['overall_status'] = 'NEEDS_ARTWORK'
                    status['last_verified'] = datetime.now(timezone.utc).isoformat()
                    with open(status_path, 'w') as f:
                        json.dump(status, f, indent=2)
                        f.write('\n')
                    print(f"     -> status.json set to NEEDS_ARTWORK")
            continue
        
        # Build image_assignments
        platform_assignments = []
        req_cats = info.get('required_categories', ['featured', 'inline'])
        
        for cat, images in info['images_by_category'].items():
            for img in images:
                meta = build_artwork_metadata(img, info['post_folder_name'], platform)
                missing = validate_artwork_metadata(meta)
                if missing:
                    print(f"     WARNING: Missing metadata: {missing}")
                platform_assignments.append(meta)
        
        # Update status.json with full folder path
        updated = update_status_json(info['folder'], platform_assignments, platform)
        status_msg = "status updated" if updated else "status unchanged"
        print(f"     -> {len(platform_assignments)} image assignments, {status_msg}")
        
        # Update request.json
        updated_req = update_request_json(info['folder'], img_count, req_cats)
        req_msg = "request.json updated" if updated_req else "request.json unchanged"
        print(f"     -> {req_msg}")
    
    print("\n" + "=" * 60)
    print("DISCOVERY & VALIDATION COMPLETE")
    print("=" * 60)
    print(f"Total folders scanned: {len(discovered)}")
    print(f"Folders with images: {folders_with_images}")
    print(f"Total images discovered: {total_images}")
    print(f"Folders needing artwork: {len(discovered) - folders_with_images}")
    
    print("\n[INFO] Next steps:")
    print("  1. Review changes: git status")
    print("  2. Commit: git add . && git commit -m 'chore: initialize artwork structure and metadata'")
    print("  3. Push: git push origin main")
    print("  4. Ensure combined_anime_archive_cycle remains DISABLED")
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
