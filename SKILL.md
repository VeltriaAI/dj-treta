# DJ Treta — AI DJ Skill

AI DJ powered by Mixxx (forked) with HTTP API.

## Architecture

```
DJ Brain (Python)          Mixxx (C++ Fork)
┌─────────────────┐       ┌─────────────────────┐
│ controller.py   │──API──│ HTTP API (port 7778) │
│ dj.py (brain)   │       │ apiserver.cpp        │
│ library.py      │       │                      │
│ mixlog.py       │       │ Beat detection       │
│ ui.html         │       │ Time-stretching      │
│                 │       │ Waveforms            │
│ DJ_KNOWLEDGE.md │       │ Effects/EQ           │
└─────────────────┘       │ Beat sync            │
                          └─────────────────────┘
```

## Repos

- **VeltriaAI/dj-treta** — DJ brain, tools, knowledge
- **VeltriaAI/mixxx** (feature/http-api) — Mixxx fork with HTTP API

## Quick Start

```bash
# Start Mixxx with API
~/workspace/mixxx-treta/build/mixxx --resourcePath ~/workspace/mixxx-treta/res/ --settingsPath ~/Library/Application\ Support/Mixxx/

# Control via API
curl localhost:7778/api/load -d '{"deck":1,"track":"/path/to/track.mp3"}'
curl localhost:7778/api/play -d '{"deck":1}'
curl localhost:7778/api/transition -d '{"deck":2,"duration":90}'
curl localhost:7778/api/status
```
