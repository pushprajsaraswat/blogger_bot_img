# Android ChatGPT artwork publishing bridge

This local-only receiver transfers actual image bytes from the ChatGPT Android share sheet into the repository's existing artwork structure.

## Flow

ChatGPT Android → Android Share sheet → installed local PWA → Termux FastAPI receiver → local Git checkout → discovery_validate.py → Git commit and push.

ChatGPT does not directly call localhost. You explicitly share/save the generated image to the installed share target. A URL is not treated as an image file.

## Install on Android

Use the standard Termux app on ARM64 Android. In Termux:

~~~sh
pkg update && pkg upgrade
pkg install python git gh
mkdir -p "$HOME/apps"
cd "$HOME/apps"
git clone https://github.com/pushprajsaraswat/blogger_bot_img.git
cd blogger_bot_img
python -m venv .venv
. .venv/bin/activate
pip install -r automation/android/requirements.txt
gh auth login
gh auth setup-git
~~~

Generate a secret and start the receiver:

~~~sh
export BLOGGER_BOT_REPO="$HOME/apps/blogger_bot_img"
mkdir -p "$HOME/.config/blogger-image-inbox"
if [ ! -f "$HOME/.config/blogger-image-inbox/secret" ]; then
  umask 077
  python -c 'import secrets; print(secrets.token_urlsafe(32))' > "$HOME/.config/blogger-image-inbox/secret"
fi
export SHARE_SECRET="$(cat "$HOME/.config/blogger-image-inbox/secret")"
export PORT=8765
python automation/android/server.py

# On later starts, repeat the exports and start command. The secret file
# remains private in Termux and keeps the installed Android share target valid.
~~~

Keep Termux running. Open http://127.0.0.1:8765 in Android Chrome and install the page using the browser menu. Once installed, share an image from ChatGPT or Gallery and choose Blogger Artwork Inbox. The receiver displays an inbox ID. Open the publisher, select the correct pending post and category, enter that ID, and publish.

Each publish operation handles one image, creates one Git commit, and pushes to main. Files are stored under PLATFORM/POST_FOLDER/artwork/CATEGORY/. The existing discovery validator records image assignments in status.json.

## Hermes skill

Copy automation/hermes/SKILL.md into ~/.hermes/skills/blogger-image-publisher/SKILL.md and restart Hermes. Hermes provides the one-request-at-a-time planning and review workflow; FastAPI handles the local binary transfer and Git publishing.

## Android limitations and security

- The official Hermes Termux package is currently marked broken in its official Android installation guide (checked 2026-11-22). Re-check that guide before installing Hermes; do not use unofficial mirrors.
- Android may stop background Termux processes. Keep the session open. A wake lock and battery-optimization exemption may help but cannot guarantee uptime.
- The receiver binds only to 127.0.0.1. Do not expose it to your LAN or the public internet.
- Keep SHARE_SECRET private. Restart with a new secret if exposed.
- GitHub authentication stays in the GitHub CLI credential store; never commit tokens.
- The receiver checks image signatures, file size, request category and count, and does not overwrite existing files.
- This first version is a single-device local bridge, not a public multi-user service.
- For a public deployment, add TLS, authentication, rate limits, CSRF protection, and a durable job queue.
