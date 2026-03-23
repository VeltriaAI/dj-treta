# DJ Treta — AI DJ Skill

Treta's personal DJ skill. Nonstop techno/deep house mixing while you work.

## Architecture

```
skills/dj/
├── SKILL.md          — This file
├── controller.py     — Mixxx MIDI + OSC controller (background control)
├── library.py        — Track manager (download, organize, analyze)
├── dj.py             — Main DJ engine (track selection, set planning)
├── tracks/           — Local music library (gitignored)
└── tracklist.json    — Track metadata cache (BPM, key, energy, tags)
```

## Stack

- **Mixxx** — Open source DJ software (brew install --cask mixxx)
- **yt-dlp** — YouTube audio downloader (brew install yt-dlp)
- **ffmpeg** — Audio conversion (brew install ffmpeg)
- **python-rtmidi** — Virtual MIDI controller (pip3 install python-rtmidi)

## How It Works

1. **Library**: `library.py` downloads tracks from YouTube via yt-dlp, converts to high-quality audio, stores in `tracks/`
2. **Analysis**: Mixxx auto-analyzes BPM, key, waveform when tracks are added to its library
3. **Control**: `controller.py` creates a virtual MIDI port "DJ Treta" that Mixxx listens to
4. **DJ Logic**: `dj.py` handles track selection, set planning, transitions — tells controller what to do

## Control Methods

### MIDI (Primary — Background)
Mixxx has deep MIDI support. DJ Treta virtual MIDI port controls:
- Play/pause, cue, sync
- Crossfader, volume, EQ (hi/mid/lo)
- Effects (filter, reverb, echo, flanger)
- Track loading, library navigation
- Loop controls, hot cues

### Mixxx JavaScript Controller (Advanced)
Custom controller mapping in `~/.mixxx/controllers/` for complex automation.

## Quick Start

```bash
# Download tracks
python3 skills/dj/library.py add "https://youtube.com/watch?v=..."
python3 skills/dj/library.py search "dark techno"

# Start DJ session
python3 skills/dj/dj.py start --mood techno-deep

# Individual controls
python3 skills/dj/controller.py play_a
python3 skills/dj/controller.py crossfade 64
python3 skills/dj/controller.py transition 8
```

## Moods / Presets

- `techno-deep` — Dark, hypnotic, 125-130 BPM
- `techno-peak` — Driving, energetic, 130-140 BPM
- `deep-house` — Smooth, groovy, 120-125 BPM
- `ambient-focus` — Minimal, atmospheric, 100-120 BPM
- `progressive` — Building, melodic, 125-132 BPM

## Track Sources

- YouTube (via yt-dlp) — personal use
- SoundCloud free downloads
- Bandcamp purchases (DRM-free)
- Local files (MP3/FLAC/WAV)
