#!/usr/bin/env python3
"""
DJ Treta Server — HTTP API + WebSocket for the DJ engine.
Serves the Chrome UI and provides real-time status updates.

Run:  python3 server.py
Open: http://localhost:7777
"""

import http.server
import importlib
import json
import os
import threading
import time
import sys
from urllib.parse import urlparse, parse_qs
from pathlib import Path

# Add skill dir to path
SKILL_DIR = Path(__file__).parent
sys.path.insert(0, str(SKILL_DIR))

import engine as engine_module
from engine import DJEngine

# ── Config ──────────────────────────────────────────────────────────────

PORT = 7777
TRACKS_DIR = SKILL_DIR / "tracks"

# ── Global DJ Engine ────────────────────────────────────────────────────

dj = DJEngine()
dj.start()

# ── Auto DJ ─────────────────────────────────────────────────────────────

class AutoDJ:
    """Automatic DJ — manages playlist, auto-transitions between tracks."""

    def __init__(self, engine):
        self.engine = engine
        self.playlist = []
        self.current_index = 0
        self.enabled = False
        self.active_deck = 1
        self.transition_duration = 12.0
        self._thread = None

    def build_playlist(self):
        """Scan tracks directory and build playlist."""
        self.playlist = []
        if TRACKS_DIR.exists():
            for f in sorted(TRACKS_DIR.iterdir()):
                if f.suffix.lower() in ('.mp3', '.wav', '.flac', '.m4a', '.ogg'):
                    self.playlist.append(str(f))
        return self.playlist

    def start(self):
        """Start auto DJ."""
        if not self.playlist:
            self.build_playlist()

        if not self.playlist:
            return "No tracks found in library"

        self.enabled = True
        self.current_index = 0

        # Load first track on deck 1
        self.engine.load(1, self.playlist[0])
        self.engine.set_crossfader(0.0)
        self.engine.play(1)
        self.active_deck = 1

        # Load next track on deck 2
        if len(self.playlist) > 1:
            self.engine.load(2, self.playlist[1])
            self.current_index = 1

        # Start monitoring thread
        self._thread = threading.Thread(target=self._monitor, daemon=True)
        self._thread.start()

        return f"Auto DJ started — {len(self.playlist)} tracks in playlist"

    def stop(self):
        """Stop auto DJ."""
        self.enabled = False
        return "Auto DJ stopped"

    def skip(self):
        """Skip to next track."""
        self._do_transition()

    def _monitor(self):
        """Monitor playback and auto-transition when track is ending."""
        while self.enabled:
            active = self.engine.deck1 if self.active_deck == 1 else self.engine.deck2

            if active.playing and active.audio is not None:
                remaining = active.duration - (active.position / active.sample_rate)

                # When less than transition_duration + 2 seconds left, transition
                if remaining < self.transition_duration + 2:
                    self._do_transition()

            time.sleep(1)

    def _do_transition(self):
        """Transition to the other deck with next track."""
        next_deck = 2 if self.active_deck == 1 else 1
        other = self.engine.deck2 if next_deck == 2 else self.engine.deck1

        # Make sure next deck has a track and is playing
        if other.audio is not None and not other.playing:
            other.playing = True

        # Start transition
        self.engine.transition(next_deck, self.transition_duration)
        self.active_deck = next_deck

        # Wait for transition to finish, then load next track on the now-inactive deck
        def _load_next():
            time.sleep(self.transition_duration + 1)
            self.current_index = (self.current_index + 1) % len(self.playlist)
            inactive_deck = 1 if self.active_deck == 2 else 2
            self.engine.load(inactive_deck, self.playlist[self.current_index])

        threading.Thread(target=_load_next, daemon=True).start()

    def status(self):
        return {
            "enabled": self.enabled,
            "playlist_length": len(self.playlist),
            "current_index": self.current_index,
            "active_deck": self.active_deck,
            "playlist": [os.path.basename(p) for p in self.playlist],
        }


auto_dj = AutoDJ(dj)


# ── Hot Reload ─────────────────────────────────────────────────────────

def reload_engine():
    """
    Hot-reload the engine module WITHOUT stopping audio playback.

    Strategy:
    1. Snapshot all deck state (audio buffers, positions, playing, volumes, etc.)
    2. Snapshot mixer state (crossfader, master volume, auto-DJ, playlist)
    3. Reload the engine module via importlib
    4. Create a fresh DJEngine from the reloaded module
    5. Transplant saved audio buffers and state into new engine's decks
    6. Start new engine's audio stream
    7. Kill old engine's stream
    8. Swap the global `dj` reference

    The audio buffers (numpy arrays) are the precious state — they survive the reload.
    At worst there's a tiny glitch during the stream swap.
    """
    global dj, engine_module, auto_dj

    try:
        print("[Hot Reload] Saving engine state...")

        # ── 1. Snapshot deck state ──
        state = {
            "crossfader": dj.crossfader,
            "master_volume": dj.master_volume,
            "auto_dj_enabled": dj._auto_dj,
            "playlist": list(dj._playlist),
            "playlist_index": dj._playlist_index,
            "transitioning": dj._transitioning,
        }

        deck_states = {}
        for num, deck in [(1, dj.deck1), (2, dj.deck2)]:
            deck_states[num] = {
                "audio": deck.audio,
                "audio_original": getattr(deck, 'audio_original', deck.audio),
                "position": deck.position,
                "_fpos": getattr(deck, '_fpos', float(deck.position)),
                "speed": getattr(deck, 'speed', 1.0),
                "playing": deck.playing,
                "volume": deck.volume,
                "eq_hi": deck.eq_hi,
                "eq_mid": deck.eq_mid,
                "eq_lo": deck.eq_lo,
                "track_name": deck.track_name,
                "track_path": deck.track_path,
                "duration": deck.duration,
                "bpm": deck.bpm,
                "effective_bpm": getattr(deck, 'effective_bpm', deck.bpm),
                "first_beat": deck.first_beat,
                "beat_grid_offset": getattr(deck, 'beat_grid_offset', 0),
                "beat_grid_interval": getattr(deck, 'beat_grid_interval', 0),
                "loop_start": deck.loop_start,
                "loop_end": deck.loop_end,
                "looping": deck.looping,
                "sample_rate": deck.sample_rate,
                "waveform": getattr(deck, 'waveform', []),
                "waveform_peaks": getattr(deck, 'waveform_peaks', []),
                "waveform_colors": getattr(deck, 'waveform_colors', []),
            }

        # ── 2. Stop old engine's stream (brief silence here) ──
        old_engine = dj
        if old_engine.stream:
            old_engine.stream.stop()
            old_engine.stream.close()
            old_engine.stream = None
        old_engine._running = False
        old_engine._auto_dj = False  # stop monitor thread

        # ── 3. Reload the engine module ──
        print("[Hot Reload] Reloading engine module...")
        engine_module = importlib.reload(engine_module)

        # ── 4. Create new engine from reloaded module ──
        new_engine = engine_module.DJEngine()

        # ── 5. Transplant deck state ──
        for num, deck in [(1, new_engine.deck1), (2, new_engine.deck2)]:
            ds = deck_states[num]
            deck.audio = ds["audio"]
            deck.audio_original = ds["audio_original"]
            deck.position = ds["position"]
            deck._fpos = ds["_fpos"]
            deck.speed = ds["speed"]
            deck.playing = ds["playing"]
            deck.volume = ds["volume"]
            deck.eq_hi = ds["eq_hi"]
            deck.eq_mid = ds["eq_mid"]
            deck.eq_lo = ds["eq_lo"]
            deck.track_name = ds["track_name"]
            deck.track_path = ds["track_path"]
            deck.duration = ds["duration"]
            deck.bpm = ds["bpm"]
            deck.effective_bpm = ds["effective_bpm"]
            deck.first_beat = ds["first_beat"]
            deck.beat_grid_offset = ds["beat_grid_offset"]
            deck.beat_grid_interval = ds["beat_grid_interval"]
            deck.loop_start = ds["loop_start"]
            deck.loop_end = ds["loop_end"]
            deck.looping = ds["looping"]
            deck.sample_rate = ds["sample_rate"]
            deck.waveform = ds["waveform"]
            deck.waveform_peaks = ds.get("waveform_peaks", [])
            deck.waveform_colors = ds.get("waveform_colors", [])

        # ── 6. Restore mixer state ──
        new_engine.crossfader = state["crossfader"]
        new_engine.master_volume = state["master_volume"]
        new_engine._playlist = state["playlist"]
        new_engine._playlist_index = state["playlist_index"]
        new_engine._transitioning = state["transitioning"]

        # ── 7. Start new engine (creates stream + monitor thread) ──
        new_engine.start()

        # Re-enable auto-DJ if it was on
        if state["auto_dj_enabled"]:
            new_engine._auto_dj = True

        # ── 8. Swap global references ──
        dj = new_engine
        auto_dj.engine = new_engine

        print("[Hot Reload] Engine reloaded successfully — music continues")
        return {"ok": True, "msg": "Engine hot-reloaded. New code is live."}

    except Exception as e:
        print(f"[Hot Reload] FAILED: {e}")
        import traceback
        traceback.print_exc()

        # Emergency recovery: if dj is broken, try to restart old engine
        if dj.stream is None and dj._running is False:
            try:
                dj.start()
                print("[Hot Reload] Emergency: restarted old engine")
            except Exception:
                pass

        return {"ok": False, "msg": f"Reload failed: {str(e)}"}


# ── HTTP Handler ────────────────────────────────────────────────────────

class DJHandler(http.server.SimpleHTTPRequestHandler):
    """Handles API requests and serves the UI."""

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # API endpoints
        if path == '/api/status':
            self._json_response({
                **dj.status(),
                "auto_dj": auto_dj.status(),
            })

        elif path == '/api/tracks':
            tracks = []
            if TRACKS_DIR.exists():
                for f in sorted(TRACKS_DIR.iterdir()):
                    if f.suffix.lower() in ('.mp3', '.wav', '.flac', '.m4a', '.ogg'):
                        tracks.append({
                            "name": f.stem,
                            "filename": f.name,
                            "path": str(f),
                            "size_mb": round(f.stat().st_size / 1024 / 1024, 1),
                        })
            self._json_response({"tracks": tracks})

        elif path == '/api/waveform/1':
            self._json_response({
                "peaks": getattr(dj.deck1, 'waveform_peaks', []),
                "colors": getattr(dj.deck1, 'waveform_colors', []),
                "rms": dj.deck1.waveform,
                "waveform": dj.deck1.waveform,  # backward compat
            })

        elif path == '/api/waveform/2':
            self._json_response({
                "peaks": getattr(dj.deck2, 'waveform_peaks', []),
                "colors": getattr(dj.deck2, 'waveform_colors', []),
                "rms": dj.deck2.waveform,
                "waveform": dj.deck2.waveform,  # backward compat
            })

        elif path == '/api/mixlog':
            try:
                from mixlog import get_recent
                self._json_response({"log": get_recent(20)})
            except Exception as e:
                self._json_response({"log": [], "error": str(e)})

        elif path == '/':
            self._serve_ui()

        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Read body
        content_len = int(self.headers.get('Content-Length', 0))
        body = {}
        if content_len > 0:
            body = json.loads(self.rfile.read(content_len))

        if path == '/api/load':
            deck = body.get('deck', 1)
            track = body.get('track', '')
            # If just filename, resolve to full path
            if not os.path.isabs(track):
                track = str(TRACKS_DIR / track)
            dj.load(deck, track)
            self._json_response({"ok": True, "deck": deck})

        elif path == '/api/play':
            deck = body.get('deck', 1)
            self._json_response({"ok": True, "msg": dj.play(deck)})

        elif path == '/api/pause':
            deck = body.get('deck', 1)
            self._json_response({"ok": True, "msg": dj.pause(deck)})

        elif path == '/api/volume':
            deck = body.get('deck', 1)
            level = body.get('level', 0.8)
            self._json_response({"ok": True, "msg": dj.volume(deck, level)})

        elif path == '/api/crossfade':
            pos = body.get('position', 0.5)
            self._json_response({"ok": True, "msg": dj.set_crossfader(pos)})

        elif path == '/api/master':
            level = body.get('level', 0.8)
            self._json_response({"ok": True, "msg": dj.set_master(level)})

        elif path == '/api/transition':
            deck = body.get('deck', 2)
            duration = body.get('duration', 8.0)
            self._json_response({"ok": True, "msg": dj.transition(deck, duration)})

        elif path == '/api/drop':
            deck = body.get('deck', 2)
            self._json_response({"ok": True, "msg": dj.drop(deck)})

        elif path == '/api/seek':
            deck = body.get('deck', 1)
            seconds = body.get('seconds', 0)
            self._json_response({"ok": True, "msg": dj.seek(deck, seconds)})

        elif path == '/api/autodj/start':
            # Use the engine's built-in auto-DJ
            tracks = sorted(TRACKS_DIR.glob("*.mp3"))
            # Filter to individual tracks only (< 15 min = ~100MB)
            individual = [str(t) for t in tracks if t.stat().st_size < 100 * 1024 * 1024]
            if individual:
                dj.set_playlist(individual)
                dj.enable_auto_dj()
                self._json_response({"ok": True, "msg": f"Auto-DJ enabled with {len(individual)} tracks"})
            else:
                self._json_response({"ok": False, "msg": "No tracks found"})

        elif path == '/api/autodj/stop':
            dj.disable_auto_dj()
            self._json_response({"ok": True, "msg": "Auto-DJ disabled"})

        elif path == '/api/autodj/skip':
            # Force transition now
            active_deck = 1 if dj.crossfader < 0.5 else 2
            other_deck = 2 if active_deck == 1 else 1
            other = dj.deck2 if other_deck == 2 else dj.deck1
            if other.audio is not None:
                other.playing = True
                dj.transition(other_deck, 10)
            self._json_response({"ok": True, "msg": "Skipping..."})

        elif path == '/api/autodj/playlist':
            tracks = body.get('tracks', [])
            full_paths = []
            for t in tracks:
                if not os.path.isabs(t):
                    t = str(TRACKS_DIR / t)
                full_paths.append(t)
            dj.set_playlist(full_paths)
            dj.enable_auto_dj()
            self._json_response({"ok": True, "msg": f"Playlist set: {len(full_paths)} tracks"})

        elif path == '/api/switch-output':
            device = body.get('device', None)
            self._json_response({"ok": True, "msg": dj.switch_output(device)})

        elif path == '/api/sync':
            deck = body.get('deck', 1)
            self._json_response({"ok": True, "msg": dj.sync_bpm(deck)})

        elif path == '/api/nudge_bpm':
            deck = body.get('deck', 1)
            delta = body.get('delta', 0.1)
            self._json_response({"ok": True, "msg": dj.nudge_bpm(deck, delta)})

        elif path == '/api/reload':
            result = reload_engine()
            self._json_response(result)

        else:
            self.send_error(404)

    def _json_response(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _serve_ui(self):
        """Serve the single-page DJ UI."""
        ui_path = SKILL_DIR / "ui.html"
        if ui_path.exists():
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(ui_path.read_bytes())
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<h1>DJ Treta</h1><p>UI not found. Create ui.html</p>")

    def log_message(self, format, *args):
        """Suppress default request logging."""
        pass


# ── Main ────────────────────────────────────────────────────────────────

def main():
    print(f"[DJ Treta] Server starting on http://localhost:{PORT}")
    print(f"[DJ Treta] Tracks directory: {TRACKS_DIR}")
    print(f"[DJ Treta] {len(list(TRACKS_DIR.glob('*.mp3')))} tracks available")

    server = http.server.HTTPServer(('', PORT), DJHandler)

    try:
        print(f"[DJ Treta] Live at http://localhost:{PORT}")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[DJ Treta] Shutting down...")
        dj.stop()
        server.shutdown()


if __name__ == '__main__':
    main()
