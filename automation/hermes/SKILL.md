---
name: blogger-image-publisher
description: Work through one pending blogger_bot_img artwork request at a time and publish ChatGPT-generated images through the Android share receiver.
---

# Blogger Image Publisher

## Rules
- Work on exactly one content request at a time.
- Read that request's content.json and request.json before creating artwork.
- Never invent content IDs, folder paths, requested categories, or filenames.
- Never overwrite an existing image or exceed the requested category count.
- Publish one image per action and verify the remote commit before claiming success.
- Never put GitHub credentials or SHARE_SECRET in prompts, skill files, or repository content.

## Workflow
1. Inspect the repository's pending request and select one request.
2. Read docs/ARTWORK_GUIDE.md and the selected post's content.json and request.json.
3. Ask ChatGPT to generate one image for one requested category.
4. In the ChatGPT Android app, save/share the generated image and choose the installed Blogger Artwork Inbox PWA. The PWA transfers the actual image bytes to the local Termux receiver.
5. Use the PWA to select the matching content request and category. Publish only one image.
6. The receiver validates the image signature and size, checks category capacity, runs discovery_validate.py, commits and pushes.
7. Verify the exact artwork path exists on origin/main before reporting success.
8. Continue with the next image only after successful verification.

## Failure handling
If Hermes is unavailable on Android, do not claim Hermes performed the operation. The FastAPI receiver is independently usable. On validation, authentication, pull, or push failure, keep the inbox file and report the actual error.
