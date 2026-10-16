// v2light: динамический свет. Темнота и тёплый подсвет рисуются в буферы пониженного разрешения (stats.light.bufScale),
// пятна — один закэшированный радиальный спрайт (масштабируется под радиус), тёплые — спрайт на цвет. Потом буферы
// растягиваются на кадр без сглаживания, поверх — виньетка (кэш). HUD рисуется после — не освещается.
import { VIEW_W, VIEW_H, HALF_W } from '../config.js';
import { CFG } from '../data/config.js';

const SPR = 128;
let holeSpr = null;
const warmSpr = new Map();
function mk(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
function holeSprite() {
  if (holeSpr) return holeSpr;
  const c = mk(SPR, SPR), x = c.getContext('2d'), r = SPR / 2, g = x.createRadialGradient(r, r, 0, r, r, r);
  g.addColorStop(0, 'rgba(0,0,0,1)'); g.addColorStop(0.55, 'rgba(0,0,0,0.7)'); g.addColorStop(1, 'rgba(0,0,0,0)');   // профиль m1f
  x.fillStyle = g; x.fillRect(0, 0, SPR, SPR);
  return (holeSpr = c);
}
export function warmSprite(rgb) {
  let c = warmSpr.get(rgb);
  if (c) return c;
  c = mk(SPR, SPR); const x = c.getContext('2d'), r = SPR / 2, g = x.createRadialGradient(r, r, 0, r, r, r);
  g.addColorStop(0, `rgba(${rgb},1)`); g.addColorStop(1, `rgba(${rgb},0)`);
  x.fillStyle = g; x.fillRect(0, 0, SPR, SPR);
  warmSpr.set(rgb, c);
  return c;
}
export const LS = () => (CFG.stats && CFG.stats.light) || {};
export const lightHigh = (game) => !game.settings || game.settings.lightQ !== 'low';

export class LightPass {
  constructor() { this.k = 0; this.vig = null; this.vigKey = ''; this.stats = { lights: 0, culled: 0, k: 0 }; }
  ensure(k) {
    if (this.k === k) return;
    this.k = k;
    const w = Math.ceil(VIEW_W * k), h = Math.ceil(VIEW_H * k);
    this.dark = mk(w, h); this.d = this.dark.getContext('2d');
    this.warm = mk(w, h); this.w = this.warm.getContext('2d');
  }
  /** Виньетка в разрешении буфера темноты (накладывается на него же — без лишнего прохода по всему кадру). */
  vignette() {
    const V = LS().vignette || {}, W = this.dark ? this.dark.width : VIEW_W, H = this.dark ? this.dark.height : VIEW_H, key = JSON.stringify(V) + W;
    if (this.vig && this.vigKey === key) return this.vig;
    const c = mk(W, H), x = c.getContext('2d'), cx = W / 2, cy = H / 2, R = Math.hypot(cx, cy);
    const g = x.createRadialGradient(cx, cy, R * (V.inner ?? 0.45), cx, cy, R);
    const rgb = V.rgb || '6,6,14';
    g.addColorStop(0, `rgba(${rgb},0)`); g.addColorStop(1, `rgba(${rgb},${V.a ?? 0.55})`);
    x.fillStyle = g; x.fillRect(0, 0, W, H);
    this.vigKey = key;
    return (this.vig = c);
  }
  /** holes: [sx, sy, r, a]; warm: [sx, sy, r, a, rgb] — в экранных пикселях кадра. */
  draw(ctx, ambient, holes, warm, game, extra = null) {
    const L = LS(), k = (L.bufScale || {})[lightHigh(game) ? 'high' : 'low'] ?? 0.5;
    this.ensure(k);
    const P = game._prof; let q0 = P ? performance.now() : 0; const pq = (k2) => { if (!P) return; const t1 = performance.now(); P[k2] = (P[k2] || 0) + t1 - q0; q0 = t1; };
    const d = this.d, w = this.w, W = this.dark.width, H = this.dark.height, pad = L.cullPad ?? 80;
    const vis = (x, y, r) => x + r > -pad && x - r < VIEW_W + pad && y + r > -pad && y - r < VIEW_H + pad;
    d.globalCompositeOperation = 'source-over'; d.clearRect(0, 0, W, H);
    d.fillStyle = ambient; d.fillRect(0, 0, W, H);
    d.globalCompositeOperation = 'destination-out';
    const hs = holeSprite();
    let n = 0, culled = 0;
    for (const [x, y, r, a] of holes) {
      if (!vis(x, y, r) || a <= 0) { culled++; continue; }
      d.globalAlpha = Math.min(1, a); d.drawImage(hs, (x - r) * k, (y - r) * k, 2 * r * k, 2 * r * k); n++;
    }
    d.globalAlpha = 1;
    d.globalCompositeOperation = 'source-over';
    pq('L.holes'); d.drawImage(this.vignette(), 0, 0); pq('L.vig');
    w.globalCompositeOperation = 'source-over'; w.clearRect(0, 0, W, H);
    let bx0 = 1e9, by0 = 1e9, bx1 = -1e9, by1 = -1e9;   // рамка тёплого света: складываем на кадр только её
    for (const [x, y, r, a, rgb] of warm) {
      if (!vis(x, y, r) || a <= 0) { culled++; continue; }
      bx0 = Math.min(bx0, x - r); by0 = Math.min(by0, y - r); bx1 = Math.max(bx1, x + r); by1 = Math.max(by1, y + r);
      w.globalAlpha = Math.min(1, a); w.drawImage(warmSprite(rgb || '230,134,43'), (x - r) * k, (y - r) * k, 2 * r * k, 2 * r * k); n++;
    }
    w.globalAlpha = 1;
    pq('L.warm'); if (extra && extra(w, k)) { bx0 = -1e9; by0 = -1e9; bx1 = 1e9; by1 = 1e9; }   // туман — по всему кадру   // туман над водой (atmo.js) — в тот же буфер, складывается со светом
    ctx.save();
    ctx.imageSmoothingEnabled = !!L.smooth && lightHigh(game);   // high: мягкий попиксельный градиент; low: без сглаживания (в Firefox в 4–5 раз дешевле)
    pq('L.mist'); ctx.drawImage(this.dark, 0, 0, W, H, 0, 0, VIEW_W, VIEW_H); pq('L.darkUp');
    const x0 = Math.max(0, Math.floor(bx0 * k)), y0 = Math.max(0, Math.floor(by0 * k)), x1 = Math.min(W, Math.ceil(bx1 * k)), y1 = Math.min(H, Math.ceil(by1 * k));
    if (x1 > x0 && y1 > y0) { ctx.globalCompositeOperation = 'lighter'; ctx.drawImage(this.warm, x0, y0, x1 - x0, y1 - y0, x0 / k, y0 / k, (x1 - x0) / k, (y1 - y0) / k); }
    ctx.restore(); pq('L.warmUp');
    this.stats = { lights: n, culled, k, holes: holes.length, warm: warm.length };
  }
}

/** Мягкое дрожание огня: 0..1, разные фазы у разных огней (seed). */
export function flick(t, seed) {
  const F = LS().flicker || {}, s = F.speed ?? 9;
  return 0.5 + 0.3 * Math.sin(t * s + seed * 7.1) + 0.2 * Math.sin(t * s * 2.3 + seed * 3.7);
}
export const TILE_PX = HALF_W * Math.SQRT2;
