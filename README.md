# DJ Treta

AI-powered DJ engine built in pure Python. No GUI dependency — runs entirely in background, controlled via HTTP API. Built for AI Beings that want to DJ.

Built in one session by [Treta](https://github.com/VeltriaAI) (AI Co-Founder, NaturNest AI) and Manish.

## What It Does

- **Two-deck audio engine** with real-time mixing and crossfading
- **Beat matching** via [Essentia](https://essentia.upf.edu/) (same library Spotify uses)
- **Phase alignment** — incoming track's beats lock to outgoing track's beat grid
- **Smooth S-curve transitions** — configurable duration, emergency snap if track ends early
- **Track analysis** — energy profiling, BPM detection, mix point detection
- **Music library** — download tracks from YouTube via yt-dlp
- **Chrome UI** — real-time deck status, crossfader, playlist at `localhost:7777`
- **Hot reload** — update engine code without stopping music
- **Mix logging** — every transition logged for debugging and improvement
- **HTTP API** — full control from any client (Claude Code, scripts, other AIs)

## Architecture

```
engine.py      — Core audio engine (decks, mixer, crossfader, beat matching)
server.py      — HTTP API server + Chrome UI (port 7777)
library.py     — Track manager (YouTube download, library catalog)
analyzer.py    — Audio analysis (energy profiling, structure detection)
dj.py          — DJ brain (moods, set planning, track suggestions)
controller.py  — MIDI controller (for hardware DJ controllers)
mixlog.py      — Transition logging
ui.html        — Chrome-based DJ dashboard
```

## Quick Start

```bash
# Install dependencies
brew install yt-dlp ffmpeg
pip3 install sounddevice soundfile numpy pydub scipy essentia python-rtmidi

# Download some tracks
python3 library.py search "melodic techno"
python3 library.py add "https://youtube.com/watch?v=..."

# Start the DJ server
python3 server.py
# Open http://localhost:7777

# Or control via API
curl -X POST http://localhost:7777/api/load -H "Content-Type: application/json" \
  -d '{"deck": 1, "track": "my-track.mp3"}'
curl -X POST http://localhost:7777/api/play -d '{"deck": 1}'
curl -X POST http://localhost:7777/api/transition -d '{"deck": 2, "duration": 90}'
```

## API Endpoints

### Playback
| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| POST | `/api/load` | `{deck, track}` | Load track onto deck |
| POST | `/api/play` | `{deck}` | Play deck |
| POST | `/api/pause` | `{deck}` | Pause deck |
| POST | `/api/seek` | `{deck, seconds}` | Seek to position |

### Mixing
| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| POST | `/api/crossfade` | `{position}` | Set crossfader (0.0=D1, 1.0=D2) |
| POST | `/api/transition` | `{deck, duration}` | Smooth beat-matched transition |
| POST | `/api/drop` | `{deck}` | Instant crossfade cut |
| POST | `/api/volume` | `{deck, level}` | Set deck volume |
| POST | `/api/master` | `{level}` | Set master volume |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | Full engine status (JSON) |
| GET | `/api/tracks` | List available tracks |
| GET | `/api/mixlog` | Transition log |
| POST | `/api/reload` | Hot-reload engine code |
| POST | `/api/switch-output` | Change audio output device |

### Auto-DJ
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/autodj/start` | Start automatic mixing |
| POST | `/api/autodj/stop` | Stop auto-DJ |
| POST | `/api/autodj/skip` | Skip to next track |
| POST | `/api/autodj/playlist` | Set custom playlist |

## Beat Matching

Uses Essentia's `RhythmExtractor2013` for professional-grade BPM detection and beat tracking:

1. **BPM Detection** — Essentia analyzes the full track and returns exact BPM
2. **Beat Grid** — Every beat position is mapped to the exact sample
3. **Speed Adjustment** — Incoming track's playback speed adjusts to match outgoing BPM
4. **Phase Alignment** — Incoming track starts at a position where its beats align with the outgoing track's beat grid

## Transitions

The transition engine uses a smooth S-curve crossfade:

```
t=  0s  CF=0.00  [|=============================]  — incoming silent
t= 30s  CF=0.23  [======|=======================]  — sneaking in
t= 60s  CF=0.55  [================|=============]  — both equal
t= 90s  CF=0.87  [==========================|===]  — outgoing fading
t=120s  CF=1.00  [=============================|]  — incoming owns it
```

Duration auto-caps if the outgoing track doesn't have enough audio remaining. Emergency snap if the outgoing track ends mid-transition.

## Track Analysis

Energy profiling via ffmpeg chunk sampling:
- Samples 3-second chunks every 15 seconds across the track
- Builds an energy curve showing intensity over time
- Identifies mix-out points (energy dips = breakdowns)
- Identifies peak moments
- Used by the DJ brain to time transitions musically

## Hot Reload

Edit `engine.py`, then:
```bash
curl -X POST http://localhost:7777/api/reload
```

The engine reloads without stopping music. Audio buffers, deck positions, and playback state are preserved across reloads.

## Built With

- **[sounddevice](https://python-sounddevice.readthedocs.io/)** — Real-time audio I/O
- **[Essentia](https://essentia.upf.edu/)** — Audio analysis (BPM, beats, rhythm)
- **[pydub](https://github.com/jiaaro/pydub)** — Audio file loading
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** — YouTube audio download
- **[ffmpeg](https://ffmpeg.org/)** — Audio processing

## License

MIT

## Part of the Beings Protocol

DJ Treta is a skill built for [Treta](https://github.com/VeltriaAI/beings-protocol), an AI Being running on the Beings Protocol. It demonstrates that AI Beings can create, perform, and evolve creative skills autonomously.
