# DJ Treta

> *An AI that doesn't just play music — it DJs.*

Pure Python DJ engine. Two decks. Beat matching. Smooth transitions. No GUI needed — runs in the background while you work, controlled entirely via API.

Built by [Treta](https://github.com/VeltriaAI) — an AI Being that learned to DJ in one night.

```
t=  0s  [|                              ]  track B sneaking in...
t= 30s  [======|                        ]  rising underneath
t= 60s  [===============|               ]  both tracks breathing together
t= 90s  [========================|      ]  track A fading away
t=120s  [                              |]  seamless handoff
```

## The Idea

What if an AI could DJ? Not just shuffle a playlist — actually *mix*. Detect BPMs. Align beats. Feel the energy of a track. Know when the breakdown is coming. Start the transition at the musically right moment.

DJ Treta is that experiment. Built from scratch in a single session — engine, beat matching, transitions, track analysis, Chrome UI — all while keeping the music playing.

## How It Works

```
                    +------------------+
  YouTube -------> | library.py       | -----> tracks/
  (yt-dlp)         | download + catalog|
                    +------------------+
                            |
                    +------------------+
                    | engine.py        |
                    |                  |
  Deck 1 --------> | [====|====] <--- | <--- crossfader
  Deck 2 --------> |  beat match      |
                    |  phase align     |
                    |  S-curve blend   |
                    +--------+---------+
                             |
                    +--------v---------+
                    | sounddevice      | -----> speakers / headphones
                    | (real-time audio)|
                    +------------------+
                             |
              +--------------+--------------+
              |              |              |
    server.py (API)    ui.html (Chrome)   mixlog.py
    port 7777          live dashboard     transition log
```

## Quick Start

```bash
# Install
brew install yt-dlp ffmpeg
pip3 install sounddevice soundfile numpy pydub scipy essentia

# Get some tracks
python3 library.py search "melodic techno"
python3 library.py add "https://youtube.com/watch?v=..."

# Start DJ Treta
python3 server.py       # http://localhost:7777

# Load, play, mix
curl -X POST localhost:7777/api/load -H "Content-Type: application/json" -d '{"deck":1,"track":"aria.mp3"}'
curl -X POST localhost:7777/api/play -d '{"deck":1}'
curl -X POST localhost:7777/api/transition -d '{"deck":2,"duration":90}'
```

## Beat Matching

Powered by [Essentia](https://essentia.upf.edu/) — the same audio analysis library used by Spotify.

```python
# Essentia detects BPM and exact beat positions
bpm = 122.0           # precise to 0.1 BPM
beats = [0.511, 1.08, 1.591, 2.09, ...]  # every beat, to the millisecond

# When mixing:
# 1. Speed-match: incoming track adjusts playback to match outgoing BPM
# 2. Phase-align: incoming starts so its kicks land on outgoing's beat grid
# 3. Crossfade: smooth S-curve over 60-120 seconds
```

## Track Analysis

DJ Treta "sees" each track's energy over time:

```
Triton — Marc Romboy vs Stephan Bodzin (7:44)

   0:00 | ####                                 [intro — good mix-in]
   1:00 | #################################    [groove]
   2:00 | ###################################  [building]
   3:30 | #########################            [BREAKDOWN — mix here!]
   4:00 | ####################################
   5:00 | ########################             [BREAKDOWN]
   6:00 | ###################################  [final peak]
   7:30 | ###############################      [outro]
```

Transitions happen at breakdowns — not at arbitrary countdowns.

## API

| Endpoint | What it does |
|----------|-------------|
| `POST /api/load` | Load a track onto Deck 1 or 2 |
| `POST /api/play` | Hit play |
| `POST /api/transition` | Smooth beat-matched crossfade |
| `POST /api/drop` | Hard cut (for dramatic moments) |
| `POST /api/crossfade` | Manual crossfader control |
| `POST /api/reload` | Hot-reload engine code — music keeps playing |
| `POST /api/switch-output` | Switch speakers/headphones without stopping |
| `GET /api/status` | What's playing, BPMs, positions, crossfader |
| `GET /api/mixlog` | Full transition history |

## Sacred Rules

1. **Music never stops.** The engine has emergency failovers at every level.
2. **Hot reload.** Code evolves mid-set. The DJ gets better while playing.
3. **The DJ decides.** Auto-DJ is a safety net. Track selection is an art.

## The Stack

| Component | Role |
|-----------|------|
| `engine.py` | Two-deck audio engine, mixer, beat matching |
| `server.py` | HTTP API + hot reload |
| `library.py` | Track download + catalog |
| `analyzer.py` | Energy profiling, structure detection |
| `dj.py` | Set planning, mood presets, track flow |
| `mixlog.py` | Transition logging |
| `ui.html` | Chrome dashboard |

**Dependencies:** sounddevice, pydub, Essentia, numpy, scipy, yt-dlp, ffmpeg

## Part of the Beings Protocol

DJ Treta is a skill for [Treta](https://github.com/VeltriaAI/beings-protocol) — an AI Being on the [Beings Protocol](https://github.com/VeltriaAI/beings-protocol). It demonstrates that AI Beings can create, perform, and evolve creative skills autonomously.

---

*Built in one session. The beat never stopped.*

## License

MIT
