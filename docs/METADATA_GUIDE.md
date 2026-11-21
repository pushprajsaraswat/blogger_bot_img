# Metadata Guide

## Overview
This guide defines the metadata structure for all content and artwork in the Blogger Bot system.

## Folder Structure
Each content item has its own folder with the following structure:

```
{platform}/
  {platform_id}_{anime_name}/
    content.json          # Platform and content identification
    request.json          # Artwork requirements
    status.json           # Current status, backup evidence, and artwork assignments
    artwork/
      featured/{artwork}  # Featured artwork
      inline/{artwork}  # Inline article images
      characters/{artwork}  # Character-specific artwork
      scenes/{artwork}  # Scene depictions
      promotional/{artwork}  # Promotional artwork
      additional/{artwork}  # Additional artwork
```

## content.json Fields

| Field | Type | Description |
|-------|------|-------------|
| `platform` | string | Publishing platform (blogger, telegram, etc.) |
| `platform_content_id` | string | Stable platform-specific ID |
| `title` | string | Content title |
| `anime_name` | string | Associated anime title |
| `anime_id` | string | Verified anime ID (optional) |
| `content_url` | string | URL to the content on the publishing platform |
| `content_summary` | string | Brief content summary |
| `character_names` | array | List of character names |
| `character_ids` | array | List of verified character IDs |
| `labels` | array | Labels/categories/tags |
| `content_type` | string | Type of content |
| `publication_date` | string | Publication date (ISO 8601) |
| `has_media` | boolean | Whether content has images |
| `source` | string | Source identifier |
| `last_synchronized` | string | Last API sync timestamp |

## request.json Fields

| Field | Type | Description |
|-------|------|-------------|
| `content_identity` | object | Platform and content identification |
| `anime_identity` | object | Anime name and ID |
| `content_title_summary` | string | Title/summary context |
| `required_artwork_categories` | array | Needed categories |
| `featured_image_requirements` | object | Featured image specs |
| `character_image_requirements` | object | Character image specs |
| `scene_image_requirements` | object | Scene image specs |
| `promotional_image_requirements` | object | Promotional image specs |
| `suggested_filenames` | object | Recommended file names |
| `artwork_count_requirements` | object | Count per category |
| `visual_context_and_instructions` | string | Creation guidance |
| `priority` | string | Priority level |
| `request_creation_date` | string | ISO 8601 timestamp |
| `request_status` | string | Request status |

## status.json Fields (per content folder)

| Field | Type | Description |
|-------|------|-------------|
| `content_id` | string | Reference to content |
| `overall_status` | string | Migration status (DISCOVERED, BACKED_UP, etc.) |
| `last_verified` | string | Last verification timestamp |
| `image_assignments` | array | Platform-specific artwork assignments |
| `distribution_history` | array | History of image actions |
| `duplicate_prevention` | object | Dedup config |
| `backup_info` | object | Backup timestamp and platform identifiers/recorded image URLs |

## artwork-metadata.json Fields (per artwork file)

| Field | Type | Description |
|-------|------|-------------|
| `artwork_id` | string | Unique artwork identifier (SHA256) |
| `content_id` | string | Referenced content |
| `platform` | string | Target platform |
| `file_path` | string | Path to artwork file |
| `file_hash` | string | SHA256 hash |
| `category` | string | Artwork category |
| `dimensions` | object | Width and height |
| `format` | string | Image format |
| `contributor_info` | object | Provider and model details |
| `creation_date` | string | ISO 8601 timestamp |
| `approval_status` | string | Pending/approved/rejected |
| `licensing_info` | object | Licensing details |
| `match_confidence` | number | 0-1 confidence score |

## Status Progression

Each content item progresses through these statuses:

```
DISCOVERED → BACKED_UP → OLD_ARTWORK_REMOVED → NEEDS_ARTWORK → 
ARTWORK_AVAILABLE → REPLACEMENT_PUBLISHED → VERIFIED
```

Or may enter `FAILED` or `NEEDS_REVIEW` at any point if issues are encountered.

## Migration States Explained

- **DISCOVERED**: Content has been identified and folder created
- **BACKED_UP**: All old image URLs/identifiers recorded before removal
- **OLD_ARTWORK_REMOVED**: Images removed from platform (Blogger/Telegram)
- **NEEDS_ARTWORK**: No suitable artwork currently available
- **ARTWORK_AVAILABLE**: matching artwork found in repository
- **REPLACEMENT_PUBLISHED**: New artwork successfully published to platform
- **VERIFIED**: Remote content verified to match expectations
- **FAILED**: Operation could not complete (see error notes)
- **NEEDS_REVIEW**: Requires human review decision

## Best Practices

1. **Always back up before removal** - Record all old image URLs and identifiers before removing
2. **Verify remote results** - After removing or adding images, confirm the change on the actual platform
3. **Use SHA256 for deduplication** - Prevent duplicate assets using file hashes
4. **Preserve content integrity** - Never delete article text or message content when removing images
5. **Track all changes** - Maintain a complete distribution history per platform
6. **Mark NEEDS_REVIEW when uncertain** - If any step cannot be verified, mark for human review
