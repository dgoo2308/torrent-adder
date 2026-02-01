#!/usr/bin/env python3
"""
Simple Torrent Adder GUI using native macOS dialogs via osascript
Fetches directories from the torrent-api service
Auto-suggests download directory based on torrent name
"""

import json
import base64
import urllib.request
import urllib.error
import urllib.parse
import subprocess
import sys
import re
from pathlib import Path


class TransmissionClient:
    def __init__(self, host, port, username=None, password=None):
        self.url = f"http://{host}:{port}/transmission/rpc"
        self.session_id = None
        self.auth_header = None
        if username and password:
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            self.auth_header = f"Basic {credentials}"
    
    def _request(self, method, arguments=None):
        payload = json.dumps({"method": method, "arguments": arguments or {}}).encode()
        headers = {"Content-Type": "application/json"}
        if self.auth_header:
            headers["Authorization"] = self.auth_header
        if self.session_id:
            headers["X-Transmission-Session-Id"] = self.session_id
        req = urllib.request.Request(self.url, data=payload, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 409:
                self.session_id = e.headers.get("X-Transmission-Session-Id")
                return self._request(method, arguments)
            raise Exception(f"HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise Exception(f"Connection error: {e.reason}")
        except Exception as e:
            raise Exception(f"Request failed: {e}")
    
    def add_torrent(self, torrent_source, download_dir):
        """Add torrent from local file or magnet link"""
        args = {"paused": False}
        
        if torrent_source.startswith("magnet:"):
            args["filename"] = torrent_source
        else:
            with open(torrent_source, "rb") as f:
                args["metainfo"] = base64.b64encode(f.read()).decode()
        
        if download_dir:
            args["download-dir"] = download_dir
        result = self._request("torrent-add", args)
        return result.get("arguments", {})


def osascript(script):
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    return result.stdout.strip(), result.returncode


def show_error(message):
    osascript(f'display dialog "{message}" with title "Torrent Adder" buttons {{"OK"}} default button "OK" with icon stop')


def show_info(message):
    osascript(f'display dialog "{message}" with title "Torrent Adder" buttons {{"OK"}} default button "OK" with icon note')


def choose_from_list(items, prompt, default_item=None):
    items_str = ", ".join(f'"{item}"' for item in items)
    default = default_item if default_item and default_item in items else items[0]
    script = f'choose from list {{{items_str}}} with prompt "{prompt}" with title "Torrent Adder" default items {{"{default}"}}'
    result, code = osascript(script)
    if code != 0 or result == "false":
        return None
    return result


def ask_yes_no(prompt, title="Torrent Adder"):
    """Show yes/no dialog, returns True for yes, False for no"""
    script = f'display dialog "{prompt}" with title "{title}" buttons {{"Choose Other", "Yes"}} default button "Yes"'
    result, code = osascript(script)
    if code != 0:
        return None  # Cancelled
    return "Yes" in result


def ask_text_input(prompt, default="", title="Torrent Adder"):
    """Show text input dialog, returns entered text or None if cancelled"""
    script = f'display dialog "{prompt}" with title "{title}" default answer "{default}" buttons {{"Cancel", "OK"}} default button "OK"'
    result, code = osascript(script)
    if code != 0:
        return None
    # Extract text from result like "button returned:OK, text returned:Some Text"
    match = re.search(r'text returned:(.*)$', result)
    if match:
        return match.group(1).strip()
    return None


def load_config():
    config_paths = [
        Path.home() / ".config" / "torrent-adder" / "config.json",
        Path(__file__).parent / "config.json",
    ]
    for path in config_paths:
        if path.exists():
            with open(path) as f:
                return json.load(f)
    return {
        "host": "192.168.1.100", "port": 9091,
        "username": "", "password": "",
        "api_host": "192.168.1.100", "api_port": 8765
    }


def fetch_directories(api_host, api_port):
    """Fetch directory options from the API, returns (dirs_list, tv_shows_list, tv_base_path)"""
    dirs = []
    tv_shows = []
    tv_base = "/media/lacie/Media/TV Shows"
    
    try:
        with urllib.request.urlopen(f"http://{api_host}:{api_port}/movies", timeout=5) as r:
            data = json.loads(r.read().decode())
            dirs.append(("Movies", data["path"]))
        
        with urllib.request.urlopen(f"http://{api_host}:{api_port}/downloads", timeout=5) as r:
            data = json.loads(r.read().decode())
            dirs.append(("Downloads", data["path"]))
        
        # Add special options
        dirs.append(("── New TV Show Folder ──", "__NEW_TV__"))
        
        with urllib.request.urlopen(f"http://{api_host}:{api_port}/tvshows", timeout=5) as r:
            data = json.loads(r.read().decode())
            tv_base = data["base"]
            for show in data["shows"]:
                dirs.append((f"TV: {show}", f"{tv_base}/{show}"))
                tv_shows.append(show.lower())
    except:
        dirs = [
            ("Movies", "/media/lacie/Media/Movies"),
            ("Downloads", "/media/lacie/Downloads"),
            ("── New TV Show Folder ──", "__NEW_TV__"),
        ]
    
    return dirs, tv_shows, tv_base


def bdecode_string(data, idx):
    """Decode a bencoded string, return (string, next_index)"""
    colon = data.index(b':', idx)
    length = int(data[idx:colon])
    start = colon + 1
    return data[start:start + length], start + length

def bdecode(data, idx=0):
    """Simple bencoded data decoder"""
    if data[idx:idx+1] == b'd':  # dict
        idx += 1
        result = {}
        while data[idx:idx+1] != b'e':
            key, idx = bdecode_string(data, idx)
            result[key], idx = bdecode(data, idx)
        return result, idx + 1
    elif data[idx:idx+1] == b'l':  # list
        idx += 1
        result = []
        while data[idx:idx+1] != b'e':
            item, idx = bdecode(data, idx)
            result.append(item)
        return result, idx + 1
    elif data[idx:idx+1] == b'i':  # int
        end = data.index(b'e', idx)
        return int(data[idx+1:end]), end + 1
    elif data[idx:idx+1].isdigit():  # string
        return bdecode_string(data, idx)
    else:
        raise ValueError(f"Unknown type at {idx}")

def get_torrent_name(torrent_path):
    """Extract name from .torrent file metadata"""
    try:
        with open(torrent_path, 'rb') as f:
            data = f.read()
        decoded, _ = bdecode(data)
        if b'info' in decoded and b'name' in decoded[b'info']:
            return decoded[b'info'][b'name'].decode('utf-8', errors='replace')
    except:
        pass
    # Fallback to filename
    return Path(torrent_path).stem


def extract_torrent_name(torrent_source):
    """Extract display name from magnet link or .torrent file"""
    if torrent_source.startswith("magnet:"):
        dn_match = re.search(r'dn=([^&]+)', torrent_source)
        if dn_match:
            return urllib.parse.unquote_plus(dn_match.group(1))
        return "Magnet link"
    else:
        # Parse .torrent file for actual name
        return get_torrent_name(torrent_source)


def detect_tv_show(name, tv_shows):
    """Try to match torrent name to existing TV show directory"""
    
    # Common TV patterns: Show.Name.S01E01, Show Name S01E01, etc.
    # Extract potential show name (everything before SxxExx)
    tv_pattern = re.match(r'^(.+?)[.\s][Ss]\d{1,2}[Ee]\d{1,2}', name)
    if not tv_pattern:
        return None
    
    # Normalize: "Spartacus.House.of.Ashur" -> "spartacus house of ashur"
    potential_show = tv_pattern.group(1).replace('.', ' ').replace('-', ' ').strip().lower()
    
    best_match = None
    best_score = 0
    
    for show in tv_shows:
        show_normalized = show.lower()
        
        # Exact match
        if potential_show == show_normalized:
            return show
        
        # Check if one starts with the other (prefix matching)
        # "spartacus house of ashur" should match "Spartacus House of Ashur"
        # "spartacus" folder should also match "spartacus house of ashur" torrent
        if potential_show.startswith(show_normalized) or show_normalized.startswith(potential_show):
            # Score by length of match - prefer longer matches
            match_len = min(len(potential_show), len(show_normalized))
            if match_len > best_score:
                best_score = match_len
                best_match = show
    
    return best_match


def main():
    torrent_source = sys.argv[1] if len(sys.argv) > 1 else None
    
    if not torrent_source:
        show_error("No torrent file or magnet link provided")
        sys.exit(1)
    
    is_magnet = torrent_source.startswith("magnet:")
    
    if not is_magnet:
        torrent_path = Path(torrent_source)
        if not torrent_path.exists():
            show_error(f"File not found:\\n{torrent_source}")
            sys.exit(1)
    
    config = load_config()
    api_host = config.get("api_host", config["host"])
    api_port = config.get("api_port", 8765)
    
    # Fetch directories
    dir_options, tv_shows, tv_base = fetch_directories(api_host, api_port)
    display_names = [d[0] for d in dir_options]
    
    # Get torrent name
    torrent_name = extract_torrent_name(torrent_source)
    
    # Try to auto-detect TV show
    suggested_dir = None
    matched_show = detect_tv_show(torrent_name, tv_shows)
    if matched_show:
        # Find the display name for this show
        for name, path in dir_options:
            if name.lower() == f"tv: {matched_show}".lower():
                suggested_dir = name
                break
    
    # Truncate name for display
    display_name = torrent_name
    if len(display_name) > 50:
        display_name = display_name[:47] + "..."
    
    # If we have a suggested directory, ask for confirmation first
    selected = None
    selected_path = None
    
    if suggested_dir:
        # Find the path for suggested dir
        for name, path in dir_options:
            if name == suggested_dir:
                suggested_path = path
                break
        
        # Ask user to confirm
        confirm = ask_yes_no(
            f"Add to {suggested_dir}?\\n\\n{display_name}"
        )
        
        if confirm is None:
            # User cancelled
            sys.exit(0)
        elif confirm:
            # User agreed
            selected = suggested_dir
            selected_path = suggested_path
        # else: User wants to choose other - fall through to list
    
    # Show full list if no suggestion or user wants to choose
    if not selected:
        selected = choose_from_list(
            display_names,
            f"Download directory for:\\n{display_name}"
        )
        
        if not selected:
            sys.exit(0)
        
        # Handle special options
        if selected == "── New TV Show Folder ──":
            # Extract suggested folder name from torrent
            suggested_name = ""
            tv_pattern = re.match(r'^(.+?)[.\s][Ss]\d{1,2}[Ee]\d{1,2}', torrent_name)
            if tv_pattern:
                suggested_name = tv_pattern.group(1).replace('.', ' ').strip()
            
            folder_name = ask_text_input(
                "Enter new TV show folder name:",
                default=suggested_name
            )
            if not folder_name:
                sys.exit(0)
            selected_path = f"{tv_base}/{folder_name}"
        else:
            # Find the actual path
            for name, path in dir_options:
                if name == selected:
                    selected_path = path
                    break
    
    if not selected_path:
        show_error("Could not find selected directory")
        sys.exit(1)
    
    # Add torrent
    try:
        client = TransmissionClient(
            config["host"], config["port"],
            config.get("username"), config.get("password")
        )
        result = client.add_torrent(torrent_source, selected_path)
        
        if "torrent-added" in result:
            name = result["torrent-added"].get("name", torrent_name)
            show_info(f"✓ Torrent added!\\n\\n{name}\\n\\nDownloading to:\\n{selected_path}")
        elif "torrent-duplicate" in result:
            name = result["torrent-duplicate"].get("name", torrent_name)
            show_error(f"Torrent already exists:\\n\\n{name}")
        elif not result:
            show_error("No response from Transmission")
        else:
            show_info(f"Torrent added to:\\n{selected_path}")
            
    except Exception as e:
        show_error(f"Failed to add torrent:\\n\\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
