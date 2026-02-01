# Torrent Adder

A simple macOS app for adding torrents to a remote Transmission server with smart directory selection.

## Features

- **Native macOS dialogs** - Uses AppleScript for clean, native UI
- **Supports .torrent files and magnet links** - Open files or click magnet links in browser
- **Smart TV show detection** - Automatically suggests the right TV show folder based on torrent name
- **Directory API** - Fetches available directories from a remote server
- **Auto-start torrents** - Torrents start downloading immediately

## Installation

### macOS App

The app is created using AppleScript and lives in `/Applications/TorrentAdder.app`.

To rebuild the app:

```bash
osacompile -o /Applications/TorrentAdder.app -e '
on open location theURL
    do shell script "/usr/bin/python3 /Users/dgoo2308/git/torrent-adder/torrent_adder.py " & quoted form of theURL
end open location

on open theFiles
    repeat with theFile in theFiles
        set filePath to POSIX path of theFile
        do shell script "/usr/bin/python3 /Users/dgoo2308/git/torrent-adder/torrent_adder.py " & quoted form of filePath
    end repeat
end open

on run
    display dialog "Drop a .torrent file on this app, use Open With, or click a magnet link" with title "Torrent Adder" buttons {"OK"} with icon note
end run
'
```

Then register it:

```bash
# Add bundle ID and URL scheme
plutil -replace CFBundleIdentifier -string "com.nellika.torrentadder" /Applications/TorrentAdder.app/Contents/Info.plist
plutil -replace CFBundleURLTypes -json '[{"CFBundleURLName":"Magnet Link","CFBundleURLSchemes":["magnet"]}]' /Applications/TorrentAdder.app/Contents/Info.plist
plutil -replace CFBundleDocumentTypes -json '[{"CFBundleTypeName":"BitTorrent File","CFBundleTypeRole":"Viewer","CFBundleTypeExtensions":["torrent"],"LSHandlerRank":"Owner"}]' /Applications/TorrentAdder.app/Contents/Info.plist

# Register with Launch Services
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f /Applications/TorrentAdder.app
```

### Server-side API (LibreELEC/Linux)

The directory API runs on the server hosting the media files. Install it as a systemd service:

```bash
# Copy torrent-api.py to /storage/ (or your preferred location)
# Create systemd service at /storage/.config/system.d/torrent-api.service

[Unit]
Description=Torrent Directory API
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /storage/torrent-api.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

Enable and start:

```bash
systemctl daemon-reload
systemctl enable torrent-api
systemctl start torrent-api
```

## Configuration

Edit `config.json`:

```json
{
    "host": "192.168.1.205",
    "port": 9091,
    "username": "",
    "password": "",
    "api_host": "192.168.1.205",
    "api_port": 8765
}
```

- `host` / `port` - Transmission RPC server
- `username` / `password` - Transmission authentication (leave empty if none)
- `api_host` / `api_port` - Directory API server

## Usage

### Opening .torrent files

1. Right-click a `.torrent` file
2. Select **Open With** → **TorrentAdder**
3. Choose download directory (or accept the auto-suggestion for TV shows)

To set as default: **Get Info** → **Open with** → **TorrentAdder** → **Change All...**

### Magnet links

Click a magnet link in your browser. On first use, select TorrentAdder and check "Always use".

### Smart directory detection

For TV shows with names like `Show.Name.S01E02.1080p...`, the app will:
1. Extract the show name ("Show Name")
2. Search for a matching folder in your TV Shows directory
3. Pre-select it and ask for confirmation

## API Endpoints

The directory API provides:

- `GET /` - List all base directories
- `GET /movies` - Movies directory path
- `GET /downloads` - Downloads directory path  
- `GET /tvshows` - List all TV show directories

## Requirements

- macOS (for the GUI app)
- Python 3.x
- Transmission daemon with RPC enabled
- Network access to Transmission and the directory API

## License

MIT
