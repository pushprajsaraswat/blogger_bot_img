# Contributing to Blogger Bot Artwork

## Overview
This repository centralizes artwork management for the Blogger Bot publishing system. Contributors can add artwork through GitHub.

## How to Contribute

### 1. Find Content needing Artwork
Look for folders with `request.json` where `request_status` is `pending`.

### 2. Read the Requirements
Read `content.json` and `request.json` to understand:
- The content and anime identity
- Required artwork categories
- Character and scene requirements
- Preferred dimensions and aspect ratios

### 3. Create Artwork Independently
Create artwork following these guidelines:
- Match the anime art style
- Create images at the preferred dimensions
- Use supported formats (jpg, png, webp)
- Include appropriate metadata

### 4. Commit the Artwork
Place the artwork in the content item's `artwork/` directory:
```
{content_folder}/artwork/{artwork_name}.{ext}
```

### 5. Update Metadata
Create or update `metadata.json` in the content folder with:
- Artwork ID (SHA256 hash)
- Category
- Format
- Contributor info
- Creation date

### 6. Set Approval Status
Update `request_status` in `request.json` to `in_progress` or `completed` as appropriate.

## Artwork Guidelines
- Do not fabricate character descriptions or scenes
- Match existing visual aesthetic of the publication
- Support multiple contributors and providers
- Use SHA256 hashes for deduplication
- Include contributor info (provider and model name for AI, or 'human' for hand-drawn)

## Submission Review
All contributions are reviewed before acceptance. The system validates:
- File format and dimensions
- SHA256 hash uniqueness
- Metadata completeness
- Category matching

Thank you for contributing!
