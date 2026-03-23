#!/usr/bin/env python3
"""
DJ Treta Engine — Bare minimum AI DJ software
Two decks, crossfader, volume, EQ, real-time mixing.
No GUI. Pure Python. Controlled via function calls or CLI.

Usage:
    # As a library (from Claude/Treta):
    from engine import DJEngine
    dj = DJEngine()
    dj.load(1, "path/to/track.mp3")
    dj.play(1)
    dj.crossfade(64)

    # As CLI:
    python3 engine.py load 1 track.mp3
    python3 engine.py play 1
"""

import numpy as np
import sounddevice as sd
from pydub import AudioSegment
from scipy.signal import resample
import threading
import time
import json
import sys
import os

try:
    from mixlog import (log_transition_start, log_transition_phase,
                        log_transition_end, log_track_ended, log_load, log_error)
except ImportError:
    # Fallback if mixlog not available
    def log_transition_start(*a, **kw): pass
    def log_transition_phase(*a, **kw): pass
    def log_transition_end(*a, **kw): pass
    def log_track_ended(*a, **kw): pass
    def log_load(*a, **kw): pass
    def log_error(*a, **kw): pass

# ── Constants ───────────────────────────────────────────────────────────

SAMPLE_RATE = 44100
CHANNELS = 2
BLOCK_SIZE = 2048  # ~46ms per block at 44100Hz


# ── BPM Detection ──────────────────────────────────────────────────────

def detect_bpm(audio_mono, sr):
    """
    Detect BPM using Essentia's RhythmExtractor2013 (professional grade).
    Also returns beat positions for phase alignment.
    Falls back to autocorrelation if essentia unavailable.
    """
    try:
        import essentia.standard as es
        # Essentia expects float32 numpy array
        if not isinstance(audio_mono, np.ndarray):
            audio_mono = np.array(audio_mono, dtype=np.float32)
        audio_mono = audio_mono.astype(np.float32)

        rhythm = es.RhythmExtractor2013(method='multifeature')
        bpm, beats, confidence, _, intervals = rhythm(audio_mono)

        # Store beat positions globally so we can use them for phase alignment
        detect_bpm._last_beats = beats
        detect_bpm._last_confidence = float(confidence)

        return round(float(bpm), 1)

    except ImportError:
        # Fallback: simple autocorrelation
        start = int(len(audio_mono) * 0.2)
        end = start + sr * 30
        if end > len(audio_mono):
            end = len(audio_mono)
        segment = audio_mono[start:end]
        if len(segment) < sr * 5:
            return 120.0

        hop = 512
        n_frames = len(segment) // hop
        energy = np.array([np.sum(segment[i*hop:(i+1)*hop] ** 2) for i in range(n_frames)])
        onset = np.maximum(0, np.diff(energy))
        corr = np.correlate(onset, onset, mode='full')
        corr = corr[len(corr)//2:]

        fps = sr / hop
        min_lag = int(fps * 60 / 140)
        max_lag = min(int(fps * 60 / 110), len(corr) - 1)
        if max_lag <= min_lag:
            return 120.0

        search = corr[min_lag:max_lag]
        best_lag = min_lag + np.argmax(search)
        bpm = 60.0 * fps / best_lag
        return round(bpm, 1)

# Store last beat analysis results
detect_bpm._last_beats = None
detect_bpm._last_confidence = 0


def time_stretch(audio, original_bpm, target_bpm):
    """
    Time-stretch audio to match target BPM by resampling.
    This changes speed without pitch correction (simple but effective for small BPM diffs).
    For diffs < 5%, the pitch shift is barely noticeable.
    """
    if abs(original_bpm - target_bpm) < 0.5:
        return audio  # close enough, no stretching needed

    ratio = original_bpm / target_bpm  # >1 = slow down, <1 = speed up
    new_length = int(len(audio) * ratio)

    if audio.ndim == 2:
        # Stereo: resample each channel
        stretched = np.zeros((new_length, audio.shape[1]), dtype=np.float32)
        for ch in range(audio.shape[1]):
            stretched[:, ch] = resample(audio[:, ch], new_length).astype(np.float32)
    else:
        stretched = resample(audio, new_length).astype(np.float32)

    return stretched


def lowpass_filter(data, cutoff, sr, order=4):
    """Butterworth low-pass filter for isolating kick drums."""
    from scipy.signal import butter, filtfilt
    nyq = sr / 2
    b, a = butter(order, cutoff / nyq, btype='low')
    return filtfilt(b, a, data)


def build_beat_grid(audio_mono, sr, approx_bpm):
    """
    Build a stable beat grid from audio using low-pass filtered onset detection.
    Returns: (exact_bpm, grid_offset_samples, beat_interval_samples)

    The grid offset is the position (in samples) of the first beat modulo beat_interval.
    This allows us to calculate where ANY beat falls: offset + N * interval.
    """
    if approx_bpm == 0:
        return 0, 0, 0

    # Low-pass at 200Hz — only kick drums survive
    try:
        filtered = lowpass_filter(audio_mono, 200, sr)
    except Exception:
        # scipy not available, use unfiltered
        filtered = audio_mono

    hop = 128
    n_frames = min(len(filtered) // hop, sr * 20 // hop)  # max 20 seconds
    energy = np.array([np.sum(filtered[i*hop:(i+1)*hop]**2) for i in range(n_frames)])

    onset = np.maximum(0, np.diff(energy))

    beat_samples = int(60 * sr / approx_bpm)
    min_gap = int(beat_samples * 0.7 / hop)
    threshold = np.mean(onset) + 1.5 * np.std(onset)

    kicks = []
    last = -min_gap
    for i in range(len(onset)):
        if onset[i] > threshold and (i - last) >= min_gap:
            kicks.append(i * hop)
            last = i

    if len(kicks) < 4:
        return approx_bpm, 0, beat_samples

    # Use MEDIAN interval (robust to outliers from hi-hats/snares)
    intervals = [kicks[i+1] - kicks[i] for i in range(len(kicks)-1)]
    median_interval = int(np.median(intervals))

    exact_bpm = round(60.0 * sr / median_interval, 2)

    # Grid offset: use the middle kick's position modulo interval
    grid_offset = kicks[len(kicks)//2] % median_interval

    return exact_bpm, grid_offset, median_interval


def find_first_beat(audio_mono, sr, bpm):
    """Find the grid offset (first beat position) from audio."""
    # Sample from 20% into the track (skip intro)
    start = int(len(audio_mono) * 0.2)
    end = min(start + sr * 15, len(audio_mono))
    segment = audio_mono[start:end]

    _, offset, _ = build_beat_grid(segment, sr, bpm)
    # Adjust offset relative to full track
    return start + offset


def align_beats(outgoing_pos, outgoing_offset, outgoing_interval,
                incoming_offset, incoming_interval, sr):
    """
    Calculate the start position for the incoming track so its kicks
    land exactly when the outgoing track's kicks land.

    Returns: sample position to seek the incoming track to.
    """
    if outgoing_interval == 0 or incoming_interval == 0:
        return 0

    # Where is the outgoing track in its beat cycle right now?
    outgoing_phase = (outgoing_pos - outgoing_offset) % outgoing_interval

    # The incoming track needs to start so that its phase matches
    # incoming_start should satisfy: (incoming_start - incoming_offset) % incoming_interval == outgoing_phase_mapped
    # Map the phase from outgoing tempo to incoming tempo
    phase_ratio = outgoing_phase / outgoing_interval  # 0.0 to 1.0
    incoming_phase = int(phase_ratio * incoming_interval)

    # Start position: offset + phase alignment
    start_pos = incoming_offset + incoming_phase

    # Make sure it's reasonable (within first 2 beats)
    while start_pos > incoming_interval * 2:
        start_pos -= incoming_interval

    return max(0, start_pos)


def build_energy_profile(filepath, sample_interval=15, chunk_duration=3):
    """
    Build an energy profile of a track by sampling at intervals.
    Uses ffmpeg to extract small chunks — no memory issues.
    Returns: dict with energy_profile, mix_out_points, mix_in_points, peak_time
    """
    import subprocess as sp

    filepath = str(filepath)

    # Get duration
    result = sp.run(['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', filepath],
                    capture_output=True, text=True)
    try:
        duration = float(json.loads(result.stdout)['format']['duration'])
    except Exception:
        return None

    profile = []
    for t in range(0, int(duration), sample_interval):
        sp.run(['ffmpeg', '-y', '-ss', str(t), '-t', str(chunk_duration), '-i', filepath,
                '-ar', '22050', '-ac', '1', '/tmp/_dj_chunk.wav'],
               capture_output=True)
        try:
            import soundfile as sf
            data, sr = sf.read('/tmp/_dj_chunk.wav')
            rms = float(np.sqrt(np.mean(data ** 2)))
        except Exception:
            rms = 0
        profile.append({'time': t, 'energy': round(rms, 5)})

    if not profile:
        return None

    # Normalize
    max_e = max(p['energy'] for p in profile)
    for p in profile:
        p['energy_norm'] = round(p['energy'] / max_e, 2) if max_e > 0 else 0

    # Find mix-out points (energy drops > 15%)
    mix_out = []
    for i in range(1, len(profile)):
        drop = profile[i - 1]['energy_norm'] - profile[i]['energy_norm']
        if drop > 0.15:
            mix_out.append({'time': profile[i]['time'], 'drop': round(drop, 2)})

    # Find mix-in points (low energy zones)
    mix_in = [{'time': p['time'], 'energy': p['energy_norm']}
              for p in profile if p['energy_norm'] < 0.3]

    peak_time = max(profile, key=lambda p: p['energy_norm'])['time']
    avg_energy = round(np.mean([p['energy_norm'] for p in profile]), 2)

    return {
        'duration': round(duration, 1),
        'energy_profile': profile,
        'mix_out_points': mix_out[:5],
        'mix_in_points': mix_in[:5],
        'peak_time': peak_time,
        'avg_energy': avg_energy,
    }


class Deck:
    """A single deck — loads and plays one track."""

    def __init__(self, number):
        self.number = number
        self.audio = None           # numpy array (samples x channels)
        self.audio_original = None  # original audio before time-stretching
        self.sample_rate = SAMPLE_RATE
        self.position = 0           # current sample position (int for display)
        self._fpos = 0.0            # fractional position for beat-matched playback
        self.playing = False
        self.volume = 1.0           # 0.0 to 1.0
        self.speed = 1.0            # playback speed multiplier (1.0 = normal)
        self.eq_hi = 1.0            # EQ multipliers (0.0 to 2.0, 1.0 = neutral)
        self.eq_mid = 1.0
        self.eq_lo = 1.0
        self.track_name = ""
        self.track_path = ""
        self.duration = 0           # total duration in seconds
        self.bpm = 0.0              # original detected BPM
        self.effective_bpm = 0.0    # BPM after speed adjustment
        self.first_beat = 0         # first beat position (samples)
        self.loop_start = None      # loop points (sample positions)
        self.loop_end = None
        self.looping = False
        self.beat_positions = []    # exact beat positions (samples) from Essentia
        self.energy_profile = None  # track structure analysis
        self.mix_out_points = []    # best points to start mixing out
        self.mix_in_points = []     # best points for incoming track
        self.peak_time = 0          # when the track hits peak energy

    def load(self, filepath):
        """Load an audio file onto this deck."""
        print(f"[Deck {self.number}] Loading: {os.path.basename(filepath)}")
        self.playing = False
        self.position = 0
        self._fpos = 0.0
        self.speed = 1.0

        # Load with pydub (handles MP3, WAV, FLAC, etc via ffmpeg)
        seg = AudioSegment.from_file(filepath)

        # Convert to our standard format
        seg = seg.set_frame_rate(SAMPLE_RATE).set_channels(CHANNELS)

        # Convert to numpy float32 array (-1.0 to 1.0)
        samples = np.array(seg.get_array_of_samples(), dtype=np.float32)
        samples = samples / (2 ** 15)  # 16-bit to float

        # Reshape to (samples, channels)
        self.audio = samples.reshape(-1, CHANNELS)
        self.audio_original = self.audio.copy()
        self.sample_rate = SAMPLE_RATE
        self.track_name = os.path.basename(filepath)
        self.track_path = filepath
        self.duration = len(self.audio) / SAMPLE_RATE
        self.loop_start = None
        self.loop_end = None
        self.looping = False

        # Detect BPM and beat positions using Essentia (professional grade)
        mono = self.audio.mean(axis=1)
        self.bpm = detect_bpm(mono, SAMPLE_RATE)
        self.effective_bpm = self.bpm

        # Get beat positions from Essentia (stored by detect_bpm)
        if detect_bpm._last_beats is not None and len(detect_bpm._last_beats) > 0:
            # Convert beat times (seconds) to sample positions
            self.beat_positions = [int(b * SAMPLE_RATE) for b in detect_bpm._last_beats]
            self.first_beat = self.beat_positions[0]
            # Beat grid interval from actual beats
            if len(self.beat_positions) > 1:
                intervals = [self.beat_positions[i+1] - self.beat_positions[i]
                             for i in range(min(20, len(self.beat_positions)-1))]
                self.beat_grid_interval = int(np.median(intervals))
            else:
                self.beat_grid_interval = int(60 * SAMPLE_RATE / self.bpm)
            self.beat_grid_offset = self.first_beat % self.beat_grid_interval
        else:
            self.beat_positions = []
            self.beat_grid_interval = int(60 * SAMPLE_RATE / self.bpm) if self.bpm > 0 else 0
            self.beat_grid_offset = 0
            self.first_beat = 0

        mins = int(self.duration // 60)
        secs = int(self.duration % 60)
        print(f"[Deck {self.number}] Loaded: {self.track_name} ({mins}:{secs:02d}) | {self.bpm} BPM")
        log_load(self.track_name, self.number, self.bpm,
                 self.beat_grid_offset, self.beat_grid_interval)

        # Build energy profile in background (doesn't block loading)
        def _analyze():
            profile = build_energy_profile(filepath)
            if profile:
                self.energy_profile = profile
                self.mix_out_points = profile.get('mix_out_points', [])
                self.mix_in_points = profile.get('mix_in_points', [])
                self.peak_time = profile.get('peak_time', 0)
                mo = [f"{m['time']//60}:{m['time']%60:02d}" for m in self.mix_out_points[:2]]
                print(f"[Deck {self.number}] Profile: peak@{self.peak_time//60:.0f}:{self.peak_time%60:02d} | mix-out: {mo}")

        # Check if we have a cached profile first
        analysis_dir = os.path.join(os.path.dirname(os.path.abspath(filepath if os.path.isabs(filepath) else os.path.join(os.getcwd(), filepath))), '..', 'analysis')
        cache_file = os.path.join(os.path.dirname(__file__), 'analysis', os.path.splitext(os.path.basename(filepath))[0] + '.json')
        if os.path.exists(cache_file):
            try:
                with open(cache_file) as f:
                    cached = json.load(f)
                self.energy_profile = cached
                self.mix_out_points = cached.get('mix_out_points', [])
                self.mix_in_points = cached.get('mix_in_points', [])
                self.peak_time = cached.get('peak_time', 0)
                mo = [f"{m['time']//60}:{m['time']%60:02d}" for m in self.mix_out_points[:2]]
                print(f"[Deck {self.number}] Profile (cached): peak@{self.peak_time//60:.0f}:{self.peak_time%60:02d} | mix-out: {mo}")
            except Exception:
                threading.Thread(target=_analyze, daemon=True).start()
        else:
            threading.Thread(target=_analyze, daemon=True).start()

        return True

    def match_bpm(self, target_bpm):
        """
        Beat-match this deck to a target BPM by adjusting playback speed.
        No resampling needed — speed change happens in real-time in get_block().
        For small BPM diffs (<8%), pitch change is barely noticeable.
        """
        if self.bpm == 0 or target_bpm == 0:
            return

        bpm_diff = abs(self.bpm - target_bpm)
        if bpm_diff < 0.5:
            self.speed = 1.0
            self.effective_bpm = self.bpm
            return  # close enough

        # Only adjust if within 8% — beyond that it sounds unnatural
        if bpm_diff / self.bpm > 0.08:
            print(f"[Deck {self.number}] BPM diff too large ({self.bpm} → {target_bpm}), playing at original speed")
            self.speed = 1.0
            self.effective_bpm = self.bpm
            return

        # Speed = target/original. If track is 123 BPM and target is 126, speed = 1.024
        self.speed = target_bpm / self.bpm
        self.effective_bpm = target_bpm
        print(f"[Deck {self.number}] Beat matched: {self.bpm} → {target_bpm} BPM (speed: {self.speed:.3f}x)")

    def get_block(self, num_samples):
        """
        Get the next block of audio samples.
        Uses fractional positioning for beat-matched playback.
        When speed != 1.0, reads samples at a different rate using linear interpolation.
        """
        if self.audio is None or not self.playing:
            return np.zeros((num_samples, CHANNELS), dtype=np.float32)

        audio_len = len(self.audio)

        # Handle looping
        if self.looping and self.loop_end is not None:
            if int(self._fpos) >= self.loop_end:
                self._fpos = float(self.loop_start or 0)

        # Handle end of track
        if int(self._fpos) >= audio_len - 2:
            self.playing = False
            self.position = audio_len
            return np.zeros((num_samples, CHANNELS), dtype=np.float32)

        block = np.zeros((num_samples, CHANNELS), dtype=np.float32)

        if abs(self.speed - 1.0) < 0.001:
            # Normal speed — direct copy (fast path, no interpolation needed)
            start = int(self._fpos)
            end = start + num_samples
            if end <= audio_len:
                block[:] = self.audio[start:end]
            else:
                avail = audio_len - start
                if avail > 0:
                    block[:avail] = self.audio[start:audio_len]
                if not self.looping:
                    self.playing = False
            self._fpos += num_samples
        else:
            # Speed-adjusted playback — linear interpolation between samples
            # This is how real DJ software does pitch/tempo adjustment
            for i in range(num_samples):
                pos = self._fpos + i * self.speed
                idx = int(pos)
                frac = pos - idx

                if idx >= audio_len - 2:
                    if not self.looping:
                        self.playing = False
                    break

                # Linear interpolation between adjacent samples
                block[i] = self.audio[idx] * (1.0 - frac) + self.audio[idx + 1] * frac

            self._fpos += num_samples * self.speed

        self.position = int(self._fpos)

        # Apply volume
        block *= self.volume

        return block

    def get_position_str(self):
        """Get current position as mm:ss."""
        if self.audio is None:
            return "--:--"
        pos_sec = self.position / SAMPLE_RATE
        return f"{int(pos_sec // 60)}:{int(pos_sec % 60):02d}"

    def get_remaining_str(self):
        """Get remaining time as mm:ss."""
        if self.audio is None:
            return "--:--"
        remaining = self.duration - (self.position / SAMPLE_RATE)
        remaining = max(0, remaining)
        return f"{int(remaining // 60)}:{int(remaining % 60):02d}"

    def seek(self, seconds):
        """Seek to a position in seconds."""
        if self.audio is not None:
            self.position = int(seconds * SAMPLE_RATE)
            self.position = max(0, min(self.position, len(self.audio) - 1))
            self._fpos = float(self.position)

    def status(self):
        """Get deck status."""
        return {
            "deck": self.number,
            "track": self.track_name or "(empty)",
            "playing": self.playing,
            "position": self.get_position_str(),
            "remaining": self.get_remaining_str(),
            "duration": f"{int(self.duration // 60)}:{int(self.duration % 60):02d}",
            "volume": round(self.volume, 2),
            "bpm": self.bpm,
            "peak_time": self.peak_time,
            "mix_out_points": [m['time'] for m in self.mix_out_points[:3]],
        }


class DJEngine:
    """
    Two-deck DJ engine with crossfader and real-time mixing.
    Outputs audio directly to system speakers.
    """

    def __init__(self):
        self.deck1 = Deck(1)
        self.deck2 = Deck(2)
        self.crossfader = 0.5       # 0.0 = full deck1, 1.0 = full deck2
        self.master_volume = 0.8
        self.stream = None
        self._running = False
        self._lock = threading.Lock()
        # Auto-DJ playlist (built into engine — music NEVER stops)
        self._playlist = []
        self._playlist_index = 0
        self._auto_dj = False
        self._transitioning = False
        self._monitor_thread = None

    def _audio_callback(self, outdata, frames, time_info, status):
        """Called by sounddevice for each audio block."""
        if status:
            pass  # ignore underflow warnings

        with self._lock:
            # Get audio from both decks
            block1 = self.deck1.get_block(frames)
            block2 = self.deck2.get_block(frames)

            # Apply crossfader (equal power crossfade)
            gain1 = np.cos(self.crossfader * np.pi / 2)
            gain2 = np.sin(self.crossfader * np.pi / 2)

            # Mix
            mixed = (block1 * gain1) + (block2 * gain2)

            # Apply master volume
            mixed *= self.master_volume

            # Clip to prevent distortion
            np.clip(mixed, -1.0, 1.0, out=mixed)

            outdata[:] = mixed

    def start(self):
        """Start the audio engine."""
        if self._running:
            return "Engine already running"

        self.stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype='float32',
            blocksize=BLOCK_SIZE,
            callback=self._audio_callback,
        )
        self.stream.start()
        self._running = True

        # Start the auto-DJ monitor thread
        self._monitor_thread = threading.Thread(target=self._auto_dj_monitor, daemon=True)
        self._monitor_thread.start()

        print("[DJ Treta] Engine started — audio output active")
        return "Engine running"

    def stop(self):
        """Stop the audio engine."""
        self._auto_dj = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self._running = False
        self.deck1.playing = False
        self.deck2.playing = False
        print("[DJ Treta] Engine stopped")
        return "Engine stopped"

    # ── Auto-DJ (built into engine — music NEVER stops) ─────────────

    def set_playlist(self, track_paths):
        """Set the auto-DJ playlist. Tracks will loop."""
        self._playlist = list(track_paths)
        self._playlist_index = 0
        print(f"[DJ Treta] Playlist set: {len(self._playlist)} tracks")
        return f"Playlist: {len(self._playlist)} tracks"

    def enable_auto_dj(self):
        """Enable auto-DJ — engine handles transitions automatically."""
        if not self._playlist:
            return "No playlist set"
        self._auto_dj = True
        print("[DJ Treta] Auto-DJ ENABLED — I'll handle transitions")
        return "Auto-DJ enabled"

    def disable_auto_dj(self):
        """Disable auto-DJ."""
        self._auto_dj = False
        return "Auto-DJ disabled"

    def _next_playlist_track(self):
        """Get the next track from the playlist (loops)."""
        if not self._playlist:
            return None
        track = self._playlist[self._playlist_index % len(self._playlist)]
        self._playlist_index = (self._playlist_index + 1) % len(self._playlist)
        return track

    def _auto_dj_monitor(self):
        """
        Runs in background. Monitors playback and auto-transitions.
        This is the sacred guardian — music NEVER stops.
        """
        while self._running:
            time.sleep(2)  # check every 2 seconds

            if not self._auto_dj or self._transitioning:
                continue

            # Which deck is active?
            if self.crossfader < 0.5:
                active, inactive = self.deck1, self.deck2
                active_num, inactive_num = 1, 2
            else:
                active, inactive = self.deck2, self.deck1
                active_num, inactive_num = 2, 1

            # Is active deck playing?
            if not active.playing and active.audio is not None:
                # Track ended and nothing transitioned — emergency!
                # Check if inactive has something
                if inactive.audio is not None:
                    inactive.playing = True
                    self.crossfader = 1.0 if inactive_num == 2 else 0.0
                    print(f"[Auto-DJ] Emergency: switched to Deck {inactive_num}")
                    # Load next on the now-empty deck
                    next_track = self._next_playlist_track()
                    if next_track:
                        self.load(active_num, next_track)
                continue

            if not active.playing:
                continue

            # Check remaining time
            remaining = active.duration - (active.position / active.sample_rate)

            # Smart timing — same rules as the DJ cron:
            # > 5 min: just make sure next track is preloaded
            # 3-5 min: start transition, duration = (remaining - 30) * 0.6
            # < 3 min: urgent, duration = remaining * 0.5
            # < 30s: emergency snap
            if remaining > 300:
                # Preload zone — make sure inactive deck has something
                if inactive.audio is None:
                    next_track = self._next_playlist_track()
                    if next_track:
                        self.load(inactive_num, next_track)
                continue

            if remaining < 30 and remaining > 0:
                # Emergency snap
                if inactive.audio is not None:
                    inactive.playing = True
                    self.crossfader = 1.0 if inactive_num == 2 else 0.0
                    print(f"[Auto-DJ] Emergency snap to Deck {inactive_num}")
                continue

            # Calculate transition duration
            if remaining <= 180:  # < 3 min
                transition_dur = remaining * 0.5
            else:  # 3-5 min
                transition_dur = (remaining - 30) * 0.6

            transition_dur = max(15, min(transition_dur, remaining - 10))

            if remaining < 300 and remaining > 10:
                self._transitioning = True

                # Make sure inactive deck has a track
                if inactive.audio is None:
                    next_track = self._next_playlist_track()
                    if next_track:
                        self.load(inactive_num, next_track)

                if inactive.audio is not None:
                    actual_dur = min(transition_dur, remaining - 2)
                    print(f"[Auto-DJ] {active.track_name[:30]}... → {inactive.track_name[:30]}... ({actual_dur:.0f}s transition)")
                    inactive.playing = True
                    self.transition(inactive_num, duration=actual_dur)

                    # Wait for transition to finish, then preload next
                    def _post_transition(t_dur=actual_dur, a_num=active_num):
                        time.sleep(t_dur + 5)
                        self._transitioning = False
                        next_track = self._next_playlist_track()
                        if next_track:
                            self.load(a_num, next_track)
                            print(f"[Auto-DJ] Preloaded next on Deck {a_num}")

                    threading.Thread(target=_post_transition, daemon=True).start()
                else:
                    self._transitioning = False

    def switch_output(self, device=None):
        """
        Hot-switch audio output device WITHOUT stopping playback.
        Saves deck state, swaps the stream, resumes seamlessly.
        device: device index or None for system default.
        """
        # Save state
        d1_playing = self.deck1.playing
        d2_playing = self.deck2.playing
        d1_pos = self.deck1.position
        d2_pos = self.deck2.position

        # Swap stream
        if self.stream:
            self.stream.stop()
            self.stream.close()

        kwargs = {
            'samplerate': SAMPLE_RATE,
            'channels': CHANNELS,
            'dtype': 'float32',
            'blocksize': BLOCK_SIZE,
            'callback': self._audio_callback,
        }
        if device is not None:
            kwargs['device'] = device

        self.stream = sd.OutputStream(**kwargs)
        self.stream.start()

        # Restore state — music never stopped in memory, just the output
        self.deck1.playing = d1_playing
        self.deck2.playing = d2_playing
        self.deck1.position = d1_pos
        self.deck2.position = d2_pos

        dev_name = sd.query_devices(device if device else sd.default.device[1])['name']
        print(f"[DJ Treta] Output switched to: {dev_name} — no interruption")
        return f"Output: {dev_name}"

    # ── Deck Controls ───────────────────────────────────────────────

    def load(self, deck_num, filepath, beatmatch=True):
        """Load a track onto a deck. Auto beat-matches to the playing deck."""
        deck = self.deck1 if deck_num == 1 else self.deck2
        other = self.deck2 if deck_num == 1 else self.deck1
        result = deck.load(filepath)

        # Auto beat-match to the playing deck
        if beatmatch and other.playing and other.bpm > 0 and deck.bpm > 0:
            deck.match_bpm(other.bpm)

        return result

    def play(self, deck_num=1):
        """Play a deck."""
        deck = self.deck1 if deck_num == 1 else self.deck2
        if deck.audio is None:
            return f"Deck {deck_num}: no track loaded"
        deck.playing = True
        return f"Deck {deck_num}: PLAYING — {deck.track_name}"

    def pause(self, deck_num=1):
        """Pause a deck."""
        deck = self.deck1 if deck_num == 1 else self.deck2
        deck.playing = False
        return f"Deck {deck_num}: paused"

    def stop_deck(self, deck_num=1):
        """Stop a deck and reset position."""
        deck = self.deck1 if deck_num == 1 else self.deck2
        deck.playing = False
        deck.position = 0
        return f"Deck {deck_num}: stopped"

    def volume(self, deck_num, level):
        """Set deck volume (0.0 to 1.0)."""
        deck = self.deck1 if deck_num == 1 else self.deck2
        deck.volume = max(0.0, min(1.0, float(level)))
        return f"Deck {deck_num} volume: {deck.volume}"

    def seek(self, deck_num, seconds):
        """Seek to position in seconds."""
        deck = self.deck1 if deck_num == 1 else self.deck2
        deck.seek(float(seconds))
        return f"Deck {deck_num}: seeked to {deck.get_position_str()}"

    # ── Mixer ───────────────────────────────────────────────────────

    def set_crossfader(self, position):
        """Set crossfader. 0.0 = Deck 1, 0.5 = center, 1.0 = Deck 2."""
        self.crossfader = max(0.0, min(1.0, float(position)))
        return f"Crossfader: {self.crossfader}"

    def set_master(self, level):
        """Set master volume (0.0 to 1.0)."""
        self.master_volume = max(0.0, min(1.0, float(level)))
        return f"Master volume: {self.master_volume}"

    # ── Transitions ─────────────────────────────────────────────────

    def transition(self, to_deck=2, duration=60.0):
        """
        DJ transition — simple, reliable, tested.
        Just a smooth crossfade with safety checks.
        """
        def _run():
            fps = 20
            incoming = self.deck2 if to_deck == 2 else self.deck1
            outgoing = self.deck1 if to_deck == 2 else self.deck2

            # ── Use requested duration directly ──
            # The cron already calculates safe duration based on remaining time.
            # Just use it. The emergency check in the loop handles track ending early.
            actual_duration = duration
            if outgoing.audio is not None:
                out_pos = int(getattr(outgoing, '_fpos', outgoing.position))
                actual_remaining = (len(outgoing.audio) - out_pos) / SAMPLE_RATE
                print(f"[DJ Treta] Outgoing has {actual_remaining:.0f}s left, transition={duration:.0f}s")
                # Only cap if truly impossible (duration > remaining)
                if actual_duration > actual_remaining:
                    actual_duration = max(10, actual_remaining - 5)
                    print(f"[DJ Treta] Capped to {actual_duration:.0f}s")

            # ── Beat match + Phase align ──
            if outgoing.playing and outgoing.bpm > 0 and incoming.bpm > 0:
                incoming.match_bpm(outgoing.bpm)

                # Phase alignment using exact beat positions from Essentia
                out_beats = getattr(outgoing, 'beat_positions', [])
                in_beats = getattr(incoming, 'beat_positions', [])
                if out_beats and in_beats:
                    # Find the next beat in the outgoing track after current position
                    out_pos = int(getattr(outgoing, '_fpos', outgoing.position))
                    next_out_beat = None
                    for b in out_beats:
                        if b > out_pos:
                            next_out_beat = b
                            break

                    if next_out_beat is not None:
                        # Time until next outgoing beat
                        time_to_beat = (next_out_beat - out_pos) / SAMPLE_RATE
                        # Start incoming track at its first beat, delayed by the same amount
                        # So both kicks land at the same moment
                        in_start = max(0, in_beats[0] - int(time_to_beat * SAMPLE_RATE))
                        incoming.position = in_start
                        incoming._fpos = float(in_start)
                        print(f"[DJ Treta] Phase aligned via Essentia beats: incoming starts at {in_start/SAMPLE_RATE:.3f}s")

            # Log
            log_transition_start(
                outgoing.track_name, incoming.track_name,
                2 if to_deck == 1 else 1, to_deck, actual_duration,
                outgoing.bpm, incoming.bpm, incoming.speed,
                incoming.position, self.crossfader
            )

            # Make sure incoming is playing
            if not incoming.playing and incoming.audio is not None:
                incoming.playing = True

            cf_start = self.crossfader
            cf_end = 1.0 if to_deck == 2 else 0.0
            t_start = time.time()
            total_steps = int(actual_duration * fps)

            # ── Single smooth crossfade with emergency checks ──
            for i in range(total_steps):
                # Emergency: outgoing died
                if not outgoing.playing:
                    print(f"[DJ Treta] Outgoing ended at step {i}/{total_steps} — completing")
                    break

                r = i / total_steps
                # Smooth S-curve
                ease = r * r * (3 - 2 * r)
                with self._lock:
                    self.crossfader = cf_start + (cf_end - cf_start) * ease
                time.sleep(1.0 / fps)

            # ── Always land clean ──
            with self._lock:
                self.crossfader = cf_end
            outgoing.playing = False
            outgoing.volume = 1.0

            elapsed = time.time() - t_start
            log_transition_end(incoming.track_name, to_deck, self.crossfader)
            print(f"[DJ Treta] Transition done ({elapsed:.1f}s, CF={cf_end}) — {incoming.track_name[:40]}")

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return f"Transitioning to Deck {to_deck} over {duration:.0f}s..."

    def drop(self, to_deck=2):
        """Instant crossfade cut."""
        self.crossfader = 1.0 if to_deck == 2 else 0.0
        return f"DROP to Deck {to_deck}!"

    def blend(self, duration=30.0):
        """
        Long atmospheric blend — perfect for ambient/deep techno.
        Both tracks play together at length, slow organic crossover.
        """
        def _run():
            fps = 20
            incoming = self.deck2 if self.crossfader < 0.5 else self.deck1
            to_deck = 2 if self.crossfader < 0.5 else 1

            # Make sure incoming is playing
            if not incoming.playing and incoming.audio is not None:
                incoming.playing = True

            total_steps = int(duration * fps)
            cf_start = self.crossfader
            cf_end = 1.0 if to_deck == 2 else 0.0

            for i in range(total_steps):
                ratio = i / total_steps
                # Very gentle S-curve — almost linear in the middle
                # This keeps both tracks audible for most of the transition
                ease = ratio * ratio * ratio * (ratio * (6 * ratio - 15) + 10)
                with self._lock:
                    self.crossfader = cf_start + (cf_end - cf_start) * ease
                time.sleep(1.0 / fps)

            with self._lock:
                self.crossfader = cf_end

            print(f"[DJ Treta] Blend complete — landed on Deck {to_deck}")

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return f"Blending over {duration}s..."

    # ── Status ──────────────────────────────────────────────────────

    def status(self):
        """Get full engine status."""
        return {
            "engine": "running" if self._running else "stopped",
            "master_volume": self.master_volume,
            "crossfader": round(self.crossfader, 2),
            "deck1": self.deck1.status(),
            "deck2": self.deck2.status(),
        }

    def now_playing(self):
        """Quick status of what's playing."""
        d1 = self.deck1
        d2 = self.deck2
        lines = []
        if d1.playing:
            lines.append(f"Deck 1: {d1.track_name} [{d1.get_position_str()}/{d1.get_remaining_str()} remaining]")
        if d2.playing:
            lines.append(f"Deck 2: {d2.track_name} [{d2.get_position_str()}/{d2.get_remaining_str()} remaining]")
        if not lines:
            lines.append("Nothing playing")
        lines.append(f"Crossfader: {'<' * int((1-self.crossfader)*10)}|{'>' * int(self.crossfader*10)} ({self.crossfader:.1f})")
        return "\n".join(lines)


# ── Singleton for use from Claude/Treta ─────────────────────────────────

_engine = None

def get_engine():
    """Get or create the singleton DJ engine."""
    global _engine
    if _engine is None:
        _engine = DJEngine()
        _engine.start()
    return _engine


# ── CLI ─────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("DJ Treta Engine")
        print("  start                    — Start audio engine")
        print("  load <deck> <file>       — Load track")
        print("  play <deck>              — Play deck")
        print("  pause <deck>             — Pause deck")
        print("  volume <deck> <0-1>      — Set volume")
        print("  crossfade <0-1>          — Set crossfader")
        print("  master <0-1>             — Set master volume")
        print("  transition <deck> <sec>  — Smooth crossfade")
        print("  drop <deck>              — Instant cut")
        print("  blend <sec>              — EQ transition")
        print("  seek <deck> <sec>        — Seek position")
        print("  status                   — Show status")
        print("  demo                     — Load tracks and play")
        return

    dj = get_engine()
    cmd = sys.argv[1]

    if cmd == "start":
        print(dj.start() if not dj._running else "Already running")

    elif cmd == "load":
        deck = int(sys.argv[2])
        filepath = sys.argv[3]
        dj.load(deck, filepath)

    elif cmd == "play":
        deck = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        print(dj.play(deck))

    elif cmd == "pause":
        deck = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        print(dj.pause(deck))

    elif cmd == "volume":
        print(dj.volume(int(sys.argv[2]), float(sys.argv[3])))

    elif cmd == "crossfade":
        print(dj.set_crossfader(float(sys.argv[2])))

    elif cmd == "master":
        print(dj.set_master(float(sys.argv[2])))

    elif cmd == "transition":
        deck = int(sys.argv[2]) if len(sys.argv) > 2 else 2
        dur = float(sys.argv[3]) if len(sys.argv) > 3 else 8.0
        print(dj.transition(deck, dur))

    elif cmd == "drop":
        deck = int(sys.argv[2]) if len(sys.argv) > 2 else 2
        print(dj.drop(deck))

    elif cmd == "blend":
        dur = float(sys.argv[2]) if len(sys.argv) > 2 else 16.0
        print(dj.blend(dur))

    elif cmd == "seek":
        print(dj.seek(int(sys.argv[2]), float(sys.argv[3])))

    elif cmd == "status":
        print(json.dumps(dj.status(), indent=2))

    elif cmd == "demo":
        # Quick demo — load tracks from our library and play
        tracks_dir = os.path.join(os.path.dirname(__file__), "tracks")
        tracks = [f for f in os.listdir(tracks_dir) if f.endswith('.mp3')]
        if len(tracks) >= 1:
            dj.load(1, os.path.join(tracks_dir, tracks[0]))
            dj.play(1)
            print(f"Playing: {tracks[0]}")
        if len(tracks) >= 2:
            dj.load(2, os.path.join(tracks_dir, tracks[1]))
            print(f"Deck 2 ready: {tracks[1]}")
        print("\nDJ Treta is live! Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(5)
                print(dj.now_playing())
        except KeyboardInterrupt:
            dj.stop()
            print("\nDJ Treta out.")

    else:
        print(f"Unknown: {cmd}")


if __name__ == "__main__":
    main()
