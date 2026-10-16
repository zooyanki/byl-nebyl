// Препятствия грей-бокса по design/scale.md §3: ель 128–160, берёза 96–128, валуны 12–24 / 32,
// частокол 80 (столбы ворот 96, факелы на 48), сруб 4×4 (стена 68, охлупень 112, конёк 124),
// крада 2×2 (дрова 24, пламя до 72), чур 62, развалины — полуэтаж 32.
import { PAL } from '../palette.js';
import { HALF_W, HALF_H, TILE_W, TILE_H } from '../config.js';
import { w2s } from '../core/iso.js';
import { rect, poly, strokePoly, isoBox, disc, ellipse, figure } from './shapes.js';
import { drawRestSource, drawFxFrame } from './rest_fx.js';
import { drawHearthArt, drawPerunArt } from './boss_art.js';
import { CFG } from '../data/config.js';
import { VA, BLD_SHEET, sheetOf, frameOf, bakeSheet } from './village_art.js';
import { V2, v2, v2Blit } from './v2art.js';
import { flick } from './light.js';

// --- v2art: статичные листы v2 (деревья, прясло тына, избы) — спрайт { c, ox, oy } в системе drawProp (опора toS(p.x, p.y)).
const V2A = () => (CFG.stats && CFG.stats.v2art) || {};
const V2SPR = new Map();
/** Кадр листа v2 в canvas; (cx, cy) — мировая точка, куда встаёт pivot; flip — зеркало; sx0/sw — вырезка по x (прясло по клеткам). */
function v2Sprite(name, p, cx, cy, o = {}) {
  const sh = v2(name);
  if (!sh) return null;
  const m = sh.meta, [fw, fh] = m.frame_size || m.size, [px, py] = m.pivot, sx0 = o.sx0 ?? 0, sw = o.sw ?? fw;
  const key = name + (o.flip ? ':f' : '') + ':' + sx0 + ':' + sw + (o.glow ? ':g' : '');
  let c = V2SPR.get(key);
  if (!c) {
    c = document.createElement('canvas'); c.width = sw; c.height = fh;
    const g = c.getContext('2d', { willReadFrequently: true });
    g.save(); if (o.flip) { g.translate(sw, 0); g.scale(-1, 1); }
    g.drawImage(sh.img, o.flip ? fw - sx0 - sw : sx0, 0, sw, fh, 0, 0, sw, fh);
    g.restore();
    const W = o.glow && v2(o.glow);   // маска окон v2 (избы) — запекается аддитивно: окна тёплые всегда (тон зоны постоянный)
    if (W) { g.globalCompositeOperation = 'lighter'; g.globalAlpha = (((CFG.stats || {}).light || {}).windowMasksV2 || {}).maskA ?? 0.55; g.drawImage(W.img, sx0, 0, sw, fh, 0, 0, sw, fh); }
    const d = g.getImageData(0, 0, sw, fh).data; c.mask = new Uint8Array(sw * fh);   // маска для «рентгена» — одна на общий canvas
    for (let i = 0; i < sw * fh; i++) c.mask[i] = d[i * 4 + 3] > 0 ? 1 : 0;
    V2SPR.set(key, c);
    V2.counters.sprites = V2SPR.size;
  }
  const [a, b] = w2s(p.x, p.y), [u, v] = w2s(cx, cy);
  const pxs = o.flip ? (fw - px) - sx0 : px - sx0;   // при зеркале pivot листа — fw − px
  return { c, mask: c.mask, ox: Math.round(pxs - (u - a)), oy: Math.round(py - (v - b)), v2: name };
}
/** Какой лист v2 у пропса: дерево (кроме низких hMax перед путём), высокий тын (не низкий плетень, не столб ворот), изба-заглушка. */
export function v2PropSheet(p) {
  if (p.type === 'tree' && !p.hMax) return p.birch ? 'tree_birch' : 'tree_spruce';
  if (p.type === 'tree' && p.hMax) {   // v2b2: низкие деревья (treeRules) — самый высокий лист с hMax листа ≤ hMax дерева
    const L = p.birch ? ['tree_birch_h112', 'tree_birch_h96'] : ['tree_spruce_h120', 'tree_spruce_h80'];
    for (const n of L) { const sh = v2(n); if (sh && (sh.meta.hMax ?? 999) <= p.hMax) return n; }
    return null;
  }
  if (p.type === 'palisade' && !p.tyn && !p.tynH && !p.gatepost) return 'palisade_u4';
  if (p.type === 'izba' && !sheetOf(p)) return (V2A().izba || {})[p.id] || null;
  if (p.type === 'church') return V2A().church || null;   // v2art r2: клетская церковь 11×6 (ответ Василия)
  return null;
}
function v2PropSprite(p) {
  const name = v2PropSheet(p), sh = name && v2(name);
  if (!sh) return null;
  if (p.type === 'tree') return v2Sprite(name, p, p.x + 0.5, p.y + 0.5, { flip: p.seed > 0.5 });
  if (p.type === 'palisade') {
    // прясло 4 тайла вдоль u: клетка тына берёт свою полосу 16 px (крайние — до края листа); вдоль v — зеркало (истинная пара)
    const ys = p.axis === 'y', k = ((Math.floor(ys ? p.y : p.x) % 4) + 4) % 4, [fw] = sh.meta.frame_size || sh.meta.size, px = sh.meta.pivot[0];
    const a = k === 0 ? 0 : px + (k - 2) * HALF_W, b = k === 3 ? fw : px + (k - 1) * HALF_W;
    const x0 = ys ? p.x : p.x - k, y0 = ys ? p.y - k : p.y;
    const cx = ys ? x0 + 0.5 : x0 + 2, cy = ys ? y0 + 2 : y0 + 0.5;
    return ys ? v2Sprite(name, p, cx, cy, { flip: true, sx0: fw - b, sw: b - a }) : v2Sprite(name, p, cx, cy, { sx0: a, sw: b - a });
  }
  if (p.type === 'izba' || p.type === 'church') {
    const [fx, fy, fw2, fh2] = p.fp || [p.x, p.y, p.size, p.size], cx = fx + fw2 / 2, cy = fy + fh2 / 2;
    const spr = v2Sprite(name, p, cx, cy, { glow: name + '_windows' });
    if (spr && !p._lights) {   // окна — по windows.anchors листа (центр окна)
      const W = (sh.meta.windows || {}).anchors || [];
      p._lights = W.map((w) => [-spr.ox + w.x + w.w / 2, -spr.oy + w.y + w.h / 2, 'window']);
      p._winSrc = name;
    }
    return spr;
  }
  return null;
}

// toS(x,y) -> [sx,sy] экранные координаты мировой точки
export function drawProp(ctx, p, toS, time) {
  // крада и Чуров камень — анимированные спрайты художника (покой / отдых, общая фаза); без спрайта — заглушка грей-бокса
  if (p.type === 'fire' && p.krada) { const [x, y] = toS(p.x + p.size / 2, p.y + p.size / 2); if (drawRestSource(ctx, 'krada', p.restOn ? 'rest' : 'idle', x, y, time)) return; }
  if (p.type === 'churstone') { const [x, y] = toS(p.x + 0.5, p.y + 0.5); if (drawRestSource(ctx, 'churov', p.restOn ? 'rest' : 'idle', x, y, time)) return; }
  if (p.type === 'fire') return fire(ctx, p, toS, time);   // анимирован — рисуем каждый кадр
  if (p.type === 'hearth') return hearth(ctx, p, toS, time);   // огнища капища (веха M1b)
  if (p.type === 'perun') return perun(ctx, p, toS, time);
  if (p.type === 'ladya') return ladya(ctx, p, toS, time);
  if (p.type === 'cart') return cart(ctx, p, toS);
  if (p.type === 'anvil') return anvil(ctx, p, toS);
  if (p.type === 'relic') return relic(ctx, p, toS, time);
  if (p.type === 'stump') { const [x, y] = toS(p.x + 0.5, p.y + 0.5); if (!drawFxFrame(ctx, 'stump', p.variant || 0, x, y, { flip: p.seed > 0.5 })) ashPile(ctx, p, toS); return; }   // горелый пень (GDD v1.11); без спрайта — кучка пепла
  const v2c = p.type === 'church' && v2PropSheet(p) && v2(v2PropSheet(p));   // v2art r2: церковь v2 11×6 — лист v2 вместо bld_church
  if ((p.type === 'gateseg' || sheetOf(p) || zalIzba(p)) && !v2c && drawBld(ctx, p, toS, time)) return;   // m1k: постройки и ворота Ладоги — листы художника
  if (!p._spr) p._spr = v2PropSprite(p) || (p.shared ? sharedSprite(p) : bake(p));   // остальное статично — запекаем в спрайт (v2art: листы v2)
  const [sx, sy] = toS(p.x, p.y);
  ctx.drawImage(p._spr.c, sx - p._spr.ox, sy - p._spr.oy);
}

// Закрывает ли запечённый спрайт прямоугольник r (экранные px)? Проверка по маске непрозрачных пикселей.
/** m1k D4: непрозрачный ли пиксель спрайта пропса в экранной точке (X, Y). */
export function propMaskAt(p, toS, X, Y) {
  const s = p._spr;
  if (!s) return false;
  const [sx, sy] = toS(p.x, p.y), lx = Math.floor(X - (sx - s.ox)), ly = Math.floor(Y - (sy - s.oy));
  if (lx < 0 || ly < 0 || lx >= s.c.width || ly >= s.c.height) return false;
  if (!s.mask) propCovers(p, toS, { x: sx - s.ox, y: sy - s.oy, w: 1, h: 1 });
  return !!(s.mask && s.mask[ly * s.c.width + lx]);
}
/** Экранная рамка спрайта пропса {x, y, w, h} или null. */
export function propBox(p, toS) {
  const s = p._spr;
  if (!s) return null;
  const [sx, sy] = toS(p.x, p.y);
  return { x: sx - s.ox, y: sy - s.oy, w: s.c.width, h: s.c.height };
}
export function propCovers(p, toS, r) {
  const s = p._spr;
  if (!s) return false;
  const [sx, sy] = toS(p.x, p.y);
  const x0 = sx - s.ox, y0 = sy - s.oy, W = s.c.width, H = s.c.height;
  if (r.x + r.w <= x0 || r.x >= x0 + W || r.y + r.h <= y0 || r.y >= y0 + H) return false;
  if (!s.mask) {
    const d = s.c.getContext('2d').getImageData(0, 0, W, H).data;
    s.mask = new Uint8Array(W * H);
    for (let i = 0; i < W * H; i++) s.mask[i] = d[i * 4 + 3] > 0 ? 1 : 0;
  }
  let hits = 0;
  for (let yy = r.y; yy < r.y + r.h; yy += 3) {
    for (let xx = r.x; xx < r.x + r.w; xx += 3) {
      if (r.ell) { const ex = (xx - r.ell.cx) / r.ell.rx, ey = (yy - r.ell.cy) / r.ell.ry; if (ex * ex + ey * ey > 1) continue; }
      const lx = xx - x0, ly = yy - y0;
      if (lx >= 0 && ly >= 0 && lx < W && ly < H && s.mask[ly * W + lx]) hits++;
    }
  }
  return hits >= 6;
}

/** Лист художника для пропса (постройка / сегмент ворот) и его кадр; null — листа нет. */
/** v2b2: изба 4×4 Залесья без облика (была заглушка кодом) → izba_small_tes / _sod v2 (чередуются по месту). */
export function zalIzba(p) {
  if (p.type !== 'izba' || p.burnt || p.variant || (V2A().izba || {})[p.id]) return null;
  const n = (Math.round(p.x) + Math.round(p.y)) % 2 ? 'izba_small_sod' : 'izba_small_tes';
  return v2(n) ? n : null;
}
export function bldSheet(p, time = 0) {
  let name = p.type === 'gateseg' ? (p.open || !p.closedSheet ? p.openSheet : p.closedSheet) : sheetOf(p) || zalIzba(p);
  const sub = (V2A().izbaSmall || {})[name], s2 = (sub && v2(sub)) || (name && name.startsWith('izba_small') && v2(name));   // v2b2: избы 4×4 Ладоги — листы v2
  if (s2 && sub) name = sub;
  const sh = s2 || (name && VA.sheets[name]);
  if (!sh) return null;
  const n = sh.meta.frame_count || 1;
  const fr = p.type === 'gateseg' ? (n > 1 ? Math.floor(time * (sh.meta.fps || 8)) % n : 0) : p.type === 'sign' ? Math.min(n - 1, p.stage || 0) : frameOf(sh.meta, p.door);
  return { name, sh, fr };
}
/** Постройка художника: кадр запекается один раз (маска для «рентгена» — по нему же), поверх — дым из anchors_px.smoke. */
function drawBld(ctx, p, toS, time) {
  const B = bldSheet(p, time);
  if (!B) return false;
  const key = B.name + ':' + B.fr, bk = p._bk || (p._bk = {});
  let spr = bk[key];
  if (!spr) {
    spr = bakeSheet(B.sh, B.fr);
    const [ax, ay] = p.anchor || [p.x, p.y];   // сегмент ворот: лист привязан к мин. углу ворот, опора пропса — его клетка
    spr.ox -= ((ax - ay) - (p.x - p.y)) * HALF_W; spr.oy -= ((ax + ay) - (p.x + p.y)) * HALF_H;
    bk[key] = spr;
  }
  p._spr = spr;
  const [sx, sy] = toS(p.x, p.y);
  ctx.drawImage(spr.c, sx - spr.ox, sy - spr.oy);
  const WM = maskV2(B.name);
  if (WM) {   // v2art: маска окон художника поверх кадра — аддитивно, с лёгким дрожанием огня
    const k = (((CFG.stats || {}).light || {}).windowMasksV2 || {}).maskA ?? 0.55;
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = k * (0.85 + 0.15 * flick(time * 0.35, p.x * 3 + p.y));
    const [fw, fh] = WM.meta.frame_size || WM.meta.size;
    ctx.drawImage(WM.img, (B.fr % (WM.meta.frame_count || 1)) * fw, 0, fw, fh, sx - spr.ox, sy - spr.oy, fw, fh); ctx.restore();
    V2.counters.masks = (V2.counters.masks || 0) + 1;
  }
  const sa = p.smoke ? (smokeV2(B.name) || smokeAnchor(B.sh.meta, B.fr)) : null, pt = sa && sa.pt;
  p._smoked = !!pt;   // v1.13.3: дым — только у видов из smokeKinds (изба, с сенями, на подклете, баня)
  p._smokeSrc = sa ? sa.src : null;
  if (!p._lights || p.type === 'gateseg') p._lights = bldLights(p, B, spr);
  p._smokePt = pt ? [-spr.ox + pt[0], -spr.oy + pt[1]] : null;   // v2light: точка для клубов дыма (atmo.js)
  if (pt) drawFxFrame(ctx, 'smoke', Math.floor(time * ((FXfps) || 5) + p.seed * 4), sx - spr.ox + pt[0], sy - spr.oy + pt[1]);
  return true;
}
/** v2light: точки света постройки (смещения от toS(p.x, p.y)): факелы ворот — anchors_px.torch_A/B (только у открытых, как
 *  свет факелов в ladoga.js), окна/двери жилых — anchors_px.door, иначе передний угол чуть выше земли (окно/дверь фасада). */
function bldLights(p, B, spr) {
  const A = B.sh.meta.anchors_px || {}, out = [], pick = (a) => a && (Array.isArray(a) ? a : a[B.fr] || a['0']);
  const at = (pt, kind) => out.push([-spr.ox + pt[0], -spr.oy + pt[1], kind]);
  if (p.type === 'gateseg') {
    if (p.open || !p.closedSheet) for (const k of ['torch_A', 'torch_B']) { const pt = pick(A[k]); if (pt) at(pt, 'torch'); }
    return out;
  }
  const kinds = ((CFG.stats && CFG.stats.light && CFG.stats.light.window) || {}).kinds || ['izba', 'banya'];
  if (!kinds.some((k) => B.name.includes(k))) return out;
  // v2art: маски художника для бани / мастерской / лавки — окна по anchors[кадр] (cx, cy), у лавки — точка lamp у прилавка
  const MV2 = maskV2(B.name);
  if (MV2) {
    const an = MV2.meta.anchors || {}, list = Array.isArray(an) ? an : an[B.fr] || an['0'] || [];
    for (const w of list) at([w.cx ?? w.x + w.w / 2, w.cy ?? w.y + w.h / 2], 'window');
    const lamp = pick(MV2.meta.lamp);
    if (lamp) at(lamp, 'window');
    p._winSrc = MV2.meta.image ? MV2.meta.image.replace('.png', '') : 'v2';
    return out;
  }
  // v2: окна по маскам художника (stats.light.windowMasks), масштаб по ширине листа
  const WM = (((CFG.stats && CFG.stats.light) || {}).windowMasks || {}).list || [], M = WM.find((m) => B.name.includes(m.match));
  const pv = B.sh.meta.pivot, fs = B.sh.meta.frame_size;
  if (M && pv && fs) { const k = fs[0] / M.size[0]; for (const [ax, ay] of M.anchors) at([pv[0] + (ax - M.pivot[0]) * k, pv[1] + (ay - M.pivot[1]) * k], 'window'); p._winSrc = M.src; return out; }
  const door = pick(A.door), fc = B.sh.meta.front_corner_px;
  if (door) at(door, 'window');
  else if (fc) at([fc[0] - 10, fc[1] - 12], 'window');
  else at([spr.ox, spr.oy - 14], 'window');
  return out;
}
/** m1l (B-40): точка дыма листа. У bld_izba_small_tes_kon / _tes_prich художник не поставил anchors_px.smoke (есть только
 *  gable_vent — дымник во фронтоне), поэтому избы izba_sw / izba_se не дымили. Порядок: anchors_px.smoke → gable_vent →
 *  конёк над передним углом (front_corner_px − heights_px.ridge). Возвращает {pt, src} или null. */
/** v2art: маска окон v2 для листа постройки (stats.light.windowMasksV2) или null. */
export function maskV2(name) { const M = ((CFG.stats || {}).light || {}).windowMasksV2 || {}; return (M[name] && v2(M[name])) || null; }
/** v2art: точка дыма из ответа художника (stats.v2art.smoke: izba_small_tes_kon / _prich → [107, 62] во всех кадрах). */
export function smokeV2(name) { const s = (V2A().smoke || {})[name]; return Array.isArray(s) ? { pt: s, src: 'v2art' } : null; }
export function smokeAnchor(meta, fr) {
  const A = (meta && meta.anchors_px) || {};
  const pick = (a) => a && (Array.isArray(a) ? a : a[fr] || a['0']);
  for (const src of ['smoke', 'gable_vent']) { const pt = pick(A[src]); if (pt) return { pt, src }; }
  const fc = meta && meta.front_corner_px, rh = meta && meta.heights_px && meta.heights_px.ridge;
  if (fc && rh) return { pt: [fc[0], fc[1] - rh], src: 'ridge' };
  return null;
}
const FXfps = 5;   // fx_smoke_wisp: 4 кадра, 5 к/с (JSON художника)

export function propHeight(p) {
  { const n = v2PropSheet(p), sh = n && v2(n); if (sh) return sh.meta.pivot[1] + 4; }   // v2art: высота листа v2 над опорой
  if (p.type === 'gateseg' || sheetOf(p) || zalIzba(p)) { const B = bldSheet(p); if (B) return B.sh.meta.frame_size[1]; return p.type === 'gateseg' ? 100 : 132; }
  if (p.type === 'tree') return p.hMax ? p.hMax + 6 : p.birch ? 132 : 166;   // m1k D9: низкие деревья перед путём
  if (p.type === 'palisade') return p.tyn ? 44 : p.gatepost ? 100 : 86;   // m1i: низкий тын Залесья — как стена (44)
  if (p.type === 'fire' && p.krada) return 112;       // спрайт fx_rest_krada: 120 px, опора на 108
  return { rock: 36, wall: 44, izba: 132, fire: 80, hearth: 56, perun: 120, relic: 30, idol: 66, well: 64, churstone: 50, gate: 80, chest: 22, body: 12, bush: 24, ladya: 140, cart: 24, anvil: 16, stump: 18 }[p.type] || 40;
}

function drawRaw(ctx, p, toS) {
  switch (p.type) {
    case 'tree': return p.birch ? birch(ctx, p, toS) : pine(ctx, p, toS);
    case 'rock': return rock(ctx, p, toS);
    case 'wall': return wall(ctx, p, toS);
    case 'palisade': return palisade(ctx, p, toS);
    case 'izba': if (!p._lights) { const [a, b] = toS(p.x, p.y), [c, d] = toS(p.x + p.size, p.y + p.size); p._lights = [[c - a - 4, d - b - 18, 'window']]; } return izba(ctx, p, toS);
    case 'idol': return idol(ctx, p, toS);
    case 'well': return well(ctx, p, toS);
    case 'churstone': return churstone(ctx, p, toS);
    case 'gate': return gate(ctx, p, toS);
    case 'bush': return bush(ctx, p, toS);
    case 'ash': return ashPile(ctx, p, toS);
    case 'chest': return chest(ctx, p, toS);
    case 'body': return body(ctx, p, toS);
    case 'gateseg': return palisade(ctx, { ...p, gatepost: false }, toS);   // m1k: листа ворот нет — клетка тына
    case 'sign': return idol(ctx, p, toS);
    default: if (BLD_SHEET[p.type]) return izba(ctx, p, toS);               // m1k: постройка без листа — сруб-заглушка
  }
}

// Деревья чащи (сотни на тропе) делят запечённые спрайты: ключ — порода и семя с шагом 1/12.
const SHARED = new Map();
function sharedSprite(p) {
  const q = Math.round(p.seed * 12);
  const key = p.type + (p.birch ? 'b' : 'p') + q + (p.hMax ? 'h' + p.hMax : '');
  let s = SHARED.get(key);
  if (!s) { s = bake({ ...p, seed: q / 12 }); SHARED.set(key, s); }
  return s;
}

function bake(p) {
  const ph = propHeight(p) + 14;
  const extra = p.type === 'tree' ? 40 : p.gatepost === 'right' ? 110 : 0;
  // (чтобы гнутая перекладина ворот по оси y тоже влезла, extra симметричен)
  const W = p.size * TILE_W + 48 + extra * 2, H = p.size * TILE_H + ph + 8;
  const c = document.createElement('canvas');
  c.width = W; c.height = H;
  const ox = Math.round(W / 2), oy = ph;
  const [bx, by] = w2s(p.x, p.y);
  const local = (x, y) => { const [ix, iy] = w2s(x, y); return [Math.round(ix - bx + ox), Math.round(iy - by + oy)]; };
  drawRaw(c.getContext('2d'), p, local);
  return { c, ox, oy };
}

function pine(ctx, p, toS) {
  const [x, y] = toS(p.x + 0.5, p.y + 0.5);
  const H0 = Math.round(128 + p.seed * 32);         // 128–160, эталон 150
  const H = p.hMax ? Math.min(H0, p.hMax) : H0;     // m1k D9: молодая ель перед путём ≤ 96 px (крона ужата пропорционально)
  const half = Math.round((25 + Math.round(p.seed * 6)) * (p.hMax ? Math.max(0.7, H / H0) : 1));   // крона 50–62
  ellipse(ctx, x, y, 16, 6, PAL.ink, 0.4);
  figure(ctx, [{ x: x - 2, y: y - 22, w: 5, h: 22, c: PAL.wood_dk }]);   // ствол 5
  const bottom = y - 16, top = y - H, n = 6;
  for (let k = 0; k < n; k++) {
    const t = k / n;
    const base = bottom - (bottom - top) * t * 0.88;
    const tip = base - ((bottom - top) / n) * 1.7;
    const hw = half * (1 - t * 0.78);
    poly(ctx, [[x - hw - 1, base + 1], [x + hw + 1, base + 1], [x, tip - 1]], PAL.ink);
    poly(ctx, [[x - hw, base], [x + hw, base], [x, tip]], PAL.pine);
    poly(ctx, [[x - hw, base], [x - hw * 0.1, base], [x, tip]], PAL.moss);
    rect(ctx, x - hw + 3, base - 1, hw * 2 - 6, 1, PAL.pine_dk);
    rect(ctx, x + hw * 0.3, base - 4, hw * 0.4, 1, PAL.pine_dk);
  }
}

function birch(ctx, p, toS) {
  const [x, y] = toS(p.x + 0.5, p.y + 0.5);
  const H = Math.min(Math.round(96 + p.seed * 32), p.hMax || 999);   // 96–128; m1k D9: перед путём ≤ 112
  ellipse(ctx, x, y, 13, 5, PAL.ink, 0.4);
  const trunkTop = y - Math.round(H * 0.62);
  figure(ctx, [{ x: x - 2, y: trunkTop, w: 4, h: y - trunkTop, c: PAL.birch }]);
  for (let i = 0; i < 9; i++) rect(ctx, x - 2 + (i % 2) * 2, y - 6 - i * 7, 2, 1, PAL.ink);
  const cy = y - H + 26;
  const blobs = [[-14, 6, 12], [13, 4, 12], [0, -6, 14], [-7, -16, 10], [8, -15, 10], [0, 12, 11], [-1, -22, 8]];
  const c1 = p.seed > 0.5 ? PAL.bronze_lt : PAL.moss_lt, c2 = p.seed > 0.5 ? PAL.bronze_hi : PAL.bronze_lt;
  for (const [dx, dy, r] of blobs) disc(ctx, x + dx, cy + dy, r + 1, PAL.ink);
  for (const [dx, dy, r] of blobs) disc(ctx, x + dx, cy + dy, r, c1);
  for (const [dx, dy, r] of blobs) disc(ctx, x + dx - 2, cy + dy - 2, r * 0.45, c2);
  rect(ctx, x - 1, cy + 4, 2, 14, PAL.birch);
}

// m1i (critics_m1f П.16): камни — тёплый серо-оливковый вместо холодного slate: грани — дизеринг двух цветов палитры,
// шум (тёмные и светлые крапины) и мох на верхушке и по верхнему краю освещённой грани. Только палитра v2, без нового арта.
const DITHER = new Map();
function dither(ctx, a, b) {
  const key = a + b;
  let pat = DITHER.get(key);
  if (!pat) {
    const c = document.createElement('canvas'); c.width = 2; c.height = 2;
    const g = c.getContext('2d');
    g.fillStyle = a; g.fillRect(0, 0, 2, 2); g.fillStyle = b; g.fillRect(0, 0, 1, 1); g.fillRect(1, 1, 1, 1);
    pat = { c, pats: new WeakMap() }; DITHER.set(key, pat);
  }
  let pt = pat.pats.get(ctx);
  if (!pt) { pt = ctx.createPattern(pat.c, 'repeat'); pat.pats.set(ctx, pt); }
  return pt;
}
function fillPoly(ctx, pts, style) {
  ctx.fillStyle = style; ctx.beginPath();
  pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath(); ctx.fill();
}
const hsh = (x, y, s) => { const v = Math.sin(x * 127.1 + y * 311.7 + s * 74.7) * 43758.5453; return v - Math.floor(v); };
/** Цвета камня (для автотеста m1i): верх, освещённая грань, теневые грани, мох. */
export const STONE = { top: [PAL.birch, PAL.slate_lt], lit: [PAL.moss_lt, PAL.slate_lt], shade: [PAL.slate, PAL.wood], back: [PAL.slate_dk, PAL.wood_dk], moss: [PAL.moss, PAL.moss_lt] };

function rock(ctx, p, toS) {
  // валун: усечённая «пирамида» — верх меньше основания, чтобы не походило на ящик
  const s = p.size, ins = 0.08, k = 0.28 + p.seed * 0.12;
  const h = s > 1 ? 30 + Math.round(p.seed * 4) : 12 + Math.round(p.seed * 12);
  const base = [toS(p.x + ins, p.y + ins), toS(p.x + s - ins, p.y + ins), toS(p.x + s - ins, p.y + s - ins), toS(p.x + ins, p.y + s - ins)];
  const a0 = p.x + s * k, a1 = p.x + s * (1 - k * 0.8), b0 = p.y + s * k, b1 = p.y + s * (1 - k * 0.8);
  const top = [toS(a0, b0), toS(a1, b0), toS(a1, b1), toS(a0, b1)].map(([x, y]) => [x, y - h]);
  const [T, R, B, L] = base, [t, r, b, l] = top;
  poly(ctx, [T, R, B, L], PAL.ink);
  fillPoly(ctx, [L, B, b, l], dither(ctx, ...STONE.lit));
  fillPoly(ctx, [B, R, r, b], dither(ctx, ...STONE.shade));
  fillPoly(ctx, [T, R, r, t], dither(ctx, ...STONE.back));
  fillPoly(ctx, [L, T, t, l], dither(ctx, ...STONE.lit));
  fillPoly(ctx, [t, r, b, l], dither(ctx, ...STONE.top));
  // шум: крапины по силуэту
  const hull = [L, l, t, r, R, B];
  const xs = hull.map((q) => q[0]), ys = hull.map((q) => q[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  ctx.save(); ctx.beginPath(); hull.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath(); ctx.clip();
  for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
    const v = hsh(x, y, p.seed * 13 + p.x);
    if (v < 0.06) rect(ctx, x, y, 1, 1, PAL.slate_dk);
    else if (v > 0.965) rect(ctx, x, y, 1, 1, PAL.birch);
  }
  ctx.restore();
  // мох: пятна на верхушке и потёки по верхнему краю освещённой грани
  ctx.save(); ctx.beginPath(); [t, r, b, l].forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath();
  [L, B, b, l].forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath(); ctx.clip();
  const n = 3 + Math.round(p.seed * 4) + (s > 1 ? 4 : 0);
  for (let i = 0; i < n; i++) {
    const u = hsh(i, p.x, p.seed), w = hsh(p.y, i, p.seed + 1);
    const mx = Math.round(l[0] + (r[0] - l[0]) * u), my = Math.round(t[1] + (b[1] + 3 - t[1]) * w);
    const sz = 2 + Math.round(hsh(i, i, p.seed) * (s > 1 ? 4 : 2));
    rect(ctx, mx - sz, my, sz * 2, Math.max(1, sz - 1), PAL.moss);
    rect(ctx, mx - sz + 1, my, sz, 1, PAL.moss_lt);
  }
  ctx.restore();
  strokePoly(ctx, [l, t, r], PAL.birch, false);
  strokePoly(ctx, [T, R, B, L], PAL.ink);
  strokePoly(ctx, [L, l, t], PAL.ink, false);
  strokePoly(ctx, [R, r], PAL.ink, false);
  strokePoly(ctx, [B, b], PAL.night, false);
}

// m1i (critics_m1f П.16): стены Залесья — той же логикой, что тын Ладоги (palisade): брёвна с заострёнными верхушками
// и обвязкой; ось и линия брёвен — по футпринту стены (½ тайла), высота — прежняя (полуэтаж 32, местами ниже).
export function wallAsTyn(p) {
  const [fx, fy, fw, fh] = p.fp, ys = fh > fw;
  return { ...p, x: ys ? fx + fw / 2 - 0.5 : fx, y: ys ? fy : fy + fh / 2 - 0.5, axis: ys ? 'y' : 'x', gatepost: false, tynH: 32 - Math.round(p.seed * 6), bands: [10, 22] };
}
function wall(ctx, p, toS) { palisade(ctx, wallAsTyn(p), toS); }
/** Высоты трёх кольев звена (px, без острия). Низкий плетень-тын Залесья (p.tynH): строго TYN_MIN–TYN_MAX — герой (≈46 px)
 *  виден из-за него (дизайнер, m1i); высокий тын посада Ладоги и капища — 80 (воротные столбы 96), как было. */
export const TYN_MIN = 26, TYN_MAX = 32;
export function stakeHeights(p) {
  p = lowTyn(p);
  const H = p.tynH || (p.gatepost ? 96 : 80);
  return [0.17, 0.5, 0.83].map((t) => {
    const j = Math.round(((t + 0.5) * 13 + p.seed * 7) % (p.tynH ? 5 : 8));
    return p.tynH ? Math.max(TYN_MIN, Math.min(TYN_MAX, H - j + 2)) : H - j + (p.gatepost ? 0 : 4);
  });
}

/** Низкий тын Залесья (p.tyn): высота кольев TYN_MIN–TYN_MAX, обвязка на 10 и 22 — как у стен (wallAsTyn). */
export function lowTyn(p) { return p.tyn && !p.tynH ? { ...p, gatepost: false, tynH: 32 - Math.round(p.seed * 6), bands: [10, 22] } : p; }
function palisade(ctx, p, toS) {
  p = lowTyn(p);
  const ys = p.axis === 'y';
  const logs = [0.17, 0.5, 0.83].map((t) => (ys ? [0.5, t] : [t, 0.5]));   // шаг ≈ 0,31–0,33 тайла
  const hs = stakeHeights(p);
  logs.forEach(([fx, fy], i) => {
    const [x, y] = toS(p.x + fx, p.y + fy);
    const hh = hs[i];
    figure(ctx, [{ x: x - 3, y: y - hh, w: 6, h: hh, c: PAL.wood }]);
    rect(ctx, x - 3, y - hh, 2, hh, PAL.wood_md);
    rect(ctx, x + 2, y - hh, 1, hh, PAL.wood_dk);
    poly(ctx, [[x - 4, y - hh], [x + 4, y - hh], [x, y - hh - 6]], PAL.ink);
    poly(ctx, [[x - 3, y - hh], [x + 3, y - hh], [x, y - hh - 5]], PAL.wood_lt);
  });
  // обвязка на 24 и 64
  for (const z of p.bands || [24, 64]) {
    const a = toS(p.x + (ys ? 0.5 : 0), p.y + (ys ? 0 : 0.5)), b = toS(p.x + (ys ? 0.5 : 1), p.y + (ys ? 1 : 0.5));
    poly(ctx, [[a[0], a[1] - z], [b[0], b[1] - z], [b[0], b[1] - z + 2], [a[0], a[1] - z + 2]], PAL.wood_dk);
  }
  if (p.gatepost) {
    const [x, y] = toS(p.x + 0.5, p.y + 0.5);
    figure(ctx, [{ x: x - 1, y: y - 52, w: 3, h: 8, c: PAL.wood_dk }]);   // факел на 48
    disc(ctx, x, y - 55, 3.5, PAL.ember);
    disc(ctx, x, y - 55, 2, PAL.flame);
    if (p.gatepost === 'right') {                                         // перекладина ворот на 84–90
      const a = ys ? toS(p.x + 0.5, p.y - 2.5) : toS(p.x - 2.5, p.y + 0.5), b = toS(p.x + 0.5, p.y + 0.5);
      poly(ctx, [[a[0], a[1] - 91], [b[0], b[1] - 91], [b[0], b[1] - 83], [a[0], a[1] - 83]], PAL.ink);
      poly(ctx, [[a[0], a[1] - 90], [b[0], b[1] - 90], [b[0], b[1] - 84], [a[0], a[1] - 84]], PAL.wood_md);
      const m = ys ? toS(p.x + 0.5, p.y - 1) : toS(p.x - 1, p.y + 0.5);
      disc(ctx, m[0], m[1] - 87, 5, PAL.ink); disc(ctx, m[0], m[1] - 87, 4, PAL.bronze); disc(ctx, m[0], m[1] - 87, 1.5, PAL.bronze_hi);
    }
  }
}

function izba(ctx, p, toS) {
  if (p.burnt) return burntBarn(ctx, p, toS);
  const s = p.size, h = 68, R = 44, o = 0.3;          // стена 68 (17 венцов), подъём кровли 44, свес 0,3
  const [ox, oy] = toS(p.x, p.y);
  const box = isoBox(ctx, ox, oy, s, s, h, PAL.wood_md, PAL.wood_md, PAL.wood);
  for (let k = 4; k < h; k += 4) {                    // венцы по 4 px
    poly(ctx, [[box.L[0], box.L[1] - k], [box.B[0], box.B[1] - k], [box.B[0], box.B[1] - k + 1], [box.L[0], box.L[1] - k + 1]], PAL.wood_dk);
    poly(ctx, [[box.B[0], box.B[1] - k], [box.R[0], box.R[1] - k], [box.R[0], box.R[1] - k + 1], [box.B[0], box.B[1] - k + 1]], PAL.wood_dk);
  }
  const P = (x, y, z) => { const [a, b] = toS(x, y); return [a, b - z]; };
  // m1f: p.door === '+x' — дверь на торце +X (к колодцу), окно переезжает на фасад +Y
  const dx = p.door === '+x';
  // окно 12×12 на высоте 28–44 (торец +X), светится
  const w0 = dx ? P(p.x + 1.2, p.y + s, 28) : P(p.x + s, p.y + 1.2, 28), w1 = dx ? P(p.x + 1.95, p.y + s, 28) : P(p.x + s, p.y + 1.95, 28);
  poly(ctx, [[w0[0], w0[1] + 1], [w1[0], w1[1] + 1], [w1[0], w1[1] - 17], [w0[0], w0[1] - 17]], PAL.ink);
  poly(ctx, [w0, w1, [w1[0], w1[1] - 16], [w0[0], w0[1] - 16]], PAL.flame);
  // дверной проём 1,5 тайла × 56 от порога 4 (фасад +Y)
  const d0 = dx ? P(p.x + s, p.y + 1.4, 4) : P(p.x + 1.4, p.y + s, 4), d1 = dx ? P(p.x + s, p.y + 2.9, 4) : P(p.x + 2.9, p.y + s, 4);
  poly(ctx, [[d0[0] - 2, d0[1] + 2], [d1[0] + 2, d1[1] + 2], [d1[0] + 2, d1[1] - 58], [d0[0] - 2, d0[1] - 58]], PAL.wood_lt);
  poly(ctx, [d0, d1, [d1[0], d1[1] - 56], [d0[0], d0[1] - 56]], PAL.wood_dk);
  // кровля: конёк вдоль оси X
  const x0 = p.x - o, x1 = p.x + s + o, ym = p.y + s / 2;
  const backA = P(x0, p.y - o, h - 4), backB = P(x1, p.y - o, h - 4);
  const ridgeA = P(x0, ym, h + R), ridgeB = P(x1, ym, h + R);
  const frontA = P(x0, p.y + s + o, h - 4), frontB = P(x1, p.y + s + o, h - 4);
  poly(ctx, [backA, backB, ridgeB, ridgeA], PAL.wood_dk);
  poly(ctx, [P(p.x + s, p.y, h), P(p.x + s, p.y + s, h), P(p.x + s, ym, h + R - 4)], PAL.wood_md);   // фронтон
  const v0 = P(p.x + s, ym - 0.3, h + 10), v1 = P(p.x + s, ym + 0.3, h + 10);                           // волоковое окошко
  poly(ctx, [v0, v1, [v1[0], v1[1] - 6], [v0[0], v0[1] - 6]], PAL.ink);
  poly(ctx, [frontA, frontB, ridgeB, ridgeA], PAL.bronze_dk);
  for (let k = 1; k < 8; k++) {
    const t = k / 8;
    const a = [ridgeA[0] + (frontA[0] - ridgeA[0]) * t, ridgeA[1] + (frontA[1] - ridgeA[1]) * t];
    const b = [ridgeB[0] + (frontB[0] - ridgeB[0]) * t, ridgeB[1] + (frontB[1] - ridgeB[1]) * t];
    strokePoly(ctx, [a, b], PAL.wood, false);
  }
  strokePoly(ctx, [frontA, frontB, ridgeB, backB], PAL.ink, false);
  strokePoly(ctx, [ridgeA, ridgeB], PAL.wood_lt, false);
  strokePoly(ctx, [frontA, ridgeA, backA], PAL.ink, false);
  // конь на коньке (+12)
  figure(ctx, [{ x: ridgeB[0] - 2, y: ridgeB[1] - 12, w: 4, h: 12, c: PAL.wood_lt }, { x: ridgeB[0] + 1, y: ridgeB[1] - 13, w: 6, h: 4, c: PAL.wood_lt }]);
}

function fire(ctx, p, toS, time) {
  // крада 2×2: кольцо камней Ø 2,5 тайла, кладка дров 24, пламя до 72
  const [x, y] = toS(p.x + p.size / 2, p.y + p.size / 2);
  const rx = 1.25 * HALF_W * Math.SQRT2, ry = 1.25 * HALF_H * Math.SQRT2;
  for (let i = 0; i < 14; i++) {
    const a = (i / 14) * Math.PI * 2;
    figure(ctx, [{ x: x + Math.cos(a) * rx - 3, y: y + Math.sin(a) * ry - 2, w: 6, h: 4, c: i % 2 ? PAL.slate_lt : PAL.mist }]);
  }
  for (let k = 0; k < 6; k++) {                        // кладка дров «колодцем»
    const yy = y - 4 - k * 4, wide = k % 2 === 0;
    figure(ctx, [{ x: x - (wide ? 12 : 9), y: yy, w: wide ? 24 : 18, h: 3, c: k % 2 ? PAL.wood : PAL.wood_md }]);
  }
  const f1 = Math.sin(time * 9) * 3, f2 = Math.sin(time * 13 + 1) * 2;
  const by = y - 24;
  poly(ctx, [[x - 13, by + 2], [x + 13, by + 2], [x + 2 + f2, by - 48 - f1]], PAL.red_lt);
  poly(ctx, [[x - 9, by + 2], [x + 9, by + 2], [x - f2, by - 36 + f1]], PAL.ember);
  poly(ctx, [[x - 5, by + 2], [x + 5, by + 2], [x + f2 * 0.5, by - 20]], PAL.flame);
}

function idol(ctx, p, toS) {
  // чур 62×14
  const [ox, oy] = toS(p.x + 0.3, p.y + 0.3);
  isoBox(ctx, ox, oy, 0.42, 0.42, 56, PAL.wood_lt, PAL.wood_md, PAL.wood);
  const [x, y] = toS(p.x + 0.5, p.y + 0.5);
  rect(ctx, x - 4, y - 50, 3, 2, PAL.ink); rect(ctx, x + 1, y - 50, 3, 2, PAL.ink);
  rect(ctx, x - 1, y - 47, 2, 4, PAL.wood_dk);
  rect(ctx, x - 3, y - 41, 6, 1, PAL.ink);
  rect(ctx, x - 6, y - 30, 12, 2, PAL.wood_dk);
  figure(ctx, [{ x: x - 7, y: y - 62, w: 14, h: 4, c: PAL.wood }]);
}

function well(ctx, p, toS) {
  // колодец-сруб 2×2: венцы 18 px, тёмная вода, два столба и ворот (высота 60)
  const s = p.size, i = 0.25;
  const [ox, oy] = toS(p.x + i, p.y + i);
  isoBox(ctx, ox, oy, s - 2 * i, s - 2 * i, 18, PAL.wood_lt, PAL.wood_md, PAL.wood);
  const top = [toS(p.x + i + 0.18, p.y + i + 0.18), toS(p.x + s - i - 0.18, p.y + i + 0.18), toS(p.x + s - i - 0.18, p.y + s - i - 0.18), toS(p.x + i + 0.18, p.y + s - i - 0.18)].map(([x, y]) => [x, y - 18]);
  poly(ctx, top, PAL.night);
  for (let k = 6; k < 18; k += 6) { const [a, b] = toS(p.x + i, p.y + s - i), [c, d] = toS(p.x + s - i, p.y + s - i), [e, f] = toS(p.x + s - i, p.y + i); strokePoly(ctx, [[a, b - k], [c, d - k], [e, f - k]], PAL.wood_dk, false); }
  const [l1, l2] = toS(p.x + i + 0.1, p.y + s / 2), [r1, r2] = toS(p.x + s - i - 0.1, p.y + s / 2);
  rect(ctx, l1 - 1, l2 - 58, 3, 42, PAL.wood_dk); rect(ctx, r1 - 1, r2 - 58, 3, 42, PAL.wood_dk);
  strokePoly(ctx, [[l1, l2 - 54], [r1, r2 - 54]], PAL.wood_lt, false);
  strokePoly(ctx, [[l1, l2 - 55], [r1, r2 - 55]], PAL.ink, false);
  const [mx, my] = toS(p.x + s / 2, p.y + s / 2);
  rect(ctx, mx, my - 53, 1, 26, PAL.slate_lt);
  rect(ctx, mx - 3, my - 28, 7, 6, PAL.wood_md); rect(ctx, mx - 3, my - 28, 7, 1, PAL.wood_lt);
}

function churstone(ctx, p, toS) {
  // Чуров камень: серая стела 0,5×0,35 высотой 34 с резной светящейся руной
  const [ox, oy] = toS(p.x + 0.25, p.y + 0.32);
  isoBox(ctx, ox, oy, 0.5, 0.36, 34, PAL.slate_lt, PAL.slate, PAL.slate_dk);
  const [x, y] = toS(p.x + 0.5, p.y + 0.68);
  rect(ctx, x - 4, y - 28, 1, 14, PAL.flame); rect(ctx, x - 4, y - 28, 5, 1, PAL.flame); rect(ctx, x - 4, y - 21, 4, 1, PAL.flame);
  rect(ctx, x + 2, y - 26, 1, 10, PAL.bronze_hi);
}

// Закрытые ворота капища: две створки из тёса во весь проём (ось y), высота 72.
function gate(ctx, p, toS) {
  const [fx, fy, fw, fh] = p.fp;
  const [ox, oy] = toS(fx + 0.35, fy);
  const b = isoBox(ctx, ox, oy, 0.3, fh, 72, PAL.wood_md, PAL.wood, PAL.wood_dk);
  for (let k = 1; k < 8; k++) {                                       // доски
    const a = toS(fx + 0.65, fy + (fh * k) / 8);
    rect(ctx, a[0], a[1] - 72, 1, 72, PAL.wood_dk);
  }
  const m = toS(fx + 0.65, fy + fh / 2);
  rect(ctx, m[0] - 1, m[1] - 72, 2, 72, PAL.ink);                     // щель между створками
  for (const z of [16, 52]) { const a = toS(fx + 0.65, fy), c = toS(fx + 0.65, fy + fh); strokePoly(ctx, [[a[0], a[1] - z], [c[0], c[1] - z]], PAL.bronze_dk, false); }
  disc(ctx, m[0] - 4, m[1] - 34, 2.5, PAL.bronze); disc(ctx, m[0] + 4, m[1] - 34, 2.5, PAL.bronze);
  return b;
}

// Кованый сундук (сюжетный, лесная тропа М1): 0,9 × 0,5 тайла, высота 18, оковка бронзой; открытый — крышка откинута.
function chest(ctx, p, toS) {
  const [fx, fy, fw, fh] = p.fp;
  const [ox, oy] = toS(fx + 0.05, fy + 0.05);
  const b = isoBox(ctx, ox, oy, fw - 0.1, fh - 0.1, 12, p.open ? PAL.ink : PAL.wood_md, PAL.wood, PAL.wood_dk);
  for (const t of [0.2, 0.8]) { const a = toS(fx + 0.05 + (fw - 0.1) * t, fy + fh - 0.05); rect(ctx, a[0] - 1, a[1] - 12, 2, 12, PAL.bronze); }
  const lock = toS(fx + fw / 2, fy + fh - 0.05);
  rect(ctx, lock[0] - 2, lock[1] - 9, 4, 4, PAL.bronze_lt); rect(ctx, lock[0] - 1, lock[1] - 7, 1, 1, PAL.ink);
  if (p.open) {                                                      // откинутая крышка за сундуком
    const a = toS(fx + 0.05, fy + 0.05), c = toS(fx + fw - 0.05, fy + 0.05);
    poly(ctx, [[a[0], a[1] - 12], [c[0], c[1] - 12], [c[0], c[1] - 22], [a[0], a[1] - 22]], PAL.wood_md);
    strokePoly(ctx, [[a[0], a[1] - 12], [c[0], c[1] - 12], [c[0], c[1] - 22], [a[0], a[1] - 22]], PAL.ink);
  } else {
    const t0 = b.T, r0 = b.R;
    strokePoly(ctx, [[b.L[0], b.L[1] - 12], [b.B[0], b.B[1] - 12], [r0[0], r0[1] - 12]], PAL.bronze_lt, false);
    rect(ctx, t0[0] - 1, t0[1] - 13, 2, 1, PAL.bronze_hi);
  }
}

// Тело жреца у тропы: лежит плоско, белая свита в крови, рядом посох.
function body(ctx, p, toS) {
  const [x, y] = toS(p.x + 0.5, p.y + 0.5);
  ellipse(ctx, x, y, 16, 5, PAL.ink, 0.45);
  figure(ctx, [{ x: x - 14, y: y - 6, w: 22, h: 6, c: PAL.birch }, { x: x + 8, y: y - 8, w: 7, h: 7, c: PAL.wood_lt }]);
  rect(ctx, x + 8, y - 9, 7, 2, PAL.mist);                            // седые волосы
  rect(ctx, x - 6, y - 5, 6, 3, PAL.red_dk); rect(ctx, x - 4, y - 4, 3, 1, PAL.red);
  rect(ctx, x - 13, y - 3, 20, 1, PAL.bronze);                        // пояс
  for (let i = 0; i < 14; i++) rect(ctx, x - 22 + i * 2, y + 3 - i, 2, 1, PAL.wood_lt);   // посох
  if (!p.taken) { rect(ctx, x - 2, y + 1, 7, 1, PAL.ink); rect(ctx, x + 4, y, 2, 2, PAL.wood_dk); }   // чёрный нож
}

// Подлесок (кромка чащи перед тропой): низкий куст 1 тайл, высота до 22 — не закрывает тропу.
function bush(ctx, p, toS) {
  const [x, y] = toS(p.x + 0.5, p.y + 0.5);
  ellipse(ctx, x, y, 15, 6, PAL.ink, 0.4);
  const k = p.seed;
  const blobs = [[-9, -6, 7], [8, -5, 7], [0, -11, 8], [-4, -15, 6], [5, -14, 5], [0, -4, 8]];
  const c1 = k > 0.7 ? PAL.moss : PAL.pine, c2 = k > 0.7 ? PAL.moss_lt : PAL.moss;
  for (const [dx, dy, r] of blobs) disc(ctx, x + dx, y + dy, r + 1, PAL.ink);
  for (const [dx, dy, r] of blobs) disc(ctx, x + dx, y + dy, r, c1);
  for (const [dx, dy, r] of blobs) disc(ctx, x + dx - 1, y + dy - 2, r * 0.45, c2);
  if (k < 0.3) { rect(ctx, x - 5, y - 12, 2, 2, PAL.red_lt); rect(ctx, x + 3, y - 8, 2, 2, PAL.red_lt); }   // ягоды
}

// Огнище капища (грей-бокс, спрайта нет): кольцо камней Ø 1,2 тайла; пламя осквернённое — зелёное (Небыль), освящённое — тёплое.
function hearth(ctx, p, toS, time) {
  const [x, y] = toS(p.x + 0.5, p.y + 0.5);
  if (drawHearthArt(ctx, p, x, y, time)) return;                          // спрайт художника M1b (64×120, pivot 32,108)
  const rx = 0.6 * HALF_W * Math.SQRT2, ry = 0.6 * HALF_H * Math.SQRT2;
  ellipse(ctx, x, y, rx + 2, ry + 1, PAL.ink, 0.5);
  for (let i = 0; i < 10; i++) {
    const a = (i / 10) * Math.PI * 2;
    figure(ctx, [{ x: x + Math.cos(a) * rx - 3, y: y + Math.sin(a) * ry - 3, w: 6, h: 5, c: i % 2 ? PAL.slate : PAL.slate_lt }]);
  }
  const [c1, c2, c3] = p.cursed ? [PAL.nebyl_dk, PAL.nebyl, PAL.linen] : [PAL.red_lt, PAL.ember, PAL.flame];
  const f1 = Math.sin(time * 10 + p.x) * 3, f2 = Math.sin(time * 14 + p.y) * 2;
  poly(ctx, [[x - 9, y - 2], [x + 9, y - 2], [x + f2, y - 36 - f1]], c1);
  poly(ctx, [[x - 6, y - 2], [x + 6, y - 2], [x - f2, y - 26 + f1]], c2);
  poly(ctx, [[x - 3, y - 2], [x + 3, y - 2], [x + f2 * 0.5, y - 14]], c3);
}

// Идол Перуна 2×2 (грей-бокс): резной столб 110 px с усами-молниями; пока жив Кривша — горит.
function perun(ctx, p, toS, time) {
  { const [x, y] = toS(p.x + 1, p.y + 1); if (drawPerunArt(ctx, p, x, y, time)) return; }   // спрайт художника M1b (80×160, pivot 40,148), центр 2×2
  const [ox, oy] = toS(p.x + 0.6, p.y + 0.6);
  isoBox(ctx, ox, oy, 0.8, 0.8, 104, p.burning ? PAL.wood_md : PAL.slate, p.burning ? PAL.wood : PAL.slate_dk, p.burning ? PAL.wood_dk : PAL.ink);
  const [x, y] = toS(p.x + 1, p.y + 1);
  rect(ctx, x - 8, y - 96, 16, 3, PAL.bronze);                       // венец
  rect(ctx, x - 5, y - 86, 3, 3, PAL.ink); rect(ctx, x + 2, y - 86, 3, 3, PAL.ink);   // очи
  rect(ctx, x - 7, y - 76, 14, 2, PAL.bronze_lt);                    // усы-молнии
  rect(ctx, x - 1, y - 70, 2, 30, PAL.wood_dk);
  if (!p.burning) { rect(ctx, x - 6, y - 104, 12, 6, PAL.ink); return; }   // погас, обуглен
  const f1 = Math.sin(time * 9) * 4, f2 = Math.sin(time * 13 + 1) * 3;
  for (const [dx, h0] of [[-9, 60], [8, 54], [0, 70]]) {
    poly(ctx, [[x + dx - 7, y - 40], [x + dx + 7, y - 40], [x + dx + f2, y - 40 - h0 - f1]], PAL.red_lt);
    poly(ctx, [[x + dx - 4, y - 40], [x + dx + 4, y - 40], [x + dx - f2 * 0.5, y - 40 - h0 * 0.7 + f1]], PAL.ember);
  }
  poly(ctx, [[x - 5, y - 60], [x + 5, y - 60], [x + f1 * 0.5, y - 104]], PAL.flame);
}

// «Громовник» у подножия погасшего идола (заглушка вехи (в)): секира с бронзовым мерцанием.
function relic(ctx, p, toS, time) {
  if (p.taken) return;          // «Громовник» поднят (M1c)
  const [x, y] = toS(p.x + 0.5, p.y + 0.5);
  ellipse(ctx, x, y, 12, 4, PAL.bronze_hi, 0.25 + 0.15 * Math.sin(time * 4));
  poly(ctx, [[x - 12, y - 2], [x + 10, y - 7], [x + 11, y - 5], [x - 11, y]], PAL.wood_lt);
  poly(ctx, [[x + 4, y - 14], [x + 13, y - 10], [x + 12, y - 1], [x + 6, y - 4]], PAL.mist);
  rect(ctx, x + 6, y - 12, 2, 2, PAL.linen);
}

/** Обгоревший сарай у входа в тупик Мары (GDD v1.8.1 B-31): руины избы — вход в тупик читается с основного пути. */
function burntBarn(ctx, p, toS) {
  const s = p.size, h = 34;
  const [ox, oy] = toS(p.x, p.y);
  const box = isoBox(ctx, ox, oy, s, 2, h, PAL.wood_dk, PAL.wood_dk, PAL.slate_dk);
  for (let k = 4; k < h; k += 6) {
    poly(ctx, [[box.L[0], box.L[1] - k], [box.B[0], box.B[1] - k], [box.B[0], box.B[1] - k + 1], [box.L[0], box.L[1] - k + 1]], PAL.ink);
    poly(ctx, [[box.B[0], box.B[1] - k], [box.R[0], box.R[1] - k], [box.R[0], box.R[1] - k + 1], [box.B[0], box.B[1] - k + 1]], PAL.ink);
  }
  const P = (x, y, z) => { const [a, b] = toS(x, y); return [a, b - z]; };
  // пролом стены и обрушенная кровля (конёк сгорел — остался один скат)
  const hole0 = P(p.x + 0.6, p.y + 2, 4), hole1 = P(p.x + 2.2, p.y + 2, 4);
  poly(ctx, [hole0, hole1, [hole1[0], hole1[1] - 22], [hole0[0], hole0[1] - 22]], PAL.ink);
  const ridge = P(p.x + s * 0.5, p.y + 1, h + 10), front = P(p.x + s, p.y + 2.3, h - 10), back = P(p.x - 0.2, p.y + 2.3, h - 6);
  poly(ctx, [back, front, ridge], PAL.slate);
  strokePoly(ctx, [back, front, ridge], PAL.ink, false);
  // обугленные брёвна перед сараем
  poly(ctx, [P(p.x + 0.4, p.y + 2.4, 2), P(p.x + 2.4, p.y + 2.9, 2), P(p.x + 2.4, p.y + 2.9, 5), P(p.x + 0.4, p.y + 2.4, 5)], PAL.wood_dk);
  poly(ctx, [P(p.x + 0.2, p.y + 3.1, 1), P(p.x + 1.8, p.y + 3.4, 1), P(p.x + 1.8, p.y + 3.4, 4), P(p.x + 0.2, p.y + 3.1, 4)], PAL.ink);
}

/** Кучка пепла на тропке к тупику. */
function ashPile(ctx, p, toS) {
  const [x, y] = toS(p.x + 0.5, p.y + 0.5);
  ellipse(ctx, x, y, 9, 4, PAL.ink, 0.6);
  disc(ctx, x - 2, y - 1, 4, PAL.slate_dk);
  disc(ctx, x + 3, y, 3, PAL.slate);
  disc(ctx, x, y - 2, 2, PAL.slate_lt);
}

/** v2art: ладья у пристани — лист ladya_u (ось вдоль x) / ladya_v (вдоль y), 4 кадра @4, pivot [100,131] = центр корпуса
 *  на воде (p.x + len/2, p.y + beam/2). Под корпусом — отражение кодом: перевёрнутый кадр полосами с дрожанием, в пределах
 *  reflection_x; низ корпуса в листе уже обрезан по воде. Фонарь у кормы — точка тёплого света (anchors_px.lantern). */
function ladya(ctx, p, toS, time = 0) {
  const len = p.len || 12, beam = p.beam || 3, alongY = beam > len, name = alongY ? 'ladya_v' : 'ladya_u', sh = v2(name);
  if (sh) {
    const m = sh.meta, L = V2A().ladya || {}, [fw, fh] = m.frame_size, [px, py] = m.pivot, n = m.frames || 4;
    const fr = Math.floor(time * (L.fps ?? m.fps ?? 4)) % n, [cx, cy] = toS(p.x + len / 2, p.y + beam / 2);
    const rx = (m.anchors_px && m.anchors_px.reflection_x) || [0, fw], x0 = Math.min(rx[0], rx[1]), x1 = Math.max(rx[0], rx[1]);
    const RL = Math.round(py * (L.reflectLen ?? 1)), A = L.reflectA ?? 0.28;
    ctx.save();
    for (let r = 0; r < RL; r += 2) {   // строка r под водой = строка py − r листа (зеркало), гаснет книзу
      const sy = py - r - 2; if (sy < 0) break;
      ctx.globalAlpha = A * (1 - r / RL);
      const dx = Math.round(Math.sin(time * 3 + r * 0.45) * (1 + r / 40));
      ctx.drawImage(sh.img, fr * fw + x0, sy, x1 - x0, 2, cx - px + x0 + dx, cy + r, x1 - x0, 2);
    }
    ctx.restore();
    v2Blit(ctx, sh, fr, cx, cy);
    const [ax, ay] = toS(p.x, p.y), lan = m.anchors_px && m.anchors_px.lantern;
    if (L.lantern !== false && lan) p._lights = [[cx - ax - px + lan[0], cy - ay - py + lan[1], 'window']];
    p._ladyaFrame = fr; V2.counters.ladya = (V2.counters.ladya || 0) + 1;
    return;
  }
  const pts = [[p.x, p.y + beam / 2], [p.x + 1.2, p.y], [p.x + len - 1.2, p.y], [p.x + len, p.y + beam / 2], [p.x + len - 1.2, p.y + beam], [p.x + 1.2, p.y + beam]].map(([x, y]) => toS(x, y));
  // v2light: плоский серый шестиугольник-заглушка ладьи у пристани читался как «серый многоугольник на воде» — не рисуем,
  // пока художник не даст лист ладьи (пропс и его клетки остаются; вода там и так непроходима)
  void pts; void poly; void strokePoly;
}
function cart(ctx, p, toS) {
  const [x, y] = toS(p.x + 1.5, p.y + 1);
  rect(ctx, x - 16, y - 10, 32, 8, PAL.slate);
  rect(ctx, x - 14, y - 16, 28, 6, PAL.wood_md);
}
function anvil(ctx, p, toS) {
  const [x, y] = toS(p.x + 0.5, p.y + 0.5);
  rect(ctx, x - 6, y - 8, 12, 5, PAL.slate_lt);
  rect(ctx, x - 2, y - 3, 4, 4, PAL.slate);
}
