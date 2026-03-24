/**
 * Mixxx HTTP API Client
 *
 * Thin wrapper around the Mixxx HTTP API running on port 7778.
 * All deck control, status, and track loading goes through here.
 */

import axios, { AxiosInstance } from 'axios';

export interface DeckStatus {
  deck: number;
  playing: boolean;
  track_loaded: boolean;
  bpm: number;
  file_bpm: number;
  visual_bpm: number;
  key: number;
  visual_key: number;
  position: number;
  position_seconds: number;
  duration: number;
  remaining_seconds: number;
  volume: number;
  eq_hi: number;
  eq_mid: number;
  eq_lo: number;
  sync_enabled: boolean;
  loop_enabled: boolean;
  loop_start_position: number;
  loop_end_position: number;
  beat_active: boolean;
  rate: number;
  track_color: number;
}

export interface MixxxStatus {
  engine: string;
  crossfader: number;
  master_volume: number;
  headphone_volume: number;
  deck1: DeckStatus;
  deck2: DeckStatus;
}

export class MixxxClient {
  private http: AxiosInstance;
  private baseUrl: string;

  constructor(host: string = 'http://localhost:7778') {
    this.baseUrl = host;
    this.http = axios.create({
      baseURL: host,
      timeout: 10000,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  // ── Status ──────────────────────────────────────────────────────

  async getStatus(): Promise<MixxxStatus> {
    const { data } = await this.http.get('/api/status');
    return data;
  }

  async getDeckStatus(deck: number): Promise<DeckStatus> {
    const status = await this.getStatus();
    return deck === 1 ? status.deck1 : status.deck2;
  }

  // ── Deck Control ────────────────────────────────────────────────

  async loadTrack(deck: number, trackPath: string): Promise<any> {
    const { data } = await this.http.post('/api/load', { deck, track: trackPath });
    return data;
  }

  async play(deck: number): Promise<any> {
    const { data } = await this.http.post('/api/play', { deck });
    return data;
  }

  async pause(deck: number): Promise<any> {
    const { data } = await this.http.post('/api/pause', { deck });
    return data;
  }

  async stop(deck: number): Promise<any> {
    const { data } = await this.http.post('/api/stop', { deck });
    return data;
  }

  async eject(deck: number): Promise<any> {
    const { data } = await this.http.post('/api/eject', { deck });
    return data;
  }

  // ── Mixing ──────────────────────────────────────────────────────

  async setCrossfader(position: number): Promise<any> {
    const { data } = await this.http.post('/api/crossfader', { position });
    return data;
  }

  async setVolume(deck: number, level: number): Promise<any> {
    const { data } = await this.http.post('/api/volume', { deck, level });
    return data;
  }

  async setEQ(deck: number, hi?: number, mid?: number, lo?: number): Promise<any> {
    const payload: any = { deck };
    if (hi !== undefined) payload.hi = hi;
    if (mid !== undefined) payload.mid = mid;
    if (lo !== undefined) payload.lo = lo;
    const { data } = await this.http.post('/api/eq', payload);
    return data;
  }

  async setFilter(deck: number, value: number): Promise<any> {
    const { data } = await this.http.post('/api/filter', { deck, value });
    return data;
  }

  async setSync(deck: number, enabled: boolean = true): Promise<any> {
    const { data } = await this.http.post('/api/sync', { deck, enabled });
    return data;
  }

  async transition(deck: number, duration: number): Promise<any> {
    const { data } = await this.http.post('/api/transition', { deck, duration });
    return data;
  }

  // ── Generic Control ────────────────────────────────────────────

  async control(group: string, key: string, value: number = 1): Promise<any> {
    const { data } = await this.http.post('/api/control', { group, key, value });
    return data;
  }

  async getControl(group: string, key: string): Promise<number> {
    const { data } = await this.http.get('/api/control', { params: { group, key } });
    return data.value ?? 0;
  }

  // ── Health Check ────────────────────────────────────────────────

  async isAlive(): Promise<boolean> {
    try {
      await this.http.get('/api/status');
      return true;
    } catch {
      return false;
    }
  }
}
