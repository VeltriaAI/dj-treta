#!/usr/bin/env python3
"""
DJ Treta — Mix Logger
Logs all transitions and DJ decisions for debugging and review.
"""

import json
import time
from datetime import datetime
from pathlib import Path

LOG_FILE = Path(__file__).parent / "mixlog.json"

_log = []

def log_event(event_type, data):
    """Log a DJ event."""
    entry = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "timestamp": time.time(),
        "event": event_type,
        **data,
    }
    _log.append(entry)

    # Also print for real-time visibility
    print(f"[MixLog {entry['time']}] {event_type}: {json.dumps(data, default=str)}")

    # Write to file
    try:
        with open(LOG_FILE, "w") as f:
            json.dump(_log, f, indent=2, default=str)
    except Exception:
        pass

def log_transition_start(from_track, to_track, from_deck, to_deck, duration,
                          from_bpm, to_bpm, speed, phase_offset, crossfader_start):
    log_event("transition_start", {
        "from": from_track[:40],
        "to": to_track[:40],
        "from_deck": from_deck,
        "to_deck": to_deck,
        "duration_sec": duration,
        "from_bpm": from_bpm,
        "to_bpm": to_bpm,
        "speed_adjust": round(speed, 4),
        "phase_offset_samples": phase_offset,
        "crossfader_start": round(crossfader_start, 3),
    })

def log_transition_phase(phase_name, crossfader, elapsed):
    log_event("transition_phase", {
        "phase": phase_name,
        "crossfader": round(crossfader, 3),
        "elapsed_sec": round(elapsed, 1),
    })

def log_transition_end(to_track, to_deck, final_crossfader):
    log_event("transition_end", {
        "landed_on": to_track[:40],
        "deck": to_deck,
        "crossfader": round(final_crossfader, 3),
    })

def log_track_ended(track, deck, was_playing):
    log_event("track_ended", {
        "track": track[:40],
        "deck": deck,
        "was_playing": was_playing,
    })

def log_load(track, deck, bpm, beat_grid_offset, beat_grid_interval):
    log_event("track_loaded", {
        "track": track[:40],
        "deck": deck,
        "bpm": bpm,
        "grid_offset": beat_grid_offset,
        "grid_interval": beat_grid_interval,
    })

def log_error(msg, context=None):
    log_event("error", {
        "message": msg,
        "context": str(context)[:100] if context else None,
    })

def get_log():
    """Return all log entries."""
    return _log

def get_recent(n=10):
    """Return last N log entries."""
    return _log[-n:]
