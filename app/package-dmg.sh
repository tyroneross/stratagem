#!/bin/bash
# Package Stratagem as a DMG installer with drag-to-Applications
set -euo pipefail

APP_NAME="Stratagem"
DMG_NAME="${APP_NAME}-Installer"
VERSION="0.1"
VOLUME_NAME="${APP_NAME} ${VERSION}"
DMG_FILE="${DMG_NAME}.dmg"
STAGING_DIR=".dmg-staging"
BUILD_DIR="build/Build/Products/Release"

cd "$(dirname "$0")"

# Step 1: Check for xcodegen and generate project if needed
if ! command -v xcodegen &>/dev/null; then
    echo "Error: xcodegen is required. Install with: brew install xcodegen"
    exit 1
fi

if [ ! -d "${APP_NAME}.xcodeproj" ]; then
    echo "=== Generating Xcode project ==="
    xcodegen generate
fi

# Step 2: Build the app
echo "=== Building ${APP_NAME} ==="
xcodebuild \
    -scheme "${APP_NAME}" \
    -configuration Release \
    -derivedDataPath build \
    -arch arm64 \
    build

# Step 3: Verify the .app exists
if [ ! -d "${BUILD_DIR}/${APP_NAME}.app" ]; then
    echo "Error: ${APP_NAME}.app not found at ${BUILD_DIR}/"
    exit 1
fi

# Step 4: Prepare staging directory
echo ""
echo "=== Preparing DMG contents ==="
rm -rf "${STAGING_DIR}" "${DMG_FILE}"
mkdir -p "${STAGING_DIR}"

# Copy .app bundle
cp -R "${BUILD_DIR}/${APP_NAME}.app" "${STAGING_DIR}/"

# Create Applications symlink (drag-to-install target)
ln -s /Applications "${STAGING_DIR}/Applications"

# Step 5: Create DMG
echo ""
echo "=== Creating DMG ==="
hdiutil create \
    -volname "${VOLUME_NAME}" \
    -srcfolder "${STAGING_DIR}" \
    -ov \
    -format UDZO \
    -imagekey zlib-level=9 \
    "${DMG_FILE}"

# Clean up staging
rm -rf "${STAGING_DIR}"

# Show result
DMG_SIZE=$(du -h "${DMG_FILE}" | cut -f1)
echo ""
echo "=== Done ==="
echo "  ${DMG_FILE} (${DMG_SIZE})"
echo ""
echo "  To install: Open the DMG and drag Stratagem to Applications"
