#!/usr/bin/env python3
"""
DJ Treta Controller — Unified MIDI + HTTP control for Mixxx.

MIDI for real-time: crossfader, volume, EQ, play/cue/sync (zero latency)
HTTP for commands: load track, get status, library, analysis (high-level)

Usage:
    from controller import DJTretaController
    dj = DJTretaController()
    dj.load(1, "/path/to/track.mp3")  # HTTP
    dj.play(1)                         # MIDI (instant)
    dj.crossfade(0.5)                  # MIDI (smooth)
    dj.transition(2, 60)               # MIDI crossfade over 60s
"""

import rtmidi
import requests
import time
import json
import sys
import threading

# ── MIDI Configuration ──────────────────────────────────────────────────

CH1 = 0x00  # MIDI Channel 1 (Deck 1)
CH2 = 0x01  # MIDI Channel 2 (Deck 2)

CC = {
    'volume':     7,
    'rate':       8,
    'crossfader': 10,
    'master_vol': 11,
    'head_vol':   12,
    'eq_lo':      16,
    'eq_mid':     17,
    'eq_hi':      18,
    'filter':     19,
}

NOTE = {
    'play':    1,
    'cue':     2,
    'sync':    3,
    'loop':    4,
    'hotcue1': 5,
    'hotcue2': 6,
    'hotcue3': 7,
    'hotcue4': 8,
}


class DJTretaController:
    """Unified MIDI + HTTP controller for Mixxx."""

    def __init__(self, midi_port="DJ Treta", api_host="http://localhost:7778"):
        self.api = api_host
        self.midi_out = rtmidi.MidiOut()
        self.midi_out.open_virtual_port(midi_port)
        self._transitioning = False
        print(f"[DJ Treta] MIDI port '{midi_port}' + API at {api_host}")

    # ── MIDI: Real-time Controls ────────────────────────────────────

    def _cc(self, channel, cc, value):
        """Send MIDI Control Change. Value 0-127."""
        self.midi_out.send_message([0xB0 | channel, cc, max(0, min(127, int(value)))])

    def _note_on(self, channel, note, velocity=127):
        """Send MIDI Note On."""
        self.midi_out.send_message([0x90 | channel, note, velocity])

    def _note_off(self, channel, note):
        """Send MIDI Note Off."""
        self.midi_out.send_message([0x80 | channel, note, 0])

    def _tap(self, channel, note, velocity=127):
        """Button press (note on then off)."""
        self._note_on(channel, note, velocity)
        time.sleep(0.02)
        self._note_off(channel, note)

    def _ch(self, deck):
        return CH1 if deck == 1 else CH2

    # ── Crossfader ──────────────────────────────────────────────────

    def crossfade(self, position):
        """Set crossfader. 0.0 = Deck 1, 1.0 = Deck 2."""
        self._cc(CH1, CC['crossfader'], position * 127)

    # ── Volume ──────────────────────────────────────────────────────

    def volume(self, deck, level):
        """Set deck volume. 0.0 to 1.0."""
        self._cc(self._ch(deck), CC['volume'], level * 127)

    def master_volume(self, level):
        """Set master volume. 0.0 to 1.0."""
        self._cc(CH1, CC['master_vol'], level * 127)

    # ── EQ ──────────────────────────────────────────────────────────

    def eq(self, deck, hi=None, mid=None, lo=None):
        """Set deck EQ. Values 0.0 to 1.0 (0.5 = neutral)."""
        ch = self._ch(deck)
        if hi is not None:  self._cc(ch, CC['eq_hi'], hi * 127)
        if mid is not None: self._cc(ch, CC['eq_mid'], mid * 127)
        if lo is not None:  self._cc(ch, CC['eq_lo'], lo * 127)

    def filter(self, deck, value):
        """Set quick effect / filter. 0.0 to 1.0 (0.5 = neutral)."""
        self._cc(self._ch(deck), CC['filter'], value * 127)

    # ── Transport ───────────────────────────────────────────────────

    def play(self, deck):
        """Toggle play/pause via MIDI."""
        self._tap(self._ch(deck), NOTE['play'])

    def cue(self, deck):
        """Trigger cue point."""
        self._tap(self._ch(deck), NOTE['cue'])

    def sync(self, deck):
        """Toggle sync."""
        self._tap(self._ch(deck), NOTE['sync'])

    def loop(self, deck):
        """Toggle loop."""
        self._tap(self._ch(deck), NOTE['loop'])

    def hotcue(self, deck, num):
        """Trigger hot cue (1-4)."""
        key = f'hotcue{num}'
        if key in NOTE:
            self._tap(self._ch(deck), NOTE[key])

    # ── Pitch / Rate ────────────────────────────────────────────────

    def rate(self, deck, value):
        """Set pitch/rate. 0.0 to 1.0 (0.5 = normal speed)."""
        self._cc(self._ch(deck), CC['rate'], value * 127)

    # ── Transitions (MIDI-powered, butter smooth) ───────────────────

    def transition(self, to_deck=2, duration=60.0):
        """
        Smooth S-curve crossfade via MIDI.
        30 MIDI messages per second — way smoother than HTTP polling.
        """
        if self._transitioning:
            print("[DJ Treta] Transition already in progress")
            return
        self._transitioning = True

        def _run():
            fps = 30
            steps = int(duration * fps)
            for i in range(steps + 1):
                r = i / steps
                ease = r * r * (3 - 2 * r)  # S-curve
                pos = ease if to_deck == 2 else (1.0 - ease)
                self.crossfade(pos)
                time.sleep(1.0 / fps)
            self._transitioning = False
            print(f"[DJ Treta] Transition to Deck {to_deck} complete ({duration}s)")

        threading.Thread(target=_run, daemon=True).start()

    def blend(self, to_deck=2, duration=90.0):
        """
        EQ blend transition — cuts bass on incoming, swaps bass, fades old track.
        More musical than a simple crossfade.
        """
        if self._transitioning:
            return
        self._transitioning = True

        def _run():
            fps = 20
            other = 1 if to_deck == 2 else 2

            # Phase 1: Cut incoming bass, bring crossfader to center
            self.eq(to_deck, lo=0.0)
            steps1 = int(duration * 0.3 * fps)
            for i in range(steps1):
                r = i / steps1
                self.crossfade(0.5 if to_deck == 2 else 0.5)
                time.sleep(1.0 / fps)

            # Phase 2: Bass swap — the magic moment
            steps2 = int(duration * 0.2 * fps)
            for i in range(steps2):
                r = i / steps2
                self.eq(other, lo=1.0 - r)    # Kill outgoing bass
                self.eq(to_deck, lo=r)          # Bring incoming bass
                time.sleep(1.0 / fps)

            # Phase 3: Fade out old track
            steps3 = int(duration * 0.4 * fps)
            for i in range(steps3):
                r = i / steps3
                ease = r * r * (3 - 2 * r)
                pos = (0.5 + 0.5 * ease) if to_deck == 2 else (0.5 - 0.5 * ease)
                self.crossfade(pos)
                time.sleep(1.0 / fps)

            # Reset EQ
            self.eq(other, lo=0.5)
            self.eq(to_deck, lo=0.5)
            self._transitioning = False
            print(f"[DJ Treta] EQ blend to Deck {to_deck} complete")

        threading.Thread(target=_run, daemon=True).start()

    def drop(self, to_deck=2):
        """Instant crossfade cut."""
        self.crossfade(1.0 if to_deck == 2 else 0.0)

    # ── HTTP: High-level Commands ───────────────────────────────────

    def load(self, deck, path):
        """Load a track by file path (HTTP API)."""
        r = requests.post(f"{self.api}/api/load", json={"deck": deck, "track": path})
        return r.json()

    def status(self):
        """Get full engine status (HTTP API)."""
        r = requests.get(f"{self.api}/api/status")
        return r.json()

    def get_bpm(self, deck):
        """Get BPM of a deck."""
        s = self.status()
        return s[f'deck{deck}']['bpm']

    def get_position(self, deck):
        """Get playback position (0.0 to 1.0)."""
        s = self.status()
        return s[f'deck{deck}']['position']

    def is_playing(self, deck):
        """Check if a deck is playing."""
        s = self.status()
        return s[f'deck{deck}']['playing']

    def eject(self, deck):
        """Eject track from deck (HTTP API)."""
        requests.post(f"{self.api}/api/eject", json={"deck": deck})

    # ── Utility ─────────────────────────────────────────────────────

    def close(self):
        """Clean up MIDI port."""
        if self.midi_out:
            del self.midi_out
            self.midi_out = None

    def __del__(self):
        self.close()


# ── CLI ─────────────────────────────────────────────────────────────────

def main():
    dj = DJTretaController()

    if len(sys.argv) < 2:
        print("DJ Treta Controller — MIDI + HTTP")
        print(f"  MIDI port: DJ Treta")
        print(f"  API: {dj.api}")
        print()
        print("Commands:")
        print("  play <deck>")
        print("  crossfade <0-1>")
        print("  volume <deck> <0-1>")
        print("  eq <deck> <hi> <mid> <lo>")
        print("  transition <deck> <duration>")
        print("  blend <deck> <duration>")
        print("  load <deck> <path>")
        print("  status")
        return

    cmd = sys.argv[1]

    if cmd == "play":
        dj.play(int(sys.argv[2]))
    elif cmd == "crossfade":
        dj.crossfade(float(sys.argv[2]))
    elif cmd == "volume":
        dj.volume(int(sys.argv[2]), float(sys.argv[3]))
    elif cmd == "eq":
        dj.eq(int(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]))
    elif cmd == "transition":
        dj.transition(int(sys.argv[2]), float(sys.argv[3]))
        time.sleep(float(sys.argv[3]) + 1)
    elif cmd == "blend":
        dj.blend(int(sys.argv[2]), float(sys.argv[3]))
        time.sleep(float(sys.argv[3]) + 1)
    elif cmd == "load":
        print(dj.load(int(sys.argv[2]), sys.argv[3]))
    elif cmd == "status":
        print(json.dumps(dj.status(), indent=2))
    else:
        print(f"Unknown: {cmd}")

    dj.close()


if __name__ == "__main__":
    main()
