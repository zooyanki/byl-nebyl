// m1k D4 (GDD v1.13.2 §10.3, §15 stats.xray): видимость за кронами и кровлями.
//  • окно вокруг героя всегда: эллипс rx×ry вокруг середины тела (pivot + dy) — кроны/кровли перед героем → alpha;
//  • над врагом в агро / под курсором (прямоугольник 24 × рост) → alpha; над прочими врагами в idleRange тайлах на экране → alphaIdle;
//  • над дверью невыбитой избы → alphaDoor; переход t с; растворено не больше maxFaded спрайтов (ближайшие к герою);
//  • вместо «призраков» — контур 1 px по силуэту, если закрыто ≥ minCovered пикселей (герой всегда; враги — в агро/под курсором).
import { CFG } from '../data/config.js';
import { PAL } from '../palette.js';
import { propCovers, propMaskAt, propBox } from './props.js';

export const XR = () => (CFG.stats && CFG.stats.xray) || {};

/** Области растворения: [{a, d, x, y, w, h, ell?}] (d — глубина того, кого открываем). */
export function xrayRegions(game, toS, vis, isAggro) {
  const X = XR(), E = X.heroEllipse || {}, out = [], hero = game.hero, map = game.map;
  const A = X.alpha ?? 0.35, AI = X.alphaIdle ?? 0.5, AD = X.alphaDoor ?? 0.3, R = X.idleRange ?? 9;
  if (!hero.dead) {
    const [sx, sy] = toS(hero.x, hero.y), rx = E.rx ?? 56, ry = E.ry ?? 40, cy = sy + (E.dy ?? -22);
    out.push({ a: A, d: hero.x + hero.y, x: sx - rx, y: cy - ry, w: rx * 2, h: ry * 2, ell: { cx: sx, cy, rx, ry }, who: 'hero' });
  }
  for (const e of game.enemies) {
    if (e.dead || e.dummy) continue;
    const [sx, sy] = toS(e.x, e.y), h = (e.def && e.def.height) || 40;
    if (!vis(sx, sy, h)) continue;
    const hot = e === game.hoverEnemy || isAggro(e);
    if (!hot && Math.hypot(e.x - hero.x, e.y - hero.y) > R) continue;
    const hw = e.kind === 'upyr' ? 14 : 12;   // v2art: упырь v2 шире
    out.push({ a: hot ? A : AI, d: e.x + e.y, x: sx - hw, y: sy - h, w: hw * 2, h, who: hot ? 'aggro' : 'idle' });
  }
  for (const dd of map.objects) if (dd.type === 'hut' && !dd.done) {
    const ax = dd.door === '+x', a0 = ax ? toS(dd.x, dd.y - 0.75) : toS(dd.x - 0.75, dd.y), a1 = ax ? toS(dd.x, dd.y + 0.75) : toS(dd.x + 0.75, dd.y);
    out.push({ a: AD, d: dd.x + dd.y + 0.5, x: Math.min(a0[0], a1[0]), y: Math.min(a0[1], a1[1]) - 60, w: Math.abs(a1[0] - a0[0]) + 1, h: Math.abs(a1[1] - a0[1]) + 62, who: 'door' });
  }
  return out;
}

/** Желаемая альфа каждого пропса (Map p → a), не больше maxFaded растворённых (ближайшие к герою). */
export function xrayWants(game, props, toS, regions) {
  const X = XR(), want = new Map();
  if (game.settings && game.settings.xray === false) return want;
  const hero = game.hero, cand = [];
  for (const p of props) {
    if (p.type === 'fire' || !p._spr) continue;
    let a = 1;
    for (const q of regions) if (p.depth > q.d && q.a < a && propCovers(p, toS, q)) a = q.a;
    if (a < 1) cand.push({ p, a, dist: Math.hypot(p.fp[0] + p.fp[2] / 2 - hero.x, p.fp[1] + p.fp[3] / 2 - hero.y) });
  }
  cand.sort((u, v) => u.dist - v.dist);
  const max = X.maxFaded ?? 12;
  for (let i = 0; i < cand.length && i < max; i++) want.set(cand[i].p, cand[i].a);
  return want;
}

// --- контур по силуэту
let SCR = null;
const SW = 160, SH = 176, AX = 80, AY = 150;   // скретч-холст: якорь (ноги) в (AX, AY)
function scratch() {
  if (!SCR) { SCR = document.createElement('canvas'); SCR.width = SW; SCR.height = SH; SCR.out = document.createElement('canvas'); SCR.out.width = SW; SCR.out.height = SH; }
  return SCR;
}
/** Силуэт (draw(ctx, AX, AY)) → доля его пикселей, закрытых пропсами перед ним, и контур 1 px цветом color (если закрыт ≥ minCovered). */
export function outlineIfCovered(ctx, game, toS, sx, sy, depth, draw, color, only = null) {
  const X = XR(), O = X.outline || {}, min = O.minCovered ?? 0.25;
  const x0 = sx - AX, y0 = sy - AY;
  const front = [];
  for (const p of game.map.props) {
    if (!p._spr || p.depth <= depth || p.type === 'fire' || (only && !only(p))) continue;
    const b = propBox(p, toS);
    if (b && b.x < x0 + SW && b.x + b.w > x0 && b.y < y0 + SH && b.y + b.h > y0) front.push(p);
  }
  // оптимизация: перед силуэтом нет ни одного пропса — закрыто 0%, силуэт не рисуем и не читаем пиксели (тот же итог)
  if (!front.length) return { frac: 0, drawn: false };
  const C = scratch(), c = C.getContext('2d', { willReadFrequently: true });
  c.setTransform(1, 0, 0, 1, 0, 0); c.clearRect(0, 0, SW, SH); c.imageSmoothingEnabled = false;
  draw(c, AX, AY);
  const img = c.getImageData(0, 0, SW, SH), d = img.data;
  let tot = 0, cov = 0;
  for (let y = 0; y < SH; y += 2) for (let x = 0; x < SW; x += 2) {
    if (d[(y * SW + x) * 4 + 3] < 200) continue;
    tot++;
    for (const p of front) if (propMaskAt(p, toS, x0 + x, y0 + y)) { cov++; break; }
  }
  const frac = tot ? cov / tot : 0;
  if (frac < min || !front.length) return { frac, drawn: false };
  const o = C.out.getContext('2d'), oi = o.createImageData(SW, SH), od = oi.data;
  const [r, g, b] = hex(color), on = (x, y) => x >= 0 && y >= 0 && x < SW && y < SH && d[(y * SW + x) * 4 + 3] >= 200;
  for (let y = 0; y < SH; y++) for (let x = 0; x < SW; x++) {
    if (on(x, y)) continue;
    if (on(x - 1, y) || on(x + 1, y) || on(x, y - 1) || on(x, y + 1)) { const k = (y * SW + x) * 4; od[k] = r; od[k + 1] = g; od[k + 2] = b; od[k + 3] = 255; }
  }
  o.putImageData(oi, 0, 0);
  ctx.drawImage(C.out, Math.round(x0), Math.round(y0));
  return { frac, drawn: true };
}
function hex(c) { const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})/i.exec(c || '#ffffff'); return m ? [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16)] : [255, 255, 255]; }
/** Цвет контура врага: обычный red_lt, матёрый / вожак / былинный bronze, босс bronze_hi. */
export function outlineColor(e) {
  const O = XR().outline || {};
  const k = e.boss ? (O.boss || 'bronze_hi') : (e.elite || e.leader) ? (O.elite || 'bronze') : (O.enemy || 'red_lt');
  return PAL[k] || PAL.red_lt;
}

/** v2art r4: постройка (для контура NPC): не дерево, не тын, не мелкий реквизит. */
const NOT_BLD = new Set(['tree', 'palisade', 'gateseg', 'fire', 'stump', 'cart', 'well', 'sign', 'churstone', 'anvil', 'relic', 'hearth', 'perun', 'ladya', 'rock', 'bush', 'fence']);
export const isBuilding = (p) => !NOT_BLD.has(p.type);
