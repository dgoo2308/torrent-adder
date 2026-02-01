#!/bin/bash
#
# TorrentAdder Install Script
# Installs the app to /Applications and registers it for .torrent files and magnet links
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="TorrentAdder"
APP_PATH="/Applications/${APP_NAME}.app"
INSTALL_DIR="$HOME/.local/share/torrent-adder"
CONFIG_DIR="$HOME/.config/torrent-adder"

echo "Installing TorrentAdder..."

# Create directories
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"

# Copy Python script
cp "$SCRIPT_DIR/torrent_adder.py" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/torrent_adder.py"

# Copy config template if not exists
if [ ! -f "$CONFIG_DIR/config.json" ]; then
    cp "$SCRIPT_DIR/config.json.example" "$CONFIG_DIR/config.json"
    echo "Created config at $CONFIG_DIR/config.json - please edit with your settings"
fi

# Remove old app if exists
rm -rf "$APP_PATH"

# Create AppleScript app
osacompile -o "$APP_PATH" -e '
on open location theURL
    do shell script "exec '$INSTALL_DIR/torrent_adder.py' " & quoted form of theURL
end open location

on open theFiles
    repeat with theFile in theFiles
        set filePath to POSIX path of theFile
        do shell script "exec '$INSTALL_DIR/torrent_adder.py' " & quoted form of filePath
    end repeat
end open

on run
    display dialog "Drop a .torrent file on this app, use Open With, or click a magnet link" with title "Torrent Adder" buttons {"OK"} with icon note
end run
'

# Set bundle identifier
plutil -replace CFBundleIdentifier -string "com.nellika.torrentadder" "$APP_PATH/Contents/Info.plist"

# Register for magnet URLs
plutil -replace CFBundleURLTypes -json '[{"CFBundleURLName":"Magnet Link","CFBundleURLSchemes":["magnet"]}]' "$APP_PATH/Contents/Info.plist"

# Register for .torrent files
plutil -replace CFBundleDocumentTypes -json '[{"CFBundleTypeName":"BitTorrent File","CFBundleTypeRole":"Viewer","CFBundleTypeExtensions":["torrent"],"LSHandlerRank":"Owner"}]' "$APP_PATH/Contents/Info.plist"

# Copy icon - prefer bundled, fallback to Transmission Remote GUI
if [ -f "$SCRIPT_DIR/resources/icon.icns" ]; then
    cp "$SCRIPT_DIR/resources/icon.icns" "$APP_PATH/Contents/Resources/droplet.icns"
    echo "Copied bundled icon"
elif [ -f "/Applications/Transmission Remote GUI.app/Contents/Resources/transgui.icns" ]; then
    cp "/Applications/Transmission Remote GUI.app/Contents/Resources/transgui.icns" "$APP_PATH/Contents/Resources/droplet.icns"
    echo "Copied icon from Transmission Remote GUI"
fi

# Register with Launch Services
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$APP_PATH"

# Touch to refresh and clear icon cache
touch "$APP_PATH"
touch "$APP_PATH/Contents/Info.plist"
touch "$APP_PATH/Contents/Resources/droplet.icns"

# Try to clear icon cache (may require restart/logout to take full effect)
rm -rf ~/Library/Caches/com.apple.iconservices.store 2>/dev/null || true
killall Finder 2>/dev/null || true
killall Dock 2>/dev/null || true

echo ""
echo "✓ TorrentAdder installed successfully!"
echo ""
echo "Installed to:"
echo "  App:    $APP_PATH"
echo "  Script: $INSTALL_DIR/torrent_adder.py"
echo "  Config: $CONFIG_DIR/config.json"
echo ""
echo "To set as default for .torrent files:"
echo "  1. Right-click any .torrent file"
echo "  2. Get Info → Open with → TorrentAdder → Change All"
echo ""
echo "For magnet links, click one in your browser and select TorrentAdder"
