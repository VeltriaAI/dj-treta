# DJ Treta — Knowledge Base

> Comprehensive DJ theory, techniques, and actionable rules for an AI DJ controlling Mixxx via HTTP API.
> Compiled from professional DJ resources, mixing theory, and genre-specific conventions.

---

## Table of Contents

1. [Track Structure & Phrasing](#1-track-structure--phrasing)
2. [Mixing Techniques](#2-mixing-techniques)
3. [Harmonic Mixing & The Camelot Wheel](#3-harmonic-mixing--the-camelot-wheel)
4. [Track Selection Theory](#4-track-selection-theory)
5. [Set Structure & Energy Flow](#5-set-structure--energy-flow)
6. [Technical Skills](#6-technical-skills)
7. [Creative Techniques](#7-creative-techniques)
8. [Genre-Specific Knowledge](#8-genre-specific-knowledge)
9. [Actionable Rules for AI DJ](#9-actionable-rules-for-ai-dj)

---

## 1. Track Structure & Phrasing

### Understanding Musical Phrases

Electronic dance music (especially house and techno) is built on a rigid phrase structure:

- **Beat**: A single count (the kick drum in 4/4 time)
- **Bar**: 4 beats (1 bar = 4 beats)
- **Phrase**: 8 bars = 32 beats (the fundamental structural unit)
- **Section**: 2-4 phrases = 16-32 bars (intro, verse, chorus, breakdown, drop, outro)

### Common Track Structure (House/Techno)

```
[Intro: 16-32 bars] → [Build: 8-16 bars] → [Drop/Main: 32-64 bars] →
[Breakdown: 16-32 bars] → [Build: 8-16 bars] → [Drop 2: 32-64 bars] →
[Outro: 16-32 bars]
```

### Phrase Counting Rules

| Element | Length | Beats |
|---------|--------|-------|
| Short phrase | 4 bars | 16 beats |
| Standard phrase | 8 bars | 32 beats |
| Long phrase | 16 bars | 64 beats |
| Full section | 32 bars | 128 beats |

### Why Phrasing Matters

- Every structural change in a track (new element entering, breakdown starting, drop hitting) happens on a phrase boundary — typically every 8 or 16 bars.
- If you start a transition mid-phrase, the incoming track's structure will be misaligned with the outgoing track, creating a "trainwreck" where elements clash.
- **Rule**: Always start the incoming track on beat 1 of a phrase boundary in the outgoing track.

---

## 2. Mixing Techniques

### 2.1 EQ Mixing (The Foundation)

EQ mixing is the most critical skill. The mixer's 3-band EQ (Low/Mid/High) controls which frequencies from each track are heard.

**Bass Swap Technique** (most important):
1. With Track B's volume fader up but bass EQ cut (turned fully left/down), begin the blend
2. At the target phrase boundary, simultaneously:
   - Turn Track A's bass EQ down (to zero/kill)
   - Turn Track B's bass EQ up (to noon/center)
3. This must be done quickly (within 1-2 beats) to avoid two basslines clashing

**Why**: Two basslines playing simultaneously = muddy, distorted sound. Only one bass should dominate at any given time.

**Mid and High EQ**:
- Mids can overlap more than bass but still benefit from gradual swapping
- Highs (hi-hats, cymbals) can often coexist without clashing
- Cutting highs on the outgoing track during a blend removes its "presence" gracefully

### 2.2 Filter Mixing

Filters are more dramatic than EQ cuts:

- **Low-pass filter (LPF)**: Removes highs, leaving only bass/low-mids. Makes a track sound "underwater" or "distant." Use on the outgoing track to fade it away.
- **High-pass filter (HPF)**: Removes bass, leaving only highs/mids. Makes a track sound "thin" or "telephonic." Use on the incoming track to tease it before revealing the full sound.

**Filter Sweep Transition**:
1. Incoming track: Start with HPF fully engaged (only highs audible)
2. Gradually open the HPF over 8-16 bars
3. Simultaneously apply LPF to outgoing track
4. At the drop/phrase boundary: snap both filters off — full impact of new track

### 2.3 Long Blend vs Short Cut

| Technique | Duration | When to Use |
|-----------|----------|-------------|
| **Long blend** | 16-64 bars (30s-2min) | Melodic/deep genres, atmospheric transitions, building tension |
| **Medium blend** | 8-16 bars (15-30s) | Standard house/techno transitions |
| **Short cut** | 1-4 bars (2-8s) | High-energy moments, genre changes, dramatic effect |
| **Instant swap** | 0 bars (immediate) | Power cuts, surprise drops, double drops |

**Rules for choosing**:
- Deep house, melodic techno, progressive → long blends (16-32 bars)
- Tech house, standard techno → medium blends (8-16 bars)
- Hard techno, drum & bass, peak-time energy → short cuts (1-8 bars)
- Never use long blends at peak energy — kills momentum

### 2.4 Echo/Delay Effects During Transitions

- **Echo out**: Apply echo/delay to the outgoing track at the transition point, then cut the channel. The echoes trail off naturally while the new track takes over.
- Typical settings: 1/2 beat or 1 beat delay time, medium feedback (50-70%), with decay
- Creates a professional "tail" on the outgoing track
- Works best combined with HPF — echo + filter = smooth exit

### 2.5 The Double Drop

Two tracks drop simultaneously, both playing their chorus/main section at the same time.

**Requirements**:
- Identical BPM (exact match, not approximate)
- Compatible keys (same Camelot code or adjacent)
- Complementary frequency content (one bass-heavy, one mid/high-focused, OR use EQ to split)
- Precise phase alignment (beat 1 of both drops must hit together)

**Execution**:
1. Cue both tracks to their drop points
2. During the buildup of Track A, bring in Track B's buildup
3. At the drop: both tracks hit simultaneously
4. EQ to prevent frequency clashing — typically cut bass on one track

**Used in**: Drum & bass (common), techno (occasional), trance (buildups)

---

## 3. Harmonic Mixing & The Camelot Wheel

### The Camelot System

The Camelot Wheel maps all 24 musical keys to a numbered clock (1-12), with A = minor, B = major.

### Complete Camelot Key Chart

| Camelot | Musical Key | Camelot | Musical Key |
|---------|-------------|---------|-------------|
| **1A** | A-flat minor (Ab min) | **1B** | B major |
| **2A** | E-flat minor (Eb min) | **2B** | F-sharp major (F# maj) |
| **3A** | B-flat minor (Bb min) | **3B** | D-flat major (Db maj) |
| **4A** | F minor | **4B** | A-flat major (Ab maj) |
| **5A** | C minor | **5B** | E-flat major (Eb maj) |
| **6A** | G minor | **6B** | B-flat major (Bb maj) |
| **7A** | D minor | **7B** | F major |
| **8A** | A minor | **8B** | C major |
| **9A** | E minor | **9B** | G major |
| **10A** | B minor | **10B** | D major |
| **11A** | F-sharp minor (F# min) | **11B** | A major |
| **12A** | D-flat minor (Db min) | **12B** | E major |

### Compatible Key Rules (Ranked by Smoothness)

Given a current track with Camelot code `N[A/B]`:

| Move | Example (from 8A) | Effect | Smoothness |
|------|-------------------|--------|------------|
| **Same key** | 8A → 8A | Perfect match, no harmonic tension | 10/10 |
| **+1 number, same letter** | 8A → 9A | Gentle uplift, one step around circle of fifths | 9/10 |
| **-1 number, same letter** | 8A → 7A | Gentle descent, smooth and natural | 9/10 |
| **Same number, swap letter** | 8A → 8B | Minor ↔ Major shift, mood change (same notes) | 8/10 |
| **+1 number, swap letter** | 8A → 9B | Diagonal move, subtle key shift with mood change | 7/10 |
| **-1 number, swap letter** | 8A → 7B | Diagonal move, reverse direction | 7/10 |
| **+2 numbers** | 8A → 10A | Noticeable key change, energy boost | 5/10 |
| **+7 numbers (semitone up)** | 8A → 3A | Dramatic semitone lift, high energy | 4/10 |
| **Random jump** | 8A → 4B | Harsh clash if blended — only use with hard cuts | 2/10 |

### Actionable Harmonic Rules

1. **Safe zone**: Same key, +/-1 number (same letter), same number (swap letter) — use for blended transitions
2. **Creative zone**: +/-2 numbers, diagonal moves — use with shorter blends
3. **Danger zone**: +/-3 or more numbers — only use with hard cuts, echo-outs, or track isolation (no overlap)
4. **Energy boost trick**: Going UP the Camelot wheel (+1, +2) creates uplift. Going DOWN creates relaxation.
5. **Mood shift**: Swapping A↔B (minor↔major) on the same number creates an emotional shift without harmonic clash

---

## 4. Track Selection Theory

### Energy Levels

Assign every track an energy level from 1-10:

| Energy | Characteristics | Use In Set |
|--------|----------------|------------|
| 1-2 | Ambient, minimal, sparse percussion | Opening, deep interludes |
| 3-4 | Groovy, deep, subtle | Warm-up, cool-down |
| 5-6 | Driving, rhythmic, building | Mid-set, building phases |
| 7-8 | Powerful, peak-time, big melodies/drops | Peak hour |
| 9-10 | Relentless, high-intensity, raw | Climactic moments (use sparingly) |

### Energy Flow Rules

1. **Never jump more than 2 energy levels at once** (e.g., don't go from 3 to 7)
2. **Build gradually**: 3 → 4 → 5 → 6 → 7 → 8 → (brief dip to 6) → 9
3. **Create waves**: Rise for 3-4 tracks, then dip 1-2 levels for 1-2 tracks, then rise again
4. **Peak sustainably**: Don't play 5 tracks at energy 9 in a row — the crowd tires. Play 2-3 peak tracks, then release.
5. **The dip before the peak**: The most powerful moments come AFTER a brief energy reduction. A breakdown or melodic interlude makes the next drop hit harder.

### Reading the Crowd (For AI: Use Proxy Signals)

Physical indicators that map to energy response:
- **Positive**: Dancing intensity, hands up, crowd moving forward, cheering after drops
- **Neutral**: Steady dancing, head nodding, maintaining position
- **Negative**: People leaving the floor, checking phones, moving to bar, conversation increasing

**AI Proxy**: Since an AI DJ can't see the crowd, use these heuristics:
- Time of event (early = low energy, peak hour = high energy, late = declining)
- Previous track's energy level and planned trajectory
- Genre/BPM momentum — don't break the flow without reason
- Pre-programmed set arc with real-time adjustment hooks

### Surprise Factor

- Every 5-8 tracks, introduce something unexpected: a genre detour, an unusual vocal, a classic throwback
- The surprise should still be harmonically compatible or use a clean transition (hard cut, echo out)
- Surprises work best at energy levels 5-7 (mid-set), not during peak moments

### Genre-Bending

- Match BPM and energy when crossing genres — the BPM is the bridge
- Example: Deep house (122 BPM) → Melodic techno (124 BPM) → Tech house (126 BPM) is a natural progression
- Use tracks that blur genre lines as "bridge tracks" between styles
- Acapellas from one genre over instrumentals from another create genre-bending moments

---

## 5. Set Structure & Energy Flow

### The Classic Arc (1-2 Hour Set)

```
Time:     0%    15%    30%    50%    70%    85%    100%
Energy:   3 → 4 → 5 → 6 → 7 → 8 → 9 → 8 → 7 → 6 → 5
Phase:    |OPEN |  BUILD  | PEAK TIME |  COOL |CLOSE|
```

### Phase Breakdown

#### Opening (0-15% of set time)
- **Energy**: 3-4
- **BPM**: Lower end of genre range
- **Goal**: Set the mood, don't demand attention
- **Tracks**: Deep, atmospheric, minimal percussion
- **Transitions**: Long blends (32+ bars), smooth and unnoticeable
- **Mistakes to avoid**: Playing bangers too early, forcing energy

#### Building (15-50% of set time)
- **Energy**: 4 → 7 (gradual climb with small dips)
- **BPM**: Gradually increasing (e.g., 120 → 126)
- **Goal**: Steadily increase energy, introduce stronger elements
- **Transitions**: Medium blends (16-32 bars), more EQ work
- **Technique**: Each track should feel like a natural step up from the last

#### Peak Time (50-80% of set time)
- **Energy**: 7-9 (with 1-2 dips to 6 for breathing room)
- **BPM**: Genre peak range (126-132 for house/techno)
- **Goal**: Maximum dancefloor engagement
- **Tracks**: Your biggest, most impactful selections
- **Transitions**: Shorter blends (8-16 bars), more effects, dramatic cuts
- **The golden rule**: The best track in your set should come about 65-75% through

#### Cool-Down (80-95% of set time)
- **Energy**: 7 → 5 (graceful descent)
- **BPM**: Gradually decreasing
- **Goal**: Release tension without killing the vibe
- **Transitions**: Return to medium/long blends
- **Technique**: Use more melodic, emotional tracks

#### Closing (95-100% of set time)
- **Energy**: 4-5
- **The closing track**: Should be memorable, emotional, leave an impression
- **Options**: A beautiful melodic piece, a classic, an unexpected vocal track
- **Never**: End abruptly or on a forgettable track

### Tracks Per Hour

| Genre | Tracks/Hour | Avg Track Play Time |
|-------|-------------|-------------------|
| Deep house | 8-10 | 6-7 min |
| Melodic techno | 10-12 | 5-6 min |
| Tech house | 12-15 | 4-5 min |
| Peak-time techno | 14-18 | 3-4 min |
| Hard techno | 16-22 | 2.5-3.5 min |
| Drum & bass | 18-25 | 2-3 min |

### Tension Building Techniques

Before a "big moment" (a well-known track, a massive drop):

1. **Energy dip**: Play 1-2 tracks at lower energy to create contrast
2. **Breakdown extension**: Loop a breakdown section for 16-32 extra bars
3. **Filter sweep**: Gradually apply LPF to remove energy, then snap it off at the drop
4. **Percussion strip**: Remove kick/bass elements using EQ, leaving only hi-hats and atmosphere
5. **Silence gap**: A brief 1-2 beat silence before a drop creates massive impact (advanced, risky)

---

## 6. Technical Skills

### 6.1 Beatmatching

**Tempo Matching**:
- Match BPM of incoming track to outgoing track (within +/- 0.05 BPM for seamless blend)
- Acceptable drift: Up to +/- 3% tempo adjustment without noticeable pitch change
- Beyond +/- 6%: Track sounds unnatural — use hard cut instead of blend

**Phase Alignment**:
- The kick drums of both tracks must land at the same time
- If kicks are offset, the mix sounds "flammy" (double-hit effect)
- In Mixxx: Use waveform display to visually align transients
- Check phase by monitoring the blend in headphones — kicks should sound like ONE hit, not two

**BPM Transition Strategy**:
- Small changes (1-2 BPM): Adjust incoming track to match, blend normally
- Medium changes (3-5 BPM): Match BPM, blend, then gradually shift overall tempo
- Large changes (6+ BPM): Don't blend — use hard cut, echo out, or breakdown transition

### 6.2 Gain Staging

**Volume Matching Rules**:
1. Before any transition, match the perceived loudness of both tracks
2. Use the GAIN/TRIM knob (not the channel fader) to match levels
3. Target: Channel meters should peak at the same level for both tracks
4. The master output should kiss the red occasionally but never stay there
5. Different tracks have different mastering levels — always check gain before blending

**Level Targets**:
- Channel meters: Peak around 0 dB (occasionally touching +1 to +3 dB)
- Master output: Peak at 0 dB, never sustained in the red
- Headroom: Keep 3-6 dB of headroom on the master for transient peaks during blends

**Common Gain Mistakes**:
- Bringing in a new track too loud (blows out the mix)
- Not compensating for EQ cuts (cutting bass reduces perceived volume — may need gain boost)
- Volume creep: Each track slightly louder than the last until the mix distorts

### 6.3 Hot Cues

Strategic cue point placement for transitions:

| Cue # | Purpose | Placement |
|-------|---------|-----------|
| 1 | **Mix-in point** | First beat of the intro (or first phrase after intro percussion starts) |
| 2 | **Drop point** | First beat of the main drop/chorus |
| 3 | **Breakdown start** | First beat of the main breakdown |
| 4 | **Mix-out point** | Start of the outro (where elements begin stripping away) |
| 5 | **Vocal hook** | Start of a recognizable vocal or melodic phrase |
| 6 | **Loop point** | A good 4-8 bar section for looping during extended blends |

### 6.4 Loop Techniques

**Extending intros/outros for longer blends**:
- Set a 4, 8, or 16 bar loop at the start of the incoming track
- This gives you unlimited time to perfect the blend before releasing the loop
- When ready, exit the loop — the track continues from where the loop ends

**Creative looping**:
- Loop a percussion-only section while blending in the next track's melodic elements
- Loop a breakdown's atmospheric pad to create a drone under the new track
- Use progressively shorter loops (8 → 4 → 2 → 1 bar) to create a "stutter" buildup effect

**Loop lengths and their uses**:

| Length | Beats | Use |
|--------|-------|-----|
| 16 bars | 64 | Extended blending, atmospheric holds |
| 8 bars | 32 | Standard blend extension |
| 4 bars | 16 | Rhythmic loops, percussion holds |
| 2 bars | 8 | Tension building, repetitive hooks |
| 1 bar | 4 | Stutter effects, buildup tension |
| 1/2 bar | 2 | Intense buildup, roll effect |
| 1 beat | 1 | Siren/alarm effect (use briefly) |

### 6.5 The Kill Switch

Completely cutting an EQ band (to -inf dB) for dramatic effect:

**Bass kill**: Removes all low-end energy instantly. Creates a sudden "lift" sensation. Used to:
- Create tension before a drop (kill bass → 4-8 bars → restore = massive impact)
- Clean up a blend (kill outgoing track's bass, restore incoming)
- Create rhythmic patterns (kill/restore bass every 4 bars)

**Mid kill**: Removes body/vocals. Creates a ghostly, hollow sound. Used for:
- Isolating percussion and bass (drum-only breakdowns)
- Transitioning between vocal and instrumental sections

**High kill**: Removes all brightness. Creates a dark, muffled sound. Used for:
- Simulating a "walls closing in" effect
- Transitioning from bright to dark tracks

---

## 7. Creative Techniques

### 7.1 "Third Track" Illusion

When two tracks are playing simultaneously in a blend, the combination can create something neither track produces alone — a "third track" emerges from the interaction.

**How to achieve it**:
- Choose tracks with complementary elements (one percussion-heavy, one melodic)
- Use EQ to isolate the best elements of each: bass from Track A, melody from Track B
- The result is a unique hybrid that exists only in this mix
- Best duration: 8-16 bars — long enough to appreciate, short enough to feel special

### 7.2 Acapella Mixing

Using isolated vocal tracks over instrumentals from different songs:

**Technique**:
1. Load an acapella (or use stem separation to isolate vocals)
2. Match the acapella's BPM and key to the instrumental playing
3. Use EQ to carve space: cut mids on the instrumental to make room for vocals
4. Layer vocals over instrumental, creating an on-the-fly remix

**Rules**:
- Acapella must be in a compatible key (same Camelot code or +/-1)
- BPM must match exactly — vocal phrasing is very unforgiving of tempo drift
- Works best with well-known vocals over unexpected instrumentals

### 7.3 Building-to-Drop Transitions

Teasing the crowd with breakdowns before delivering the payoff:

1. Play Track A's breakdown (energy drops, atmosphere builds)
2. During breakdown, tease elements of Track B (filtered, quiet)
3. As Track A's buildup begins, increase Track B's presence
4. At Track A's drop point, cut Track A entirely and let Track B's drop hit instead

This creates a "bait and switch" — the crowd expects Track A's drop but gets Track B's, which (if chosen well) is even more impactful.

### 7.4 Back-to-Back Mixing (Rapid Transitions)

Playing short segments of multiple tracks in rapid succession:

- Each track plays for only 16-32 bars (30-60 seconds)
- Transitions are quick cuts or 4-bar blends
- Creates a high-energy, DJ-showcase feel
- Best used during peak energy moments
- Risk: Can feel rushed if done poorly — each track must land its most impactful moment

### 7.5 Live Remixing

Using loops, cues, and effects to create unique versions of tracks:

- **Loop + EQ**: Loop a section, then progressively EQ out elements and bring in elements from another track
- **Cue juggling**: Jump between hot cues on the same track to rearrange its structure
- **Effect chains**: Apply reverb → delay → filter in sequence to transform a familiar track
- **Tempo manipulation**: Gradually speed up or slow down a looped section for tension

---

## 8. Genre-Specific Knowledge

### 8.1 BPM Ranges by Subgenre

| Subgenre | BPM Range | Sweet Spot | Energy |
|----------|-----------|------------|--------|
| Lo-fi house | 100-115 | 110 | 2-3 |
| Deep house | 118-125 | 122 | 3-5 |
| Afro house | 118-128 | 124 | 4-6 |
| Melodic house | 120-126 | 123 | 4-6 |
| Progressive house | 122-128 | 126 | 5-7 |
| Melodic techno | 120-130 | 125 | 5-7 |
| Tech house | 124-130 | 127 | 5-7 |
| Minimal techno | 125-135 | 130 | 4-6 |
| Techno (standard) | 128-135 | 132 | 6-8 |
| Peak-time techno | 130-140 | 135 | 8-9 |
| Trance | 130-145 | 138 | 7-9 |
| Hard techno | 140-160 | 148 | 9-10 |
| Industrial techno | 135-155 | 145 | 8-10 |
| Drum & bass | 170-180 | 174 | 7-10 |
| Acid techno | 130-145 | 138 | 7-9 |

### 8.2 What Makes a Good Melodic Techno Transition

Melodic techno demands the smoothest transitions in all of electronic music:

1. **Long blends are standard**: 16-32 bars minimum. The genres' atmospheric nature rewards patience.
2. **Harmonic compatibility is critical**: Always stay within Camelot +/-1. Dissonant keys destroy the mood.
3. **Use filter sweeps**: HPF on incoming track, slowly reveal over 16 bars. LPF on outgoing.
4. **Match the melodic energy**: Don't blend a dark, brooding track into a euphoric one without a bridge.
5. **Breakdown-to-intro blending**: The best transition point is outgoing track's outro/breakdown into incoming track's intro.
6. **Let tracks breathe**: Play each track for 4-5 minutes minimum. The genre is about journeys, not quick hits.

### 8.3 Key Artists & Their Mixing Styles

| Artist | Style | BPM Range | Mixing Approach |
|--------|-------|-----------|----------------|
| **Tale of Us** | Melodic techno, atmospheric | 120-130 | Long, seamless blends. Emotional arcs. Harmonic mixing essential. Dark-to-euphoric journeys. |
| **Solomun** | Deep house, eclectic house | 118-128 | Soulful selections. Mixes funk, R&B influence into house. Long blends. Genre-fluid. |
| **Charlotte de Witte** | Dark techno, hard techno | 132-148 | Driving, relentless energy. Shorter transitions. Raw, pounding rhythms. Industrial textures. |
| **Amelie Lens** | Hypnotic techno, acid | 130-142 | Bass-heavy, hypnotic loops. Builds tension through repetition. Powerful drops. |
| **Boris Brejcha** | High-tech minimal | 126-134 | Signature melodic hooks. Playful mixing. Long builds. Distinctive sound design. |
| **ARTBAT** | Melodic techno, progressive | 122-130 | Epic builds, emotional breakdowns. Clean harmonic transitions. Big-room feel. |
| **Peggy Gou** | House, tech house, eclectic | 120-128 | Genre-bending. Mixes house, disco, electro. Fun, crowd-reading approach. |
| **Adam Beyer** | Techno, driving techno | 130-138 | Precision mixing. Tool-based transitions. Technical, clean blends. Systematic. |
| **Nina Kraviz** | Acid techno, experimental | 128-145 | Eclectic selections. Unexpected track choices. Raw, unpolished aesthetic. Surprise-driven. |
| **Dixon** | Deep melodic techno | 120-128 | Ultra-long blends (2+ minutes). Atmospheric. Subtle. Almost invisible transitions. |

### 8.4 Festival vs Club Mixing

| Aspect | Festival | Club |
|--------|----------|------|
| **Energy arc** | Higher baseline, faster build | Gradual build from zero |
| **Transition style** | Shorter, more dramatic | Longer, subtler |
| **Track selection** | More anthems, recognizable tracks | Deeper cuts, DJ selections |
| **Effects use** | Heavy (reverb, build FX, noise sweeps) | Subtle (EQ, filters) |
| **BPM range** | Narrower (stay in peak range) | Wider (journey from low to high) |
| **Crowd reading** | Less individual, read energy en masse | More responsive, real-time adjustment |
| **Set length** | Typically 1-1.5 hours | 2-6 hours |
| **Transition speed** | Power-block mixing (rapid succession) | Full-track appreciation |

---

## 9. Actionable Rules for AI DJ

### Pre-Set Preparation

1. **Analyze every track in the library**: BPM, key (Camelot notation), energy level (1-10), genre tag
2. **Pre-compute compatible pairs**: For each track, list all tracks within +/-1 Camelot key AND +/-5 BPM
3. **Tag structural points**: Identify intro length, first drop, breakdown, outro start (in bars from start)
4. **Group by energy level**: Create energy-level buckets for quick access during set planning

### Track Selection Algorithm

```
For each next track selection:
1. Current track's Camelot key → find all tracks in compatible keys
2. Filter by BPM range: current_bpm +/- 4 BPM
3. Filter by energy: current_energy +/- 2 levels (prefer +1 during build, -1 during cooldown)
4. Filter by genre compatibility (if maintaining genre cohesion)
5. Avoid repeating artist within last 5 tracks
6. Prefer tracks not yet played
7. Score remaining candidates by harmonic smoothness + energy fit
8. Every 5-8 tracks: boost score for "surprise" candidates (different subgenre, unexpected key)
```

### Transition Execution Rules

```
WHEN transitioning from Track A to Track B:

1. TEMPO: Adjust Track B's BPM to match Track A (max adjustment: +/- 4%)
2. GAIN: Match Track B's peak level to Track A's
3. CUE POINT: Set Track B to start on its mix-in hot cue (or bar 1)
4. TIMING: Start Track B on beat 1 of an 8-bar phrase boundary in Track A
5. BLEND TYPE: Choose based on energy and genre:
   - Energy 1-5 → Long blend (16-32 bars)
   - Energy 5-7 → Medium blend (8-16 bars)
   - Energy 7-9 → Short blend (4-8 bars)
   - Hard cut → 0-2 bars (use with echo/delay out)
6. EQ MANAGEMENT:
   - Start: Track B bass at -inf, mids at -6dB, highs at 0dB
   - Gradually bring mids to 0 over first half of blend
   - BASS SWAP at phrase boundary (halfway or 3/4 through blend):
     → Track A bass to -inf, Track B bass to 0 simultaneously
   - Gradually remove Track A highs over final quarter of blend
7. FADER: Track A fader down to 0 by end of blend
8. CLEANUP: Ensure Track A is fully stopped and reset
```

### Timing Reference (at 128 BPM)

| Duration | Musical Length | Use |
|----------|--------------|-----|
| 1.875 sec | 1 bar (4 beats) | Quick cut timing |
| 7.5 sec | 4 bars (16 beats) | Short blend unit |
| 15 sec | 8 bars (32 beats) | Standard phrase |
| 30 sec | 16 bars (64 beats) | Medium blend |
| 60 sec | 32 bars (128 beats) | Long blend |
| 120 sec | 64 bars (256 beats) | Extended atmospheric blend |

**Formula**: `seconds_per_bar = (4 * 60) / BPM`

### Set Programming Template (2-Hour Set)

| Segment | Time | Tracks | Energy | BPM (House/Techno) | Transition Style |
|---------|------|--------|--------|-------------------|------------------|
| Opening | 0:00-0:20 | 3-4 | 3-4 | 120-122 | Long blends (32 bars) |
| Warm-up | 0:20-0:40 | 3-4 | 4-5 | 122-124 | Long blends (16-32 bars) |
| Building | 0:40-1:00 | 4-5 | 5-7 | 124-127 | Medium blends (16 bars) |
| Peak 1 | 1:00-1:15 | 3-4 | 7-8 | 127-130 | Medium-short blends (8-16 bars) |
| Breather | 1:15-1:25 | 2-3 | 6-7 | 128-130 | Medium blends (16 bars) |
| Peak 2 | 1:25-1:40 | 3-4 | 8-9 | 130-132 | Short blends (4-8 bars) |
| Cool-down | 1:40-1:50 | 2-3 | 6-7 | 128-130 | Medium blends (16 bars) |
| Closing | 1:50-2:00 | 2-3 | 5-4 | 125-128 | Long blends (32 bars) |
| **Total** | **2:00** | **~24-30** | | | |

### Error Prevention Rules

1. **Never play two basslines simultaneously** — always bass-swap
2. **Never blend tracks more than 6 BPM apart** — use hard cuts instead
3. **Never blend tracks more than +/-3 Camelot keys apart** — harmonic clash
4. **Never start a transition mid-phrase** — always on beat 1 of an 8-bar boundary
5. **Never play the same energy level for more than 4 consecutive tracks**
6. **Never end a set on a high-energy track** — always wind down
7. **Never apply echo/delay with feedback > 80%** — creates runaway feedback loops
8. **Never cut to a track without gain-matching first** — volume spikes destroy ears and speakers
9. **Never loop for more than 64 bars** — the crowd notices and it kills momentum
10. **Never ignore the key** — even one badly clashing transition undermines the whole set

### Mixxx HTTP API Mapping Notes

When controlling Mixxx, these concepts map to specific controls:

- **BPM/Tempo**: `rate` or `bpm` controls per deck
- **EQ Low/Mid/High**: `[EqualizerRack1_[Channel1]_Effect1]` parameters
- **Filters**: `[QuickEffectRack1_[Channel1]]` superknob (HPF/LPF)
- **Gain**: `pregain` control per channel
- **Crossfader**: `crossfader` control
- **Play/Cue**: `play`, `cue_default`, `hotcue_X_activate`
- **Loop**: `beatloop_X_activate` (where X = number of beats)
- **Sync**: `sync_enabled` or `beatsync`
- **Volume fader**: `volume` per channel

---

## Sources

- [DJ.Studio — Phrasing in DJ Mixing](https://dj.studio/blog/phrasing-dj-mixing)
- [PulseDJ — What is Phrasing](https://blog.pulsedj.com/what-is-phrasing)
- [LearningToDJ — Ultimate Guide to Phrasing](https://learningtodj.com/blog/ultimate-guide-to-phrasing-in-djing/)
- [DJ TechTools — Phrasing The Perfect Mix](https://djtechtools.com/2009/01/26/phrasing-the-perfect-mix/)
- [DJverse UK — Mastering Phrase Mixing](https://djverseuk.com/mastering-phrase-mixing-the-ultimate-dj-guide-for-2024/)
- [DJ.Studio — EQ Mixing Tips](https://dj.studio/blog/dj-eqmixing)
- [MusicRadar — 5 Essential EQ & Filter Tricks](https://www.musicradar.com/news/eq-and-filter-tricks-for-djs)
- [Digital DJ Tips — EQ, Filters and Effects](https://www.digitaldjtips.com/rock-the-dancefloor/adding-eq-filters-and-effects/)
- [DJ TechTools — Filter vs EQ](https://djtechtools.com/2011/12/07/filter-vs-eq-which-when-why/)
- [DJ TechTools — EQ Critical Techniques](https://djtechtools.com/amp/2012/03/11/eq-critical-dj-techniques-theory/)
- [Mixed In Key — Harmonic Mixing Guide](https://mixedinkey.com/harmonic-mixing-guide/)
- [DJ.Studio — Camelot Wheel Guide](https://dj.studio/blog/camelot-wheel)
- [Music City SF — Camelot Wheel Explained](https://musiccitysf.com/accelerator-blog/camelot-wheel-dj-mixing-guide/)
- [Mixed In Key — Camelot Wheel](https://mixedinkey.com/camelot-wheel/)
- [FaderPro — Camelot Wheel Explained](https://blog.faderpro.com/music-theory/camelot-wheel-dj-harmonic-mixing/)
- [DJ.Studio — Anatomy of a Great DJ Mix](https://dj.studio/blog/anatomy-great-dj-mix-structure-energy-flow-transition-logic)
- [The Ghost Production — Energy Flow in DJ Sets](https://theghostproduction.com/dj-resources/energy-flow-dj-sets/)
- [Mixed In Key — Control Energy Level](https://mixedinkey.com/book/control-the-energy-level-of-your-dj-sets/)
- [Musicianstool — Building the Perfect DJ Set](https://musicianstool.com/blog/building-the-perfect-dj-set-from-scratch)
- [ZIPDJ — Advanced DJ Techniques](https://www.zipdj.com/blog/advanced-dj-techniques)
- [DJ.Studio — 23 Advanced Mixing Techniques](https://dj.studio/blog/advanced-dj-mixing-techniques)
- [We Are Crossfader — 12 High-Energy Transitions](https://wearecrossfader.co.uk/blog/12-high-energy-dj-transitions/)
- [Mixed In Key — 5 Mixing Techniques](https://mixedinkey.com/wiki/5-mixing-techniques-every-dj-should-know/)
- [Pioneer DJ — Mixing Techniques Behind Every Genre](https://blog.pioneerdj.com/djtips/we-uncover-the-mixing-techniques-behind-every-major-genre/)
- [Pirate — DJ Volume & Gain Staging](https://pirate.com/en/blog/dj-tips/how-to-control-dj-volume-levels-gain-staging/)
- [DJ TechTools — Gain Staging for DJs](https://djtechtools.com/2015/10/11/gain-staging-for-djs-staying-out-of-the-red/)
- [VIPZONE — What is Double Dropping](https://www.vipzone-samples.com/en/what-is-double-dropping/)
- [Beatmatch Guru — How to Double Drop](https://beatmatchguru.com/how-to-double-drop-music-tracks-in-your-dj-sets/)
- [LearningToDJ — Echo DJ Effect](https://learningtodj.com/blog/understanding-the-echo-dj-effect/)
- [LearningToDJ — Delay DJ Effect](https://learningtodj.com/blog/understanding-the-delay-dj-effect/)
- [Digital DJ Tips — 3 Essential Effects](https://www.digitaldjtips.com/do-you-know-how-to-use-these-3-essential-dj-effects/)
- [Play House — Hard Techno BPM](https://playhousesound.com/what-is-the-bpm-of-most-modern-hard-techno-tracks-in-2026/)
- [Techno Airlines — Techno BPM Guide](https://www.technoairlines.com/blog/techno-bpm-the-heartbeat-of-techno-music)
- [Peace of Mind — BPMs in House & Techno](https://peaceofmind.link/understanding-bpms-in-house-techno-its-not-just-about-speed/)
- [ZIPDJ — House Music BPM](https://www.zipdj.com/blog/house-music-bpm)
- [Relentless Beats — How DJs Read a Crowd](https://relentlessbeats.com/2026/02/behind-the-booth-how-djs-read-a-crowd-and-control-a-nights-energy/)
- [LearningToDJ — Read the Dancefloor](https://learningtodj.com/blog/how-to-read-the-dancefloor-for-energy-cues/)
- [The Ghost Production — How to Read the Crowd](https://theghostproduction.com/dj-resources/how-to-read-the-crowd/)
- [Hobo Tech — DJ EQ Kill Switches](https://hobo-tech.com/technologies/livetips/dj-eq-adding-kill-switches/)
