#!/bin/bash
# Open Stratagem — double-click this file from Finder
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/app" && pwd)"
APP_PATH="${APP_DIR}/build/Build/Products/Release/Stratagem.app"

# If already running, just activate it
if pgrep -x "Stratagem" > /dev/null 2>&1; then
    osascript -e 'tell application "Stratagem" to activate'
    exit 0
fi

# If built, open it
if [ -d "$APP_PATH" ]; then
    open "$APP_PATH"
    exit 0
fi

# Not built yet — build first
echo "Building Stratagem..."
cd "$APP_DIR"

if ! command -v xcodegen &>/dev/null; then
    echo "Error: xcodegen required. Install: brew install xcodegen"
    read -rp "Press Enter to close..."
    exit 1
fi

[ ! -d "Stratagem.xcodeproj" ] && xcodegen generate

xcodebuild \
    -scheme Stratagem \
    -configuration Release \
    -derivedDataPath build \
    -arch arm64 \
    build -quiet

if [ -d "$APP_PATH" ]; then
    echo "Build complete. Opening..."
    open "$APP_PATH"
else
    echo "Build failed — Stratagem.app not found."
    read -rp "Press Enter to close..."
    exit 1
fi
