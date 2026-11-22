---
name: blogger-image-publisher
description: Coordinate ChatGPT-generated artwork for blogger_bot_img on Android/Termux. Select one pending post, prepare image instructions, receive shared image files, and publish one image at a time.
---

# Blogger Image Publisher

## Operating model
- ChatGPT Android generates artwork.
- The Android share sheet transfers actual image bytes to the local FastAPI receiver.
- Hermes coordinates repository inspection and publishing. Do not claim an image has transferred until a real file is present in the Termux inbox.
- The local repository defaults to ~/apps/blogger_bot_img. Confirm the actual path before acting.

## Hard rules
- Work on exactly one content request at a time.
- Read the selected post's content.json and request.json. Inspect identity, categories, counts, visual instructions, and suggested filenames. Do not print or ingest large embedded data-URI/base64 blocks from content_summary or content.json; extract only relevant text fields.
- Never invent content IDs, folder paths, categories, filenames, image facts, or dimensions.
- Never overwrite an existing image or exceed the requested category count.
- Do not alter request.json request_status or claim content is completed merely because an image was committed. Downstream Blogger/Telegram distribution is separate.
- Never put GitHub credentials or SHARE_SECRET in prompts, skill files, repository content, or logs.

## Setup and diagnostics
1. Confirm repository path and branch with: git -C "$HOME/apps/blogger_bot_img" status --short --branch
2. Install this skill locally: mkdir -p ~/.hermes/skills/blogger-image-publisher && cp "$HOME/apps/blogger_bot_img/automation/hermes/SKILL.md" ~/.hermes/skills/blogger-image-publisher/SKILL.md
3. Check hermes skills or hermes skills list. Start a new Hermes session and invoke /blogger-image-publisher.
4. Check http://127.0.0.1:8765/health. If unavailable, follow automation/android/README.md to start the receiver.
5. The receiver is a separate process. Hermes terminal access does not imply the receiver is running.

## Per-image workflow
1. Inspect pending requests and select one. Use content_identity.platform_content_id, content_identity.title, anime_identity.anime_name, required_artwork_categories, artwork_count_requirements, featured_image_requirements, suggested_filenames, and visual_context_and_instructions.
2. Read docs/ARTWORK_GUIDE.md. Create one detailed ChatGPT image prompt for one category. Include target dimensions/aspect ratio where specified, composition, mood, anime/content context, and instructions to avoid unintended text, logos, or watermarks.
3. Ask the user to generate that image in ChatGPT and share/save it to the installed Blogger Artwork Inbox PWA. A successful share displays an inbox ID. A temporary image URL is not a substitute for file bytes.
4. The user selects the matching post/category in the PWA and submits the inbox ID. The receiver checks image signature, maximum size, requested category and remaining category count; it then runs discovery_validate.py, commits the image and relevant status metadata, and pushes the configured branch.
5. Verify the exact path and commit on the remote branch. Report path and commit only after verification.
6. Continue with the next required image for that same request. Move to another request only when all required artwork files have been committed and verified.

## Safety and recovery
- Receiver binds to 127.0.0.1 only. Do not expose it to LAN or public internet.
- On failed validation, Git pull, commit, or push, preserve the inbox image and report the error. Inspect git status before retrying.
- Never force-push, reset, delete existing artwork, or silently overwrite files.
- If Hermes cannot access the local Termux path, ask the user to run commands in Termux; do not assume Hermes and Termux share a filesystem.
- Do not claim Blogger or Telegram publication has happened. This system commits artwork into the repository; platform distribution is a later stage.
