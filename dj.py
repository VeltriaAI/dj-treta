#!/usr/bin/env python3
"""
DJ Treta — Main DJ Engine
Manages DJ sessions: track selection, set planning, mood-based mixing.
Orchestrates library.py (tracks) and controller.py (Mixxx MIDI control).
"""

import json
import sys
import os
import random
from pathlib import Path

SKILL_DIR = Path(__file__).parent
TRACKLIST_FILE = SKILL_DIR / "tracklist.json"
TRACKS_DIR = SKILL_DIR / "tracks"

# ── Mood Presets ────────────────────────────────────────────────────────

MOODS = {
    "techno-deep": {
        "name": "Deep Techno",
        "description": "Dark, hypnotic, minimal. Perfect for deep focus.",
        "bpm_range": (125, 132),
        "search_queries": [
            "deep techno mix",
            "dark minimal techno",
            "hypnotic techno",
            "underground techno",
            "deep driving techno",
        ],
        "tags": ["techno", "deep", "dark", "minimal"],
    },
    "techno-peak": {
        "name": "Peak Time Techno",
        "description": "Driving, energetic, relentless. For when you need maximum focus.",
        "bpm_range": (130, 140),
        "search_queries": [
            "peak time techno",
            "hard techno mix",
            "driving techno",
            "industrial techno",
            "warehouse techno",
        ],
        "tags": ["techno", "peak", "hard", "driving"],
    },
    "deep-house": {
        "name": "Deep House",
        "description": "Smooth, groovy, warm. Relaxed but engaged.",
        "bpm_range": (120, 126),
        "search_queries": [
            "deep house mix",
            "organic house",
            "melodic deep house",
            "afro house mix",
            "soulful deep house",
        ],
        "tags": ["house", "deep", "groovy", "melodic"],
    },
    "progressive": {
        "name": "Progressive House/Techno",
        "description": "Building, melodic, euphoric. Great for creative work.",
        "bpm_range": (125, 132),
        "search_queries": [
            "progressive house mix",
            "progressive techno",
            "melodic techno mix",
            "anjunadeep mix",
            "progressive trance",
        ],
        "tags": ["progressive", "melodic", "building"],
    },
    "ambient-focus": {
        "name": "Ambient Focus",
        "description": "Minimal, atmospheric, textural. Maximum concentration.",
        "bpm_range": (90, 120),
        "search_queries": [
            "ambient techno mix",
            "ambient electronic focus",
            "deep ambient music work",
            "minimal ambient mix",
            "atmospheric electronic",
        ],
        "tags": ["ambient", "minimal", "focus", "atmospheric"],
    },
    "indie-dance": {
        "name": "Indie Dance",
        "description": "Funky, eclectic, fun. For lighter work sessions.",
        "bpm_range": (115, 128),
        "search_queries": [
            "indie dance mix",
            "nu disco mix",
            "funky house mix",
            "disco house",
            "indie electronic",
        ],
        "tags": ["indie", "disco", "funky", "eclectic"],
    },
}

# ── Curated Starter Packs ──────────────────────────────────────────────
# YouTube search queries to build an initial library for each mood

STARTER_PACKS = {
    "techno-deep": [
        "Amelie Lens dark techno set",
        "Charlotte de Witte techno mix",
        "ANNA techno set",
        "Kobosil techno mix",
        "Dax J techno set",
        "Blawan techno mix",
        "Paula Temple techno set",
        "Marcel Dettmann boiler room",
        "Ben Klock techno set",
        "Randomer techno mix",
    ],
    "deep-house": [
        "Solomun boiler room",
        "Dixon deep house set",
        "Black Coffee deep house mix",
        "Damian Lazarus deep house",
        "Bedouin melodic house set",
        "Hernan Cattaneo progressive set",
    ],
    "progressive": [
        "Tale of Us melodic techno",
        "Stephan Bodzin live set",
        "Adriatique melodic techno mix",
        "Mind Against techno set",
        "Recondite live set",
        "Kiasmos live",
    ],
}


def load_tracklist():
    """Load track metadata."""
    if TRACKLIST_FILE.exists():
        with open(TRACKLIST_FILE) as f:
            return json.load(f)
    return {"tracks": []}


def get_tracks_for_mood(mood_key):
    """Get tracks matching a mood from the library."""
    if mood_key not in MOODS:
        print(f"Unknown mood: {mood_key}")
        print(f"Available: {', '.join(MOODS.keys())}")
        return []

    mood = MOODS[mood_key]
    tracklist = load_tracklist()
    tracks = tracklist.get("tracks", [])

    # Filter by tags if available
    matching = []
    for t in tracks:
        track_tags = set(t.get("tags", []))
        mood_tags = set(mood["tags"])
        if track_tags & mood_tags:  # any tag overlap
            matching.append(t)

    # If no tag matches, return all tracks (we'll sort by BPM later)
    if not matching:
        matching = tracks

    return matching


def suggest_downloads(mood_key, count=5):
    """Suggest YouTube searches for a mood."""
    if mood_key not in MOODS:
        print(f"Unknown mood: {mood_key}")
        return

    mood = MOODS[mood_key]
    queries = mood["search_queries"]
    starters = STARTER_PACKS.get(mood_key, [])

    print(f"\n🎵 {mood['name']} — {mood['description']}")
    print(f"   BPM range: {mood['bpm_range'][0]}-{mood['bpm_range'][1]}")
    print(f"\nSuggested searches (use 'library.py search <query>'):")
    for q in queries[:count]:
        print(f"  • {q}")

    if starters:
        print(f"\nStarter pack artists/sets:")
        for s in starters:
            print(f"  • {s}")


def plan_set(mood_key=None, duration_min=60):
    """Plan a DJ set from available tracks."""
    tracklist = load_tracklist()
    tracks = tracklist.get("tracks", [])

    if not tracks:
        print("Library is empty! Download some tracks first.")
        print("  python3 library.py search 'deep techno mix'")
        print("  python3 library.py add <url>")
        return

    if mood_key:
        tracks = get_tracks_for_mood(mood_key)

    # Shuffle for variety
    random.shuffle(tracks)

    # Build set within duration
    total_duration = 0
    set_tracks = []
    for t in tracks:
        dur = t.get("duration", 300)  # default 5 min
        if total_duration + dur <= duration_min * 60:
            set_tracks.append(t)
            total_duration += dur

    mood_name = MOODS[mood_key]["name"] if mood_key else "Mixed"
    print(f"\n🎧 DJ Treta — {mood_name} Set ({len(set_tracks)} tracks, ~{total_duration//60} min)")
    print("=" * 60)
    for i, t in enumerate(set_tracks, 1):
        dur_min = t.get("duration", 0) // 60
        dur_sec = t.get("duration", 0) % 60
        bpm_str = f" [{t['bpm']} BPM]" if t.get('bpm') else ""
        print(f"  {i:2d}. {t['artist']} — {t['title']} ({dur_min}:{dur_sec:02d}){bpm_str}")

    return set_tracks


def library_status():
    """Show library overview."""
    tracklist = load_tracklist()
    tracks = tracklist.get("tracks", [])

    if not tracks:
        print("Library is empty.")
        return

    total_duration = sum(t.get("duration", 0) for t in tracks)
    hours = total_duration // 3600
    mins = (total_duration % 3600) // 60

    # Count by tags
    tag_counts = {}
    for t in tracks:
        for tag in t.get("tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    print(f"\n🎵 DJ Treta Library")
    print(f"   Tracks: {len(tracks)}")
    print(f"   Duration: {hours}h {mins}m")
    if tag_counts:
        print(f"   Tags: {', '.join(f'{k}({v})' for k, v in sorted(tag_counts.items(), key=lambda x: -x[1]))}")

    # Check file existence
    missing = sum(1 for t in tracks if not Path(t.get("file", "")).exists())
    if missing:
        print(f"   ⚠ Missing files: {missing}")


# ── CLI ─────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("DJ Treta — AI DJ Engine")
        print()
        print("  moods                  — List available moods")
        print("  suggest <mood>         — Get download suggestions for a mood")
        print("  plan [mood] [minutes]  — Plan a set")
        print("  status                 — Library overview")
        return

    cmd = sys.argv[1]

    if cmd == "moods":
        print("\n🎧 DJ Treta Moods\n")
        for key, mood in MOODS.items():
            print(f"  {key:20s} {mood['description']}")
            print(f"  {'':20s} BPM: {mood['bpm_range'][0]}-{mood['bpm_range'][1]}")
            print()

    elif cmd == "suggest":
        mood = sys.argv[2] if len(sys.argv) > 2 else "techno-deep"
        suggest_downloads(mood)

    elif cmd == "plan":
        mood = sys.argv[2] if len(sys.argv) > 2 else None
        duration = int(sys.argv[3]) if len(sys.argv) > 3 else 60
        plan_set(mood, duration)

    elif cmd == "status":
        library_status()

    else:
        print(f"Unknown: {cmd}")


if __name__ == "__main__":
    main()
