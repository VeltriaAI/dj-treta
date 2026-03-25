# DJ Treta — AI DJ Skill

> Read this file before every session. It's the complete guide for any AI Being to use this skill.

## What This Is

DJ Treta is an AI DJ system. Three components work together:

| Component | Repo | What it does |
|-----------|------|-------------|
| **Mixxx Fork** | `VeltriaAI/mixxx` (branch: `feature/http-api`) | C++ DJ software with HTTP API — handles ALL audio |
| **DJ Treta Being** | `VeltriaAI/dj-treta-being` | Autonomous brain (smolagents + Gemini) — picks tracks, decides transitions, self-improves |
| **DJ Treta Skill** (this repo) | `VeltriaAI/dj-treta` | MCP server + DJ knowledge + library tools + Chrome UI |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  AI Being (Claude / any MCP client)                                 │
│  "play something darker" / "how's the energy?" / "skip this"       │
└──────────┬──────────────────────────────────────────────────────────┘
           │ MCP tools (28 tools)
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  MCP Server (TypeScript, stdio)         mcp-server/src/index.ts     │
│  dj_talk → command queue → brain        dj_status → Mixxx API      │
│  dj_load_track, dj_transition, etc.     dj_search_youtube → yt-dlp │
└──────────┬─────────────────────┬────────────────────────────────────┘
           │                     │
     ┌─────▼─────┐        ┌─────▼──────────────────────────────────┐
     │ DJ Brain   │        │ Mixxx Fork (C++)        port 7778     │
     │ (Gemini)   │──HTTP──│ apiserver.cpp                         │
     │ daemon.py  │        │ Beat detection, time-stretching       │
     │ smolagents │        │ Waveforms, EQ, effects, sync          │
     │            │        │ PortAudio → speakers/headphones        │
     └────────────┘        └───────────────────────────────────────┘
```

## Two Ways to DJ

### 1. Direct Control (MCP tools → Mixxx)
You control everything yourself via MCP tools. No brain needed.

```
dj_status           → see what's playing
dj_list_tracks      → browse library
dj_load_track       → load a track on a deck
dj_play             → hit play
dj_transition       → smooth crossfade (blend / bass_swap / filter_sweep)
dj_eq / dj_filter   → shape the sound
```

### 2. Autonomous Brain (MCP → Brain → Mixxx)
The Gemini brain DJs autonomously. You talk to it, it decides and acts.

```
dj_agent_start      → start the brain daemon
dj_talk             → "go darker" / "what are you feeling?" / "build energy"
dj_mood             → change the set mood
dj_agent_status     → check what the brain is doing
dj_agent_stop       → stop the brain
```

## Starting Everything

### Step 1: Start Mixxx
```bash
~/workspace/mixxx-treta/build/mixxx \
  --resourcePath ~/workspace/mixxx-treta/res/ \
  --settingsPath ~/Library/Application\ Support/Mixxx/
```
Wait for GUI to appear. API is ready when `curl localhost:7778/api/status` responds.

Audio output is configured in Mixxx Preferences → Sound Hardware → Output → Master.

### Step 2 (Optional): Start the Brain
```bash
cd ~/beings/dj-treta
source .venv/bin/activate
python -m agent --mood melodic-techno --duration 60
```
Requires SSH tunnel to LiteLLM: `ssh -L 4000:localhost:4000 epadmin@20.235.125.250`

Or use `dj_agent_start` MCP tool (spawns daemon from MCP server).

### Step 3: DJ!
Use MCP tools directly, or talk to the brain via `dj_talk`.

## MCP Tools Reference

### Deck Controls
| Tool | Description |
|------|-------------|
| `dj_status` | Full status — both decks, crossfader, BPM, key, remaining time |
| `dj_load_track` | Load a track file onto a deck (1 or 2) |
| `dj_play` | Start playback |
| `dj_pause` | Pause playback |
| `dj_stop` | Stop and rewind to beginning |
| `dj_eject` | Eject track from deck |
| `dj_volume` | Set deck volume (0.0–1.0) |
| `dj_crossfade` | Set crossfader position (0.0 = Deck 1, 1.0 = Deck 2) |
| `dj_eq` | Set EQ bands (hi/mid/lo, 0.0–4.0, neutral = 1.0) |
| `dj_filter` | Quick effect filter (0.0 = HPF, 0.5 = neutral, 1.0 = LPF) |
| `dj_sync` | Enable beat sync on a deck |

### Transitions
| Tool | Description |
|------|-------------|
| `dj_transition` | Smooth crossfade — techniques: `blend` (S-curve), `bass_swap` (EQ swap), `filter_sweep` (HPF reveal) |

### Track Analysis
| Tool | Description |
|------|-------------|
| `dj_analyze_track` | Get BPM, key, position, duration for loaded track |
| `dj_suggest_next` | Suggest harmonically compatible tracks (Camelot wheel) |

### Library & Discovery
| Tool | Description |
|------|-------------|
| `dj_list_tracks` | List all tracks organized by genre folder |
| `dj_search_youtube` | Search YouTube for tracks to download |
| `dj_download_track` | Download from YouTube into library (by genre folder) |

### Set Management
| Tool | Description |
|------|-------------|
| `dj_set_history` | Tracks played in this session with timestamps |
| `dj_energy_arc` | Energy level over the set |
| `dj_save_set` | Save set history to JSON |
| `dj_record` | Start/stop/status of Mixxx recording |

### Perception (Listening)
| Tool | Description |
|------|-------------|
| `dj_listen` | Raw real-time data — VU meters, beats, crossfader |
| `dj_feel` | Musical perception — energy, mood, tension, transition readiness |

### Brain Communication
| Tool | Description |
|------|-------------|
| `dj_talk` | Two-way conversation with the Gemini brain — say anything, she responds and acts |
| `dj_mood` | Change the set mood (dark-techno, melodic-techno, deep, progressive, etc.) |
| `dj_agent_start` | Start the autonomous brain daemon |
| `dj_agent_stop` | Stop the brain daemon |
| `dj_agent_status` | Check brain state — phase, current track, tracks played |

## Music Library

Location: `~/Music/DJTreta/` — organized by genre folders:

```
~/Music/DJTreta/
├── dark-techno/      Charlotte de Witte, Amelie Lens, Argy, Enrico Sangiuliano
├── deep/             Kiasmos, Moderat, Aria, Triton, Jon Hopkins, Nils Frahm
├── melodic-techno/   Adriatique, Colyn, ARTBAT, Recondite, Bodzin, Massano
├── minimal/          Boris Brejcha, MRAK
├── progressive/      Mind Against, Innellea, Agents Of Time, Bicep
├── psychill/         Shpongle, Tycho, Carbon Based Lifeforms, Ott
└── vocal/            Anyma, Ben Böhmer, CamelPhat, Jan Blomqvist, Monolink
```

To add tracks: use `dj_search_youtube` → `dj_download_track` with genre folder.

## Mixxx HTTP API (port 7778)

The full API reference — for when you need to go beyond MCP tools.

### Real-time
- `GET /api/live` — VU meters, beat_active, beat_distance, crossfader (poll at 10Hz)
- `GET /api/status` — full deck state (BPM, position, duration, remaining, EQ, sync, loops)
- `GET /api/deck/:id` — single deck detailed
- `GET /api/deck/:id/track_info` — deep metadata: title, artist, BPM, key, waveform (200pts), cue points, beat grid

### Deck Controls
- `POST /api/load` `{deck, track}` — load by file path
- `POST /api/play` / `pause` / `stop` / `eject` `{deck}`
- `POST /api/seek` `{deck, position}` — 0.0–1.0
- `POST /api/volume` `{deck, level}`

### Mixing
- `POST /api/crossfade` `{position}` — 0–1 mapped to Mixxx -1/+1
- `POST /api/eq` `{deck, hi?, mid?, lo?}`
- `POST /api/filter` `{deck, value}` — 0.0–1.0 (0.5=neutral)
- `POST /api/transition` `{deck, duration}` — server-side S-curve at 20fps

### Sync & BPM
- `POST /api/sync` / `sync_off` `{deck}`
- `POST /api/rate` `{deck, rate}` — pitch -1.0 to 1.0

### Loops & Cues
- `POST /api/loop` `{deck, action}` — in/out/toggle/halve/double
- `POST /api/hotcue` `{deck, num, action}` — activate/set/clear (1-8)

### Effects & Other
- `POST /api/effect` `{deck, unit, action, mix?, super?}`
- `POST /api/autodj` `{action}` — enable/disable/skip/fade_now
- `POST /api/pfl` `{deck, enabled}` — headphone cue
- `POST /api/library` `{action}` — navigate Mixxx library UI
- `GET /api/tracks` — list audio files from ~/Music
- `GET/POST /api/control` — generic read/write ANY Mixxx control (escape hatch)

### Master
- `POST /api/master` `{level}` — master volume

## Brain (DJ Treta Being)

The autonomous brain lives at `~/beings/dj-treta/` (repo: `VeltriaAI/dj-treta-being`).

### State Machine
```
STARTING → PLAYING → PREPARING → TRANSITIONING → PLAYING (loop)
                                                      ↓
                                                   RECOVERY → restart Mixxx → PLAYING
                                                      ↓
                                                   STOPPED (if unrecoverable)
```

### Brain Capabilities (smolagents tools)
- **DJ controls**: load, play, pause, EQ, filter, crossfade, sync, volume
- **Music discovery**: YouTube search + download
- **Library**: list tracks, set history
- **Self-awareness**: read/write own code, config, identity files
- **Self-improvement**: save learnings, recall past learnings, run shell commands
- **Perception**: real-time Mixxx data (VU, beats, position)

### Command Queue
External control via `/tmp/dj-treta-command.json`:
```json
{"command": "talk", "args": {"message": "go darker, I want some Charlotte de Witte energy"}}
{"command": "change_mood", "args": {"mood": "dark-techno"}}
{"command": "skip", "args": {}}
{"command": "transition_now", "args": {"technique": "bass_swap", "duration": 45}}
{"command": "extend_set", "args": {"minutes": 30}}
{"command": "stop", "args": {}}
```

State written to `/tmp/dj-treta-state.json` (read by MCP `dj_agent_status`).

### Config (`config.yaml`)
```yaml
mixxx:
  url: "http://localhost:7778"
llm:
  model: "openai/gemini-3-flash"
  api_base: "http://localhost:4000"
  api_key: "sk-litellm-vertex-serra-2026"
library:
  music_dir: "~/Music/DJTreta"
transitions:
  lookahead_seconds: 120
  default_duration: 60
daemon:
  poll_hz: 2
  max_errors: 10
```

## DJ Knowledge

`DJ_KNOWLEDGE.md` contains comprehensive DJ theory:
1. Track structure & phrasing (beats, bars, phrases, sections)
2. Mixing techniques (EQ mixing, filter transitions, bass swaps)
3. Harmonic mixing & Camelot wheel
4. Track selection theory
5. Set structure & energy flow
6. Creative techniques
7. Genre-specific knowledge (BPM ranges, transition styles)
8. Actionable rules for AI DJ (algorithms, decision trees)

## Sacred Rules

1. **Music never stops.** Emergency failovers at every level. Daemon auto-restarts Mixxx on crash.
2. **The DJ has taste.** Track selection is an art, not random shuffle. BPM, key, energy, genre all matter.
3. **Transitions are musical.** Start at breakdowns, align to phrases, use appropriate technique per genre.
4. **Self-improvement.** The brain saves learnings, reads its own code, evolves between sets.

## File Structure

```
dj-treta/                          (this repo — VeltriaAI/dj-treta)
├── SKILL.md                       ← YOU ARE HERE — read this first
├── README.md                      — Public-facing project description
├── DJ_KNOWLEDGE.md                — Comprehensive DJ theory (660+ lines)
├── IMPROVEMENT_PLAN.md            — Audit and improvement roadmap
├── MIXXX_FORK_PLAN.md             — Mixxx fork architecture plan
├── mcp-server/                    — TypeScript MCP server
│   ├── src/index.ts               — All 28 MCP tools
│   ├── src/mixxx-client.ts        — HTTP client for Mixxx API
│   └── src/camelot.ts             — Camelot wheel key compatibility
├── controller.py                  — MIDI + HTTP controller (rtmidi)
├── listener.py                    — 10Hz perception engine (energy, mood, breakdowns)
├── dj.py                          — Mood presets, set planning
├── library.py                     — Track download/catalog (yt-dlp)
├── mixlog.py                      — Transition event logger
├── ui.html                        — Chrome dashboard (46KB)
├── tracklist.json                 — Track metadata cache
├── tracks/                        — Downloaded tracks (gitignored)
├── sets/                          — Saved set histories
├── analysis/                      — Track analysis profiles
└── _archive/python-engine/        — Old pure-Python audio engine (deprecated)
```
