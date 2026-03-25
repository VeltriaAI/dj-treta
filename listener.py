#!/usr/bin/env python3
"""
DJ Treta Listening Engine

Polls Mixxx /api/live at 10Hz (100ms), builds real-time musical perception.
Outputs: energy level, energy direction, beat phase, transition opportunities,
breakdown/buildup/drop detection, mood estimation.

Designed for Claude Agent SDK integration — clean interface, ring buffer history.

Usage:
    # As a module (for MCP or Agent SDK):
    from listener import ListeningEngine
    engine = ListeningEngine()
    engine.poll()
    engine.analyze()
    print(engine.get_perception())
    print(engine.suggest_action())

    # As a standalone process:
    python listener.py [--api http://localhost:7778] [--hz 10]
"""

import argparse
import json
import sys
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from typing import Optional

try:
    import urllib.request
    import urllib.error
except ImportError:
    pass


# ── Data Types ────────────────────────────────────────────────────────

@dataclass
class DeckLive:
    playing: bool = False
    bpm: float = 0.0
    beat_active: bool = False
    beat_distance: float = 0.0
    playposition: float = 0.0
    volume: float = 0.0
    vu_left: float = 0.0
    vu_right: float = 0.0
    peak_indicator: bool = False


@dataclass
class LiveReading:
    timestamp: int = 0  # milliseconds since epoch
    crossfader: float = 0.0
    master_vu_left: float = 0.0
    master_vu_right: float = 0.0
    deck1: DeckLive = field(default_factory=DeckLive)
    deck2: DeckLive = field(default_factory=DeckLive)
    local_time: float = 0.0  # time.time() when reading was taken


@dataclass
class Perception:
    energy: float = 0.0                # 0-10, current energy level
    energy_direction: str = "steady"   # rising, falling, steady, building, dropping
    beat_phase: str = "unknown"        # kick, offbeat, breakdown, buildup
    tension: float = 0.0               # 0-10, musical tension
    density: float = 0.0               # 0-10, how "full" the sound is
    mood: str = "unknown"              # melancholic, euphoric, dark, dreamy, driving, chill
    transition_ready: bool = False     # good moment to start a transition?
    breakdown_detected: bool = False
    buildup_detected: bool = False
    drop_detected: bool = False
    active_deck: int = 0               # which deck is louder / more present
    master_loudness: float = 0.0       # 0-1 current master loudness


# ── Listening Engine ──────────────────────────────────────────────────

class ListeningEngine:
    """
    Polls Mixxx at 10Hz, maintains a 30-second ring buffer of readings,
    and derives musical perception from the audio data.
    """

    # Ring buffer size: 300 readings = 30 seconds at 10Hz
    BUFFER_SIZE = 300

    # Analysis windows (in number of readings at 10Hz)
    WINDOW_1S = 10
    WINDOW_2S = 20
    WINDOW_5S = 50
    WINDOW_10S = 100

    def __init__(self, api_url: str = "http://localhost:7778"):
        self.api = api_url
        self.history: deque[LiveReading] = deque(maxlen=self.BUFFER_SIZE)
        self.perception = Perception()
        self._last_energy_samples: deque[float] = deque(maxlen=self.WINDOW_10S)
        self._beat_count_window: deque[bool] = deque(maxlen=self.WINDOW_2S)
        self._prev_energy: float = 0.0
        self._energy_before_quiet: float = 0.0  # for drop detection

    def poll(self) -> Optional[LiveReading]:
        """Fetch real-time data from Mixxx /api/live. Returns the reading or None on error."""
        try:
            req = urllib.request.Request(f"{self.api}/api/live", method="GET")
            req.add_header("Accept", "application/json")
            with urllib.request.urlopen(req, timeout=1) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

        def parse_deck(d: dict) -> DeckLive:
            return DeckLive(
                playing=bool(d.get("playing", False)),
                bpm=float(d.get("bpm", 0)),
                beat_active=bool(d.get("beat_active", False)),
                beat_distance=float(d.get("beat_distance", 0)),
                playposition=float(d.get("playposition", 0)),
                volume=float(d.get("volume", 0)),
                vu_left=float(d.get("vu_left", 0)),
                vu_right=float(d.get("vu_right", 0)),
                peak_indicator=bool(d.get("peak_indicator", False)),
            )

        reading = LiveReading(
            timestamp=int(data.get("timestamp", 0)),
            crossfader=float(data.get("crossfader", 0)),
            master_vu_left=float(data.get("master_vu_left", 0)),
            master_vu_right=float(data.get("master_vu_right", 0)),
            deck1=parse_deck(data.get("deck1", {})),
            deck2=parse_deck(data.get("deck2", {})),
            local_time=time.time(),
        )

        self.history.append(reading)
        return reading

    def analyze(self) -> Perception:
        """Analyze the history buffer and update self.perception."""
        if len(self.history) < 2:
            return self.perception

        latest = self.history[-1]

        # ── Master loudness ──
        master_loud = (latest.master_vu_left + latest.master_vu_right) / 2.0
        self.perception.master_loudness = master_loud

        # ── Active deck (which deck is more present) ──
        # Use crossfader + volume + VU to determine
        d1_presence = self._deck_presence(latest.deck1, latest.crossfader, deck_num=1)
        d2_presence = self._deck_presence(latest.deck2, latest.crossfader, deck_num=2)
        self.perception.active_deck = 1 if d1_presence >= d2_presence else 2

        # ── Energy (0-10) from VU meters over last 5 seconds ──
        energy_raw = self._compute_energy()
        self.perception.energy = round(min(10.0, max(0.0, energy_raw)), 1)

        # ── Energy direction ──
        self.perception.energy_direction = self._compute_energy_direction()

        # ── Beat phase ──
        self.perception.beat_phase = self._compute_beat_phase(latest)

        # ── Breakdown / Buildup / Drop detection ──
        self._detect_structural_events()

        # ── Density (0-10) ──
        self.perception.density = self._compute_density()

        # ── Tension (0-10) ──
        self.perception.tension = self._compute_tension()

        # ── Mood ──
        self.perception.mood = self._compute_mood(latest)

        # ── Transition readiness ──
        self.perception.transition_ready = self._is_transition_ready()

        return self.perception

    # ── Internal analysis methods ──

    def _deck_presence(self, deck: DeckLive, crossfader: float, deck_num: int) -> float:
        """How present a deck is in the mix (0-1)."""
        if not deck.playing:
            return 0.0
        vu = (deck.vu_left + deck.vu_right) / 2.0
        vol = deck.volume
        # Crossfader: -1 = full deck1, +1 = full deck2
        if deck_num == 1:
            cf_weight = max(0.0, 1.0 - max(0.0, crossfader))  # 1 when cf=-1, 0 when cf=+1
        else:
            cf_weight = max(0.0, 1.0 + min(0.0, crossfader))  # 1 when cf=+1, 0 when cf=-1
        return vu * vol * cf_weight

    def _compute_energy(self) -> float:
        """Derive energy (0-10) from VU meter averages over the last 5 seconds."""
        window = min(len(self.history), self.WINDOW_5S)
        if window == 0:
            return 0.0

        total_vu = 0.0
        for i in range(window):
            r = self.history[-(i + 1)]
            # Combine master VU
            vu = (r.master_vu_left + r.master_vu_right) / 2.0
            total_vu += vu

        avg_vu = total_vu / window
        # VU meters in Mixxx are 0-1 (can exceed 1 on peaks)
        # Map to 0-10 energy scale with a slight curve for perception
        energy = avg_vu * 12.0  # 0.83 VU = energy 10
        self._last_energy_samples.append(energy)
        self._prev_energy = energy
        return energy

    def _compute_energy_direction(self) -> str:
        """Compare recent energy vs previous energy to determine direction."""
        samples = list(self._last_energy_samples)
        if len(samples) < self.WINDOW_2S:
            return "steady"

        recent = samples[-self.WINDOW_1S:]  # last 1 second
        previous = samples[-self.WINDOW_2S:-self.WINDOW_1S]  # 1-2 seconds ago

        recent_avg = sum(recent) / len(recent)
        prev_avg = sum(previous) / len(previous)
        delta = recent_avg - prev_avg

        # Check for sustained building (10+ seconds of consistent rise)
        if len(samples) >= self.WINDOW_10S:
            early = samples[:self.WINDOW_5S]
            late = samples[-self.WINDOW_5S:]
            early_avg = sum(early) / len(early)
            late_avg = sum(late) / len(late)
            long_delta = late_avg - early_avg
            if long_delta > 1.5:
                return "building"
            if long_delta < -1.5:
                return "dropping"

        if delta > 0.5:
            return "rising"
        elif delta < -0.5:
            return "falling"
        return "steady"

    def _compute_beat_phase(self, latest: LiveReading) -> str:
        """Determine beat phase from beat_active and beat_distance."""
        active_deck = latest.deck1 if self.perception.active_deck == 1 else latest.deck2

        if not active_deck.playing or active_deck.bpm <= 0:
            return "silent"

        # Track beat activity
        self._beat_count_window.append(active_deck.beat_active)

        # Count beats in the last 2 seconds
        beat_count = sum(1 for b in self._beat_count_window if b)

        # If very few beats in 2 seconds relative to expected → breakdown
        expected_beats = (active_deck.bpm / 60.0) * 2.0  # beats expected in 2s
        if expected_beats > 0 and beat_count < expected_beats * 0.3:
            return "breakdown"

        # beat_distance: 0 = on beat, approaching 1 = near next beat
        dist = active_deck.beat_distance
        if active_deck.beat_active:
            return "kick"
        elif 0.4 < dist < 0.6:
            return "offbeat"
        else:
            return "between"

    def _detect_structural_events(self):
        """Detect breakdowns, buildups, and drops from energy patterns."""
        samples = list(self._last_energy_samples)

        # Reset flags
        self.perception.breakdown_detected = False
        self.perception.buildup_detected = False
        self.perception.drop_detected = False

        if len(samples) < self.WINDOW_2S:
            return

        recent_2s = samples[-self.WINDOW_2S:]
        recent_avg = sum(recent_2s) / len(recent_2s)

        # Breakdown: energy drops >40% in 2 seconds
        if len(samples) >= self.WINDOW_2S * 2:
            prev_2s = samples[-self.WINDOW_2S * 2:-self.WINDOW_2S]
            prev_avg = sum(prev_2s) / len(prev_2s)
            if prev_avg > 2.0 and recent_avg < prev_avg * 0.6:
                self.perception.breakdown_detected = True
                self._energy_before_quiet = prev_avg

        # Buildup: energy rising steadily over 10+ seconds
        if self.perception.energy_direction == "building":
            self.perception.buildup_detected = True

        # Drop: sudden energy spike after a quiet period
        if len(samples) >= self.WINDOW_2S:
            very_recent = samples[-self.WINDOW_1S // 2:]  # last 0.5s
            just_before = samples[-self.WINDOW_1S:-self.WINDOW_1S // 2]  # 0.5-1s ago
            if just_before:
                vr_avg = sum(very_recent) / len(very_recent)
                jb_avg = sum(just_before) / len(just_before)
                # Spike: recent much louder than just before, and just before was quiet
                if jb_avg < 3.0 and vr_avg > jb_avg + 3.0:
                    self.perception.drop_detected = True

    def _compute_density(self) -> float:
        """Density = how consistently loud the sound is (low variance = steady groove)."""
        window = min(len(self.history), self.WINDOW_5S)
        if window < 5:
            return 0.0

        vus = []
        for i in range(window):
            r = self.history[-(i + 1)]
            vus.append((r.master_vu_left + r.master_vu_right) / 2.0)

        mean = sum(vus) / len(vus)
        if mean < 0.01:
            return 0.0

        variance = sum((v - mean) ** 2 for v in vus) / len(vus)
        std = variance ** 0.5

        # Low std relative to mean = dense/full sound
        # coefficient of variation: std/mean
        cv = std / mean if mean > 0 else 1.0

        # cv near 0 = very dense (10), cv > 0.8 = sparse (0)
        density = max(0.0, min(10.0, (1.0 - cv) * 10.0))
        return round(density, 1)

    def _compute_tension(self) -> float:
        """Tension combines energy direction, density changes, and buildup state."""
        tension = 0.0

        # Buildup adds tension
        if self.perception.buildup_detected:
            tension += 4.0

        # Rising energy adds tension
        if self.perception.energy_direction in ("rising", "building"):
            tension += 2.0

        # High density + high energy = intense
        if self.perception.density > 7 and self.perception.energy > 7:
            tension += 2.0

        # Breakdown creates anticipatory tension
        if self.perception.breakdown_detected:
            tension += 3.0

        # Peak indicators add tension
        latest = self.history[-1]
        if latest.deck1.peak_indicator or latest.deck2.peak_indicator:
            tension += 1.0

        return round(min(10.0, tension), 1)

    def _compute_mood(self, latest: LiveReading) -> str:
        """Derive mood from BPM + energy + density patterns."""
        active = latest.deck1 if self.perception.active_deck == 1 else latest.deck2
        bpm = active.bpm
        energy = self.perception.energy
        density = self.perception.density

        if bpm <= 0:
            return "silent"

        # BPM-based base mood
        if bpm < 100:
            base = "chill"
        elif bpm < 120:
            base = "dreamy"
        elif bpm < 128:
            base = "groovy"
        elif bpm < 135:
            base = "driving"
        elif bpm < 145:
            base = "energetic"
        else:
            base = "intense"

        # Modify by energy
        if energy < 3:
            if base in ("driving", "energetic", "intense"):
                return "dark"  # fast bpm but low energy = dark atmosphere
            return "melancholic" if bpm < 120 else "dreamy"
        elif energy > 7:
            if base in ("driving", "energetic", "intense"):
                return "euphoric"
            return "driving"
        elif density > 7 and energy > 5:
            return "hypnotic"

        return base

    def _is_transition_ready(self) -> bool:
        """Determine if this is a good moment to start a transition."""
        # Good times: breakdown, low energy, steady state
        # Bad times: buildup, drop, rising energy

        if self.perception.buildup_detected:
            return False  # never interrupt a buildup
        if self.perception.drop_detected:
            return False  # ride the drop
        if self.perception.energy_direction == "rising":
            return False  # let it build

        if self.perception.breakdown_detected:
            return True  # perfect time
        if self.perception.energy_direction in ("falling", "dropping"):
            return True  # energy waning, good to transition
        if self.perception.energy_direction == "steady" and self.perception.energy < 5:
            return True  # chill moment, easy to blend

        return False

    def get_perception(self) -> dict:
        """Return current musical perception as a dictionary."""
        return asdict(self.perception)

    def suggest_action(self) -> str:
        """Based on perception, suggest what the DJ should do."""
        p = self.perception

        if p.drop_detected:
            return "DROP just happened! Energy peak — ride it. Don't touch anything for at least 16 bars."

        if p.buildup_detected:
            return "BUILDUP in progress — do NOT interrupt. Let it peak. Have the next track ready but wait."

        if p.breakdown_detected:
            return "BREAKDOWN detected — perfect time to start bringing in the next track. Begin a long blend or bass swap."

        if p.energy_direction == "dropping" and p.energy < 4:
            return "Energy is fading. Consider transitioning to maintain the flow, or let it settle into an ambient moment."

        if p.energy_direction == "falling":
            return "Energy dipping — good window for a transition if you have something ready."

        if p.energy > 8 and p.energy_direction == "steady":
            return "Peak energy, steady groove. The crowd is locked in. Ride this — no need to change anything yet."

        if p.energy_direction == "rising":
            return "Energy climbing — let it build naturally. Don't interrupt the momentum."

        if p.transition_ready:
            return "Good moment for a transition — energy is calm and stable."

        return "Cruising. Steady state. Watch for the next breakdown or energy shift."

    def get_snapshot(self) -> dict:
        """Get a complete snapshot: perception + suggestion + raw latest reading."""
        result = {
            "perception": self.get_perception(),
            "suggestion": self.suggest_action(),
        }
        if self.history:
            latest = self.history[-1]
            result["latest"] = {
                "timestamp": latest.timestamp,
                "master_vu": round((latest.master_vu_left + latest.master_vu_right) / 2.0, 3),
                "crossfader": round(latest.crossfader, 3),
                "deck1": {
                    "playing": latest.deck1.playing,
                    "bpm": round(latest.deck1.bpm, 1),
                    "beat_active": latest.deck1.beat_active,
                    "vu": round((latest.deck1.vu_left + latest.deck1.vu_right) / 2.0, 3),
                },
                "deck2": {
                    "playing": latest.deck2.playing,
                    "bpm": round(latest.deck2.bpm, 1),
                    "beat_active": latest.deck2.beat_active,
                    "vu": round((latest.deck2.vu_left + latest.deck2.vu_right) / 2.0, 3),
                },
            }
        return result

    def run(self, hz: float = 10.0, verbose: bool = False):
        """Main loop — poll and analyze continuously."""
        interval = 1.0 / hz
        print(f"[ListeningEngine] Polling {self.api}/api/live at {hz}Hz", file=sys.stderr)

        consecutive_errors = 0
        while True:
            start = time.time()

            reading = self.poll()
            if reading is None:
                consecutive_errors += 1
                if consecutive_errors == 1:
                    print(f"[ListeningEngine] Mixxx not reachable at {self.api}", file=sys.stderr)
                elif consecutive_errors % 50 == 0:  # every 5 seconds
                    print(f"[ListeningEngine] Still waiting for Mixxx... ({consecutive_errors} polls)", file=sys.stderr)
            else:
                if consecutive_errors > 0:
                    print(f"[ListeningEngine] Connected to Mixxx", file=sys.stderr)
                    consecutive_errors = 0

                self.analyze()

                if verbose:
                    p = self.perception
                    bar = "#" * int(p.energy) + "." * (10 - int(p.energy))
                    print(
                        f"[{bar}] E:{p.energy:.1f} {p.energy_direction:>8s} "
                        f"| {p.mood:>10s} | T:{p.tension:.0f} D:{p.density:.0f} "
                        f"| {p.beat_phase:>9s} "
                        f"| {'TRANS-RDY' if p.transition_ready else '         '}"
                        f"{'  BRK!' if p.breakdown_detected else ''}"
                        f"{'  BLD!' if p.buildup_detected else ''}"
                        f"{'  DRP!' if p.drop_detected else ''}",
                        flush=True,
                    )

            elapsed = time.time() - start
            sleep_time = max(0, interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)


# ── CLI Entry Point ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="DJ Treta Listening Engine")
    parser.add_argument("--api", default="http://localhost:7778", help="Mixxx API URL")
    parser.add_argument("--hz", type=float, default=10.0, help="Poll frequency in Hz")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print live perception")
    parser.add_argument("--snapshot", action="store_true", help="Take one snapshot and exit (JSON)")
    args = parser.parse_args()

    engine = ListeningEngine(api_url=args.api)

    if args.snapshot:
        # Single poll + analyze, output JSON
        reading = engine.poll()
        if reading is None:
            print(json.dumps({"error": f"Mixxx not reachable at {args.api}"}))
            sys.exit(1)
        engine.analyze()
        print(json.dumps(engine.get_snapshot(), indent=2))
        sys.exit(0)

    try:
        engine.run(hz=args.hz, verbose=args.verbose)
    except KeyboardInterrupt:
        print("\n[ListeningEngine] Stopped", file=sys.stderr)


if __name__ == "__main__":
    main()
