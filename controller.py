#!/usr/bin/env python3
"""
DJ Treta Controller — Virtual MIDI controller for Mixxx
Controls Mixxx via virtual MIDI port. Runs entirely in background.

Mixxx MIDI mapping uses Hercules DJControl style layout.
After first run, import the mapping file in Mixxx:
  Preferences → Controllers → DJ Treta → Load Mapping
"""

import rtmidi
import time
import sys
import json

# ── MIDI Configuration ──────────────────────────────────────────────────
# Mixxx default MIDI mappings (compatible with generic MIDI controllers)
# Channel 1 = Deck 1, Channel 2 = Deck 2

CH1 = 0  # Deck 1 (channel 0 in MIDI)
CH2 = 1  # Deck 2 (channel 1 in MIDI)

# Standard Mixxx MIDI CC mappings
CC = {
    'volume':       0x07,  # Channel volume
    'crossfader':   0x0A,  # Crossfader (on CH1)
    'eq_hi':        0x10,  # EQ High
    'eq_mid':       0x11,  # EQ Mid
    'eq_lo':        0x12,  # EQ Low
    'filter':       0x13,  # Quick Effect / Filter
    'rate':         0x14,  # Pitch/Rate
    'master_vol':   0x15,  # Master volume
    'headphone_vol': 0x16, # Headphone volume
    'mix':          0x17,  # Head mix (cue/master)
}

# Note mappings for button actions
NOTE = {
    'play':         0x01,
    'cue':          0x02,
    'sync':         0x03,
    'hotcue1':      0x04,
    'hotcue2':      0x05,
    'hotcue3':      0x06,
    'hotcue4':      0x07,
    'loop_in':      0x08,
    'loop_out':     0x09,
    'loop_toggle':  0x0A,
    'loop_halve':   0x0B,
    'loop_double':  0x0C,
    'load_track':   0x0D,
    'pfl':          0x0E,  # Pre-fader listen (headphone cue)
    'fx1':          0x10,
    'fx2':          0x11,
    'fx3':          0x12,
    'fx_enable':    0x13,
    'prev_track':   0x14,
    'next_track':   0x15,
    'scratch_on':   0x16,
}


class DJTreta:
    """Virtual MIDI DJ controller for Mixxx. Runs in background."""

    def __init__(self, port_name="DJ Treta"):
        self.port_name = port_name
        self.midi_out = None
        self._crossfader_pos = 64  # center
        self._setup_midi()

    def _setup_midi(self):
        """Create virtual MIDI output port."""
        try:
            self.midi_out = rtmidi.MidiOut()
            self.midi_out.open_virtual_port(self.port_name)
            print(f"[DJ Treta] MIDI port '{self.port_name}' is LIVE")
        except Exception as e:
            print(f"[DJ Treta] MIDI setup failed: {e}")
            raise

    # ── Low-level MIDI ──────────────────────────────────────────────

    def _cc(self, channel, cc_num, value):
        """Send Control Change."""
        self.midi_out.send_message([0xB0 | channel, cc_num, max(0, min(127, int(value)))])

    def _note_on(self, channel, note, velocity=127):
        """Send Note On."""
        self.midi_out.send_message([0x90 | channel, note, velocity])

    def _note_off(self, channel, note):
        """Send Note Off."""
        self.midi_out.send_message([0x80 | channel, note, 0])

    def _tap(self, channel, note, velocity=127, duration=0.05):
        """Button press (note on → off)."""
        self._note_on(channel, note, velocity)
        time.sleep(duration)
        self._note_off(channel, note)

    # ── Deck Controls ───────────────────────────────────────────────

    def play(self, deck=1):
        """Play/pause a deck (1 or 2)."""
        ch = CH1 if deck == 1 else CH2
        self._tap(ch, NOTE['play'])
        return f"Deck {deck}: play/pause"

    def cue(self, deck=1):
        """Set/trigger cue point."""
        ch = CH1 if deck == 1 else CH2
        self._tap(ch, NOTE['cue'])
        return f"Deck {deck}: cue"

    def sync(self, deck=1):
        """Sync BPM to other deck."""
        ch = CH1 if deck == 1 else CH2
        self._tap(ch, NOTE['sync'])
        return f"Deck {deck}: sync"

    def load(self, deck=1):
        """Load selected track onto deck."""
        ch = CH1 if deck == 1 else CH2
        self._tap(ch, NOTE['load_track'])
        return f"Deck {deck}: track loaded"

    def volume(self, deck, level):
        """Set deck volume (0-127)."""
        ch = CH1 if deck == 1 else CH2
        self._cc(ch, CC['volume'], level)
        return f"Deck {deck} volume: {level}/127"

    def eq(self, deck, hi=None, mid=None, lo=None):
        """Set deck EQ. Values 0-127, 64=neutral."""
        ch = CH1 if deck == 1 else CH2
        parts = []
        if hi is not None:
            self._cc(ch, CC['eq_hi'], hi)
            parts.append(f"hi={hi}")
        if mid is not None:
            self._cc(ch, CC['eq_mid'], mid)
            parts.append(f"mid={mid}")
        if lo is not None:
            self._cc(ch, CC['eq_lo'], lo)
            parts.append(f"lo={lo}")
        return f"Deck {deck} EQ: {', '.join(parts)}"

    def filter(self, deck, value):
        """Set deck filter/quick effect (0=full cut, 64=neutral, 127=full resonance)."""
        ch = CH1 if deck == 1 else CH2
        self._cc(ch, CC['filter'], value)
        return f"Deck {deck} filter: {value}/127"

    def rate(self, deck, value):
        """Set pitch/rate. 64=normal, <64=slower, >64=faster."""
        ch = CH1 if deck == 1 else CH2
        self._cc(ch, CC['rate'], value)
        return f"Deck {deck} rate: {value}/127"

    # ── Mixer ───────────────────────────────────────────────────────

    def crossfade(self, position):
        """Move crossfader. 0=Deck1, 64=center, 127=Deck2."""
        pos = max(0, min(127, int(position)))
        self._cc(CH1, CC['crossfader'], pos)
        self._crossfader_pos = pos
        return f"Crossfader: {pos}/127"

    def master(self, level):
        """Set master volume (0-127)."""
        self._cc(CH1, CC['master_vol'], level)
        return f"Master volume: {level}/127"

    # ── Transitions ─────────────────────────────────────────────────

    def transition(self, to_deck=2, duration=8.0, steps=40):
        """
        Smooth crossfade transition between decks.
        to_deck: target deck (1 or 2)
        duration: transition time in seconds
        """
        start = self._crossfader_pos
        end = 127 if to_deck == 2 else 0

        for i in range(steps + 1):
            ratio = i / steps
            # Ease in-out curve for smooth transition
            ease = ratio * ratio * (3 - 2 * ratio)
            pos = int(start + (end - start) * ease)
            self._cc(CH1, CC['crossfader'], pos)
            self._crossfader_pos = pos
            time.sleep(duration / steps)

        return f"Transition to Deck {to_deck} ({duration}s)"

    def drop(self, to_deck=2):
        """Instant crossfade cut to target deck."""
        pos = 127 if to_deck == 2 else 0
        self._cc(CH1, CC['crossfader'], pos)
        self._crossfader_pos = pos
        return f"DROP to Deck {to_deck}!"

    def blend(self, duration=16.0, steps=60):
        """
        DJ-style EQ transition: bring in new track's bass while cutting old track's bass.
        More musical than a simple crossfade.
        """
        # Start: crossfader center, deck 2 bass cut
        self.crossfade(64)
        self._cc(CH2, CC['eq_lo'], 0)    # Cut deck 2 bass
        self._cc(CH2, CC['eq_mid'], 40)  # Reduce deck 2 mids
        time.sleep(duration * 0.1)

        # Phase 1: Bring in deck 2 mids
        for i in range(20):
            mid_val = int(40 + (64 - 40) * i / 20)
            self._cc(CH2, CC['eq_mid'], mid_val)
            time.sleep(duration * 0.3 / 20)

        # Phase 2: Bass swap — the magic moment
        swap_steps = 30
        for i in range(swap_steps):
            ratio = i / swap_steps
            # Deck 1 bass out
            self._cc(CH1, CC['eq_lo'], int(127 * (1 - ratio)))
            # Deck 2 bass in
            self._cc(CH2, CC['eq_lo'], int(127 * ratio))
            time.sleep(duration * 0.3 / swap_steps)

        # Phase 3: Fade out deck 1
        for i in range(20):
            ratio = i / 20
            self._cc(CH1, CC['volume'], int(127 * (1 - ratio)))
            xf_pos = int(64 + 63 * ratio)
            self._cc(CH1, CC['crossfader'], xf_pos)
            self._crossfader_pos = xf_pos
            time.sleep(duration * 0.3 / 20)

        # Reset EQs
        self._cc(CH1, CC['eq_lo'], 64)
        self._cc(CH2, CC['eq_lo'], 64)
        self._cc(CH2, CC['eq_mid'], 64)

        return f"EQ blend transition ({duration}s)"

    # ── Effects ─────────────────────────────────────────────────────

    def fx(self, num=1, deck=1):
        """Toggle effect (1-3) on deck."""
        ch = CH1 if deck == 1 else CH2
        fx_map = {1: NOTE['fx1'], 2: NOTE['fx2'], 3: NOTE['fx3']}
        if num in fx_map:
            self._tap(ch, fx_map[num])
        return f"Deck {deck} FX{num} toggled"

    # ── Loops ───────────────────────────────────────────────────────

    def loop(self, deck=1, action="toggle"):
        """Control loops. Actions: toggle, in, out, halve, double."""
        ch = CH1 if deck == 1 else CH2
        actions = {
            'toggle': NOTE['loop_toggle'],
            'in': NOTE['loop_in'],
            'out': NOTE['loop_out'],
            'halve': NOTE['loop_halve'],
            'double': NOTE['loop_double'],
        }
        if action in actions:
            self._tap(ch, actions[action])
        return f"Deck {deck} loop: {action}"

    # ── Hot Cues ────────────────────────────────────────────────────

    def hotcue(self, deck=1, num=1):
        """Trigger hot cue (1-4)."""
        ch = CH1 if deck == 1 else CH2
        cue_map = {1: NOTE['hotcue1'], 2: NOTE['hotcue2'],
                   3: NOTE['hotcue3'], 4: NOTE['hotcue4']}
        if num in cue_map:
            self._tap(ch, cue_map[num])
        return f"Deck {deck} hotcue {num}"

    # ── Library Navigation ──────────────────────────────────────────

    def browse_next(self):
        """Select next track in library."""
        self._tap(CH1, NOTE['next_track'])
        return "Library: next track"

    def browse_prev(self):
        """Select previous track in library."""
        self._tap(CH1, NOTE['prev_track'])
        return "Library: previous track"

    # ── Status ──────────────────────────────────────────────────────

    def status(self):
        """Print controller status."""
        return json.dumps({
            "controller": "DJ Treta",
            "target": "Mixxx",
            "midi_port": self.port_name,
            "crossfader": self._crossfader_pos,
        }, indent=2)

    def close(self):
        """Clean up."""
        if self.midi_out:
            del self.midi_out
            self.midi_out = None
        return "DJ Treta signing off"


# ── CLI ─────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        dj = DJTreta()
        print(dj.status())
        print("\nCommands: play, cue, sync, load, volume, eq, filter,")
        print("          crossfade, transition, drop, blend, fx,")
        print("          loop, hotcue, browse_next, browse_prev, master")
        dj.close()
        return

    dj = DJTreta()
    cmd = sys.argv[1]
    args = sys.argv[2:]

    if hasattr(dj, cmd) and not cmd.startswith('_'):
        fn = getattr(dj, cmd)
        converted = []
        for a in args:
            try:
                converted.append(int(a))
            except ValueError:
                try:
                    converted.append(float(a))
                except ValueError:
                    converted.append(a)
        result = fn(*converted)
        print(result)
    else:
        print(f"Unknown: {cmd}")

    dj.close()


if __name__ == '__main__':
    main()
