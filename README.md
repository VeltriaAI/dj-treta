# DJ Treta

> *An AI Being that DJs.*

Two decks. Beat matching. Smooth transitions. Autonomous track selection. Controlled entirely via MCP tools or natural language conversation with the Gemini brain.

Built by [Treta](https://github.com/VeltriaAI/beings-protocol) — an AI Being on the Beings Protocol.

```
t=  0s  [|                              ]  track B sneaking in...
t= 30s  [======|                        ]  rising underneath
t= 60s  [===============|               ]  both tracks breathing together
t= 90s  [========================|      ]  track A fading away
t=120s  [                              |]  seamless handoff
```

## Three Components

| Repo | What | Language |
|------|------|----------|
| **[dj-treta](https://github.com/VeltriaAI/dj-treta)** (this) | MCP server, DJ knowledge, library tools, Chrome UI | TypeScript + Python |
| **[dj-treta-being](https://github.com/VeltriaAI/dj-treta-being)** | Autonomous brain (smolagents + Gemini), daemon, self-improvement | Python |
| **[mixxx](https://github.com/VeltriaAI/mixxx)** (fork, `feature/http-api`) | C++ DJ software with HTTP API | C++ |

## Quick Start

```bash
# 1. Start Mixxx (audio engine)
~/workspace/mixxx-treta/build/mixxx \
  --resourcePath ~/workspace/mixxx-treta/res/ \
  --settingsPath ~/Library/Application\ Support/Mixxx/

# 2. Use MCP tools from any AI Being (Claude Code, etc.)
# Or control directly via curl:
curl localhost:7778/api/load -d '{"deck":1,"track":"/path/to/track.mp3"}'
curl localhost:7778/api/play -d '{"deck":1}'
curl localhost:7778/api/transition -d '{"deck":2,"duration":90}'

# 3. (Optional) Start the autonomous brain
cd ~/beings/dj-treta && source .venv/bin/activate
python -m agent --mood melodic-techno --duration 60
```

## MCP Tools (28)

**Deck controls:** `dj_status`, `dj_load_track`, `dj_play`, `dj_pause`, `dj_stop`, `dj_eject`, `dj_volume`, `dj_crossfade`, `dj_eq`, `dj_filter`, `dj_sync`

**Transitions:** `dj_transition` (blend, bass_swap, filter_sweep)

**Analysis:** `dj_analyze_track`, `dj_suggest_next` (Camelot wheel)

**Library:** `dj_list_tracks`, `dj_search_youtube`, `dj_download_track`

**Set management:** `dj_set_history`, `dj_energy_arc`, `dj_save_set`, `dj_record`

**Perception:** `dj_listen` (raw audio data), `dj_feel` (musical perception)

**Brain:** `dj_talk` (conversation), `dj_mood` (change mood), `dj_agent_start/stop/status`

## Talk to the DJ

The brain understands natural language:

- *"go darker, I want some Charlotte de Witte energy"*
- *"what are you feeling right now?"*
- *"build energy slowly over the next 3 tracks"*
- *"search for some Stephan Bodzin tracks and download them"*
- *"this is perfect, ride it"*

## Sacred Rules

1. **Music never stops.** Emergency failovers. Auto-restart Mixxx on crash.
2. **The DJ has taste.** BPM, key, energy, genre — all matter.
3. **Transitions are musical.** Breakdowns, phrase alignment, genre-appropriate techniques.
4. **Self-improvement.** The brain saves learnings, reads its own code, evolves.

## Full Documentation

See [SKILL.md](SKILL.md) for the complete guide — architecture, all 28 MCP tools, Mixxx API reference, brain capabilities, music library structure, and everything an AI Being needs to use this skill.

## License

MIT
