#!/usr/bin/env bash
# AI Token Tracker installer (Linux / macOS).
# Creates a virtual environment, installs dependencies, sets up user config,
# and (on Linux) registers a desktop launcher.
set -e
cd "$(dirname "$0")"
APP_DIR="$(pwd)"

echo "==> Creating virtual environment (.venv)"
# --system-site-packages so pywebview can use the system GTK/WebKit bindings (gi) on Linux.
python3 -m venv --system-site-packages .venv

echo "==> Installing dependencies"
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt

echo "==> Setting up user config"
if [ ! -f config/user.config.yaml ]; then
  cp config/user.config.example.yaml config/user.config.yaml
  echo "    Created config/user.config.yaml — edit it with your username/home if needed."
else
  echo "    config/user.config.yaml already exists, leaving it untouched."
fi

chmod +x run.sh

# Desktop launcher (Linux only).
if [ "$(uname)" = "Linux" ]; then
  echo "==> Registering desktop launcher"
  DESKTOP_DIR="$HOME/.local/share/applications"
  mkdir -p "$DESKTOP_DIR"
  cat > "$DESKTOP_DIR/ai-token-tracker.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=AI Token Tracker
Comment=Show Claude / Codex / Antigravity token usage
Exec=$APP_DIR/run.sh
Icon=utilities-system-monitor
Terminal=false
Categories=Utility;Monitor;
StartupNotify=true
EOF
  update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
  echo "    Installed: AI Token Tracker (find it in your app menu)."
fi

echo "==> Done. Run it with: ./run.sh"
