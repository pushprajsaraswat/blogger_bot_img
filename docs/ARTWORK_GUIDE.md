# Artwork Guide

## Purpose
This guide defines how artwork is matched, validated, and distributed to publishing platforms.

## Artwork Categories

### Featured Image
- Primary representative image for the content
- Used as the cover/thumbnail
- Required for most content items
- Preferred dimensions: 1200x628 (Blogger), 800x450 (Telegram)

### Inline Images
- Images embedded within the article/content body
- Used for Blogger posts with article images
- Each image position should be documented

### Character Images
- Individual character portraits or scenes
- Required when content focuses on specific characters
- Character IDs should be documented in content.json

### Scene Images
- Key scene depictions from the anime content
- Optional, based on content type

### Promotional Images
- Banner or promotional-style artwork
- Optional, based on content needs

## Matching Rules

### Priority Order
1. **Exact platform content ID** - Match by Blogger post ID or Telegram message ID
2. **Exact post_id** - Match by stable platform identifier
3. **Verified anime_id** - Match by confirmed anime identifier
4. **Verified character_id** - Match by confirmed character identifier

### Rejection Criteria
- Artwork does not match the requested category
- Dimensions or format do not meet requirements
- SHA256 hash indicates duplicate asset
- Licensing/permission issues
- Content identity cannot be verified

## Validation Checklist
- [ ] File format is supported (jpg, png, webp)
- [ ] Dimensions match preferred specifications
- [ ] SHA256 hash is unique (no duplicate)
- [ ] Metadata is complete (artwork_id, content_id, platform, category, etc.)
- [ ] Contributor info is provided
- [ ] Licensing info is documented
- [ ] Artwork category matches request requirements
- [ ] Visual style is appropriate for the content

## Distribution Workflow

### Blogger Integration
1. Read the content item's `content.json` and `request.json`
2. Validate the contributed artwork against the request
3. Attach the image to the Blogger post via the Blogger API
4. Update `metadata.json` and `status.json`
5. Mark the request as completed

### Telegram Integration
1. Read the content item's `content.json` and `request.json`
2. Validate the contributed artwork against the request
3. Send the artwork to the Telegram channel
4. Update `metadata.json` and `status.json`
5. Mark the request as completed

## Contributor Notes
- Independent AI providers can contribute without knowing the Blogger Bot's internal model
- Human contributors follow the same workflow
- All contributions are validated against the schema before acceptance
- Rejected contributions receive feedback on what needs revision

## Submission Review
All contributions are reviewed before acceptance. The system validates:
- File format and dimensions
- SHA256 hash uniqueness
- Metadata completeness
- Category matching

Thank you for contributing!
