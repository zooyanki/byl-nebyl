// v2light: атмосфера — туман над водой, клубы дыма над печными постройками, искры «Огненного змея» (след и взрыв),
// светлячки в лесных зонах. Числа — stats.json → atmo; у каждого вида потолок частиц (max). Позиции частиц — в
// «изо-пикселях» мира (экран минус toS(0, 0)), так они не ездят за камерой. Случайность — crand (не тратит игровое зерно).
import { VIEW_W, VIEW_H, HALF_W, HALF_H } from '../config.js';
import { CFG } from '../data/config.js';
import { crand } from '../core/rng.js';
import { T_WATER, T_FOREST } from '../world/map.js';
import { warmSprite, lightHigh } from './light.js';

const AS = () => (CFG.stats && CFG.stats.atmo) || {};
const rnd = (a, b) => a + crand() * (b - a);
let puffSpr = null;
function puffSprite() {
  if (puffSpr) return puffSpr;
  const c = document.createElement('canvas'); c.width = c.height = 64;
  const x = c.getContext('2d'), g = x.createRadialGradient(32, 32, 0, 32, 32, 32);
  g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(0.5, 'rgba(255,255,255,0.55)'); g.addColorStop(1, 'rgba(255,255,255,0)');
  x.fillStyle = g; x.fillRect(0, 0, 64, 64);
  return (puffSpr = c);
}
const tinted = new Map();
function tintSprite(rgb) {   // мягкое пятно нужного цвета (туман, дым)
  let c = tinted.get(rgb); if (c) return c;
  c = document.createElement('canvas'); c.width = c.height = 64;
  const x = c.getContext('2d'); x.drawImage(puffSprite(), 0, 0); x.globalCompositeOperation = 'source-in'; x.fillStyle = `rgb(${rgb})`; x.fillRect(0, 0, 64, 64);
  tinted.set(rgb, c); return c;
}

export class Atmo {
  constructor(map) {
    this.map = map; this.smoke = []; this.sparks = []; this.flies = []; this.water = null; this.t = null;
    this.prevProj = new Map(); this.emitAcc = new Map();
    this.stats = { smoke: 0, sparks: 0, fireflies: 0, mist: 0 };
  }
  mul(game) { return lightHigh(game) ? 1 : (AS().low ?? 0.5); }
  waterTiles() {
    if (this.water) return this.water;
    const M = AS().mist || {}, st = M.step || 2, out = [], m = this.map;
    for (let y = 0; y < m.h; y += st) for (let x = 0; x < m.w; x += st) if (m.groundAt(x, y) === T_WATER) out.push([x + 0.5, y + 0.5, ((x * 73856093) ^ (y * 19349663)) % 1000 / 1000]);
    return (this.water = out);
  }
  step(game, toS) {
    const t = game.time, dt = this.t == null ? 0 : Math.min(0.1, Math.max(0, t - this.t));
    this.t = t;
    const A = AS(), o = toS(0, 0), mul = this.mul(game);
    // --- дым: от каждой постройки в кадре с точкой дыма (props.js p._smokePt)
    const S = A.smoke || {}, smax = Math.round((S.max ?? 90) * mul);
    if (dt > 0) for (const p of this.map.props) {
      if (!p._smokePt || p._litF !== this.frameNo) continue;
      let acc = (this.emitAcc.get(p) || 0) + dt * (S.rate ?? 2.2) * mul;
      const [bx, by] = toS(p.x, p.y);
      while (acc >= 1 && this.smoke.length < smax) {
        acc -= 1;
        this.smoke.push({ x: bx + p._smokePt[0] - o[0] + rnd(-1.5, 1.5), y: by + p._smokePt[1] - o[1] - 4, t: 0, dur: (S.life ?? 4) * rnd(0.8, 1.2), s: rnd(0.8, 1.2), ph: rnd(0, 6.28) });
      }
      this.emitAcc.set(p, Math.min(acc, 2));
    }
    for (const q of this.smoke) {
      q.t += dt; const k = q.t / q.dur;
      q.y -= (S.rise ?? 9) * dt * (1 - 0.4 * k);
      q.x += ((S.wind ?? 4) * k + Math.sin(t * 0.9 + q.ph) * 2) * dt;
    }
    this.smoke = this.smoke.filter((q) => q.t < q.dur);
    // --- искры змея: след в полёте и залп на месте взрыва (снаряд исчез)
    const SP = A.sparks || {}, cap = Math.round((SP.max ?? 160) * mul), now = new Map();
    for (const p of game.combat.projectiles) {
      if (p.hostile) continue;
      now.set(p, [p.x, p.y]);
      let acc = (this.emitAcc.get(p) || 0) + dt * (SP.trailRate ?? 70) * mul;
      while (acc >= 1) { acc -= 1; this.spark(p.x, p.y, 14, SP.life ?? 0.45, (SP.speed ?? 70) * 0.35, cap, p.skill === 'morozko'); }
      this.emitAcc.set(p, acc);
    }
    for (const [p, [x, y]] of this.prevProj) if (!now.has(p)) { this.emitAcc.delete(p); for (let i = 0; i < Math.round((SP.burst ?? 26) * mul); i++) this.spark(x, y, 10, SP.burstLife ?? 0.6, SP.speed ?? 70, cap, p.skill === 'morozko'); this.lastBurst = { x, y, t }; }
    this.prevProj = now;
    for (const s of this.sparks) { s.t += dt; s.vz -= (SP.grav ?? 60) * dt; s.x += s.vx * dt; s.y += s.vy * dt; s.z = Math.max(0, s.z + s.vz * dt); }
    this.sparks = this.sparks.filter((s) => s.t < s.dur);
    // --- светлячки: только лесные зоны (atmo.fireflies.zones), держим n штук вокруг камеры
    const FF = A.fireflies || {}, zid = game.zone && game.zone.id;
    if ((FF.zones || []).includes(zid)) {
      const n = Math.min(FF.max ?? 40, Math.round((FF.n ?? 26) * mul));
      const inView = (f) => { const x = f.x + o[0], y = f.y + o[1]; return x > -40 && x < VIEW_W + 40 && y > -40 && y < VIEW_H + 40; };
      this.flies = this.flies.filter(inView); if (this.flies.length > n) this.flies.length = n;
      let guard = 0;
      while (this.flies.length < n && guard++ < 200) {
        const x = rnd(-20, VIEW_W + 20) - o[0], y = rnd(-20, VIEW_H * 0.85) - o[1];
        // не над водой
        const wx = (x / HALF_W + y / HALF_H) / 2, wy = (y / HALF_H - x / HALF_W) / 2;
        const g = this.map.groundAt(Math.floor(wx), Math.floor(wy));
        if (g === T_WATER) continue;
        this.flies.push({ x, y, z: rnd(6, 26), ph: rnd(0, 6.28), sp: rnd(0.6, 1.4), forest: g === T_FOREST });
      }
      const v = (FF.speed ?? 0.35) * 20;
      for (const f of this.flies) { f.ph += dt * f.sp; f.x += Math.cos(f.ph * 0.7) * v * dt; f.y += Math.sin(f.ph * 0.9) * v * 0.5 * dt; f.z = Math.max(3, f.z + Math.sin(f.ph * 1.3) * 6 * dt); }
    } else this.flies.length = 0;
  }
  spark(x, y, z, life, sp, cap, cold) {
    if (this.sparks.length >= cap) return;
    const a = rnd(0, 6.28), v = rnd(0.3, 1) * sp / (HALF_W * Math.SQRT2);
    this.sparks.push({ x, y, z: z + rnd(-3, 3), vx: Math.cos(a) * v, vy: Math.sin(a) * v, vz: rnd(10, 40) * (sp > 40 ? 1.4 : 0.6), t: 0, dur: life * rnd(0.6, 1.2), cold });
  }
  /** Дым — под светом (темнеет со сценой). */
  drawUnder(ctx, game, toS) {
    this.step(game, toS);
    const S = AS().smoke || {}, o = toS(0, 0), spr = tintSprite(S.rgb || '150,150,160');
    ctx.save();
    for (const q of this.smoke) {
      const k = q.t / q.dur, r = (4 + (S.grow ?? 2.2) * 6 * k) * q.s;
      ctx.globalAlpha = (S.a ?? 0.32) * Math.min(1, q.t / 0.4) * (1 - k);
      ctx.drawImage(spr, q.x + o[0] - r, q.y + o[1] - r, r * 2, r * 2);
    }
    ctx.restore();
    this.stats.smoke = this.smoke.length;
  }
  /** Туман над водой — в буфер тёплого света (пониженное разрешение k), см. LightPass.draw(extra). */
  drawMist(ctx, k, game, toS) {
    const A = AS(), t = game.time, mul = this.mul(game);
    const M = A.mist || {}; let nm = 0;
    if ((M.zones || []).includes(game.zone && game.zone.id)) {
      const spr = tintSprite(M.rgb || '190,205,225'), rx = M.rx ?? 34, ry = M.ry ?? 11, mmax = Math.round((M.max ?? 70) * mul);
      // мягкие слоистые пряди: на тайл воды несколько вытянутых пятен разной высоты, плывут вдоль реки, без контура
      const nw = M.wisps ?? 3;
      for (const [x, y, h] of this.waterTiles()) {
        if (nm >= mmax) break;
        const [sx0, sy0] = toS(x, y);
        if (sx0 < -rx * 3 || sx0 > VIEW_W + rx * 3 || sy0 < -40 || sy0 > VIEW_H + 40) continue;
        for (let i = 0; i < nw; i++) {
          const ph = h * 6.28 + i * 2.1, sp = (M.speed ?? 0.35) * (0.6 + 0.3 * i);
          const sx = sx0 + Math.sin(t * sp + ph) * (M.drift ?? 6) * (1 + i) + (i - 1) * 14, sy = sy0 - 2 - i * 5 + Math.sin(t * 0.4 + ph) * 2;
          const w = rx * (0.7 + 0.25 * i), hh = ry * (0.8 + 0.3 * i);
          ctx.globalAlpha = (M.a ?? 0.07) * (0.5 + 0.5 * Math.sin(t * 0.5 + ph * 1.7)) * (1 - i * 0.2);
          ctx.drawImage(spr, (sx - w) * k, (sy - hh) * k, w * 2 * k, hh * 2 * k);
        }
        nm++;
      }
      ctx.globalAlpha = 1;
    }
    this.stats.mist = nm;
    return nm;
  }
  /** Искры и светлячки — поверх темноты. */
  drawOver(ctx, game, toS) {
    const A = AS(), t = game.time, o = toS(0, 0), mul = this.mul(game);
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    // отражения огней и окон в воде: дрожащие столбики горизонтальных чёрточек вниз от источника, только над водой
    const RF = A.reflect || {}; let nr = 0;
    if (this.warm && this.waterTiles().length) {
      const L = RF.len ?? 64, st = RF.step ?? 3, wm = RF.wMax ?? 7, sh = RF.shimmer ?? 6;
      for (const [lx, ly, r, a, rgb] of this.warm) {
        if (a <= 0.02 || lx < -20 || lx > VIEW_W + 20) continue;
        ctx.fillStyle = `rgb(${rgb || '230,134,43'})`;
        for (let dy = 8; dy < L; dy += st) {
          const y = ly + dy; if (y < 0 || y > VIEW_H) continue;
          const wx = ((lx - o[0]) / HALF_W + (y - o[1]) / HALF_H) / 2, wy = ((y - o[1]) / HALF_H - (lx - o[0]) / HALF_W) / 2;
          if (!this.map.waterSub(Math.floor(wx * 2), Math.floor(wy * 2))) continue;
          const q = 1 - dy / L, sn = Math.sin(t * sh + dy * 0.7 + lx), w = Math.max(1, Math.round(wm * q * (0.5 + 0.5 * sn)));
          ctx.globalAlpha = (RF.a ?? 0.5) * a / 0.3 * q * (0.55 + 0.45 * Math.sin(t * sh * 1.3 + dy));
          ctx.fillRect(Math.round(lx - w / 2 + Math.sin(t * 2 + dy) * 1.5), Math.round(y), w, 1); nr++;
        }
      }
    }
    this.stats.reflect = nr;
    // искры
    for (const s of this.sparks) {
      const [sx, sy] = toS(s.x, s.y), k = s.t / s.dur;
      ctx.globalAlpha = 1 - k;
      ctx.fillStyle = s.cold ? '#bfe0ff' : k < 0.35 ? '#fff2b0' : k < 0.7 ? '#ffb040' : '#e0501c';
      ctx.fillRect(Math.round(sx), Math.round(sy - s.z), 1, 1);
      if (k < 0.3) { ctx.globalAlpha = 0.5 * (1 - k); ctx.fillRect(Math.round(sx) - 1, Math.round(sy - s.z), 3, 1); }
    }
    // светлячки
    const FF = A.fireflies || {}, fs = warmSprite(FF.rgb || '214,255,120');
    for (const f of this.flies) {
      const b = Math.max(0, Math.sin(t * (FF.blink ?? 1.6) * f.sp + f.ph * 3));
      const x = Math.round(f.x + o[0]), y = Math.round(f.y + o[1] - f.z);
      ctx.globalAlpha = (FF.a ?? 0.9) * b * 0.5; ctx.drawImage(fs, x - 7, y - 7, 14, 14);
      ctx.globalAlpha = (FF.a ?? 0.9) * b; ctx.fillStyle = `rgb(${FF.rgb || '214,255,120'})`; ctx.fillRect(x, y, 1, 1);
    }
    ctx.restore();
    Object.assign(this.stats, { sparks: this.sparks.length, fireflies: this.flies.length, sparkCap: Math.round((A.sparks?.max ?? 160) * mul), smokeCap: Math.round((A.smoke?.max ?? 90) * mul) });
    game.atmoInfo = { ...this.stats };
  }
}
