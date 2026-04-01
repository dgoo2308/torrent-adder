# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TorrentAdder is a macOS app that adds `.torrent` files and magnet links to a remote Transmission server. It uses native macOS dialogs (via `osascript`/AppleScript) for the GUI and Python 3 standard library only (no pip dependencies).

## Architecture

**Two components:**

1. **`torrent_adder.py`** — The main client app (macOS). Handles torrent/magnet input, directory selection UI, TV show auto-detection, and Transmission RPC communication. Packaged as a macOS `.app` via `osacompile` in `install.sh`.

2. **`server/torrent-api.py`** — An HTTP server (runs on the same box as Transmission) that exposes directory listings and proxies Transmission RPC as a JSON API. The client never talks to Transmission directly over the network — only the server does, on localhost.

**Connection strategy (`resolve_connection`):** Tries local network first with a 2-second timeout, then falls back to a remote HTTPS URL configured in `config.json` under the `remote` key. On local, the client uses `TransmissionClient` (direct RPC). On remote, it uses `APITorrentClient` (POST to `/torrent/add`). Proxy support (SOCKS5 via curl) is optional and only used for local connections.

**Server config:** `server/config.json` next to the script. Configures media directory paths (`directories.movies`, `directories.tvshows`, `directories.downloads`) and Transmission connection (`transmission.host`, `transmission.port`, `transmission.username`, `transmission.password`).

**Client config lookup order:** `~/.config/torrent-adder/config.json` → `config.json` in script directory.

## Commands

```bash
# Install client (creates /Applications/TorrentAdder.app, copies script and config)
./install.sh

# Run directly for testing
python3 torrent_adder.py <file.torrent>
python3 torrent_adder.py "magnet:?xt=..."
python3 torrent_adder.py              # opens settings dialog
```

There are no tests, linter, or build system — this is a single-file Python script with a shell installer.

## Key Design Decisions

- **Zero external dependencies** — uses only Python stdlib. HTTP through `urllib`; SOCKS5 proxy through shelling out to `curl`. Bencode parsing is hand-rolled (`bdecode`).
- **All UI via `osascript`** — `choose from list`, `display dialog`, etc. Helper functions: `osascript()`, `show_error()`, `show_info()`, `choose_from_list()`, `ask_text_input()`, `ask_yes_no()`. Progress dialogs use background `Popen` + `terminate()` to show/dismiss.
- **Transmission RPC** — `TransmissionClient` (local) and server-side `transmission_request()` both handle the 409/session-id handshake automatically. `APITorrentClient` is used for remote mode, sending JSON to the server API.
- **Server as single entry point** — The server proxies Transmission RPC so only one port/tunnel needs exposing for remote access. Endpoints: `/`, `/movies`, `/downloads`, `/tvshows`, `/torrents` (GET), `/torrent/add` (POST).
