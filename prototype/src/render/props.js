// Препятствия грей-бокса по design/scale.md §3: ель 128–160, берёза 96–128, валуны 12–24 / 32,
// частокол 80 (столбы ворот 96, факелы на 48), сруб 4×4 (стена 68, охлупень 112, конёк 124),
// крада 2×2 (дрова 24, пламя до 72), чур 62, развалины — полуэтаж 32.
import { PAL } from '../palette.js';
import { HALF_W, HALF_H, TILE_W, TILE_H } from '../config.js';
import { w2s } from '../core/iso.js';
import { rect, poly, strokePoly, isoBox, disc, ellipse, figure } from './shapes.js';
import { drawRestSource } from './rest_fx.js';

// toS(x,y) -> [sx,sy] экранные координаты мировой точки
export function drawProp(ctx, p, toS, time) {
  // крада и Чуров камень — анимированные спрайты художника (покой / отдых, общая фаза); без спрайта — заглушка грей-бокса
  if (p.type === 'fire' && p.krada) { const [x, y] = toS(p.x + p.size / 2, p.y + p.size / 2); if (drawRestSource(ctx, 'krada', p.restOn ? 'rest' : 'idle', x, y, time)) return; }
  if (p.type === 'churstone') { const [x, y] = toS(p.x + 0.5, p.y + 0.5); if (drawRestSource(ctx, 'churov', p.restOn ? 'rest' : 'idle', x, y, time)) return; }
  if (p.type === 'fire') return fire(ctx, p, toS, time);   // анимирован — рисуем каждый кадр
  if (!p._spr) p._spr = p.shared ? sharedSprite(p) : bake(p);   // остальное статично — запекаем в спрайт
  const [sx, sy] = toS(p.x, p.y);
  ctx.drawImage(p._spr.c, sx - p._spr.ox, sy - p._spr.oy);
}

// Закрывает ли запечённый спрайт прямоугольник r (экранные px)? Проверка по маске непрозрачных пикселей.
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
      const lx = xx - x0, ly = yy - y0;
      if (lx >= 0 && ly >= 0 && lx < W && ly < H && s.mask[ly * W + lx]) hits++;
    }
  }
  return hits >= 6;
}

export function propHeight(p) {
  if (p.type === 'tree') return p.birch ? 132 : 166;
  if (p.type === 'palisade') return p.gatepost ? 100 : 86;
  if (p.type === 'fire' && p.krada) return 112;       // спрайт fx_rest_krada: 120 px, опора на 108
  return { rock: 36, wall: 36, izba: 132, fire: 80, idol: 66, well: 64, churstone: 50, gate: 80, chest: 22, body: 12, bush: 24 }[p.type] || 40;
}

function drawRaw(ctx, p, toS) {
  switch (p.type) {
    case 'tree': return p.birch ? birch(ctx, p, toS) : pine(ctx, p, toS);
    case 'rock': return rock(ctx, p, toS);
    case 'wall': return wall(ctx, p, toS);
    case 'palisade': return palisade(ctx, p, toS);
    case 'izba': return izba(ctx, p, toS);
    case 'idol': return idol(ctx, p, toS);
    case 'well': return well(ctx, p, toS);
    case 'churstone': return churstone(ctx, p, toS);
    case 'gate': return gate(ctx, p, toS);
    case 'bush': return bush(ctx, p, toS);
    case 'chest': return chest(ctx, p, toS);
    case 'body': return body(ctx, p, toS);
  }
}

// Деревья чащи (сотни на тропе) делят запечённые спрайты: ключ — порода и семя с шагом 1/12.
const SHARED = new Map();
function sharedSprite(p) {
  const q = Math.round(p.seed * 12);
  const key = p.type + (p.birch ? 'b' : 'p') + q;
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
  const H = Math.round(128 + p.seed * 32);          // 128–160, эталон 150
  const half = 25 + Math.round(p.seed * 6);         // крона 50–62
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
  const H = Math.round(96 + p.seed * 32);           // 96–128
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

function rock(ctx, p, toS) {
  // валун: усечённая «пирамида» — верх меньше основания, чтобы не походило на ящик
  const s = p.size, ins = 0.08, k = 0.28 + p.seed * 0.12;
  const h = s > 1 ? 30 + Math.round(p.seed * 4) : 12 + Math.round(p.seed * 12);
  const base = [toS(p.x + ins, p.y + ins), toS(p.x + s - ins, p.y + ins), toS(p.x + s - ins, p.y + s - ins), toS(p.x + ins, p.y + s - ins)];
  const a0 = p.x + s * k, a1 = p.x + s * (1 - k * 0.8), b0 = p.y + s * k, b1 = p.y + s * (1 - k * 0.8);
  const top = [toS(a0, b0), toS(a1, b0), toS(a1, b1), toS(a0, b1)].map(([x, y]) => [x, y - h]);
  const [T, R, B, L] = base, [t, r, b, l] = top;
  poly(ctx, [T, R, B, L], PAL.ink);
  poly(ctx, [L, B, b, l], PAL.slate);
  poly(ctx, [B, R, r, b], PAL.slate_dk);
  poly(ctx, [T, R, r, t], PAL.slate_dk);
  poly(ctx, [L, T, t, l], PAL.slate_lt);
  poly(ctx, [t, r, b, l], PAL.slate_lt);
  strokePoly(ctx, [l, t, r], PAL.mist, false);
  strokePoly(ctx, [T, R, B, L], PAL.ink);
  strokePoly(ctx, [L, l, t], PAL.ink, false);
  strokePoly(ctx, [R, r], PAL.ink, false);
  strokePoly(ctx, [B, b], PAL.night, false);
  if (s > 1) { const [mx, my] = toS(p.x + s / 2, p.y + s / 2); rect(ctx, mx - 6, my - h + 2, 5, 2, PAL.moss); rect(ctx, mx - 4, my - h + 1, 3, 1, PAL.moss_lt); }
}

function wall(ctx, p, toS) {
  // футпринт кратен ½ тайла (тонкая стена развалин — ½ тайла толщиной)
  const [fx, fy, fw, fh] = p.fp;
  const [ox, oy] = toS(fx, fy);
  const h = 32 - Math.round(p.seed * 6);            // полуэтаж 32 (развалины, местами осыпалось)
  const b = isoBox(ctx, ox, oy, fw, fh, h, PAL.mist, PAL.slate, PAL.slate_dk);
  for (let k = 6; k < h; k += 6) {
    poly(ctx, [[b.L[0], b.L[1] - k], [b.B[0], b.B[1] - k], [b.B[0], b.B[1] - k + 1], [b.L[0], b.L[1] - k + 1]], PAL.slate_dk);
    poly(ctx, [[b.B[0], b.B[1] - k], [b.R[0], b.R[1] - k], [b.R[0], b.R[1] - k + 1], [b.B[0], b.B[1] - k + 1]], PAL.night);
  }
  rect(ctx, b.B[0] - 3, b.B[1] - h + 3, 3, 1, PAL.slate_lt);
}

function palisade(ctx, p, toS) {
  const ys = p.axis === 'y';
  const logs = [0.17, 0.5, 0.83].map((t) => (ys ? [0.5, t] : [t, 0.5]));   // шаг ≈ 0,31–0,33 тайла
  const H = p.gatepost ? 96 : 80;
  for (const [fx, fy] of logs) {
    const [x, y] = toS(p.x + fx, p.y + fy);
    const hh = H - Math.round(((fx + fy) * 13 + p.seed * 7) % 8) + (p.gatepost ? 0 : 4);
    figure(ctx, [{ x: x - 3, y: y - hh, w: 6, h: hh, c: PAL.wood }]);
    rect(ctx, x - 3, y - hh, 2, hh, PAL.wood_md);
    rect(ctx, x + 2, y - hh, 1, hh, PAL.wood_dk);
    poly(ctx, [[x - 4, y - hh], [x + 4, y - hh], [x, y - hh - 6]], PAL.ink);
    poly(ctx, [[x - 3, y - hh], [x + 3, y - hh], [x, y - hh - 5]], PAL.wood_lt);
  }
  // обвязка на 24 и 64
  for (const z of [24, 64]) {
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
  const s = p.size, h = 68, R = 44, o = 0.3;          // стена 68 (17 венцов), подъём кровли 44, свес 0,3
  const [ox, oy] = toS(p.x, p.y);
  const box = isoBox(ctx, ox, oy, s, s, h, PAL.wood_md, PAL.wood_md, PAL.wood);
  for (let k = 4; k < h; k += 4) {                    // венцы по 4 px
    poly(ctx, [[box.L[0], box.L[1] - k], [box.B[0], box.B[1] - k], [box.B[0], box.B[1] - k + 1], [box.L[0], box.L[1] - k + 1]], PAL.wood_dk);
    poly(ctx, [[box.B[0], box.B[1] - k], [box.R[0], box.R[1] - k], [box.R[0], box.R[1] - k + 1], [box.B[0], box.B[1] - k + 1]], PAL.wood_dk);
  }
  const P = (x, y, z) => { const [a, b] = toS(x, y); return [a, b - z]; };
  // окно 12×12 на высоте 28–44 (торец +X), светится
  const w0 = P(p.x + s, p.y + 1.2, 28), w1 = P(p.x + s, p.y + 1.95, 28);
  poly(ctx, [[w0[0], w0[1] + 1], [w1[0], w1[1] + 1], [w1[0], w1[1] - 17], [w0[0], w0[1] - 17]], PAL.ink);
  poly(ctx, [w0, w1, [w1[0], w1[1] - 16], [w0[0], w0[1] - 16]], PAL.flame);
  // дверной проём 1,5 тайла × 56 от порога 4 (фасад +Y)
  const d0 = P(p.x + 1.4, p.y + s, 4), d1 = P(p.x + 2.9, p.y + s, 4);
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
