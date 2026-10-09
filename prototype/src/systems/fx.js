// Эффекты: всплывающие цифры урона, частицы, кольца взрывов. Позиции — в мировых координатах,
// смещения по высоте — в экранных пикселях.
import { crand } from '../core/rng.js';
const rnd = (lo, hi) => lo + crand() * (hi - lo);   // B-35: косметика не тратит игровое зерно

export class FX {
  constructor() { this.texts = []; this.parts = []; this.rings = []; this.flashes = []; this.bolts = []; }

  text(x, y, str, color, z = 24, opts = {}) {
    this.texts.push({ x, y, str, color, z, t: 0, dur: opts.dur || 0.9, big: !!opts.big, speech: !!opts.speech, ox: opts.speech ? 0 : rnd(-4, 4) });
  }
  burst(x, y, color, n = 8, z = 10, speed = 40) {
    for (let i = 0; i < n; i++) {
      const a = rnd(0, Math.PI * 2);
      this.parts.push({ x, y, ox: 0, oy: -z, vx: Math.cos(a) * rnd(0.3, 1) * speed, vy: Math.sin(a) * rnd(0.3, 1) * speed * 0.6 - speed * 0.5, g: 120, t: 0, dur: rnd(0.35, 0.7), color, size: crand() < 0.3 ? 2 : 1 });
    }
  }
  rise(x, y, color, n = 20, h = 40) {
    for (let i = 0; i < n; i++) {
      this.parts.push({ x, y, ox: rnd(-9, 9), oy: rnd(-4, 2), vx: 0, vy: -rnd(20, 60), g: 0, t: -rnd(0, 0.6), dur: rnd(0.6, 1.1), color, size: 1 });
    }
  }
  ring(x, y, radius, color, dur = 0.35) { this.rings.push({ x, y, radius, color, t: 0, dur }); }
  light(x, y, r, dur) { this.flashes.push({ x, y, r, t: 0, dur }); }
  // молния «Перунова скока»: с неба в точку приземления + след от точки взлёта
  bolt(x0, y0, x1, y1, dur = 0.35) {
    const seg = [];
    for (let i = 0; i <= 7; i++) seg.push([rnd(-5, 5) * (i > 0 && i < 7 ? 1 : 0), i / 7]);
    this.bolts.push({ x0, y0, x1, y1, t: 0, dur, seg });
  }

  update(dt) {
    for (const t of this.texts) t.t += dt;
    for (const p of this.parts) {
      p.t += dt;
      if (p.t < 0) continue;
      p.vy += p.g * dt; p.ox += p.vx * dt; p.oy += p.vy * dt;
    }
    for (const r of this.rings) r.t += dt;
    for (const f of this.flashes) f.t += dt;
    for (const b of this.bolts) b.t += dt;
    this.texts = this.texts.filter((t) => t.t < t.dur);
    this.parts = this.parts.filter((p) => p.t < p.dur);
    this.rings = this.rings.filter((r) => r.t < r.dur);
    this.flashes = this.flashes.filter((f) => f.t < f.dur);
    this.bolts = this.bolts.filter((b) => b.t < b.dur);
  }
}
