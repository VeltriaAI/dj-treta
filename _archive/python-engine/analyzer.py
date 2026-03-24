#!/usr/bin/env python3
"""
DJ Treta — Audio Analyzer
Analyzes tracks to extract musical features for intelligent mixing.

For each track, produces:
- BPM (tempo)
- Key (musical key)
- Energy curve (loudness over time)
- Beat grid (positions of every beat)
- Sections (intro, buildup, drop, breakdown, outro)
- Mix points (best positions to start/end transitions)
- Spectral character (bass-heavy, mid-focused, bright, dark)

This is DJ Treta's "ears" — how it understands music without hearing it.
"""

import librosa
import numpy as np
import json
import os
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent
TRACKS_DIR = SKILL_DIR / "tracks"
ANALYSIS_DIR = SKILL_DIR / "analysis"
ANALYSIS_DIR.mkdir(exist_ok=True)


def analyze_track(filepath, force=False):
    """
    Full analysis of a track. Returns a dict with all musical features.
    Results are cached to disk so we don't re-analyze.
    """
    filepath = Path(filepath)
    cache_file = ANALYSIS_DIR / f"{filepath.stem}.json"

    # Return cached if available
    if cache_file.exists() and not force:
        with open(cache_file) as f:
            cached = json.load(f)
            print(f"[Analyzer] Cached: {filepath.name}")
            return cached

    print(f"[Analyzer] Analyzing: {filepath.name} ...")

    # Load audio (mono for analysis, sr=22050 is standard for librosa)
    y, sr = librosa.load(str(filepath), sr=22050, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)

    print(f"  Duration: {int(duration//60)}:{int(duration%60):02d}")

    # ── BPM Detection ───────────────────────────────────────────────
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    # tempo can be an array in newer librosa
    bpm = float(tempo) if np.isscalar(tempo) else float(tempo[0])
    beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()

    print(f"  BPM: {bpm:.1f}")
    print(f"  Beats: {len(beat_times)}")

    # ── Key Detection ───────────────────────────────────────────────
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    key_idx = int(np.argmax(np.mean(chroma, axis=1)))
    key_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    key = key_names[key_idx]

    # Detect major/minor by comparing major and minor profiles
    major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    chroma_mean = np.mean(chroma, axis=1)
    # Rotate profiles to match detected key
    major_corr = np.corrcoef(np.roll(major_profile, key_idx), chroma_mean)[0, 1]
    minor_corr = np.corrcoef(np.roll(minor_profile, key_idx), chroma_mean)[0, 1]
    mode = "major" if major_corr > minor_corr else "minor"
    key_full = f"{key} {mode}"

    print(f"  Key: {key_full}")

    # ── Energy Curve ────────────────────────────────────────────────
    # RMS energy in windows, normalized 0-1
    rms = librosa.feature.rms(y=y)[0]
    # Downsample to ~1 value per second
    hop_length = 512  # default
    frames_per_sec = sr / hop_length
    chunk_size = max(1, int(frames_per_sec))
    energy_curve = []
    for i in range(0, len(rms), chunk_size):
        chunk = rms[i:i+chunk_size]
        energy_curve.append(float(np.mean(chunk)))

    # Normalize to 0-1
    max_energy = max(energy_curve) if energy_curve else 1
    if max_energy > 0:
        energy_curve = [e / max_energy for e in energy_curve]

    # ── Spectral Character ──────────────────────────────────────────
    spec_cent = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    avg_centroid = float(np.mean(spec_cent))

    # Frequency band energy
    S = np.abs(librosa.stft(y))
    freqs = librosa.fft_frequencies(sr=sr)

    # Bass (20-250 Hz), Mid (250-4000 Hz), High (4000+ Hz)
    bass_mask = (freqs >= 20) & (freqs < 250)
    mid_mask = (freqs >= 250) & (freqs < 4000)
    high_mask = freqs >= 4000

    bass_energy = float(np.mean(S[bass_mask, :])) if bass_mask.any() else 0
    mid_energy = float(np.mean(S[mid_mask, :])) if mid_mask.any() else 0
    high_energy = float(np.mean(S[high_mask, :])) if high_mask.any() else 0

    total_band = bass_energy + mid_energy + high_energy
    if total_band > 0:
        bass_pct = bass_energy / total_band
        mid_pct = mid_energy / total_band
        high_pct = high_energy / total_band
    else:
        bass_pct = mid_pct = high_pct = 0.33

    # Character label
    if bass_pct > 0.45:
        character = "bass-heavy"
    elif high_pct > 0.35:
        character = "bright"
    elif mid_pct > 0.45:
        character = "mid-focused"
    else:
        character = "balanced"

    print(f"  Character: {character} (bass={bass_pct:.0%} mid={mid_pct:.0%} high={high_pct:.0%})")

    # ── Section Detection ───────────────────────────────────────────
    # Use energy curve to detect sections
    sections = _detect_sections(energy_curve, duration)
    print(f"  Sections: {len(sections)}")
    for s in sections:
        print(f"    {s['type']:12s} {s['start_str']} → {s['end_str']} (energy: {s['avg_energy']:.2f})")

    # ── Mix Points ──────────────────────────────────────────────────
    mix_in_points = _find_mix_points(energy_curve, duration, "in")
    mix_out_points = _find_mix_points(energy_curve, duration, "out")

    print(f"  Mix-in points: {[p['time_str'] for p in mix_in_points[:3]]}")
    print(f"  Mix-out points: {[p['time_str'] for p in mix_out_points[:3]]}")

    # ── Average Energy ──────────────────────────────────────────────
    avg_energy = float(np.mean(energy_curve))

    # ── Build Result ────────────────────────────────────────────────
    result = {
        "file": str(filepath),
        "filename": filepath.name,
        "duration": round(duration, 1),
        "duration_str": f"{int(duration//60)}:{int(duration%60):02d}",
        "bpm": round(bpm, 1),
        "key": key_full,
        "key_note": key,
        "key_mode": mode,
        "avg_energy": round(avg_energy, 3),
        "character": character,
        "spectral": {
            "bass": round(bass_pct, 3),
            "mid": round(mid_pct, 3),
            "high": round(high_pct, 3),
            "centroid": round(avg_centroid, 1),
        },
        "sections": sections,
        "mix_in_points": mix_in_points[:5],
        "mix_out_points": mix_out_points[:5],
        "beat_count": len(beat_times),
        # Don't store full arrays in JSON — too large
        # Store summary stats instead
        "energy_summary": {
            "min": round(min(energy_curve), 3),
            "max": round(max(energy_curve), 3),
            "mean": round(avg_energy, 3),
            "std": round(float(np.std(energy_curve)), 3),
        },
    }

    # Cache to disk
    with open(cache_file, "w") as f:
        json.dump(result, f, indent=2)

    print(f"[Analyzer] Done: {filepath.name}")
    return result


def _detect_sections(energy_curve, duration):
    """
    Detect musical sections from energy curve.
    Uses energy levels to identify:
    - intro (low energy at start)
    - buildup (rising energy)
    - drop/peak (high energy)
    - breakdown (sudden energy dip in the middle)
    - outro (low energy at end)
    """
    if not energy_curve:
        return []

    n = len(energy_curve)
    sec_per_sample = duration / n

    # Smooth the energy curve
    window = min(15, n // 10)
    if window > 1:
        kernel = np.ones(window) / window
        smoothed = np.convolve(energy_curve, kernel, mode='same')
    else:
        smoothed = np.array(energy_curve)

    # Threshold-based section detection
    mean_e = np.mean(smoothed)
    low_thresh = mean_e * 0.5
    high_thresh = mean_e * 1.2

    sections = []
    current_type = None
    current_start = 0

    for i in range(n):
        e = smoothed[i]
        pos_ratio = i / n

        # Determine section type
        if pos_ratio < 0.05:
            sec_type = "intro"
        elif pos_ratio > 0.92:
            sec_type = "outro"
        elif e < low_thresh:
            sec_type = "breakdown"
        elif e > high_thresh:
            sec_type = "peak"
        else:
            # Check if energy is rising or falling
            if i > 5 and smoothed[i] > smoothed[i-5] * 1.1:
                sec_type = "buildup"
            elif i > 5 and smoothed[i] < smoothed[i-5] * 0.9:
                sec_type = "cooldown"
            else:
                sec_type = "groove"

        if sec_type != current_type:
            if current_type is not None:
                start_sec = current_start * sec_per_sample
                end_sec = i * sec_per_sample
                # Only add if section is at least 10 seconds
                if end_sec - start_sec >= 10:
                    avg_e = float(np.mean(smoothed[current_start:i]))
                    sections.append({
                        "type": current_type,
                        "start": round(start_sec, 1),
                        "end": round(end_sec, 1),
                        "start_str": f"{int(start_sec//60)}:{int(start_sec%60):02d}",
                        "end_str": f"{int(end_sec//60)}:{int(end_sec%60):02d}",
                        "avg_energy": round(avg_e, 3),
                    })
            current_type = sec_type
            current_start = i

    # Add final section
    if current_type:
        start_sec = current_start * sec_per_sample
        avg_e = float(np.mean(smoothed[current_start:]))
        sections.append({
            "type": current_type,
            "start": round(start_sec, 1),
            "end": round(duration, 1),
            "start_str": f"{int(start_sec//60)}:{int(start_sec%60):02d}",
            "end_str": f"{int(duration//60)}:{int(duration%60):02d}",
            "avg_energy": round(avg_e, 3),
        })

    return sections


def _find_mix_points(energy_curve, duration, direction="in"):
    """
    Find good points to mix in or out.
    Mix-in: low energy points (breakdowns, intros) where a new track can sneak in
    Mix-out: points where energy is dropping (end of a peak, heading to breakdown)
    """
    if not energy_curve:
        return []

    n = len(energy_curve)
    sec_per_sample = duration / n

    # Smooth
    window = min(10, n // 20)
    if window > 1:
        kernel = np.ones(window) / window
        smoothed = np.convolve(energy_curve, kernel, mode='same')
    else:
        smoothed = np.array(energy_curve)

    mean_e = np.mean(smoothed)
    points = []

    if direction == "in":
        # Find low-energy valleys (good for sneaking a new track in)
        for i in range(n // 10, n - n // 10):  # skip first/last 10%
            e = smoothed[i]
            if e < mean_e * 0.6:
                # Check it's a local minimum
                local_min = True
                for j in range(max(0, i-5), min(n, i+5)):
                    if smoothed[j] < e:
                        local_min = False
                        break
                if local_min:
                    t = i * sec_per_sample
                    points.append({
                        "time": round(t, 1),
                        "time_str": f"{int(t//60)}:{int(t%60):02d}",
                        "energy": round(float(e), 3),
                        "quality": round(1 - float(e), 3),  # lower energy = better mix point
                    })
    else:
        # Mix-out: find points where energy drops significantly
        for i in range(n // 4, n):  # only in the latter 75%
            if i + 5 < n:
                drop = smoothed[i] - smoothed[i+5]
                if drop > mean_e * 0.2:
                    t = i * sec_per_sample
                    points.append({
                        "time": round(t, 1),
                        "time_str": f"{int(t//60)}:{int(t%60):02d}",
                        "energy": round(float(smoothed[i]), 3),
                        "quality": round(float(drop), 3),
                    })

    # Sort by quality (best first), deduplicate (min 30s apart)
    points.sort(key=lambda p: -p['quality'])
    deduped = []
    for p in points:
        if not deduped or all(abs(p['time'] - d['time']) > 30 for d in deduped):
            deduped.append(p)
    return deduped


def analyze_library():
    """Analyze all tracks in the library."""
    results = {}
    tracks = sorted(TRACKS_DIR.glob("*.mp3"))

    print(f"[Analyzer] Scanning {len(tracks)} tracks...\n")
    for i, track in enumerate(tracks, 1):
        print(f"[{i}/{len(tracks)}]")
        try:
            result = analyze_track(track)
            results[track.name] = result
        except Exception as e:
            print(f"  ERROR: {e}")

    return results


def get_analysis(filename):
    """Get cached analysis for a track. Returns None if not analyzed."""
    cache_file = ANALYSIS_DIR / f"{Path(filename).stem}.json"
    if cache_file.exists():
        with open(cache_file) as f:
            return json.load(f)
    return None


def compatibility(track_a, track_b):
    """
    Score how well two tracks mix together (0-1).
    Considers: BPM compatibility, key compatibility, energy contrast.
    """
    if not track_a or not track_b:
        return 0

    score = 0

    # BPM compatibility (within 5% = perfect, within 10% = okay)
    bpm_a, bpm_b = track_a['bpm'], track_b['bpm']
    bpm_diff = abs(bpm_a - bpm_b) / max(bpm_a, bpm_b)
    if bpm_diff < 0.02:
        score += 0.4  # nearly identical
    elif bpm_diff < 0.05:
        score += 0.3
    elif bpm_diff < 0.10:
        score += 0.15
    # else: 0

    # Key compatibility (Camelot wheel logic simplified)
    compatible_keys = {
        'C': ['C', 'G', 'F', 'A'],
        'G': ['G', 'C', 'D', 'E'],
        'D': ['D', 'G', 'A', 'B'],
        'A': ['A', 'D', 'E', 'F#'],
        'E': ['E', 'A', 'B', 'C#'],
        'B': ['B', 'E', 'F#', 'G#'],
        'F#': ['F#', 'B', 'C#', 'D#'],
        'C#': ['C#', 'F#', 'G#', 'A#'],
        'G#': ['G#', 'C#', 'D#', 'F'],
        'D#': ['D#', 'G#', 'A#', 'C'],
        'A#': ['A#', 'D#', 'F', 'G'],
        'F': ['F', 'A#', 'C', 'D'],
    }
    key_a = track_a.get('key_note', 'C')
    key_b = track_b.get('key_note', 'C')
    if key_b in compatible_keys.get(key_a, []):
        score += 0.3
    elif key_a == key_b:
        score += 0.3

    # Energy flow (slight contrast is good, too much is jarring)
    energy_diff = abs(track_a['avg_energy'] - track_b['avg_energy'])
    if energy_diff < 0.1:
        score += 0.2  # similar energy
    elif energy_diff < 0.25:
        score += 0.15  # gentle shift
    elif energy_diff < 0.4:
        score += 0.05  # noticeable shift

    # Same character bonus
    if track_a.get('character') == track_b.get('character'):
        score += 0.1

    return round(min(1.0, score), 2)


def suggest_next(current_filename, all_analyses=None):
    """
    Suggest the best next track based on the currently playing track.
    Returns sorted list of (filename, score, reason).
    """
    current = get_analysis(current_filename)
    if not current:
        return []

    if all_analyses is None:
        all_analyses = {}
        for f in ANALYSIS_DIR.glob("*.json"):
            with open(f) as fh:
                data = json.load(fh)
                all_analyses[data['filename']] = data

    suggestions = []
    for filename, analysis in all_analyses.items():
        if filename == current_filename:
            continue
        score = compatibility(current, analysis)
        reasons = []
        bpm_diff = abs(current['bpm'] - analysis['bpm'])
        if bpm_diff < 3:
            reasons.append(f"BPM match ({analysis['bpm']:.0f})")
        if current.get('key_note') == analysis.get('key_note'):
            reasons.append(f"same key ({analysis['key']})")
        reasons.append(f"energy: {analysis['avg_energy']:.2f}")

        suggestions.append({
            "filename": filename,
            "score": score,
            "bpm": analysis['bpm'],
            "key": analysis['key'],
            "energy": analysis['avg_energy'],
            "character": analysis.get('character', '?'),
            "reason": ", ".join(reasons),
        })

    suggestions.sort(key=lambda s: -s['score'])
    return suggestions


def live_status(filename, position_sec):
    """
    What's happening at this exact moment in the track?
    Returns current section, energy, and upcoming events.
    """
    analysis = get_analysis(filename)
    if not analysis:
        return {"section": "unknown", "energy": 0, "message": "Track not analyzed"}

    # Find current section
    current_section = "unknown"
    next_section = None
    time_to_next = None

    for i, s in enumerate(analysis['sections']):
        if s['start'] <= position_sec <= s['end']:
            current_section = s['type']
            if i + 1 < len(analysis['sections']):
                next_section = analysis['sections'][i + 1]
                time_to_next = round(s['end'] - position_sec, 1)
            break

    # Estimate current energy from position
    progress = position_sec / analysis['duration'] if analysis['duration'] > 0 else 0
    # Linear interpolation from energy summary
    energy_est = analysis['energy_summary']['mean']

    # Check proximity to mix points
    nearest_mix_out = None
    for mp in analysis.get('mix_out_points', []):
        if mp['time'] > position_sec:
            nearest_mix_out = mp
            break

    result = {
        "track": analysis['filename'],
        "position": f"{int(position_sec//60)}:{int(position_sec%60):02d}",
        "bpm": analysis['bpm'],
        "key": analysis['key'],
        "section": current_section,
        "energy": round(energy_est, 2),
        "character": analysis.get('character', '?'),
    }

    if next_section:
        result["next_section"] = next_section['type']
        result["time_to_next"] = f"{int(time_to_next//60)}:{int(time_to_next%60):02d}"

    if nearest_mix_out:
        time_to_mix = nearest_mix_out['time'] - position_sec
        result["next_mix_point"] = nearest_mix_out['time_str']
        result["time_to_mix_point"] = f"{int(time_to_mix//60)}:{int(time_to_mix%60):02d}"

    return result


# ── CLI ─────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("DJ Treta Analyzer — Musical Intelligence")
        print("  analyze <file>    — Analyze a single track")
        print("  all               — Analyze entire library")
        print("  info <file>       — Show cached analysis")
        print("  suggest <file>    — Suggest next track")
        print("  live <file> <sec> — What's happening at this moment")
        print("  compat <a> <b>    — Score compatibility between tracks")
        return

    cmd = sys.argv[1]

    if cmd == "analyze" and len(sys.argv) > 2:
        filepath = sys.argv[2]
        if not os.path.isabs(filepath):
            filepath = str(TRACKS_DIR / filepath)
        result = analyze_track(filepath, force=True)
        print(json.dumps(result, indent=2))

    elif cmd == "all":
        results = analyze_library()
        print(f"\nAnalyzed {len(results)} tracks")

    elif cmd == "info" and len(sys.argv) > 2:
        analysis = get_analysis(sys.argv[2])
        if analysis:
            print(json.dumps(analysis, indent=2))
        else:
            print("Not analyzed yet. Run: analyzer.py analyze <file>")

    elif cmd == "suggest" and len(sys.argv) > 2:
        suggestions = suggest_next(sys.argv[2])
        print(f"\nBest next tracks after {sys.argv[2][:40]}...")
        for s in suggestions[:5]:
            print(f"  {s['score']:.2f} | {s['filename'][:50]}")
            print(f"        {s['bpm']:.0f} BPM | {s['key']} | {s['character']} | {s['reason']}")

    elif cmd == "live" and len(sys.argv) > 3:
        result = live_status(sys.argv[2], float(sys.argv[3]))
        print(json.dumps(result, indent=2))

    elif cmd == "compat" and len(sys.argv) > 3:
        a = get_analysis(sys.argv[2])
        b = get_analysis(sys.argv[3])
        if a and b:
            score = compatibility(a, b)
            print(f"Compatibility: {score:.2f}")
        else:
            print("One or both tracks not analyzed")

    else:
        print(f"Unknown: {cmd}")


if __name__ == "__main__":
    main()
