# Torrent Adder

A simple macOS app for adding torrents to a remote Transmission server with smart directory selection.

## Features

- **Native macOS dialogs** - Uses AppleScript for clean, native UI
- **Supports .torrent files and magnet links** - Open files or click magnet links in browser
- **Smart TV show detection** - Automatically suggests the right TV show folder based on torrent name
- **New TV Show folder** - Create new TV show directories on the fly
- **Single API backend** - One server handles directory listings and Transmission RPC proxying
- **Local/remote fallback** - Tries local network first (2s timeout), then falls back to remote HTTPS
- **Auto-start torrents** - Torrents start downloading immediately

## Architecture

```
macOS Client                          Server (LibreELEC/Linux)
┌──────────────┐    local or HTTPS    ┌──────────────────┐     localhost     ┌──────────────┐
│ TorrentAdder │ ──────────────────►  │  torrent-api.py  │ ──────────────►  │ Transmission │
│   (macOS)    │    JSON API          │   (port 8765)    │    RPC           │  (port 9091) │
└──────────────┘                      └──────────────────┘                  └──────────────┘
```

The client never talks to Transmission directly over the network. The server-side API handles all Transmission RPC communication locally, so only one endpoint needs to be exposed for remote access.

## Installation

### Client (macOS)

```bash
git clone https://github.com/dgoo2308/torrent-adder.git
cd torrent-adder
./install.sh
```

Then edit your config:
```bash
nano ~/.config/torrent-adder/config.json
```

#### Manual Installation

1. Copy `torrent_adder.py` to `~/.local/share/torrent-adder/`
2. Copy `config.json.example` to `~/.config/torrent-adder/config.json` and edit
3. Run the AppleScript commands in `install.sh` to create the app

### Server (LibreELEC/Linux)

Copy `server/torrent-api.py` and `server/config.json.example` to the server:

```bash
scp server/torrent-api.py server/config.json.example your-server:/storage/
ssh your-server "cp /storage/config.json.example /storage/config.json"
```

Edit `/storage/config.json` with your paths and Transmission credentials.

Install as a systemd service:

```bash
# Create /storage/.config/system.d/torrent-api.service

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

### Client (`~/.config/torrent-adder/config.json`)

```json
{
    "host": "192.168.1.100",
    "port": 9091,
    "username": "",
    "password": "",
    "api_host": "192.168.1.100",
    "api_port": 8765,
    "remote": {
        "api_url": "https://torrent-add.example.com",
        "username": "",
        "password": ""
    },
    "proxy": {
        "enabled": false,
        "host": "127.0.0.1",
        "port": 1080
    }
}
```

| Setting | Description |
|---------|-------------|
| `host` / `port` | Local Transmission RPC (used on LAN) |
| `username` / `password` | Transmission authentication (leave empty if none) |
| `api_host` / `api_port` | Local directory API server |
| `remote.api_url` | Remote API URL (HTTPS), used when local is unreachable |
| `remote.username` / `password` | Basic auth for remote API (e.g. nginx auth) |
| `proxy.enabled` | Enable SOCKS5 proxy for local connections |
| `proxy.host` / `proxy.port` | SOCKS5 proxy address |

**Connection strategy:** The client tries the local API first with a 2-second timeout. If unreachable, it falls back to the remote API URL. On local, it talks to Transmission RPC directly. On remote, all Transmission communication goes through the API.

### Server (`config.json` next to `torrent-api.py`)

```json
{
    "port": 8765,
    "directories": {
        "movies": "/media/lacie/Media/Movies",
        "tvshows": "/media/lacie/Media/TV Shows",
        "downloads": "/media/lacie/Downloads"
    },
    "transmission": {
        "host": "localhost",
        "port": 9091,
        "username": "",
        "password": ""
    }
}
```

| Setting | Description |
|---------|-------------|
| `port` | Port the API listens on |
| `directories.movies` | Path to movies directory |
| `directories.tvshows` | Path to TV shows directory |
| `directories.downloads` | Path to downloads directory |
| `transmission.host` / `port` | Transmission RPC address (usually localhost) |
| `transmission.username` / `password` | Transmission auth (leave empty if none) |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | List all base directories |
| `/movies` | GET | Movies directory path |
| `/downloads` | GET | Downloads directory path |
| `/tvshows` | GET | List all TV show directories |
| `/torrents` | GET | List all torrents (name, hash, status, progress, directory) |
| `/torrent/add` | POST | Add a torrent (magnet or base64 metainfo + download directory) |

### Adding a torrent via API

```bash
# Magnet link
curl -X POST http://localhost:8765/torrent/add \
  -H "Content-Type: application/json" \
  -d '{"magnet": "magnet:?xt=...", "download_dir": "/media/lacie/Downloads"}'

# .torrent file (base64-encoded)
curl -X POST http://localhost:8765/torrent/add \
  -H "Content-Type: application/json" \
  -d '{"metainfo": "<base64>", "download_dir": "/media/lacie/Downloads"}'
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

## Requirements

- macOS (for the GUI app)
- Python 3.x (uses only standard library — no pip dependencies)
- Transmission daemon with RPC enabled on the server
- Network access to the directory API (local or remote)

## License

MIT
