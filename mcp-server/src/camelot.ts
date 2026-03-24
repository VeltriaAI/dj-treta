/**
 * Camelot Wheel — Key compatibility for harmonic mixing.
 *
 * Mixxx reports keys as integer codes (EngineKey values).
 * This module maps them to Camelot notation and finds compatible keys.
 *
 * Compatible moves:
 *   - Same key (perfect match)
 *   - +1 / -1 on the wheel (adjacent energy)
 *   - Relative major/minor (A ↔ B at same number)
 */

// Mixxx key codes → musical keys
// Based on KeyUtils::keyFromKeyNumber in Mixxx source
const MIXXX_KEY_MAP: Record<number, string> = {
  0: 'INVALID',
  1: 'C',       // C major
  2: 'Db',      // Db major
  3: 'D',       // D major
  4: 'Eb',      // Eb major
  5: 'E',       // E major
  6: 'F',       // F major
  7: 'F#',      // F# major
  8: 'G',       // G major
  9: 'Ab',      // Ab major
  10: 'A',      // A major
  11: 'Bb',     // Bb major
  12: 'B',      // B major
  13: 'Cm',     // C minor
  14: 'C#m',    // C# minor
  15: 'Dm',     // D minor
  16: 'Ebm',    // Eb minor / D# minor
  17: 'Em',     // E minor
  18: 'Fm',     // F minor
  19: 'F#m',    // F# minor
  20: 'Gm',     // G minor
  21: 'G#m',    // G# minor / Ab minor
  22: 'Am',     // A minor
  23: 'Bbm',    // Bb minor
  24: 'Bm',     // B minor
};

// Musical key → Camelot code
const KEY_TO_CAMELOT: Record<string, string> = {
  // Major keys (B side)
  'C': '8B',   'Db': '3B',  'D': '10B',  'Eb': '5B',
  'E': '12B',  'F': '7B',   'F#': '2B',  'G': '9B',
  'Ab': '4B',  'A': '11B',  'Bb': '6B',  'B': '1B',
  // Minor keys (A side)
  'Cm': '5A',   'C#m': '12A', 'Dm': '7A',   'Ebm': '2A',
  'Em': '9A',   'Fm': '4A',   'F#m': '11A', 'Gm': '6A',
  'G#m': '1A',  'Am': '8A',   'Bbm': '3A',  'Bm': '10A',
};

// Reverse: Camelot code → musical key
const CAMELOT_TO_KEY: Record<string, string> = {};
for (const [key, cam] of Object.entries(KEY_TO_CAMELOT)) {
  CAMELOT_TO_KEY[cam] = key;
}

export function mixxxKeyToCamelot(keyCode: number): string | null {
  const musicalKey = MIXXX_KEY_MAP[keyCode];
  if (!musicalKey || musicalKey === 'INVALID') return null;
  return KEY_TO_CAMELOT[musicalKey] || null;
}

export function mixxxKeyToMusical(keyCode: number): string | null {
  const key = MIXXX_KEY_MAP[keyCode];
  if (!key || key === 'INVALID') return null;
  return key;
}

export function getCompatibleKeys(camelotCode: string): string[] {
  const match = camelotCode.match(/^(\d+)([AB])$/);
  if (!match) return [];

  const num = parseInt(match[1]);
  const letter = match[2];

  const compatible: string[] = [];

  // Same key
  compatible.push(camelotCode);

  // +1 on wheel
  const up = ((num % 12) + 1) || 12;
  compatible.push(`${up}${letter}`);

  // -1 on wheel
  const down = ((num - 2 + 12) % 12) + 1;
  compatible.push(`${down}${letter}`);

  // Relative major/minor (same number, swap A/B)
  const otherLetter = letter === 'A' ? 'B' : 'A';
  compatible.push(`${num}${otherLetter}`);

  return compatible;
}

export function getCompatibleMusicalKeys(keyCode: number): string[] {
  const camelot = mixxxKeyToCamelot(keyCode);
  if (!camelot) return [];

  const compatibleCamelot = getCompatibleKeys(camelot);
  return compatibleCamelot
    .map(c => CAMELOT_TO_KEY[c])
    .filter((k): k is string => !!k);
}

export function formatKeyInfo(keyCode: number): string {
  const musical = mixxxKeyToMusical(keyCode);
  const camelot = mixxxKeyToCamelot(keyCode);
  if (!musical || !camelot) return 'Unknown';
  return `${musical} (${camelot})`;
}
