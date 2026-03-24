# DJ Treta — Improvement Plan

> Audit completed 2026-03-24. From working prototype to a proper, reusable AI DJ skill.

---

## 1. Current State Assessment

### What Works

| Component | Status | Notes |
|-----------|--------|-------|
| **Mixxx HTTP API** (apiserver.cpp) | Solid | ~640 lines C++. Full deck control, EQ, effects, loops, hotcues, crossfader, track loading, sync, filter, PFL, library nav, AutoDJ, smooth transition. Well-structured, CORS enabled. |
| **Track loading by path** | Working | The killer feature. `/api/load` dispatches to main thread correctly via `QueuedConnection`. |
| **Status endpoint** | Working | `/api/status` returns comprehensive deck state: BPM, position, remaining time, EQ values, sync, loops. |
| **Track info endpoint** | Working | `/api/deck/{n}/track_info` returns metadata, beat grid, waveform summary (downsampled to 200 points), cue points. Rich data. |
| **Generic control endpoint** | Working | `/api/control` GET/POST can read/write any Mixxx ControlObject. This is the escape hatch for anything not wrapped in a dedicated endpoint. |
| **Smooth transition** (C++ side) | Working | `/api/transition` runs S-curve crossfade in a detached thread. 20fps, configurable duration. |
| **controller.py** (MIDI) | Working | Virtual MIDI port, crossfade, volume, EQ, filter, play/cue/sync, hotcues, transitions (S-curve + EQ blend). |
| **library.py** | Working | yt-dlp download, YouTube search, tracklist.json management, batch download. |
| **dj.py** | Partial | Mood presets and starter packs defined. Set planning is rudimentary (random shuffle, fit to duration). |
| **mixlog.py** | Working | Event logging with file persistence. Structured entries for transitions, loads, errors. |
| **ui.html** | Working | 1500-line single-file dashboard. Polished visuals (cyan/magenta deck colors), waveform display, deck controls, crossfader. |
| **DJ_KNOWLEDGE.md** | Excellent | 660 lines of DJ theory: phrasing, EQ mixing, harmonic mixing (Camelot), energy flow, set structure, genre BPM ranges, transition rules, error prevention. Actionable algorithm pseudocode included. |
| **Track library** | Has content | tracklist.json with tracks, `tracks/` directory with 42 audio files. |

### What's Broken or Half-Implemented

| Issue | Severity | Details |
|-------|----------|--------|
| **No DJ brain loop** | Critical | There is no autonomous loop that monitors playback, detects when to transition, selects next tracks, and executes transitions. Currently everything is manual via curl or Claude issuing commands. |
| **dj.py set planning is naive** | High | `plan_set()` does random shuffle. No harmonic compatibility check, no energy flow planning, no BPM sequencing. All the knowledge in DJ_KNOWLEDGE.md is ignored. |
| **No track analysis integration** | High | tracklist.json has `bpm: null` and `key: null` for tracks. Mixxx analyzes these on load, but there's no pipeline to read analysis results back and store them in tracklist.json. |
| **controller.py blend() has a bug** | Medium | Phase 1 crossfade target is hardcoded `0.5` regardless of `to_deck`. The conditional `0.5 if to_deck == 2 else 0.5` is always 0.5 — the crossfade doesn't actually move during Phase 1. |
| **controller.py duplicates API functionality** | Medium | MIDI-based transitions in controller.py overlap with HTTP-based transition in apiserver.cpp. Two parallel control paths, no clear ownership. |
| **No WebSocket for real-time state** | Medium | The API design in MIXXX_FORK_PLAN.md spec'd WebSocket events (position, beat, VU) but they're not implemented. Polling `/api/status` is the only option. |
| **No startup script** | Medium | Starting requires remembering a long command with `--resourcePath` and `--settingsPath`. No wrapper. |
| **tracklist.json has no energy levels** | Medium | DJ_KNOWLEDGE.md defines energy 1-10 scale. Track entries have no `energy` field. |
| **No Camelot key in tracklist** | Medium | Tracks have no Camelot code. Even if key were populated, there's no code to convert musical key to Camelot notation. |
| **`/api/tracks` only scans `~/Music`** | Low | Hardcoded path. Doesn't scan the skill's `tracks/` directory or respect any config. |
| **mixlog.py is in-memory only per session** | Low | `_log = []` resets every import. The JSON file write works, but reading previous logs on startup doesn't happen. |
| **No gain staging** | Low | No pregain matching before transitions. DJ_KNOWLEDGE.md extensively covers this. |
| **ui.html not connected to live API** | Low | Need to verify — the HTML is a static file; it likely polls `/api/status` but connection setup needs validation. |

### Duplication Between Python Engine and Mixxx API

The `_archive/python-engine/` directory was already archived, but active duplication remains:

| Capability | controller.py (MIDI) | apiserver.cpp (HTTP) | Winner |
|-----------|---------------------|---------------------|--------|
| Play/pause | MIDI note on/off | `/api/play`, `/api/pause` | HTTP (more reliable) |
| Crossfade | MIDI CC (30fps) | `/api/crossfade` | MIDI (smoother real-time) |
| EQ control | MIDI CC | `/api/eq` | HTTP (precise float values vs 0-127) |
| Volume | MIDI CC | `/api/volume` | HTTP (precise) |
| Smooth transition | `transition()` S-curve, `blend()` EQ swap | `/api/transition` S-curve only | MIDI blend is richer |
| Track loading | Not possible via MIDI | `/api/load` | HTTP (only option) |
| Status read | Not possible via MIDI | `/api/status` | HTTP (only option) |
| Filter | MIDI CC | `/api/filter` | HTTP (precise) |

**Verdict**: HTTP API should be primary for everything. MIDI's only advantage is sub-millisecond latency for real-time crossfader movement during transitions — but the C++ side `/api/transition` already runs in-process at 20fps, making even that unnecessary. controller.py can be deprecated.

### Knowledge Not Implemented in Code

DJ_KNOWLEDGE.md contains these actionable algorithms with zero code implementation:

1. **Track Selection Algorithm** (Section 9) — filter by Camelot key, BPM range, energy level, genre, artist recency, surprise factor scoring. None of this exists in dj.py.
2. **Transition Execution Rules** (Section 9) — tempo matching, gain matching, phrase-aligned start, blend type selection by energy level, EQ management sequence (bass cut → mid blend → bass swap → high fade → fader down). Only basic crossfade and a buggy EQ blend exist.
3. **Energy Flow Rules** (Section 4) — never jump >2 energy levels, create waves, peak sustainably. No energy tracking at all.
4. **Harmonic Mixing Rules** (Section 3) — Camelot wheel compatibility scoring (same key = 10/10 down to random jump = 2/10). No Camelot code anywhere in Python.
5. **Set Structure Arc** (Section 5) — opening → build → peak → cooldown → closing phases with specific energy/BPM/transition style per phase. `plan_set()` ignores all of this.
6. **Phrase-aligned transitions** — start on beat 1 of an 8-bar boundary. No beat/phrase awareness in any transition code.
7. **Genre-specific transition styles** (Section 8) — melodic techno gets 16-32 bar blends, peak techno gets 4-8 bar cuts. No genre-aware transition selection.
8. **Tension building techniques** — energy dips, breakdown extensions, filter sweeps before drops. Not implemented.
9. **Gain staging** — pregain matching before blends. Not implemented.
10. **Hot cue strategy** — mix-in point, drop point, breakdown, mix-out, vocal hook, loop point. No auto-cue placement.

### Transition Techniques: Available vs Used

| Technique | In DJ_KNOWLEDGE.md | In Code | Gap |
|-----------|-------------------|---------|-----|
| S-curve crossfade | Yes | Yes (controller.py + apiserver.cpp) | None |
| EQ bass swap | Yes (detailed) | Partial (controller.py `blend()`, buggy) | Needs proper implementation via HTTP API |
| Filter sweep (HPF/LPF) | Yes | No | `/api/filter` exists but no sweep automation |
| Echo/delay out | Yes | No | `/api/effect` exists but no echo-out sequence |
| Hard cut / instant swap | Yes | Yes (`drop()` in controller.py) | Needs HTTP equivalent |
| Double drop | Yes | No | Complex, needs phrase alignment first |
| Breakdown extension via loop | Yes | No | `/api/loop` exists but no automation |
| Kill switch (EQ band kill) | Yes | No | Could use `/api/eq` with value 0 |
| Stutter buildup (progressive loop halving) | Yes | No | `/api/loop` halve action exists |
| Acapella mixing | Yes | No | Would need stem separation |
| Building-to-drop bait-and-switch | Yes | No | Needs phrase awareness |

---

## 2. Architecture Recommendation

### Recommended: Option A — MCP Server

**The MCP server approach is the clear winner** for this use case. Here's the evaluation:

#### Option A: MCP Server (RECOMMENDED)

An MCP server wrapping the Mixxx HTTP API gives AI Beings native tool access.

**Tools to expose:**

```
# Status & Monitoring
dj_status()                          — Full mixer state (both decks, crossfader, master)
dj_deck_info(deck)                   — Detailed deck state + track metadata
dj_track_info(deck)                  — Track analysis: BPM, key, waveform, cues, beats

# Playback
dj_load(deck, path)                  — Load track by file path
dj_play(deck)                        — Start playback
dj_pause(deck)                       — Pause playback
dj_stop(deck)                        — Stop and reset to start
dj_seek(deck, position)              — Seek to position (0.0-1.0)
dj_eject(deck)                       — Eject track

# Mixing
dj_crossfade(position)               — Set crossfader (0.0=deck1, 1.0=deck2)
dj_volume(deck, level)               — Set channel volume
dj_eq(deck, hi, mid, lo)             — Set 3-band EQ
dj_filter(deck, value)               — Quick effect / filter sweep
dj_master_volume(level)              — Master output level

# Sync & Tempo
dj_sync(deck, enabled)               — Toggle sync
dj_rate(deck, value)                 — Adjust playback rate

# Transitions (high-level, DJ brain executes the sequence)
dj_transition(to_deck, duration)     — Smooth S-curve crossfade
dj_blend(to_deck, duration, style)   — EQ blend with bass swap
dj_cut(to_deck)                      — Instant cut

# Loops & Cues
dj_loop(deck, action)                — Loop control (in/out/toggle/halve/double)
dj_hotcue(deck, num, action)         — Hot cue (activate/set/clear)

# Effects
dj_effect(deck, unit, action, mix, super) — Effect unit control

# Library
dj_tracks()                          — List available tracks
dj_search(query)                     — Search YouTube for tracks
dj_download(url, tags)               — Download track from URL
dj_library()                         — Library stats (count, duration, tags)

# DJ Brain (intelligence layer)
dj_plan_set(mood, duration_min)      — Plan a set with harmonic/energy flow
dj_suggest_next()                    — Suggest next track based on current state
dj_analyze_compatibility(track_a, track_b) — Check BPM/key/energy compatibility
```

**Pros:**
- Native tool integration — any Being can call `dj_load(1, "/path/to/track.mp3")` directly
- Typed parameters with descriptions — self-documenting
- Clean separation: MCP server handles Mixxx communication, Being handles DJ decisions
- Can embed DJ knowledge (Camelot wheel, energy rules) in the intelligence tools
- Portable — any Being on the protocol can use it, not just Himani/Treta
- Can run alongside Mixxx as a single companion process

**Cons:**
- Need to build the MCP server (Python or TypeScript)
- Another process to manage

**Effort:** 2-3 days for core MCP server. 1 week for intelligence layer (DJ brain tools).

#### Option B: Python Wrapper Scripts

**Pros:** Simple, works now.
**Cons:** No native tool integration. Every call goes through `python3 -c "..."` in bash. No type safety, no discoverability. Error handling is poor. The Being has to know Python syntax.
**Verdict:** Not worth investing in. If building Python anyway, build an MCP server instead.

#### Option C: HTTP API only (current)

**Pros:** Already working. Direct curl commands.
**Cons:** Every interaction requires constructing curl commands. Verbose, error-prone. No intelligence layer — the Being has to do all DJ reasoning inline. No state management between calls.
**Verdict:** Good for debugging, not for autonomous DJ operation.

### Implementation Approach

```
┌─────────────────────────────────────────────────────────┐
│ AI Being (Treta / any Being)                            │
│   Uses MCP tools: dj_status, dj_load, dj_blend, etc.   │
└──────────────────────┬──────────────────────────────────┘
                       │ MCP protocol (stdio)
┌──────────────────────▼──────────────────────────────────┐
│ DJ Treta MCP Server (Python)                            │
│                                                         │
│ ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│ │ Mixxx Client│  │ DJ Brain     │  │ Library Mgr    │  │
│ │ (HTTP calls)│  │ (Camelot,    │  │ (tracks, tags, │  │
│ │             │  │  energy,     │  │  download,     │  │
│ │             │  │  phrasing,   │  │  analysis)     │  │
│ │             │  │  transitions)│  │                │  │
│ └─────────────┘  └──────────────┘  └────────────────┘  │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP (localhost:7778)
┌──────────────────────▼──────────────────────────────────┐
│ Mixxx (fork) with HTTP API                              │
│ apiserver.cpp — full deck/mixer/library/effects control  │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Priority List

### P0 — Critical (blocks autonomous DJ operation)

| # | Item | What | Effort |
|---|------|------|--------|
| P0.1 | **Build MCP server skeleton** | Python MCP server wrapping Mixxx HTTP API. Start with status, load, play, pause, crossfade, EQ, volume tools. | 1 day |
| P0.2 | **Track analysis pipeline** | After loading a track, read BPM/key from `/api/deck/{n}/track_info` and write back to tracklist.json. Build `dj_analyze_library()` tool that loads each unanalyzed track, waits for Mixxx analysis, reads results. | 1 day |
| P0.3 | **Camelot key system** | Implement Camelot wheel: musical key to Camelot code conversion, compatibility scoring function. Add `camelot_key` field to track entries. | 0.5 day |
| P0.4 | **Energy level tagging** | Add `energy` field (1-10) to track entries. Initially manual/heuristic (map BPM range + genre tags to energy). Later: analysis-based. | 0.5 day |
| P0.5 | **Smart track selection** | Implement the Track Selection Algorithm from DJ_KNOWLEDGE.md Section 9: filter by compatible key, BPM range, energy delta, genre, artist recency. Score and rank candidates. | 1 day |
| P0.6 | **Proper EQ blend transition** | Implement the full Transition Execution Rules from DJ_KNOWLEDGE.md: gain match → phrase-aligned start → bass-cut incoming → mid blend → bass swap at boundary → high fade → fader down. Via HTTP API, not MIDI. | 1 day |
| P0.7 | **Startup script** | Single `./start.sh` that launches Mixxx with correct flags + MCP server. Verify Mixxx API is responding before proceeding. | 0.5 day |

**Total P0: ~5.5 days**

### P1 — Important (quality and intelligence)

| # | Item | What | Effort |
|---|------|------|--------|
| P1.1 | **Set planning with energy arc** | Replace random shuffle with arc-aware planning: opening → build → peak → cooldown → close. Use genre-specific BPM ranges and transition styles per phase. | 1 day |
| P1.2 | **Filter sweep transition** | Implement HPF/LPF sweep automation: gradually open filter on incoming, close on outgoing, snap both off at drop. Use `/api/filter`. | 0.5 day |
| P1.3 | **Echo/delay out transition** | Apply echo effect to outgoing track, cut channel, let echoes trail off. Use `/api/effect`. | 0.5 day |
| P1.4 | **Hard cut with echo** | Combine instant crossfade cut with echo tail on outgoing track. High-energy transition option. | 0.25 day |
| P1.5 | **WebSocket real-time state** | Add WebSocket server to Mixxx fork for position/beat/VU push events. Eliminates polling. | 2 days |
| P1.6 | **Phrase detection** | Detect phrase boundaries using beat grid + track position. Enable phrase-aligned transition timing ("start blend at next 8-bar boundary"). | 1 day |
| P1.7 | **Gain staging** | Before each transition, read VU meters or waveform loudness, adjust pregain to match perceived levels between decks. | 0.5 day |
| P1.8 | **Deprecate controller.py** | Remove MIDI dependency. All control goes through HTTP API. Keep controller.py in `_archive/` for reference. | 0.5 day |
| P1.9 | **Fix `/api/tracks` path** | Make it scan configurable directories (at minimum the skill's `tracks/` folder) instead of hardcoded `~/Music`. | 0.25 day |
| P1.10 | **Transition history + learning** | Log every transition outcome (smooth/clash). Over time, build a compatibility matrix weighted by actual results, not just theory. | 1 day |

**Total P1: ~7.5 days**

### P2 — Nice-to-Have (advanced features, polish)

| # | Item | What | Effort |
|---|------|------|--------|
| P2.1 | **Auto-cue placement** | After analysis, set hot cues per DJ_KNOWLEDGE.md strategy: mix-in, drop, breakdown, mix-out, vocal hook, loop point. Use waveform + beat data. | 2 days |
| P2.2 | **Loop-based tension building** | Automate the "stutter buildup" pattern: loop 8 → 4 → 2 → 1 bars before a drop. | 0.5 day |
| P2.3 | **Kill switch patterns** | Rhythmic bass kill/restore every 4 bars for tension. Bass kill → 8 bars → restore for impact. | 0.5 day |
| P2.4 | **Double drop support** | Detect compatible drop points on two tracks, align them, EQ-split frequencies, hit both drops simultaneously. | 2 days |
| P2.5 | **Live UI dashboard** | Upgrade ui.html to connect to MCP server or directly to Mixxx API. Show current set plan, energy curve, next track suggestion, transition type. | 2 days |
| P2.6 | **SoundCloud support** | library.py already uses yt-dlp which supports SoundCloud. Validate and document. | 0.25 day |
| P2.7 | **Stem separation** | Integrate Demucs or similar for isolating vocals/drums/bass/melody. Enables acapella mixing. | 3 days |
| P2.8 | **Autonomous DJ daemon** | A long-running process that monitors playback, automatically transitions when current track approaches outro, maintains energy arc autonomously. The "full autopilot" mode. | 3 days |
| P2.9 | **BPM transition strategy** | Implement the rules: small BPM delta = blend with rate adjust, medium = gradual tempo shift, large = hard cut only. | 0.5 day |
| P2.10 | **Surprise track injection** | Every 5-8 tracks, boost score for genre-bending or unexpected selections. Per DJ_KNOWLEDGE.md Section 4. | 0.5 day |

**Total P2: ~14.25 days**

---

## 4. Specific Code Changes

### 4.1 New File: `mcp_server.py` (P0.1)

MCP server using the Python MCP SDK (`mcp` package). Structure:

```python
# mcp_server.py — DJ Treta MCP Server
# Wraps Mixxx HTTP API as MCP tools for any AI Being

from mcp.server import Server
from mcp.types import Tool, TextContent
import httpx  # async HTTP client

MIXXX_API = "http://localhost:7778"
app = Server("dj-treta")

@app.tool()
async def dj_status() -> str:
    """Get full mixer status — both decks, crossfader, master volume."""
    ...

@app.tool()
async def dj_load(deck: int, path: str) -> str:
    """Load a track file onto a deck."""
    ...

# ... (all tools listed in architecture section)
```

### 4.2 New File: `camelot.py` (P0.3)

```python
# Camelot wheel: key conversion and compatibility scoring

CAMELOT_MAP = {
    "Ab minor": "1A", "B major": "1B",
    "Eb minor": "2A", "F# major": "2B",
    # ... all 24 keys
}

def to_camelot(key_text: str) -> str: ...
def compatibility_score(key_a: str, key_b: str) -> int: ...  # 0-10
def compatible_keys(key: str) -> list[str]: ...  # safe zone keys
```

### 4.3 New File: `brain.py` (P0.5, P0.6, P1.1)

The DJ intelligence layer. Replaces the naive logic in dj.py:

```python
# brain.py — DJ decision engine
# Implements: track selection, transition choice, set planning, energy management

class DJBrain:
    def suggest_next(self, current_track, played_tracks, target_energy, library) -> list[Track]
    def choose_transition(self, track_a, track_b, current_energy) -> TransitionPlan
    def plan_set(self, mood, duration_min, library) -> SetPlan
    def check_compatibility(self, track_a, track_b) -> CompatibilityReport
```

### 4.4 Fix: `controller.py` blend() Phase 1 bug (P1.8 — or just archive)

Line 189: `self.crossfade(0.5 if to_deck == 2 else 0.5)` — both branches return 0.5.

If keeping controller.py, fix to:
```python
# Phase 1: gradually move crossfader toward center
start_pos = 0.0 if to_deck == 2 else 1.0
target_pos = 0.5
pos = start_pos + (target_pos - start_pos) * r
self.crossfade(pos)
```

But recommendation is to archive controller.py entirely (P1.8) and implement richer transitions via HTTP in brain.py.

### 4.5 New File: `transitions.py` (P0.6, P1.2, P1.3, P1.4)

Async transition executors that sequence HTTP API calls:

```python
async def eq_blend(client, to_deck, duration, bpm):
    """Full EQ blend: bass cut → mid blend → bass swap → high fade → fader down"""
    ...

async def filter_sweep(client, to_deck, duration):
    """HPF on incoming, LPF on outgoing, snap both off at boundary"""
    ...

async def echo_out(client, from_deck, to_deck):
    """Apply echo to outgoing, cut, let trail off"""
    ...

async def hard_cut(client, to_deck):
    """Instant crossfade cut"""
    ...
```

### 4.6 Modify: `apiserver.cpp` — Fix `/api/tracks` (P1.9)

Change the hardcoded `~/Music` scan to accept a query parameter for directory, defaulting to multiple paths:

```cpp
svr.Get("/api/tracks", [](const httplib::Request& req, httplib::Response& res) {
    QStringList searchDirs;
    auto dirParam = QString::fromStdString(req.get_param_value("dir"));
    if (!dirParam.isEmpty()) {
        searchDirs << dirParam;
    } else {
        searchDirs << QDir::homePath() + "/Music";
        // Add more default paths as needed
    }
    // ... scan all dirs
});
```

### 4.7 New File: `start.sh` (P0.7)

```bash
#!/bin/bash
# DJ Treta — Start everything

MIXXX_DIR=~/workspace/mixxx-treta
SKILL_DIR=$(dirname "$0")

echo "Starting Mixxx..."
"$MIXXX_DIR/build/mixxx" \
    --resourcePath "$MIXXX_DIR/res/" \
    --settingsPath ~/Library/Application\ Support/Mixxx/ &
MIXXX_PID=$!

echo "Waiting for API..."
until curl -s http://localhost:7778/api/status > /dev/null 2>&1; do
    sleep 1
done
echo "Mixxx API ready on :7778"

echo "Starting MCP server..."
python3 "$SKILL_DIR/mcp_server.py" &
MCP_PID=$!

echo "DJ Treta ready. Mixxx PID=$MIXXX_PID, MCP PID=$MCP_PID"
wait
```

### 4.8 Modify: tracklist.json schema (P0.2, P0.3, P0.4)

Add fields to each track entry:

```json
{
    "title": "...",
    "artist": "...",
    "bpm": 128.0,
    "key": "Am",
    "camelot_key": "8A",
    "energy": 7,
    "duration": 420,
    "genre": "techno",
    "file": "/path/to/track.mp3",
    "analyzed": true,
    "mix_in_bar": 1,
    "mix_out_bar": 200,
    "drop_bar": 32
}
```

---

## 5. Effort Summary

| Priority | Items | Total Effort | Cumulative |
|----------|-------|-------------|-----------|
| **P0** (Critical) | 7 items | ~5.5 days | 5.5 days |
| **P1** (Important) | 10 items | ~7.5 days | 13 days |
| **P2** (Nice-to-have) | 10 items | ~14.25 days | 27.25 days |

### Recommended Execution Order

**Week 1** (P0 — get autonomous DJ working):
1. P0.7 — Startup script (quick win, unblocks everything)
2. P0.1 — MCP server skeleton (core infrastructure)
3. P0.2 — Track analysis pipeline (populates BPM/key data)
4. P0.3 — Camelot key system (enables harmonic mixing)
5. P0.4 — Energy level tagging (enables energy flow)
6. P0.5 — Smart track selection (the DJ brain's core decision)
7. P0.6 — Proper EQ blend transition (sounds professional)

**Week 2** (P1 — quality and depth):
1. P1.8 — Deprecate controller.py (clean up confusion)
2. P1.1 — Set planning with energy arc
3. P1.2 + P1.3 + P1.4 — Additional transition types
4. P1.6 — Phrase detection
5. P1.7 — Gain staging
6. P1.9 — Fix /api/tracks path
7. P1.10 — Transition history

**Week 3+** (P2 — advanced):
- P2.8 — Autonomous daemon (the ultimate goal)
- P2.1 — Auto-cue placement
- P2.5 — Live UI dashboard
- Everything else as time permits

---

## 6. Gap: Current Cron-Based DJ vs Proper Autonomous DJ Brain

The current approach requires a Being (or human) to manually issue commands:
1. "Load this track on deck 1"
2. "Play deck 1"
3. (Wait, monitor via `/api/status`)
4. "Load next track on deck 2"
5. "Transition to deck 2 over 60 seconds"
6. Repeat

A proper autonomous DJ brain would:

1. **Initialize**: Load library, verify all tracks analyzed (BPM, key, energy)
2. **Plan**: Given mood/duration, generate a set list using the track selection algorithm
3. **Monitor**: Poll `/api/status` (or listen via WebSocket) at ~2Hz to track playback position
4. **Decide**: When remaining time on current track reaches the transition window (based on outro detection or a threshold like 90 seconds remaining), prepare the transition
5. **Prepare**: Load next track, gain-match, enable sync, verify BPM/key compatibility one more time
6. **Execute**: At the next phrase boundary, begin the chosen transition type (blend/sweep/cut based on energy level and genre)
7. **Clean up**: After transition completes, eject the old track, log the event
8. **Adapt**: If the set plan needs adjustment (e.g., energy seems wrong, track doesn't sound right), re-evaluate and swap

This is the P2.8 autonomous daemon — the ultimate milestone. Everything in P0 and P1 builds the components that make this possible.

---

## 7. Files to Create/Modify

| Action | File | Priority |
|--------|------|----------|
| Create | `skills/dj/mcp_server.py` | P0.1 |
| Create | `skills/dj/camelot.py` | P0.3 |
| Create | `skills/dj/brain.py` | P0.5 |
| Create | `skills/dj/transitions.py` | P0.6 |
| Create | `skills/dj/start.sh` | P0.7 |
| Modify | `skills/dj/library.py` — add analysis pipeline, energy tagging | P0.2, P0.4 |
| Modify | `skills/dj/tracklist.json` — schema additions | P0.2-P0.4 |
| Modify | `skills/dj/SKILL.md` — update architecture, add MCP tool docs | P0.1 |
| Archive | `skills/dj/controller.py` → `_archive/` | P1.8 |
| Modify | `mixxx-treta/src/api/apiserver.cpp` — fix `/api/tracks`, add WebSocket | P1.5, P1.9 |
| Modify | `skills/dj/dj.py` — replace naive planning or redirect to brain.py | P1.1 |
| Modify | `skills/dj/ui.html` — connect to live state, show set plan | P2.5 |

## Future Vision: DJ Treta Live

**Concept:** Live streaming AI DJ that takes audience requests, analyzes compatibility, and mixes them in real-time.

**Stack:**
- Frontend: React/Next.js live page with requests, chat, waveform viz
- Audio streaming: Mixxx built-in Icecast/Shoutcast broadcasting
- DJ Brain: Evaluates requests vs current set (BPM, key, energy flow)
- Audience interaction: vote on energy direction, request songs, chat with DJ

**Features:**
- Song request → AI evaluates fit → accepts/queues/declines with reason
- Live waveform visualization
- Audience energy voting
- DJ Treta responds to crowd in chat
- Request queue with estimated play time

**Priority:** P3 (after MCP server + DJ brain are solid)

## Energy Meter & Set Graph

**Concept:** Track energy level (1-10) for every track played. Plot it over time to visualize the set's arc. Use it to predict crowd feel and decide next move.

**Implementation:**
- Each track gets an energy rating when loaded (from Mixxx analysis: RMS loudness → normalized to 1-10)
- Set history stored: [{track, energy, timestamp, technique_used}]
- Graph rendered in UI (energy vs time, with track names on x-axis)
- DJ brain rules:
  - After 3+ tracks at energy 8-9: must dip to 5-6
  - After a dip: can build back up (never jump >2 levels at once)
  - Peak moments (energy 9-10) limited to 2-3 tracks max
  - Opening: start at 3-4, build gradually
  - Closing: come down from peak to 5-6 over last 3 tracks

**MCP Tools:**
- `dj_energy_graph` — returns ASCII/data of energy over the current set
- `dj_suggest_energy` — recommends up/down/hold based on current arc
- `dj_rate_energy` — manually rate a track's energy (override auto-detection)

**Priority:** P1 (after MCP server is connected)
