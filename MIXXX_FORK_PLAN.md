# Mixxx Fork Plan — DJ Treta HTTP API

Research document for adding an HTTP/WebSocket API to Mixxx for AI-driven DJ control.

---

## 1. Mixxx Architecture Overview

### Source Structure

```
mixxx/src/
├── control/          — ControlObject system (the internal API — key/value pairs)
├── controllers/      — MIDI, HID, keyboard controller support
│   └── scripting/    — QJSEngine-based JavaScript controller scripts (ES7)
├── engine/           — Audio engine (real-time thread)
│   ├── enginebuffer.cpp    — Per-deck playback buffer (seek, play, rate)
│   ├── enginemixer.cpp     — Main mixing engine
│   ├── enginexfader.cpp    — Crossfader math
│   ├── controls/           — BPM, rate, cue, loop, key, quantize controls
│   ├── bufferscalers/      — Time-stretching (RubberBand, SoundTouch, linear)
│   ├── sync/               — Beat sync / tempo sync
│   ├── sidechain/          — Broadcast (Shoutcast), recording, network stream
│   └── filters/            — Audio filters (Moog ladder, etc.)
├── mixer/            — Player management (Deck, Sampler, PreviewDeck, Microphone)
├── analyzer/         — Track analysis (beat detection, key detection, waveform, loudness)
│   └── plugins/      — Queen Mary (beats/key), SoundTouch (beats), KeyFinder
├── effects/          — Effects framework (EQ, filter, flanger, phaser, echo, reverb)
├── library/          — Track library, playlists, crates, AutoDJ
│   └── autodj/       — AutoDJ processor (automatic transitions)
├── soundio/          — Audio I/O backends (PortAudio primary, network stream)
├── waveform/         — Waveform rendering and display
├── network/          — HTTP status codes, JSON web tasks (for MusicBrainz, not for control)
├── qml/              — New QML-based UI (replacing legacy widget skins)
├── skin/             — Legacy XML skin system
├── coreservices.cpp  — Service initialization (engine, sound, players, controllers, library)
└── main.cpp          — Application entry point
```

### The Control System (Mixxx's Internal API)

This is the most important part for our purposes. Mixxx uses a **ControlObject** system as its single unified API. Every interaction — keyboard, MIDI, HID, GUI skin, and internal engine — goes through this system.

**How it works:**
- Each control is a `ConfigKey` = `(group, item)` pair, e.g., `("[Channel1]", "play")`
- `ControlObject` — creates/owns a control, registered globally
- `ControlProxy` — thread-safe read/write access to any existing control from any thread
- All values are `double` — booleans are 0.0/1.0, positions are 0.0-1.0, etc.
- Thread-safe: uses atomic operations and dual signals (`valueChanged` vs `valueChangedFromEngine`)

**Creating/accessing a control in C++:**
```cpp
// Create (owner)
ControlObject* pPlay = new ControlObject(ConfigKey("[Channel1]", "play"));

// Access from anywhere (proxy)
ControlProxy* pPlay = new ControlProxy("[Channel1]", "play");
pPlay->set(1.0);           // Start playing
double pos = pPlay->get(); // Read value
```

**From JavaScript (controller scripts):**
```javascript
engine.getValue("[Channel1]", "play");
engine.setValue("[Channel1]", "play", 1.0);
```

### Audio Backend

- **Primary:** PortAudio (cross-platform, handles all audio I/O)
- **Network:** SoundDeviceNetwork for streaming output
- **Time-stretching:** RubberBand (high quality), SoundTouch (faster), Linear (basic)
- **Sample rate:** 44100 Hz default, configurable
- **Beat detection:** Queen Mary VAMP plugin (primary), SoundTouch (alternative)
- **Key detection:** Queen Mary, KeyFinder (libkeyfinder)

### Build System

- CMake-based
- Qt 6.2+ (preferred) or Qt 5.12+
- Supports Qt QML for new UI alongside legacy widget skins
- Pre-built dependency packages for macOS (x64 and arm64)

---

## 2. Existing API/Control Options

### What Exists Today

| Method | Status | Direction | Notes |
|--------|--------|-----------|-------|
| MIDI controllers | Production | Bidirectional | Full control via virtual MIDI ports |
| HID controllers | Production | Bidirectional | USB HID device protocol |
| Keyboard | Production | Input only | Key mappings to controls |
| JS controller scripts | Production | Bidirectional | QJSEngine (ES7), `engine.getValue/setValue` |
| OSC client | Design only | Output only | Wiki proposal from 2014, never implemented in codebase |
| HTTP/REST API | None | — | Does not exist |
| WebSocket | None | — | Does not exist |
| DBus | None | — | Not implemented |

### Community Projects

**RemoteAutoDJ** (github.com/jul3x/RemoteAutoDJ):
- Node.js HTTP server (port 8787) + custom MIDI controller mapping
- Translates web UI clicks into MIDI messages sent to Mixxx
- Requires starting Node server before Mixxx, enabling "MixxxWebRemote MIDI" controller
- Limited to AutoDJ controls, not full deck control
- Architecture: Browser -> Node.js HTTP -> virtual MIDI -> Mixxx

### JavaScript Controller Scripts — Can They Open Network Ports?

**No.** The QJSEngine environment in Mixxx is sandboxed:
- Runs ES7 JavaScript, but no Node.js APIs (no `require('net')`, no `http`, no `fs`)
- Only APIs exposed: `engine.*` (getValue/setValue/makeConnection/timers), `midi.*`, `console.*`
- No access to Qt networking classes from JS
- No way to import external modules that use native bindings
- The `QJSEngine` does NOT expose `QTcpServer`, `QWebSocketServer`, or any networking

**Verdict:** Cannot add an HTTP/WebSocket server via controller scripts alone.

---

## 3. Feasibility Assessment — Three Approaches

### Approach A: Fork Mixxx C++ (Add HTTP Server to Core)

**How:** Add a new module in `src/network/` or `src/api/` that:
1. Starts a `QHttpServer` (Qt 6.5+) or lightweight embedded HTTP server
2. Exposes REST endpoints that map to `ControlProxy::get()`/`set()`
3. Optionally adds WebSocket for real-time state push

**Pros:**
- Full access to every ControlObject (hundreds of controls)
- Can read waveform data, track metadata, library contents
- Low latency — direct in-process calls, no MIDI translation
- Can add custom endpoints (batch operations, transitions, analysis results)
- WebSocket can push state changes in real-time (connect to ControlObject signals)

**Cons:**
- Must maintain a fork (merge upstream changes)
- C++ development, Qt knowledge required
- Longer build times (~15-30 min full build)
- Must rebuild on each Mixxx update

**Effort:** Medium-High. ~2-3 days for basic REST API, ~1 week for full WebSocket + REST.

### Approach B: External MIDI Bridge (Current Approach, Enhanced)

**How:** Keep our Python `controller.py` (virtual MIDI) but add:
1. Two-way communication: MIDI out (commands) + MIDI in (feedback from Mixxx)
2. Our `server.py` already provides HTTP API -> translates to MIDI -> Mixxx
3. Add Mixxx controller mapping that sends MIDI feedback for state changes

**Pros:**
- No Mixxx modification needed — works with stock Mixxx
- Already partially implemented (controller.py, server.py)
- Python is faster to iterate on
- Upgrades to new Mixxx versions are trivial

**Cons:**
- MIDI is limited: 128 values (0-127) per CC, no floating point precision
- No access to waveform data, track metadata, library search
- Cannot load specific tracks by filename via MIDI
- Latency: Python -> MIDI -> Mixxx -> MIDI -> Python adds ~10-50ms
- State feedback is unreliable — Mixxx doesn't broadcast all state changes via MIDI
- Complex workarounds needed for features like "load track by path"

**Effort:** Low. ~1-2 days to improve what we have. But ceiling is low.

### Approach C: Sidecar Process with Shared Memory / IPC

**How:** Run a separate process alongside Mixxx that:
1. Accesses Mixxx's SQLite database directly (track library, metadata)
2. Uses virtual MIDI for control commands
3. Reads Mixxx config files for state
4. Optionally uses a small Mixxx C++ plugin (if plugin system exists — it doesn't)

**Pros:**
- No fork needed
- Can read library database for track search/metadata
- MIDI for control, SQLite for data

**Cons:**
- SQLite is read-only (Mixxx locks it)
- No real-time state (playposition, VU meters, waveform)
- Fragile — depends on Mixxx's internal DB schema
- Still limited by MIDI for commands

**Effort:** Medium. ~2-3 days. But still limited.

---

## 4. Recommended Approach

### Primary: Fork Mixxx + HTTP/WebSocket API (Approach A)

**Reasoning:**
1. Our use case (AI DJ brain controlling every aspect of mixing) needs precise control that MIDI cannot provide
2. Track loading by file path is essential — MIDI cannot do this
3. Real-time position/waveform data is needed for intelligent transitions
4. The ControlObject system is perfectly designed for this — we just need to expose it over HTTP
5. Qt already has `QHttpServer` (Qt 6.5+) and `QWebSocketServer` — minimal new dependencies
6. Mixxx's architecture is clean and modular — adding an API server is a natural extension

### Secondary: Keep MIDI bridge as fallback

Keep `controller.py` working for quick testing and as a fallback if fork isn't ready.

---

## 5. HTTP API Design

### REST Endpoints

```
GET  /api/status                    — Full mixer state (all decks, crossfader, master)
GET  /api/deck/{n}                  — Deck N status (position, BPM, track, playing, volume)
POST /api/deck/{n}/load             — Load track: {"path": "/path/to/file.mp3"}
POST /api/deck/{n}/play             — Play deck
POST /api/deck/{n}/pause            — Pause deck
POST /api/deck/{n}/stop             — Stop deck
POST /api/deck/{n}/seek             — Seek: {"position": 0.5} (0.0-1.0)
POST /api/deck/{n}/volume           — Set volume: {"value": 0.8}
POST /api/deck/{n}/eq               — Set EQ: {"hi": 1.0, "mid": 0.5, "lo": 0.8}
POST /api/deck/{n}/rate             — Set playback rate: {"value": 0.02}
POST /api/deck/{n}/sync             — Sync to other deck
POST /api/deck/{n}/key              — Set key: {"value": 5}

POST /api/crossfader                — Set crossfader: {"value": 0.5} (-1.0 to 1.0)
POST /api/master/volume             — Master volume: {"value": 0.9}

POST /api/control                   — Generic: {"group": "[Channel1]", "key": "play", "value": 1.0}
GET  /api/control?group=...&key=... — Read any control

GET  /api/library/search?q=...      — Search track library
GET  /api/library/track/{id}        — Track metadata (BPM, key, duration, waveform summary)

GET  /api/waveform/{n}              — Waveform data for deck N (downsampled)

WebSocket /api/ws                   — Real-time state stream (position, VU, beat events)
```

### WebSocket Events (pushed to client)

```json
{"type": "position",  "deck": 1, "value": 0.342, "samples": 15023456}
{"type": "beat",      "deck": 1, "beat_number": 47}
{"type": "track",     "deck": 1, "title": "...", "artist": "...", "bpm": 128.0, "key": "Am"}
{"type": "vu",        "deck": 1, "left": 0.65, "right": 0.72}
{"type": "state",     "deck": 1, "playing": true, "volume": 0.8}
{"type": "crossfader","value": 0.0}
```

---

## 6. Key Mixxx Controls to Expose

### Per-Deck Controls — Group: `[ChannelN]` (N=1,2,3,4)

| Control Key | Type | Range | Description |
|-------------|------|-------|-------------|
| `play` | button | 0/1 | Play/pause toggle |
| `stop` | button | 0/1 | Stop playback |
| `cue_default` | button | 0/1 | Cue point |
| `playposition` | float | 0.0-1.0 | Track position (fraction) |
| `volume` | float | 0.0-1.0 | Channel volume fader |
| `pregain` | float | 0.0-4.0 | Pre-gain/trim |
| `pfl` | button | 0/1 | Headphone cue (pre-fader listen) |
| `bpm` | float | — | Current BPM (rate-adjusted) |
| `file_bpm` | float | — | Detected BPM (original) |
| `rate` | float | -1.0-1.0 | Playback rate adjustment |
| `key` | float | 0-23 | Musical key |
| `file_key` | string | — | Detected key |
| `beatsync` | button | 0/1 | Sync BPM to other deck |
| `sync_enabled` | button | 0/1 | Enable sync mode |
| `duration` | float | — | Track duration in seconds |
| `track_samplerate` | float | — | Sample rate |
| `waveform_zoom` | float | — | Waveform zoom level |
| `LoadSelectedTrack` | button | 0/1 | Load selected library track |
| `repeat` | button | 0/1 | Repeat mode |
| `orientation` | float | 0/1/2 | Crossfader assignment (left/center/right) |
| `hotcue_X_activate` | button | 0/1 | Trigger hot cue X (1-36) |
| `loop_enabled` | button | 0/1 | Loop active |
| `beatloop_X_activate` | button | 0/1 | Activate X-beat loop |
| `loop_start_position` | float | — | Loop start in samples |
| `loop_end_position` | float | — | Loop end in samples |
| `VuMeter` | float | 0.0-1.0 | VU meter level |
| `VuMeterL` / `VuMeterR` | float | 0.0-1.0 | Stereo VU |

### EQ Controls — Group: `[EqualizerRack1_[ChannelN]_Effect1]`

| Control Key | Type | Range | Description |
|-------------|------|-------|-------------|
| `parameter1` | float | 0.0-4.0 | Low EQ |
| `parameter2` | float | 0.0-4.0 | Mid EQ |
| `parameter3` | float | 0.0-4.0 | High EQ |
| `button_parameter1` | button | 0/1 | Kill Low |
| `button_parameter2` | button | 0/1 | Kill Mid |
| `button_parameter3` | button | 0/1 | Kill High |

### Quick Effect (Filter) — Group: `[QuickEffectRack1_[ChannelN]]`

| Control Key | Type | Range | Description |
|-------------|------|-------|-------------|
| `super1` | float | 0.0-1.0 | Quick effect knob (filter sweep) |
| `enabled` | button | 0/1 | Enable/disable |

### Master Controls — Group: `[Master]`

| Control Key | Type | Range | Description |
|-------------|------|-------|-------------|
| `crossfader` | float | -1.0-1.0 | Crossfader position |
| `gain` | float | 0.0-5.0 | Master output gain |
| `headGain` | float | 0.0-5.0 | Headphone gain |
| `headMix` | float | 0.0-1.0 | Headphone cue/main mix |
| `VuMeterL` / `VuMeterR` | float | 0.0-1.0 | Master VU meters |

### Library Controls — Group: `[Library]`

| Control Key | Type | Range | Description |
|-------------|------|-------|-------------|
| `MoveDown` / `MoveUp` | button | — | Navigate track list |
| `GoToItem` | button | — | Open/select item |

---

## 7. Implementation Plan — Step by Step

### Phase 1: Build Mixxx from Source (Day 1)

```bash
# 1. Clone
git clone https://github.com/mixxxdj/mixxx.git ~/mixxx
cd ~/mixxx
git checkout main  # or latest stable tag (e.g., 2.5.0)

# 2. Set up build environment (downloads ~1.5 GB of pre-built deps)
source tools/macos_buildenv.sh setup

# 3. Configure (Debug build with assertions)
cmake -DCMAKE_BUILD_TYPE=Debug \
      -DDEBUG_ASSERTIONS_FATAL=ON \
      -S ~/mixxx -B ~/mixxx/build

# 4. Build (15-30 min first time, faster with ccache after)
cmake --build ~/mixxx/build --parallel $(sysctl -n hw.physicalcpu)

# 5. Run
~/mixxx/build/mixxx
```

**macOS arm64 Notes:**
- The `macos_buildenv.sh` script now supports arm64 natively
- Pre-built dependencies are available for `arm64-osx-min1100`
- Qt 6.2+ is used (includes QHttpServer in Qt 6.5+)
- Xcode Command Line Tools required: `xcode-select --install`

### Phase 2: Add HTTP API Module (Day 2-3)

1. **Create new source files:**
   ```
   src/api/
   ├── apiserver.h         — QHttpServer wrapper, route registration
   ├── apiserver.cpp        — Implementation
   ├── apicontroller.h      — Request handlers (deck, master, library)
   ├── apicontroller.cpp    — Maps REST calls to ControlProxy get/set
   └── apiwebsocket.h/cpp   — WebSocket server for real-time state push
   ```

2. **Server startup in `coreservices.cpp`:**
   - After all services initialize, start `ApiServer` on configurable port (default 7778)
   - Pass `PlayerManager`, `Library`, `EffectsManager` pointers

3. **HTTP framework options (in order of preference):**
   - **QHttpServer** (Qt 6.5+) — built into Qt, minimal deps, supports routes
   - **cpp-httplib** (header-only) — zero deps, if Qt version too old
   - **Crow** — lightweight C++ REST framework, header-only

4. **Generic control endpoint:**
   ```cpp
   // POST /api/control
   void handleSetControl(const QHttpServerRequest& req, QHttpServerResponder& resp) {
       auto json = QJsonDocument::fromJson(req.body()).object();
       QString group = json["group"].toString();
       QString key = json["key"].toString();
       double value = json["value"].toDouble();

       ControlProxy proxy(group, key);
       proxy.set(value);

       resp.write(QJsonDocument({{"ok", true}}).toJson());
   }
   ```

### Phase 3: WebSocket Real-Time Stream (Day 3-4)

1. Use `QWebSocketServer` (already in Qt)
2. Connect to ControlObject signals for position, VU, play state
3. Throttle position updates to ~20-30 fps (every 33-50ms)
4. Send JSON events to connected clients

### Phase 4: Integrate with DJ Treta Brain (Day 4-5)

1. Update `server.py` to act as middleware:
   ```
   Claude/Treta -> server.py (our Python brain) -> Mixxx HTTP API (port 7778)
   ```
2. Server.py handles:
   - Set planning (track order, energy flow)
   - Transition timing (when to start crossfade)
   - Track selection (search library, pick by BPM/key compatibility)
3. Direct HTTP calls to Mixxx for:
   - Load track, play, crossfade, EQ, volume
   - Read current state (what's playing, position, BPM)

### Phase 5: UI Decision (Day 5+)

**Option 1: Use Mixxx's UI (recommended for now)**
- Mixxx handles waveforms, library browser, effects — mature and battle-tested
- Our API controls it from the backend, Mixxx GUI shows the result
- Keep our `ui.html` as a minimal monitoring dashboard

**Option 2: Custom Chrome UI (later)**
- Read waveform data via API, render in canvas
- Full control from browser
- More work, but fully customizable for AI DJ use case

---

## 8. Build Requirements — macOS arm64

### Prerequisites

```bash
# Xcode Command Line Tools
xcode-select --install

# That's it — the build env script handles everything else
```

### Dependencies (handled by macos_buildenv.sh)

The script downloads a pre-built package (~1.5 GB) containing:
- Qt 6.x (Core, Gui, Widgets, Qml, Network, Sql, Svg, OpenGL, HttpServer)
- PortAudio
- RubberBand (time-stretching)
- SoundTouch
- Chromaprint (audio fingerprinting)
- FLAC, Ogg, Vorbis, LAME (audio codecs)
- FFmpeg (libavcodec, libavformat)
- SQLite3
- libkeyfinder
- Ebur128 (loudness measurement)
- protobuf
- And more (~30 dependencies total)

### Build Time Estimates

| Build Type | First Build | Incremental |
|------------|-------------|-------------|
| Debug | ~20-30 min | ~1-5 min |
| Release | ~30-45 min | ~1-5 min |

ccache is included and auto-configured, making subsequent builds much faster.

---

## 9. Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Upstream Mixxx changes break our fork | Medium | Keep changes minimal and isolated in `src/api/` |
| Qt version doesn't include QHttpServer | Low | Use cpp-httplib (header-only fallback) |
| Build environment issues on arm64 | Low | arm64 deps are now official, CI-tested |
| Performance impact of HTTP server | Very Low | HTTP handlers run on Qt event loop, not audio thread |
| Complexity of maintaining fork | Medium | Rebase periodically; our changes are additive, not modifying core |

---

## 10. Summary

**Best approach: Fork Mixxx and add an HTTP/WebSocket API layer.**

The ControlObject system is literally designed to be a universal API — we just need to put an HTTP wrapper around it. The codebase is clean, well-structured, and the build system supports macOS arm64 with pre-built dependencies. The work is ~3-5 days for a working prototype.

The MIDI bridge approach (current) works for basic play/pause/crossfade but fundamentally cannot support:
- Loading tracks by file path
- Reading precise playposition (MIDI is 0-127, we need float)
- Accessing waveform data
- Searching the track library
- Real-time state streaming

The fork gives us all of this with full precision and low latency.
