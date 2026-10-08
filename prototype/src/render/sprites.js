// Грей-бокс «спрайты» персонажей и предметов: простые фигуры в палитре. (sx,sy) — точка ног.
import { PAL } from '../palette.js';
import { rect, ellipse, ellipseStroke, figure, pline, disc } from './shapes.js';

export function shadow(ctx, x, y, rx = 9, ry = 3.5) { ellipse(ctx, x, y, rx, ry, PAL.ink, 0.45); }

// --- 8 направлений (API спрайтов: dir 0–7; 0 — к камере, далее по часовой через «влево»: 2 — влево, 4 — от камеры, 6 — вправо)
const BACK = new Set([3, 4, 5]), FRONT = new Set([7, 0, 1]);
export const dirSide = (dir, fallback = 1) => (dir >= 5 ? 1 : dir >= 1 && dir <= 3 ? -1 : fallback);
export function dirUnit(dir) { const a = Math.PI / 2 + dir * Math.PI / 4; return [Math.cos(a), Math.sin(a)]; }
// грей-бокс указатель взгляда: клинышек на краю тени у ног
export function dirMarker(ctx, x, y, dir, rx, ry, c) {
  const [ux, uy] = dirUnit(dir);
  const px = Math.round(x + ux * (rx + 2)), py = Math.round(y + uy * (ry + 1));
  rect(ctx, px - 1, py, 3, 1, c); rect(ctx, px, py - 1, 1, 3, c);
  rect(ctx, Math.round(px + ux * 2), Math.round(py + uy * 1.5), 1, 1, c);
}

// Герой по design/scale.md §2: рост 44 px (шпиль 0–2, шелом до 7, лицо и бармица 7–12, плечи 13,
// пояс 26, колени 35, подошвы 44 — ровно на строке pivot), плечи 14, щит 13×15, клинок 16×2.
export function drawHero(ctx, x, y, h, dir, time, outline = PAL.ink) {
  if (dir == null) dir = h.dir || 0;
  const f = dirSide(dir, h.facing);
  const back = BACK.has(dir), front = FRONT.has(dir);
  const a = h.action;
  const step = h.moving ? Math.sin(h.walkPhase * 1.8) : 0;
  const bob = h.moving ? Math.round(Math.abs(step)) : 0;
  const l = Math.round(step * 2);
  if (!h.dead) { shadow(ctx, x, y, 9, 3.5); dirMarker(ctx, x, y, dir, 9, 3.5, PAL.bronze_lt); }
  const T = y - 43 - bob;               // верхняя строка силуэта
  const parts = [
    { x: x - 8 - f, y: T + 12, w: 16, h: 22, c: PAL.red },             // плащ (цветовой акцент)
    { x: x - 5 + l, y: y - 11, w: 4, h: 12, c: PAL.wood_dk },          // ноги (подошвы на y)
    { x: x + 1 - l, y: y - 11, w: 4, h: 12, c: PAL.wood_dk },
    { x: x - 7, y: T + 13, w: 14, h: 14, c: PAL.slate_lt },            // кольчуга, плечи 14
    { x: x - 6, y: T + 26, w: 12, h: 7, c: PAL.red_dk },               // подол рубахи
    { x: x + f * 7 - (f < 0 ? 3 : 0), y: T + 14, w: 3, h: 11, c: PAL.slate_lt }, // рука с мечом
    { x: x - 4, y: T + 7, w: 8, h: 6, c: PAL.wood_lt },                // лицо
    { x: x - 4, y: T + 4, w: 8, h: 3, c: PAL.mist },                   // шелом
    { x: x - 3, y: T + 2, w: 6, h: 2, c: PAL.mist },
    { x: x - 1, y: T, w: 2, h: 2, c: PAL.birch },                      // шпиль
    { cx: x - f * 8, cy: T + 21, r: 6.5, c: PAL.red_lt },              // щит Ø13
  ];
  if (back) {                                                        // спиной к камере: плащ поверх кольчуги, лица не видно
    parts.splice(5, 0, { x: x - 8 + f, y: T + 12, w: 16, h: 22, c: PAL.red });
    parts.find((q) => q.c === PAL.wood_lt).c = PAL.slate_lt;
  }
  figure(ctx, parts, h.flash > 0, outline);
  rect(ctx, x - 7, T + 26, 14, 2, PAL.bronze);                       // пояс
  rect(ctx, x - 4, T + 10, 8, 3, PAL.slate_lt);                      // бармица
  if (back) rect(ctx, x - 1, T + 13, 2, 12, PAL.red_dk);             // шов плаща
  else if (dir === 0) { rect(ctx, x - 3, T + 8, 2, 1, PAL.ink); rect(ctx, x + 1, T + 8, 2, 1, PAL.ink); } // анфас — оба глаза
  else if (front) { rect(ctx, x + (f > 0 ? -1 : -2), T + 8, 2, 1, PAL.ink); rect(ctx, x + (f > 0 ? 2 : -4), T + 8, 1, 1, PAL.ink); }
  else rect(ctx, x + (f > 0 ? 1 : -3), T + 8, 2, 1, PAL.ink);         // профиль
  rect(ctx, x - 3, T + 4, 1, 3, PAL.linen);                          // блик шелома
  rect(ctx, x - 5, y - 2, 4, 2, PAL.ink); rect(ctx, x + 1, y - 2, 4, 2, PAL.ink); // сапоги
  const sx = x - f * 8;                                              // умбон и крест щита
  rect(ctx, sx - 6, T + 20, 13, 1, PAL.linen); rect(ctx, sx, T + 15, 1, 13, PAL.linen);
  rect(ctx, sx - 1, T + 20, 3, 2, PAL.bronze_hi);
  // меч (клинок 16 px, 2 px толщиной)
  const hx = x + f * 8, hy = T + 24;
  if (a && a.type === 'attack') {
    const k = Math.min(1, a.t / a.dur);
    const ang = (-120 + 160 * Math.min(1, k / 0.6)) * Math.PI / 180;
    const ex = hx + f * Math.cos(ang) * 17, ey = hy + Math.sin(ang) * 17;
    pline(ctx, hx, hy, ex, ey, PAL.linen);
    pline(ctx, hx + 1, hy, ex + 1, ey, PAL.mist);
    if (k > 0.35 && k < 0.8) {
      ctx.save();
      ctx.globalAlpha = 0.6;
      ctx.strokeStyle = PAL.linen;
      ctx.lineWidth = 1;
      ctx.beginPath();
      if (f > 0) ctx.arc(hx, hy, 18, -1.6, 0.7);
      else ctx.arc(hx, hy, 18, Math.PI - 0.7, Math.PI + 1.6);
      ctx.stroke();
      ctx.restore();
    }
  } else if (a && a.type === 'cast') {
    pline(ctx, hx, hy, hx + f * 3, hy - 16, PAL.mist);
    const fl = 3 + Math.sin(time * 40) * 0.8;
    disc(ctx, hx + f * 4, T - 2, fl + 2, PAL.ember);
    disc(ctx, hx + f * 4, T - 2, fl, PAL.flame);
  } else {
    pline(ctx, hx, hy + 1, hx + f * 3, hy - 15, PAL.mist);
    pline(ctx, hx + 1, hy + 1, hx + 1 + f * 3, hy - 15, PAL.birch);
    rect(ctx, hx - 2, hy, 5, 1, PAL.bronze);
  }
}

// Упырь: рост 40 (сутулый), силуэт 22–24 px, r 0.35.
export function drawUpyr(ctx, x, y, e, dir, time, outline = PAL.ink) {
  const f = dirSide(dir, e.facing), back = BACK.has(dir);
  const step = e.moving ? Math.sin(e.walkPhase * 1.4) : 0;
  const l = Math.round(step * 2);
  const lunge = e.state === 'attack' ? Math.round(Math.sin(Math.min(1, e.t / e.def.attackTime) * Math.PI) * 5) : 0;
  shadow(ctx, x, y, 10, 4); dirMarker(ctx, x, y, dir, 10, 4, PAL.slate);
  const T = y - 39;
  const parts = [
    { x: x - 6 + l, y: y - 10, w: 4, h: 11, c: PAL.slate_dk },
    { x: x + 2 - l, y: y - 10, w: 4, h: 11, c: PAL.slate_dk },
    { x: x - 10, y: T + 11, w: 20, h: 19, c: PAL.slate },              // тулово
    { x: x - 9 + f * 2, y: T + 6, w: 16, h: 7, c: PAL.slate },         // горб
    { x: x + f * 9 - (f < 0 ? 6 : 0) + f * lunge, y: T + 15, w: 6, h: 14, c: PAL.mist }, // длинные руки
    { x: x - 4 + f * 6, y: T, w: 9, h: 9, c: PAL.birch },              // голова вперёд
  ];
  figure(ctx, parts, e.flash > 0, outline);
  rect(ctx, x - 9, T + 22, 18, 2, PAL.slate_dk);                     // лохмотья
  rect(ctx, x - 8, T + 26, 3, 4, PAL.slate_dk); rect(ctx, x + 3, T + 27, 3, 3, PAL.slate_dk);
  if (!back) {                                                       // глаза (спиной — не видно, виден горб)
    rect(ctx, x + f * 7 - 1, T + 3, 2, 2, PAL.red_lt);
    rect(ctx, x + f * 3 - 1, T + 3, 2, 2, PAL.red_lt);
  } else rect(ctx, x - 7 + f * 2, T + 7, 12, 3, PAL.slate_dk);
  rect(ctx, x - 4 + f * 6, T + 7, 9, 2, PAL.nebyl_dk);               // трупная зелень
  rect(ctx, x + f * 9 - (f < 0 ? 6 : 0) + f * lunge, T + 27, 6, 2, PAL.birch); // когти
}

// Анчутка: рост 26, силуэт 16–18, r 0.25.
export function drawAnchutka(ctx, x, y, e, dir, time, outline = PAL.ink) {
  const f = dirSide(dir, e.facing), back = BACK.has(dir);
  const hop = e.moving ? Math.round(Math.abs(Math.sin(e.walkPhase * 2.2)) * 4) : Math.round(Math.abs(Math.sin(time * 3 + e.id)) * 1);
  shadow(ctx, x, y, 7, 3); dirMarker(ctx, x, y, dir, 7, 3, PAL.red_dk);
  const by = y - hop;
  const parts = [
    { x: x - 5, y: by - 6, w: 3, h: 7, c: PAL.wood_dk },
    { x: x + 2, y: by - 6, w: 3, h: 7, c: PAL.wood_dk },
    { x: x - 7, y: by - 17, w: 14, h: 11, c: PAL.red },
    { x: x - 6 + f, y: by - 24, w: 12, h: 8, c: PAL.red_lt },
    { x: x - 6 + f, y: by - 26, w: 2, h: 3, c: PAL.birch },          // рожки
    { x: x + 4 + f, y: by - 26, w: 2, h: 3, c: PAL.birch },
  ];
  figure(ctx, parts, e.flash > 0, outline);
  if (!back) {
    rect(ctx, x + f * 3, by - 21, 2, 2, PAL.flame);                  // глаза
    rect(ctx, x + f * 3 - f * 4, by - 21, 2, 2, PAL.flame);
  }
  rect(ctx, x - 7, by - 9, 14, 2, PAL.red_dk);
  pline(ctx, x - f * 7, by - 8, x - f * 12, by - 13, PAL.ink);       // хвост
  pline(ctx, x - f * 12, by - 13, x - f * 11, by - 15, PAL.ink);
  if (e.state === 'attack') { disc(ctx, x + f * 9, by - 14, 3, PAL.ember); disc(ctx, x + f * 9, by - 14, 1.5, PAL.flame); }
}

// Черноярец-поджигатель (E11): человек 44 px в тёмной свите и наголовнике, топор в одной руке, факел в другой.
export function drawArsonist(ctx, x, y, e, dir, time, outline = PAL.ink) {
  const f = dirSide(dir, e.facing), back = BACK.has(dir);
  const step = e.moving ? Math.sin(e.walkPhase * 1.8) : 0;
  const l = Math.round(step * 2), bob = e.moving ? Math.round(Math.abs(step)) : 0;
  shadow(ctx, x, y, 9, 3.5); dirMarker(ctx, x, y, dir, 9, 3.5, PAL.red_dk);
  const T = y - 43 - bob;
  // замах факелом: рука поднимается к броску
  const wind = e.state === 'torch' && e.def.torch ? Math.min(1, e.t / e.def.torch.windup) : 0;
  const swing = e.state === 'attack' ? Math.sin(Math.min(1, e.t / e.def.attackTime) * Math.PI) : 0;
  const parts = [
    { x: x - 5 + l, y: y - 11, w: 4, h: 12, c: PAL.ink },                // ноги в обмотках
    { x: x + 1 - l, y: y - 11, w: 4, h: 12, c: PAL.ink },
    { x: x - 7, y: T + 12, w: 14, h: 18, c: PAL.wood_dk },               // свита
    { x: x - 7, y: T + 26, w: 14, h: 7, c: PAL.slate_dk },               // подол
    { x: x - 4, y: T + 6, w: 8, h: 7, c: back ? PAL.slate_dk : PAL.wood_md },   // лицо
    { x: x - 5, y: T + 1, w: 10, h: 6, c: PAL.slate_dk },                // наголовник
    { x: x + f * 7 - (f < 0 ? 3 : 0), y: T + 13 - Math.round(wind * 8), w: 3, h: 11, c: PAL.wood_dk },   // рука с факелом
    { x: x - f * 9 - (f > 0 ? 0 : 3), y: T + 13, w: 3, h: 11, c: PAL.wood_dk },                         // рука с топором
  ];
  figure(ctx, parts, e.flash > 0, outline);
  rect(ctx, x - 7, T + 24, 14, 2, PAL.red_dk);                          // кушак
  rect(ctx, x - 1, T + 13, 2, 9, PAL.ink);                              // волчья тамга на груди
  if (!back) { rect(ctx, x + f * 2 - 1, T + 8, 2, 1, PAL.flame); rect(ctx, x - 4, T + 11, 8, 2, PAL.slate_dk); }
  // топор
  const ax = x - f * 8, ay = T + 24 - Math.round(swing * 14);
  pline(ctx, ax, ay, ax - f * 2, ay - 14, PAL.wood_lt);
  figure(ctx, [{ x: ax - f * 2 - (f > 0 ? 6 : 0), y: ay - 17, w: 6, h: 6, c: PAL.mist }]);
  // факел (пламя над рукой)
  const tx = x + f * 9, ty = T + 12 - Math.round(wind * 12);
  pline(ctx, tx, ty + 10, tx + f, ty - 2, PAL.wood_lt);
  const fl = Math.sin(time * 17 + e.id) * 1.2;
  disc(ctx, tx + f, ty - 5, 4 + fl, PAL.red_lt);
  disc(ctx, tx + f, ty - 5, 3 + fl * 0.5, PAL.ember);
  disc(ctx, tx + f, ty - 6, 1.6, PAL.flame);
}

// Селяне и Мал (act1, М1): без оружия, бегут к пристани / показывают тропу.
export function drawNpc(ctx, x, y, n, time) {
  const f = dirSide(n.dir, n.facing), small = n.kind === 'mal';
  const step = n.moving ? Math.sin(n.walkPhase * 2) : 0, l = Math.round(step * 2);
  const H = small ? 30 : 38, T = y - H + 1;
  shadow(ctx, x, y, small ? 6 : 8, 3);
  const shirt = small ? PAL.red : n.female ? PAL.birch : PAL.linen, hair = n.old ? PAL.mist : small ? PAL.wood_lt : PAL.wood_md;
  figure(ctx, [
    { x: x - 4 + l, y: y - (small ? 8 : 10), w: 3, h: small ? 9 : 11, c: PAL.wood_dk },
    { x: x + 1 - l, y: y - (small ? 8 : 10), w: 3, h: small ? 9 : 11, c: PAL.wood_dk },
    { x: x - 5, y: T + 9, w: 10, h: small ? 13 : 18, c: shirt },
    ...(n.female ? [{ x: x - 6, y: T + 18, w: 12, h: 12, c: PAL.red_dk }] : []),
    { x: x - 3, y: T + 2, w: 7, h: 7, c: PAL.wood_lt },
    { x: x - 4, y: T, w: 8, h: 3, c: n.female ? PAL.red : hair },
  ]);
  rect(ctx, x - 5, T + 17, 10, 1, PAL.red);
  if (n.dir !== 4) rect(ctx, x + f * 2 - 1, T + 4, 2, 1, PAL.ink);
}

export function drawEnemy(ctx, x, y, e, dir, time, hovered) {
  const ol = hovered ? PAL.red_lt : e.slowT > 0 ? PAL.blue_lt : PAL.ink;   // под курсором — красная обводка, замедлен холодом — голубая
  if (e.kind === 'upyr') drawUpyr(ctx, x, y, e, dir, time, ol);
  else if (e.def.torch) drawArsonist(ctx, x, y, e, dir, time, ol);
  else drawAnchutka(ctx, x, y, e, dir, time, ol);
  if (e.slowT > 0) { ctx.save(); ctx.globalAlpha = 0.25; ctx.fillStyle = PAL.blue_lt; ctx.fillRect(x - 10, y - e.def.height, 20, e.def.height); ctx.restore(); }
  // маленькая полоска жизни над недавно раненым
  if (e.lastHitT < 3 || hovered) {
    const w = 16, hy = y - e.def.height - 6;
    rect(ctx, x - w / 2 - 1, hy - 1, w + 2, 4, PAL.ink);
    rect(ctx, x - w / 2, hy, w, 2, PAL.red_dk);
    rect(ctx, x - w / 2, hy, Math.max(1, Math.round(w * e.hp / e.maxHp)), 2, PAL.red_lt);
  }
}

export function drawCorpse(ctx, x, y, e) {
  const a = 1 - Math.max(0, (e.corpseT - 8) / 2);
  if (a <= 0) return;
  ctx.save();
  ctx.globalAlpha = a;
  if (e.kind === 'upyr') {
    figure(ctx, [{ x: x - 13, y: y - 6, w: 20, h: 6, c: PAL.slate_dk }, { x: x + 7, y: y - 8, w: 8, h: 7, c: PAL.birch }]);
    rect(ctx, x - 10, y - 4, 10, 2, PAL.nebyl_dk);
  } else if (e.def.torch) {
    figure(ctx, [{ x: x - 14, y: y - 6, w: 20, h: 6, c: PAL.wood_dk }, { x: x + 6, y: y - 7, w: 7, h: 6, c: PAL.slate_dk }]);
    rect(ctx, x - 10, y - 4, 10, 2, PAL.red_dk);
    rect(ctx, x - 18, y - 2, 6, 1, PAL.wood_lt); rect(ctx, x - 19, y - 3, 2, 2, PAL.slate);   // погасший факел
  } else {
    figure(ctx, [{ x: x - 7, y: y - 4, w: 12, h: 4, c: PAL.red_dk }, { x: x + 5, y: y - 6, w: 6, h: 5, c: PAL.red }]);
  }
  ctx.restore();
}

// Лут на земле (scale.md §3.4): меч 22–24 в длину, щит 13×8, серебро 14×7.
export function drawGroundItem(ctx, x, y, it) {
  if (it.kind === 'silver') {
    ellipse(ctx, x, y - 1, 7, 3, PAL.ink, 0.6);
    for (const [dx, dy] of [[-6, -3], [-2, -2], [2, -3], [-4, -5], [0, -5], [3, -6], [-1, -7]]) {
      rect(ctx, x + dx, y + dy, 4, 2, PAL.mist); rect(ctx, x + dx, y + dy, 2, 1, PAL.linen);
    }
  } else if (it.kind === 'potion') {
    const [c, cl] = it.potion.startsWith('life') ? [PAL.red, PAL.red_lt] : it.potion.startsWith('yar') ? [PAL.blue, PAL.blue_lt] : [PAL.bronze, PAL.bronze_hi];
    figure(ctx, [{ cx: x, cy: y - 5, r: 4, c }, { x: x - 1, y: y - 12, w: 3, h: 4, c: PAL.birch }]);
    rect(ctx, x - 2, y - 7, 2, 2, cl);
  } else {
    const c = it.color, t = it.item.type;
    ellipse(ctx, x, y - 1, 8, 3, PAL.ink, 0.45);
    if (t === 'sword' || t === 'axe') {
      pline(ctx, x - 11, y + 1, x + 11, y - 9, PAL.ink);
      pline(ctx, x - 11, y, x + 11, y - 10, PAL.mist);
      pline(ctx, x - 10, y, x + 11, y - 9, PAL.linen);
      pline(ctx, x - 9, y - 6, x - 5, y + 2, PAL.bronze_lt);
      if (t === 'axe') figure(ctx, [{ x: x + 6, y: y - 12, w: 6, h: 7, c: PAL.mist }]);
    } else if (t === 'shield') {
      ellipse(ctx, x, y - 3, 7.5, 4.5, PAL.ink); ellipse(ctx, x, y - 3, 6.5, 4, PAL.red); rect(ctx, x - 1, y - 4, 2, 2, PAL.bronze_hi);
    } else if (t === 'head') {
      figure(ctx, [{ cx: x, cy: y - 4, r: 5, c: PAL.slate_lt }]); rect(ctx, x - 6, y - 3, 13, 2, PAL.slate); rect(ctx, x, y - 11, 1, 3, PAL.bronze_lt);
    } else if (t === 'neck' || t === 'ring') {
      disc(ctx, x, y - 3, t === 'ring' ? 3 : 4, PAL.ink); disc(ctx, x, y - 3, t === 'ring' ? 2 : 3, PAL.bronze_lt); disc(ctx, x, y - 3, 1, c);
    } else if (t === 'gloves' || t === 'feet') {
      figure(ctx, [{ x: x - 7, y: y - 6, w: 6, h: 6, c: PAL.wood_lt }, { x: x + 1, y: y - 7, w: 6, h: 6, c: PAL.wood_lt }]);
    } else if (t === 'belt') {
      figure(ctx, [{ x: x - 8, y: y - 4, w: 17, h: 3, c: PAL.wood_lt }]); rect(ctx, x - 1, y - 5, 3, 5, PAL.bronze_lt);
    } else {
      figure(ctx, [{ x: x - 6, y: y - 9, w: 13, h: 9, c: PAL.slate }]);
      rect(ctx, x - 5, y - 8, 11, 2, PAL.slate_lt);
      rect(ctx, x - 5, y - 4, 11, 1, PAL.slate_dk);
    }
    rect(ctx, x - 1, y - 1, 3, 1, c);
  }
}

export function drawProjectile(ctx, x, y, p, time) {
  if (p.coal) {
    ellipse(ctx, x, y, 2, 1, PAL.ink, 0.35);
    const z = 14 + Math.sin(Math.min(1, p.travelled / p.range) * Math.PI) * 8;
    disc(ctx, x, y - z, 2.2, PAL.red);
    disc(ctx, x, y - z, 1.4, PAL.ember);
    rect(ctx, x, y - z - 1, 1, 1, PAL.flame);
    return;
  }
  if (p.element === 'cold') {          // «Дыхание Морозко»: ледяная стрела по направлению полёта
    ellipse(ctx, x, y, 3, 1.5, PAL.ink, 0.3);
    const sx = (p.vx - p.vy), sy = (p.vx + p.vy) / 2, d = Math.hypot(sx, sy) || 1, ux = sx / d, uy = sy / d, z = 20;
    for (let i = 0; i < 7; i++) rect(ctx, Math.round(x - ux * i), Math.round(y - z - uy * i), i < 2 ? 2 : 1, i < 2 ? 2 : 1, i < 2 ? PAL.linen : i < 4 ? PAL.blue_lt : PAL.blue);
    return;
  }
  ellipse(ctx, x, y, 4, 2, PAL.ink, 0.35);
  const z = 22;
  const fl = Math.sin(time * 50) * 0.6;
  disc(ctx, x, y - z, 4.5 + fl, PAL.red_lt);
  disc(ctx, x, y - z, 3.2 + fl, PAL.ember);
  disc(ctx, x, y - z, 1.8, PAL.flame);
}
