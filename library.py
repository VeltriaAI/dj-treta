#!/usr/bin/env python3
"""
DJ Treta — Track Library Manager
Downloads, organizes, and catalogs tracks for DJ sessions.
"""

import subprocess
import json
import os
import sys
import re
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────

SKILL_DIR = Path(__file__).parent
TRACKS_DIR = SKILL_DIR / "tracks"
TRACKLIST_FILE = SKILL_DIR / "tracklist.json"

# Audio quality settings
AUDIO_FORMAT = "mp3"
AUDIO_QUALITY = "320"  # kbps — max quality for MP3


def _load_tracklist():
    """Load track metadata from cache."""
    if TRACKLIST_FILE.exists():
        with open(TRACKLIST_FILE) as f:
            return json.load(f)
    return {"tracks": []}


def _save_tracklist(data):
    """Save track metadata to cache."""
    with open(TRACKLIST_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _sanitize_filename(name):
    """Clean filename for filesystem safety."""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:200]  # limit length


def add(url, tags=None):
    """
    Download a track from YouTube/SoundCloud.

    Args:
        url: YouTube or SoundCloud URL
        tags: Optional comma-separated tags (e.g., "techno,dark,peak")
    """
    TRACKS_DIR.mkdir(parents=True, exist_ok=True)

    # First get metadata without downloading
    print(f"Fetching info: {url}")
    result = subprocess.run([
        "yt-dlp", "--dump-json", "--no-download", url
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error fetching info: {result.stderr}")
        return None

    info = json.loads(result.stdout)
    title = info.get("title", "Unknown")
    uploader = info.get("uploader", "Unknown")
    duration = info.get("duration", 0)
    video_id = info.get("id", "")

    filename = _sanitize_filename(f"{uploader} - {title}")
    output_path = TRACKS_DIR / f"{filename}.{AUDIO_FORMAT}"

    # Check if already downloaded
    if output_path.exists():
        print(f"Already exists: {filename}")
        return str(output_path)

    # Download audio only
    print(f"Downloading: {title} by {uploader} ({duration}s)")
    dl_result = subprocess.run([
        "yt-dlp",
        "-x",  # extract audio
        "--audio-format", AUDIO_FORMAT,
        "--audio-quality", AUDIO_QUALITY,
        "-o", str(TRACKS_DIR / f"{filename}.%(ext)s"),
        "--no-playlist",  # single track only
        "--no-overwrites",
        url
    ], capture_output=True, text=True)

    if dl_result.returncode != 0:
        print(f"Download error: {dl_result.stderr}")
        return None

    # Update tracklist
    tracklist = _load_tracklist()
    track_entry = {
        "title": title,
        "artist": uploader,
        "duration": duration,
        "url": url,
        "video_id": video_id,
        "file": str(output_path),
        "filename": f"{filename}.{AUDIO_FORMAT}",
        "tags": tags.split(",") if tags else [],
        "bpm": None,  # Mixxx will analyze
        "key": None,   # Mixxx will analyze
    }

    # Avoid duplicates
    existing_ids = [t.get("video_id") for t in tracklist["tracks"]]
    if video_id not in existing_ids:
        tracklist["tracks"].append(track_entry)
        _save_tracklist(tracklist)

    print(f"✓ Downloaded: {filename}.{AUDIO_FORMAT}")
    return str(output_path)


def add_batch(urls_file):
    """Download multiple tracks from a file with one URL per line."""
    with open(urls_file) as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    print(f"Downloading {len(urls)} tracks...")
    results = []
    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] ", end="")
        result = add(url)
        results.append(result)

    success = sum(1 for r in results if r)
    print(f"\n✓ Downloaded {success}/{len(urls)} tracks")
    return results


def search_youtube(query, limit=10):
    """Search YouTube for tracks matching a query."""
    print(f"Searching: {query}")
    result = subprocess.run([
        "yt-dlp",
        f"ytsearch{limit}:{query}",
        "--dump-json",
        "--no-download",
        "--flat-playlist"
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Search error: {result.stderr}")
        return []

    results = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        try:
            info = json.loads(line)
            results.append({
                "title": info.get("title", "Unknown"),
                "url": info.get("url", info.get("webpage_url", "")),
                "id": info.get("id", ""),
                "duration": info.get("duration", 0),
                "uploader": info.get("uploader", info.get("channel", "Unknown")),
            })
        except json.JSONDecodeError:
            continue

    return results


def list_tracks():
    """List all tracks in the library."""
    tracklist = _load_tracklist()
    tracks = tracklist.get("tracks", [])

    if not tracks:
        print("Library is empty. Use 'add <url>' to download tracks.")
        return tracks

    print(f"DJ Treta Library — {len(tracks)} tracks\n")
    for i, t in enumerate(tracks, 1):
        tags_str = f" [{', '.join(t.get('tags', []))}]" if t.get('tags') else ""
        bpm_str = f" {t.get('bpm')} BPM" if t.get('bpm') else ""
        duration_min = t.get('duration', 0) // 60
        duration_sec = t.get('duration', 0) % 60
        print(f"  {i:2d}. {t['artist']} — {t['title']} ({duration_min}:{duration_sec:02d}){bpm_str}{tags_str}")
        exists = "✓" if Path(t.get('file', '')).exists() else "✗"
        print(f"      {exists} {t.get('filename', '')}")

    return tracks


def remove(index):
    """Remove a track from the library by index (1-based)."""
    tracklist = _load_tracklist()
    tracks = tracklist.get("tracks", [])

    if index < 1 or index > len(tracks):
        print(f"Invalid index: {index}. Library has {len(tracks)} tracks.")
        return

    track = tracks[index - 1]
    filepath = Path(track.get("file", ""))

    # Remove file
    if filepath.exists():
        filepath.unlink()
        print(f"Deleted file: {filepath.name}")

    # Remove from tracklist
    tracks.pop(index - 1)
    _save_tracklist(tracklist)
    print(f"✓ Removed: {track['artist']} — {track['title']}")


# ── CLI ─────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("DJ Treta Library Manager")
        print("  add <url> [tags]     — Download a track")
        print("  batch <file>         — Download tracks from URL list")
        print("  search <query>       — Search YouTube")
        print("  list                 — List library")
        print("  remove <index>       — Remove track by index")
        return

    cmd = sys.argv[1]

    if cmd == "add" and len(sys.argv) >= 3:
        tags = sys.argv[3] if len(sys.argv) > 3 else None
        add(sys.argv[2], tags)
    elif cmd == "batch" and len(sys.argv) >= 3:
        add_batch(sys.argv[2])
    elif cmd == "search" and len(sys.argv) >= 3:
        query = " ".join(sys.argv[2:])
        results = search_youtube(query)
        for i, r in enumerate(results, 1):
            dur = f"{int(r['duration'])//60}:{int(r['duration'])%60:02d}" if r.get('duration') else "?"
            print(f"  {i:2d}. {r['title']} ({dur})")
            print(f"      {r['url']}")
    elif cmd == "list":
        list_tracks()
    elif cmd == "remove" and len(sys.argv) >= 3:
        remove(int(sys.argv[2]))
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
