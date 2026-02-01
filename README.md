# Torrent Adder

A simple macOS app for adding torrents to a remote Transmission server with smart directory selection.

## Features

- **Native macOS dialogs** - Uses AppleScript for clean, native UI
- **Supports .torrent files and magnet links** - Open files or click magnet links in browser
- **Smart TV show detection** - Automatically suggests the right TV show folder based on torrent name
- **New TV Show folder** - Create new TV show directories on the fly
- **Directory API** - Fetches available directories from a remote server
- **Auto-start torrents** - Torrents start downloading immediately

## Installation

### Quick Install

```bash
git clone https://github.com/dgoo2308/torrent-adder.git
cd torrent-adder
./install.sh
```

Then edit your config:
```bash
nano ~/.config/torrent-adder/config.json
```

### Manual Installation

1. Copy `torrent_adder.py` to `~/.local/share/torrent-adder/`
2. Copy `config.json.example` to `~/.config/torrent-adder/config.json` and edit
3. Run the AppleScript commands in `install.sh` to create the app

## Configuration

Edit `~/.config/torrent-adder/config.json`:

```json
{
    "host": "192.168.1.100",
    "port": 9091,
    "username": "",
    "password": "",
    "api_host": "192.168.1.100",
    "api_port": 8765,
    "proxy": {
        "enabled": false,
        "host": "127.0.0.1",
        "port": 1080
    }
}
```

| Setting | Description |
|---------|-------------|
| `host` / `port` | Transmission RPC server |
| `username` / `password` | Transmission authentication (leave empty if none) |
| `api_host` / `api_port` | Directory API server |
| `proxy.enabled` | Enable SOCKS5 proxy |
| `proxy.host` / `proxy.port` | SOCKS5 proxy address |

**Note:** The proxy applies to both Transmission RPC and Directory API connections.

## Server-side API (LibreELEC/Linux)

The directory API runs on the server hosting the media files. See `server/torrent-api.py`.

Install as a systemd service:

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

### New TV Show folder

Select "── New TV Show Folder ──" to create a new directory. The folder name is auto-suggested from the torrent name.

## API Endpoints

The directory API provides:

- `GET /` - List all base directories
- `GET /movies` - Movies directory path
- `GET /downloads` - Downloads directory path  
- `GET /tvshows` - List all TV show directories

## Requirements

- macOS (for the GUI app)
- Python 3.x (uses only standard library)
- Transmission daemon with RPC enabled
- Network access to Transmission and the directory API

## License

MIT
