#!/usr/bin/env node
/**
 * DJ Treta MCP Server
 *
 * Wraps the Mixxx HTTP API (port 7778) into native MCP tools
 * that any AI Being can use for DJ control.
 *
 * Tools: dj_load_track, dj_play, dj_pause, dj_stop, dj_eject,
 *        dj_crossfade, dj_transition, dj_sync, dj_eq, dj_filter,
 *        dj_volume, dj_status, dj_analyze_track, dj_list_tracks,
 *        dj_suggest_next, dj_search_youtube, dj_download_track,
 *        dj_set_history, dj_record, dj_energy_arc, dj_save_set
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { MixxxClient } from './mixxx-client.js';
import {
  mixxxKeyToCamelot,
  mixxxKeyToMusical,
  formatKeyInfo,
  getCompatibleKeys,
} from './camelot.js';
import { readdirSync, statSync, existsSync, writeFileSync, mkdirSync } from 'fs';
import { join, basename, extname } from 'path';
import { execSync, exec } from 'child_process';
import { homedir } from 'os';

// ── Config ──────────────────────────────────────────────────────────

const MIXXX_API = process.env.MIXXX_API || 'http://localhost:7778';
const MUSIC_DIR = process.env.DJ_MUSIC_DIR || join(homedir(), 'Music', 'DJTreta');
const AUDIO_EXTENSIONS = new Set(['.mp3', '.flac', '.wav', '.ogg', '.m4a', '.aac', '.opus']);

// ── Set History State ────────────────────────────────────────────────

interface SetEntry {
  track: string;
  deck: number;
  timestamp: string;
  energy?: number;
  technique?: string;
}

let setHistory: SetEntry[] = [];
const SETS_DIR = join(homedir(), 'beings', 'himani', 'skills', 'dj', 'sets');

function estimateEnergy(bpm: number): number {
  // Heuristic energy estimation based on BPM
  // <100 = chill (1-3), 100-125 = moderate (3-5), 125-135 = energetic (5-7), 135+ = high (7-10)
  if (bpm <= 0) return 5; // unknown
  if (bpm < 100) return Math.max(1, Math.round((bpm - 60) / 15) + 1);
  if (bpm < 125) return Math.round(3 + (bpm - 100) * 0.08);
  if (bpm < 135) return Math.round(5 + (bpm - 125) * 0.2);
  return Math.min(10, Math.round(7 + (bpm - 135) * 0.1));
}

function isTrackAlreadyPlayed(trackPath: string): boolean {
  const trackName = basename(trackPath);
  return setHistory.some(entry => {
    const entryName = basename(entry.track);
    return entryName === trackName || entry.track === trackPath;
  });
}

// ── Initialize ──────────────────────────────────────────────────────

const mixxx = new MixxxClient(MIXXX_API);

const server = new McpServer({
  name: 'dj-treta',
  version: '1.0.0',
});

// ── Helpers ─────────────────────────────────────────────────────────

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function formatDeckInfo(deck: any, deckNum: number): string {
  if (!deck.track_loaded) {
    return `Deck ${deckNum}: [empty]`;
  }
  const keyStr = formatKeyInfo(deck.key);
  const playing = deck.playing ? 'PLAYING' : 'PAUSED';
  const sync = deck.sync_enabled ? ' [SYNC]' : '';
  const pos = formatTime(deck.position_seconds);
  const dur = formatTime(deck.duration);
  const rem = formatTime(deck.remaining_seconds);
  return [
    `Deck ${deckNum}: ${playing}${sync}`,
    `  BPM: ${deck.bpm.toFixed(1)} (file: ${deck.file_bpm})`,
    `  Key: ${keyStr}`,
    `  Position: ${pos} / ${dur} (${rem} remaining)`,
    `  Volume: ${(deck.volume * 100).toFixed(0)}%`,
    `  EQ — Hi: ${deck.eq_hi.toFixed(2)} Mid: ${deck.eq_mid.toFixed(2)} Lo: ${deck.eq_lo.toFixed(2)}`,
    `  Rate: ${(deck.rate * 100).toFixed(1)}%`,
  ].join('\n');
}

function scanMusicDir(): { genre: string; tracks: { name: string; path: string }[] }[] {
  if (!existsSync(MUSIC_DIR)) return [];

  const genres: { genre: string; tracks: { name: string; path: string }[] }[] = [];

  const entries = readdirSync(MUSIC_DIR);
  for (const entry of entries) {
    const fullPath = join(MUSIC_DIR, entry);
    try {
      if (!statSync(fullPath).isDirectory()) continue;
      if (entry.startsWith('.') || entry.startsWith('_')) continue;

      const tracks: { name: string; path: string }[] = [];
      const files = readdirSync(fullPath);
      for (const file of files) {
        const ext = extname(file).toLowerCase();
        if (AUDIO_EXTENSIONS.has(ext)) {
          tracks.push({
            name: basename(file, ext),
            path: join(fullPath, file),
          });
        }
      }

      if (tracks.length > 0) {
        genres.push({ genre: entry, tracks: tracks.sort((a, b) => a.name.localeCompare(b.name)) });
      }
    } catch {
      // skip unreadable dirs
    }
  }

  return genres.sort((a, b) => a.genre.localeCompare(b.genre));
}

async function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ── Deck Validation Schema ──────────────────────────────────────────

const DeckSchema = z.number().int().min(1).max(2).describe('Deck number (1 or 2)');

// ── Tool: dj_status ─────────────────────────────────────────────────

server.tool(
  'dj_status',
  'Get full DJ status — both decks, crossfader, BPM, key, remaining time',
  {},
  async () => {
    try {
      const status = await mixxx.getStatus();

      // Mixxx crossfader: -1.0 (Deck 1) to 1.0 (Deck 2)
      // Normalize to 0.0–1.0 for human readability
      const crossRaw = status.crossfader;
      const crossNorm = (crossRaw + 1) / 2; // -1→0, 0→0.5, 1→1
      const crossLabel =
        crossNorm < 0.3 ? 'Deck 1' :
        crossNorm > 0.7 ? 'Deck 2' :
        'Center';

      const lines = [
        `Engine: ${status.engine}`,
        `Crossfader: ${crossNorm.toFixed(2)} (${crossLabel})`,
        `Master Volume: ${(status.master_volume * 100).toFixed(0)}%`,
        '',
        formatDeckInfo(status.deck1, 1),
        '',
        formatDeckInfo(status.deck2, 2),
      ];

      return { content: [{ type: 'text', text: lines.join('\n') }] };
    } catch (e: any) {
      return { content: [{ type: 'text', text: `Mixxx not reachable: ${e.message}` }], isError: true };
    }
  }
);

// ── Tool: dj_load_track ─────────────────────────────────────────────

server.tool(
  'dj_load_track',
  'Load a track file onto a deck. Warns if track was already played in this set (use force=true to override)',
  {
    deck: z.number().int().min(1).max(2).describe('Deck number (1 or 2)'),
    track: z.string().describe('Full file path to the audio track'),
    force: z.boolean().default(false).describe('Force load even if track was already played'),
    technique: z.string().optional().describe('Transition technique used (for set history logging)'),
  },
  async ({ deck, track, force, technique }) => {
    try {
      // Expand ~ if present
      const trackPath = track.replace(/^~/, homedir());

      if (!existsSync(trackPath)) {
        return { content: [{ type: 'text', text: `File not found: ${trackPath}` }], isError: true };
      }

      // Check for repeat
      if (isTrackAlreadyPlayed(trackPath) && !force) {
        return {
          content: [{
            type: 'text',
            text: `WARNING: "${basename(trackPath)}" was already played in this set. Use force=true to load anyway.`,
          }],
          isError: true,
        };
      }

      const result = await mixxx.loadTrack(deck, trackPath);

      // Estimate energy from deck analysis after load
      let energy = 5;
      try {
        await sleep(500); // brief pause for Mixxx to analyze
        const deckStatus = await mixxx.getDeckStatus(deck);
        if (deckStatus.track_loaded && deckStatus.bpm > 0) {
          energy = estimateEnergy(deckStatus.bpm);
        }
      } catch {
        // non-critical, use default energy
      }

      // Log to set history
      const entry: SetEntry = {
        track: trackPath,
        deck,
        timestamp: new Date().toISOString(),
        energy,
        technique,
      };
      setHistory.push(entry);

      const repeatNote = isTrackAlreadyPlayed(trackPath) ? ' (REPEAT — forced)' : '';
      return { content: [{ type: 'text', text: `Loaded onto Deck ${deck}: ${basename(trackPath)}${repeatNote}\nEnergy: ${energy}/10\n${JSON.stringify(result)}` }] };
    } catch (e: any) {
      return { content: [{ type: 'text', text: `Failed to load track: ${e.message}` }], isError: true };
    }
  }
);

// ── Tool: dj_play ───────────────────────────────────────────────────

server.tool(
  'dj_play',
  'Start playing a deck',
  {
    deck: z.number().int().min(1).max(2).describe('Deck number (1 or 2)'),
  },
  async ({ deck }) => {
    try {
      await mixxx.play(deck);
      return { content: [{ type: 'text', text: `Deck ${deck}: playing` }] };
    } catch (e: any) {
      return { content: [{ type: 'text', text: `Failed: ${e.message}` }], isError: true };
    }
  }
);

// ── Tool: dj_pause ──────────────────────────────────────────────────

server.tool(
  'dj_pause',
  'Pause a deck',
  {
    deck: z.number().int().min(1).max(2).describe('Deck number (1 or 2)'),
  },
  async ({ deck }) => {
    try {
      await mixxx.pause(deck);
      return { content: [{ type: 'text', text: `Deck ${deck}: paused` }] };
    } catch (e: any) {
      return { content: [{ type: 'text', text: `Failed: ${e.message}` }], isError: true };
    }
  }
);

// ── Tool: dj_stop ───────────────────────────────────────────────────

server.tool(
  'dj_stop',
  'Stop and reset a deck to the beginning',
  {
    deck: z.number().int().min(1).max(2).describe('Deck number (1 or 2)'),
  },
  async ({ deck }) => {
    try {
      await mixxx.stop(deck);
      return { content: [{ type: 'text', text: `Deck ${deck}: stopped and reset` }] };
    } catch (e: any) {
      return { content: [{ type: 'text', text: `Failed: ${e.message}` }], isError: true };
    }
  }
);

// ── Tool: dj_eject ──────────────────────────────────────────────────

server.tool(
  'dj_eject',
  'Eject the track from a deck',
  {
    deck: z.number().int().min(1).max(2).describe('Deck number (1 or 2)'),
  },
  async ({ deck }) => {
    try {
      await mixxx.eject(deck);
      return { content: [{ type: 'text', text: `Deck ${deck}: ejected` }] };
    } catch (e: any) {
      return { content: [{ type: 'text', text: `Failed: ${e.message}` }], isError: true };
    }
  }
);

// ── Tool: dj_crossfade ──────────────────────────────────────────────

server.tool(
  'dj_crossfade',
  'Set crossfader position (0.0 = full Deck 1, 0.5 = center, 1.0 = full Deck 2)',
  {
    position: z.number().min(0).max(1).describe('Crossfader position 0.0–1.0'),
  },
  async ({ position }) => {
    try {
      // Convert 0.0–1.0 input to Mixxx's -1.0–1.0 range
      const mixxxPos = position * 2 - 1;
      await mixxx.setCrossfader(mixxxPos);
      const label = position < 0.3 ? 'Deck 1' : position > 0.7 ? 'Deck 2' : 'Center';
      return { content: [{ type: 'text', text: `Crossfader: ${position.toFixed(2)} (${label})` }] };
    } catch (e: any) {
      return { content: [{ type: 'text', text: `Failed: ${e.message}` }], isError: true };
    }
  }
);

// ── Tool: dj_volume ─────────────────────────────────────────────────

server.tool(
  'dj_volume',
  'Set the volume level for a deck',
  {
    deck: z.number().int().min(1).max(2).describe('Deck number (1 or 2)'),
    level: z.number().min(0).max(1).describe('Volume level 0.0–1.0'),
  },
  async ({ deck, level }) => {
    try {
      await mixxx.setVolume(deck, level);
      return { content: [{ type: 'text', text: `Deck ${deck} volume: ${(level * 100).toFixed(0)}%` }] };
    } catch (e: any) {
      return { content: [{ type: 'text', text: `Failed: ${e.message}` }], isError: true };
    }
  }
);

// ── Tool: dj_eq ─────────────────────────────────────────────────────

server.tool(
  'dj_eq',
  'Set EQ bands on a deck (0.0 = full cut, 1.0 = full boost, 1.0 = neutral)',
  {
    deck: z.number().int().min(1).max(2).describe('Deck number (1 or 2)'),
    hi: z.number().min(0).max(4).optional().describe('High EQ (0.0–4.0, neutral=1.0)'),
    mid: z.number().min(0).max(4).optional().describe('Mid EQ (0.0–4.0, neutral=1.0)'),
    lo: z.number().min(0).max(4).optional().describe('Low/Bass EQ (0.0–4.0, neutral=1.0)'),
  },
  async ({ deck, hi, mid, lo }) => {
    try {
      await mixxx.setEQ(deck, hi, mid, lo);
      const parts: string[] = [];
      if (hi !== undefined) parts.push(`Hi=${hi.toFixed(2)}`);
      if (mid !== undefined) parts.push(`Mid=${mid.toFixed(2)}`);
      if (lo !== undefined) parts.push(`Lo=${lo.toFixed(2)}`);
      return { content: [{ type: 'text', text: `Deck ${deck} EQ: ${parts.join(', ')}` }] };
    } catch (e: any) {
      return { content: [{ type: 'text', text: `Failed: ${e.message}` }], isError: true };
    }
  }
);

// ── Tool: dj_filter ─────────────────────────────────────────────────

server.tool(
  'dj_filter',
  'Set the quick effect / filter knob on a deck (0.0 = full LPF, 0.5 = neutral, 1.0 = full HPF)',
  {
    deck: z.number().int().min(1).max(2).describe('Deck number (1 or 2)'),
    value: z.number().min(0).max(1).describe('Filter value 0.0–1.0 (0.5=neutral)'),
  },
  async ({ deck, value }) => {
    try {
      await mixxx.setFilter(deck, value);
      const label = value < 0.4 ? 'LPF' : value > 0.6 ? 'HPF' : 'Neutral';
      return { content: [{ type: 'text', text: `Deck ${deck} filter: ${value.toFixed(2)} (${label})` }] };
    } catch (e: any) {
      return { content: [{ type: 'text', text: `Failed: ${e.message}` }], isError: true };
    }
  }
);

// ── Tool: dj_sync ───────────────────────────────────────────────────

server.tool(
  'dj_sync',
  'Enable beat sync on a deck — locks BPM to the other deck',
  {
    deck: z.number().int().min(1).max(2).describe('Deck number (1 or 2)'),
  },
  async ({ deck }) => {
    try {
      await mixxx.setSync(deck, true);
      return { content: [{ type: 'text', text: `Deck ${deck}: sync enabled` }] };
    } catch (e: any) {
      return { content: [{ type: 'text', text: `Failed: ${e.message}` }], isError: true };
    }
  }
);

// ── Tool: dj_transition ─────────────────────────────────────────────

server.tool(
  'dj_transition',
  'Smooth crossfade transition to a deck. Techniques: blend (S-curve crossfade), bass_swap (EQ swap at midpoint), filter_sweep (HPF reveal)',
  {
    deck: z.number().int().min(1).max(2).describe('Target deck to transition TO (1 or 2)'),
    duration: z.number().min(5).max(300).default(60).describe('Transition duration in seconds (5–300)'),
    technique: z.enum(['blend', 'bass_swap', 'filter_sweep']).default('blend').describe('Transition technique'),
  },
  async ({ deck, duration, technique }) => {
    try {
      if (technique === 'blend') {
        // Use Mixxx built-in transition (S-curve crossfade)
        await mixxx.transition(deck, duration);
        return { content: [{ type: 'text', text: `Blend transition to Deck ${deck} started (${duration}s). Mixxx is handling the S-curve crossfade.` }] };
      }

      if (technique === 'bass_swap') {
        // Bass swap: cut incoming bass, crossfade to center, swap bass, fade out old
        // Run as a background fire-and-forget operation
        runBassSwapTransition(deck, duration);
        return { content: [{ type: 'text', text: `Bass swap transition to Deck ${deck} started (${duration}s).\nPhase 1 (0–30%): Incoming bass cut, crossfade to center\nPhase 2 (30–50%): Bass swap — the drop\nPhase 3 (50–100%): Fade out old deck, reset EQ` }] };
      }

      if (technique === 'filter_sweep') {
        // Filter sweep: HPF on incoming, crossfade while opening filter
        runFilterSweepTransition(deck, duration);
        return { content: [{ type: 'text', text: `Filter sweep transition to Deck ${deck} started (${duration}s).\nPhase 1 (0–40%): HPF on incoming, start crossfade\nPhase 2 (40–80%): Open filter while crossfading\nPhase 3 (80–100%): Full crossfade, reset filter` }] };
      }

      return { content: [{ type: 'text', text: `Unknown technique: ${technique}` }], isError: true };
    } catch (e: any) {
      return { content: [{ type: 'text', text: `Failed: ${e.message}` }], isError: true };
    }
  }
);

// Background transition: bass swap
async function runBassSwapTransition(toDeck: number, duration: number) {
  const otherDeck = toDeck === 1 ? 2 : 1;
  const steps = 20; // 20 steps per phase

  try {
    // Note: Mixxx crossfader uses -1.0 to 1.0 (-1=Deck1, 1=Deck2)
    // Phase 1: Cut incoming bass, crossfade to center (30% of duration)
    await mixxx.setEQ(toDeck, undefined, undefined, 0);
    const phase1Duration = duration * 0.3;
    const phase1Step = (phase1Duration * 1000) / steps;
    for (let i = 0; i <= steps; i++) {
      const r = i / steps;
      const target = toDeck === 2 ? -1.0 + r * 1.0 : 1.0 - r * 1.0; // move to center (0)
      await mixxx.setCrossfader(target);
      await sleep(phase1Step);
    }

    // Phase 2: Bass swap (20% of duration)
    const phase2Duration = duration * 0.2;
    const phase2Step = (phase2Duration * 1000) / steps;
    for (let i = 0; i <= steps; i++) {
      const r = i / steps;
      await mixxx.setEQ(otherDeck, undefined, undefined, 1.0 - r); // Kill outgoing bass
      await mixxx.setEQ(toDeck, undefined, undefined, r);           // Bring incoming bass
      await sleep(phase2Step);
    }

    // Phase 3: Fade out old deck (50% of duration)
    const phase3Duration = duration * 0.5;
    const phase3Step = (phase3Duration * 1000) / steps;
    for (let i = 0; i <= steps; i++) {
      const r = i / steps;
      const s = r * r * (3 - 2 * r); // S-curve
      const target = toDeck === 2 ? s * 1.0 : -s * 1.0; // center → full other deck
      await mixxx.setCrossfader(target);
      await sleep(phase3Step);
    }

    // Reset EQ
    await mixxx.setEQ(otherDeck, undefined, undefined, 1.0);
    await mixxx.setEQ(toDeck, undefined, undefined, 1.0);
  } catch (e) {
    // Background operation — log but don't crash
    console.error('[dj_transition:bass_swap] Error:', e);
  }
}

// Background transition: filter sweep
async function runFilterSweepTransition(toDeck: number, duration: number) {
  const steps = 20;

  try {
    // Note: Mixxx crossfader uses -1.0 to 1.0 (-1=Deck1, 1=Deck2)
    // Start with HPF on incoming deck
    await mixxx.setFilter(toDeck, 1.0); // Full HPF

    // Phase 1: Start crossfade with HPF (40%)
    const phase1Duration = duration * 0.4;
    const phase1Step = (phase1Duration * 1000) / steps;
    for (let i = 0; i <= steps; i++) {
      const r = i / steps;
      const target = toDeck === 2 ? -1.0 + r * 0.8 : 1.0 - r * 0.8; // move toward center
      await mixxx.setCrossfader(target);
      await sleep(phase1Step);
    }

    // Phase 2: Open filter while crossfading (40%)
    const phase2Duration = duration * 0.4;
    const phase2Step = (phase2Duration * 1000) / steps;
    for (let i = 0; i <= steps; i++) {
      const r = i / steps;
      const filterVal = 1.0 - r * 0.5; // HPF → neutral
      await mixxx.setFilter(toDeck, filterVal);
      const crossTarget = toDeck === 2 ? -0.2 + r * 0.8 : 0.2 - r * 0.8; // continue toward target
      await mixxx.setCrossfader(crossTarget);
      await sleep(phase2Step);
    }

    // Phase 3: Final crossfade, reset filter (20%)
    const phase3Duration = duration * 0.2;
    const phase3Step = (phase3Duration * 1000) / steps;
    for (let i = 0; i <= steps; i++) {
      const r = i / steps;
      const target = toDeck === 2 ? 0.6 + r * 0.4 : -0.6 - r * 0.4; // finish to full
      await mixxx.setCrossfader(target);
      await sleep(phase3Step);
    }

    // Reset filter to neutral
    await mixxx.setFilter(toDeck, 0.5);
  } catch (e) {
    console.error('[dj_transition:filter_sweep] Error:', e);
  }
}

// ── Tool: dj_analyze_track ──────────────────────────────────────────

server.tool(
  'dj_analyze_track',
  'Get analysis info for the track loaded on a deck (BPM, key, position, duration)',
  {
    deck: z.number().int().min(1).max(2).describe('Deck number (1 or 2)'),
  },
  async ({ deck }) => {
    try {
      const status = await mixxx.getDeckStatus(deck);

      if (!status.track_loaded) {
        return { content: [{ type: 'text', text: `Deck ${deck}: no track loaded` }], isError: true };
      }

      const keyStr = formatKeyInfo(status.key);
      const camelot = mixxxKeyToCamelot(status.key);

      const info = [
        `Deck ${deck} Track Analysis:`,
        `  BPM: ${status.bpm.toFixed(1)} (file: ${status.file_bpm})`,
        `  Key: ${keyStr}`,
        `  Duration: ${formatTime(status.duration)}`,
        `  Position: ${formatTime(status.position_seconds)} (${(status.position * 100).toFixed(1)}%)`,
        `  Remaining: ${formatTime(status.remaining_seconds)}`,
        `  Rate adjustment: ${(status.rate * 100).toFixed(1)}%`,
        `  Sync: ${status.sync_enabled ? 'ON' : 'OFF'}`,
        `  Loop: ${status.loop_enabled ? 'ON' : 'OFF'}`,
      ];

      if (camelot) {
        const compatible = getCompatibleKeys(camelot);
        info.push(`  Compatible keys (Camelot): ${compatible.join(', ')}`);
      }

      return { content: [{ type: 'text', text: info.join('\n') }] };
    } catch (e: any) {
      return { content: [{ type: 'text', text: `Failed: ${e.message}` }], isError: true };
    }
  }
);

// ── Tool: dj_list_tracks ────────────────────────────────────────────

server.tool(
  'dj_list_tracks',
  'List available tracks from the DJ music library, organized by genre folder',
  {},
  async () => {
    const genres = scanMusicDir();

    if (genres.length === 0) {
      return { content: [{ type: 'text', text: `No tracks found in ${MUSIC_DIR}` }], isError: true };
    }

    let totalTracks = 0;
    const lines: string[] = [`DJ Treta Library — ${MUSIC_DIR}\n`];

    for (const genre of genres) {
      lines.push(`${genre.genre}/ (${genre.tracks.length} tracks)`);
      for (const track of genre.tracks) {
        lines.push(`  - ${track.name}`);
        totalTracks++;
      }
      lines.push('');
    }

    lines.push(`Total: ${totalTracks} tracks across ${genres.length} genres`);

    return { content: [{ type: 'text', text: lines.join('\n') }] };
  }
);

// ── Tool: dj_suggest_next ───────────────────────────────────────────

server.tool(
  'dj_suggest_next',
  'Suggest harmonically compatible tracks based on the currently playing deck\'s key (Camelot wheel)',
  {
    deck: z.number().int().min(1).max(2).describe('Deck to base suggestions on (1 or 2)'),
  },
  async ({ deck }) => {
    try {
      const status = await mixxx.getDeckStatus(deck);

      if (!status.track_loaded) {
        return { content: [{ type: 'text', text: `Deck ${deck}: no track loaded, cannot suggest` }], isError: true };
      }

      const currentKey = status.key;
      const currentCamelot = mixxxKeyToCamelot(currentKey);
      const currentBpm = status.bpm;

      if (!currentCamelot) {
        return { content: [{ type: 'text', text: `Deck ${deck}: key not detected, cannot suggest harmonically` }], isError: true };
      }

      const compatibleCamelot = getCompatibleKeys(currentCamelot);

      const lines: string[] = [
        `Current: ${formatKeyInfo(currentKey)} at ${currentBpm.toFixed(1)} BPM`,
        `Compatible keys: ${compatibleCamelot.join(', ')}`,
        '',
        `Suggested approach:`,
        `  - Same key (${currentCamelot}): safest, always works`,
        `  - Adjacent keys: subtle energy change`,
        `  - Relative major/minor: mood shift while staying harmonic`,
        '',
        `BPM range for smooth mixing: ${(currentBpm - 3).toFixed(0)}–${(currentBpm + 3).toFixed(0)} BPM`,
        `(Mixxx sync can handle larger gaps, but ±3 sounds most natural)`,
        '',
        `Available tracks from library:`,
      ];

      // Scan library, exclude already-played tracks
      const genres = scanMusicDir();
      let trackCount = 0;
      let skippedCount = 0;
      for (const genre of genres) {
        for (const track of genre.tracks) {
          if (isTrackAlreadyPlayed(track.path)) {
            skippedCount++;
            continue; // exclude already-played tracks
          }
          lines.push(`  [${genre.genre}] ${track.name}`);
          trackCount++;
        }
      }

      if (trackCount === 0 && skippedCount === 0) {
        lines.push('  (no tracks in library)');
      } else if (trackCount === 0) {
        lines.push(`  (all ${skippedCount} tracks already played!)`);
      } else {
        if (skippedCount > 0) {
          lines.push('');
          lines.push(`(${skippedCount} already-played track${skippedCount > 1 ? 's' : ''} excluded)`);
        }
        lines.push('');
        lines.push(`Load a track and Mixxx will analyze its key. Use dj_analyze_track to check compatibility.`);
      }

      return { content: [{ type: 'text', text: lines.join('\n') }] };
    } catch (e: any) {
      return { content: [{ type: 'text', text: `Failed: ${e.message}` }], isError: true };
    }
  }
);

// ── Tool: dj_search_youtube ─────────────────────────────────────────

server.tool(
  'dj_search_youtube',
  'Search YouTube for tracks to download',
  {
    query: z.string().describe('Search query (e.g., "amelie lens dark techno")'),
    limit: z.number().int().min(1).max(20).default(5).describe('Number of results (1–20)'),
  },
  async ({ query, limit }) => {
    try {
      const cmd = `yt-dlp "ytsearch${limit}:${query.replace(/"/g, '\\"')}" --dump-json --no-download --flat-playlist 2>/dev/null`;
      const output = execSync(cmd, { encoding: 'utf-8', timeout: 30000, maxBuffer: 10 * 1024 * 1024 });

      const results: any[] = [];
      for (const line of output.trim().split('\n')) {
        if (!line) continue;
        try {
          const info = JSON.parse(line);
          results.push({
            title: info.title || 'Unknown',
            url: info.url || info.webpage_url || '',
            id: info.id || '',
            duration: info.duration || 0,
            uploader: info.uploader || info.channel || 'Unknown',
          });
        } catch {
          continue;
        }
      }

      if (results.length === 0) {
        return { content: [{ type: 'text', text: `No results for: ${query}` }] };
      }

      const lines = [`YouTube search: "${query}" (${results.length} results)\n`];
      for (let i = 0; i < results.length; i++) {
        const r = results[i];
        const dur = r.duration ? formatTime(r.duration) : '?';
        lines.push(`${i + 1}. ${r.title} (${dur})`);
        lines.push(`   ${r.uploader}`);
        lines.push(`   https://youtube.com/watch?v=${r.id}`);
        lines.push('');
      }

      return { content: [{ type: 'text', text: lines.join('\n') }] };
    } catch (e: any) {
      return { content: [{ type: 'text', text: `Search failed: ${e.message}` }], isError: true };
    }
  }
);

// ── Tool: dj_download_track ─────────────────────────────────────────

server.tool(
  'dj_download_track',
  'Download a track from YouTube via yt-dlp into the DJ library',
  {
    url: z.string().describe('YouTube URL to download'),
    genre: z.string().default('deep').describe('Genre folder to save into (e.g., dark-techno, melodic-techno, deep, minimal, progressive, vocal)'),
  },
  async ({ url, genre }) => {
    try {
      const outputDir = join(MUSIC_DIR, genre);

      // Ensure genre directory exists
      execSync(`mkdir -p "${outputDir}"`);

      // First get info
      const infoCmd = `yt-dlp --dump-json --no-download "${url}" 2>/dev/null`;
      let info: any;
      try {
        const infoOutput = execSync(infoCmd, { encoding: 'utf-8', timeout: 30000 });
        info = JSON.parse(infoOutput);
      } catch {
        return { content: [{ type: 'text', text: `Could not fetch info for: ${url}` }], isError: true };
      }

      const title = info.title || 'Unknown';
      const uploader = info.uploader || 'Unknown';
      const duration = info.duration || 0;

      // Sanitize filename
      const filename = `${uploader} - ${title}`.replace(/[<>:"/\\|?*]/g, '').replace(/\s+/g, ' ').trim().slice(0, 200);

      // Check if already exists
      const expectedPath = join(outputDir, `${filename}.mp3`);
      if (existsSync(expectedPath)) {
        return { content: [{ type: 'text', text: `Already exists: ${filename}.mp3 in ${genre}/` }] };
      }

      // Download
      const dlCmd = `yt-dlp -x --audio-format mp3 --audio-quality 320 -o "${join(outputDir, `${filename}.%(ext)s`)}" --no-playlist --no-overwrites "${url}" 2>&1`;

      // Run download in background — don't block the tool response
      exec(dlCmd, { timeout: 300000 }, (err, stdout, stderr) => {
        if (err) {
          console.error(`[dj_download] Error downloading ${url}: ${err.message}`);
        } else {
          console.error(`[dj_download] Completed: ${filename}.mp3`);
        }
      });

      return {
        content: [{
          type: 'text',
          text: [
            `Download started:`,
            `  Title: ${title}`,
            `  Artist: ${uploader}`,
            `  Duration: ${formatTime(duration)}`,
            `  Destination: ${genre}/${filename}.mp3`,
            ``,
            `Download is running in the background. Use dj_list_tracks to check when it appears.`,
          ].join('\n'),
        }],
      };
    } catch (e: any) {
      return { content: [{ type: 'text', text: `Download failed: ${e.message}` }], isError: true };
    }
  }
);

// ── Tool: dj_set_history ─────────────────────────────────────────

server.tool(
  'dj_set_history',
  'Returns list of tracks played in this session with timestamps, energy, and techniques',
  {},
  async () => {
    if (setHistory.length === 0) {
      return { content: [{ type: 'text', text: 'No tracks played yet in this set.' }] };
    }

    const lines: string[] = [`Set History (${setHistory.length} tracks):\n`];
    for (let i = 0; i < setHistory.length; i++) {
      const entry = setHistory[i];
      const time = new Date(entry.timestamp).toLocaleTimeString();
      const energyStr = entry.energy ? ` [Energy: ${entry.energy}/10]` : '';
      const techStr = entry.technique ? ` (${entry.technique})` : '';
      lines.push(`${i + 1}. ${time} — Deck ${entry.deck}: ${basename(entry.track)}${energyStr}${techStr}`);
    }

    return { content: [{ type: 'text', text: lines.join('\n') }] };
  }
);

// ── Tool: dj_record ─────────────────────────────────────────────

server.tool(
  'dj_record',
  'Start, stop, or check status of Mixxx recording',
  {
    action: z.enum(['start', 'stop', 'status']).describe('Recording action: start, stop, or status'),
  },
  async ({ action }) => {
    try {
      if (action === 'status') {
        const val = await mixxx.getControl('[Recording]', 'status');
        const statusLabel = val === 2 ? 'RECORDING' : val === 1 ? 'READY' : 'STOPPED';
        return { content: [{ type: 'text', text: `Recording status: ${statusLabel}` }] };
      }

      // toggle_recording toggles between recording and not recording
      await mixxx.control('[Recording]', 'toggle_recording', 1);

      // Brief pause then check status
      await sleep(500);
      const val = await mixxx.getControl('[Recording]', 'status');
      const statusLabel = val === 2 ? 'RECORDING' : val === 1 ? 'READY' : 'STOPPED';

      return { content: [{ type: 'text', text: `Recording ${action === 'start' ? 'started' : 'stopped'}. Status: ${statusLabel}` }] };
    } catch (e: any) {
      return { content: [{ type: 'text', text: `Recording failed: ${e.message}` }], isError: true };
    }
  }
);

// ── Tool: dj_energy_arc ─────────────────────────────────────────

server.tool(
  'dj_energy_arc',
  'Returns the energy arc over the current set — energy level for each track over time',
  {},
  async () => {
    if (setHistory.length === 0) {
      return { content: [{ type: 'text', text: 'No tracks played yet — no energy data.' }] };
    }

    const lines: string[] = ['Energy Arc:\n'];

    for (let i = 0; i < setHistory.length; i++) {
      const entry = setHistory[i];
      const energy = entry.energy ?? 5;
      const bar = '\u2588'.repeat(energy) + '\u2591'.repeat(10 - energy);
      const time = new Date(entry.timestamp).toLocaleTimeString();
      lines.push(`${time} [${bar}] ${energy}/10  ${basename(entry.track)}`);
    }

    // Summary stats
    const energies = setHistory.map(e => e.energy ?? 5);
    const avg = energies.reduce((a, b) => a + b, 0) / energies.length;
    const peak = Math.max(...energies);
    const low = Math.min(...energies);

    lines.push('');
    lines.push(`Average energy: ${avg.toFixed(1)}/10`);
    lines.push(`Peak: ${peak}/10 | Low: ${low}/10`);
    lines.push(`Tracks: ${setHistory.length}`);

    return { content: [{ type: 'text', text: lines.join('\n') }] };
  }
);

// ── Tool: dj_save_set ───────────────────────────────────────────

server.tool(
  'dj_save_set',
  'Save the current set history, energy arc, and metadata to a JSON file',
  {},
  async () => {
    if (setHistory.length === 0) {
      return { content: [{ type: 'text', text: 'No tracks played — nothing to save.' }], isError: true };
    }

    // Create sets directory if needed
    if (!existsSync(SETS_DIR)) {
      mkdirSync(SETS_DIR, { recursive: true });
    }

    const now = new Date();
    const dateStr = now.toISOString().slice(0, 10);
    const timeStr = now.toTimeString().slice(0, 5).replace(':', '-');
    const filename = `${dateStr}_${timeStr}.json`;
    const filepath = join(SETS_DIR, filename);

    // Calculate duration
    const firstTimestamp = new Date(setHistory[0].timestamp);
    const lastTimestamp = new Date(setHistory[setHistory.length - 1].timestamp);
    const durationMinutes = Math.round((lastTimestamp.getTime() - firstTimestamp.getTime()) / 60000);

    // Build energy arc
    const energyArc = setHistory.map(entry => ({
      time: entry.timestamp,
      energy: entry.energy ?? 5,
      track: basename(entry.track),
    }));

    const energies = setHistory.map(e => e.energy ?? 5);

    const setData = {
      date: dateStr,
      start_time: setHistory[0].timestamp,
      end_time: now.toISOString(),
      duration_minutes: durationMinutes,
      track_count: setHistory.length,
      tracks: setHistory.map((entry, i) => ({
        position: i + 1,
        track: basename(entry.track),
        path: entry.track,
        deck: entry.deck,
        timestamp: entry.timestamp,
        energy: entry.energy ?? 5,
        technique: entry.technique || null,
      })),
      energy_arc: energyArc,
      energy_stats: {
        average: parseFloat((energies.reduce((a, b) => a + b, 0) / energies.length).toFixed(1)),
        peak: Math.max(...energies),
        low: Math.min(...energies),
      },
    };

    writeFileSync(filepath, JSON.stringify(setData, null, 2));

    return {
      content: [{
        type: 'text',
        text: [
          `Set saved: ${filepath}`,
          `Tracks: ${setHistory.length}`,
          `Duration: ${durationMinutes} minutes`,
          `Avg energy: ${setData.energy_stats.average}/10`,
        ].join('\n'),
      }],
    };
  }
);

// ── Start Server ────────────────────────────────────────────────────

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('[DJ Treta MCP] Server running on stdio');
  console.error(`[DJ Treta MCP] Mixxx API: ${MIXXX_API}`);
  console.error(`[DJ Treta MCP] Music dir: ${MUSIC_DIR}`);
}

main().catch((e) => {
  console.error('[DJ Treta MCP] Fatal error:', e);
  process.exit(1);
});
