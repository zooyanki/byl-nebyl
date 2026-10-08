// Звуки-заглушки: всё синтезируется WebAudio на лету, без файлов.
// play(name): hit, crit, miss, hurt, block, skill, explode, kill, pickup, silver, potion, equip, levelup, death, respawn, ui, error.
const STORE_KEY = 'byl_nebyl_mute';

export class Audio {
  constructor() {
    this.ctx = null;
    this.master = null;
    this.muted = false;
    try { this.muted = localStorage.getItem(STORE_KEY) === '1'; } catch (e) { /* без localStorage */ }
    this.count = {};       // сколько раз проигрывался каждый звук (для автотестов)
    this.last = {};
    this.noiseBuf = null;
  }

  unlock() {
    if (this.ctx) { if (this.ctx.state === 'suspended') this.ctx.resume().catch(() => {}); return; }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    this.ctx = new AC();
    this.master = this.ctx.createGain();
    this.master.gain.value = this.muted ? 0 : 0.5;
    this.master.connect(this.ctx.destination);
    const n = this.ctx.sampleRate * 0.6;
    this.noiseBuf = this.ctx.createBuffer(1, n, this.ctx.sampleRate);
    const d = this.noiseBuf.getChannelData(0);
    for (let i = 0; i < n; i++) d[i] = Math.random() * 2 - 1;
  }

  setMuted(m) {
    this.muted = m;
    try { localStorage.setItem(STORE_KEY, m ? '1' : '0'); } catch (e) { /* ignore */ }
    if (this.master) this.master.gain.setTargetAtTime(m ? 0 : 0.5, this.ctx.currentTime, 0.02);
  }
  toggle() { this.setMuted(!this.muted); return this.muted; }

  // --- примитивы
  tone(type, f0, f1, dur, vol = 0.3, delay = 0) {
    const c = this.ctx, t = c.currentTime + delay;
    const o = c.createOscillator(), g = c.createGain();
    o.type = type;
    o.frequency.setValueAtTime(f0, t);
    if (f1 !== f0) o.frequency.exponentialRampToValueAtTime(Math.max(20, f1), t + dur);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol, t + 0.008);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); g.connect(this.master);
    o.start(t); o.stop(t + dur + 0.02);
  }
  noise(dur, vol = 0.3, filter = 'bandpass', freq = 1200, q = 1, delay = 0, f1 = null) {
    const c = this.ctx, t = c.currentTime + delay;
    const s = c.createBufferSource(); s.buffer = this.noiseBuf;
    const f = c.createBiquadFilter(); f.type = filter; f.frequency.setValueAtTime(freq, t); f.Q.value = q;
    if (f1) f.frequency.exponentialRampToValueAtTime(f1, t + dur);
    const g = c.createGain();
    g.gain.setValueAtTime(vol, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    s.connect(f); f.connect(g); g.connect(this.master);
    s.start(t, Math.random() * 0.2); s.stop(t + dur + 0.02);
  }

  play(name) {
    this.count[name] = (this.count[name] || 0) + 1;
    if (!this.ctx || this.muted) return;
    const now = this.ctx.currentTime;
    if (this.last[name] && now - this.last[name] < 0.03) return;
    this.last[name] = now;
    switch (name) {
      case 'hit': this.noise(0.09, 0.35, 'bandpass', 900, 1.2); this.tone('sine', 140, 50, 0.1, 0.35); break;
      case 'crit': this.noise(0.12, 0.4, 'bandpass', 1600, 1.5); this.tone('square', 220, 60, 0.14, 0.18); this.tone('triangle', 1200, 900, 0.08, 0.12); break;
      case 'miss': this.noise(0.12, 0.18, 'highpass', 2500, 0.7, 0, 5000); break;
      case 'hurt': this.tone('square', 180, 90, 0.12, 0.16); this.noise(0.06, 0.2, 'lowpass', 700); break;
      case 'block': this.tone('square', 900, 700, 0.06, 0.12); this.noise(0.08, 0.25, 'bandpass', 3000, 3); break;
      case 'skill': this.tone('sawtooth', 160, 620, 0.28, 0.12); this.noise(0.25, 0.12, 'bandpass', 600, 2, 0, 2400); break;
      case 'explode': this.noise(0.45, 0.5, 'lowpass', 1400, 0.8, 0, 120); this.tone('sine', 90, 35, 0.35, 0.4); break;
      case 'kill': this.noise(0.18, 0.25, 'lowpass', 500, 1, 0, 150); this.tone('triangle', 200, 70, 0.2, 0.15); break;
      case 'pickup': this.tone('triangle', 660, 660, 0.07, 0.2); this.tone('triangle', 990, 990, 0.1, 0.2, 0.06); break;
      case 'silver': for (let i = 0; i < 3; i++) this.tone('square', 1900 + i * 250, 1700 + i * 250, 0.05, 0.06, i * 0.045); break;
      case 'potion': this.tone('sine', 320, 160, 0.12, 0.25); this.tone('sine', 300, 140, 0.12, 0.22, 0.13); break;
      case 'equip': this.tone('square', 1300, 1100, 0.05, 0.08); this.noise(0.1, 0.18, 'bandpass', 4000, 4); break;
      case 'levelup': [523, 659, 784, 1047].forEach((f, i) => this.tone('triangle', f, f, 0.22, 0.2, i * 0.09)); break;
      case 'death': this.tone('sawtooth', 300, 50, 1.3, 0.16); this.tone('sine', 150, 40, 1.2, 0.2, 0.1); break;
      case 'respawn': [392, 523, 659].forEach((f, i) => this.tone('sine', f, f, 0.4, 0.15, i * 0.12)); break;
      case 'ui': this.tone('square', 700, 700, 0.03, 0.06); break;
      case 'error': this.tone('square', 160, 140, 0.12, 0.1); break;
    }
  }
}
