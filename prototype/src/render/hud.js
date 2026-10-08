// HUD по макету mockup_gameplay_hud_v2: шары Жизнь/Ярь, панель, полоса опыта, уровень,
// слоты ЛКМ/ПКМ, пояс 1–4, серебро; сверху — цель, задание, журнал.
import { VIEW_W, VIEW_H, PANEL_Y } from '../config.js';
import { PAL } from '../palette.js';
import { rect, poly, disc, pline, figure } from './shapes.js';
import { drawText, textWidth } from '../core/font.js';
import { POTIONS } from '../data/items.js';
import { IMG, UI_ATLAS, drawIcon } from '../ui/assets.js';
import { MINI } from './minimap.js';

export const LAYOUT = (() => {
  const by = 328, big = 32, sm = 26, beltW = 4 * 24 + 3 * 2 + 6;
  let x = 136;
  const L = { lmb: { x, y: by, s: big } }; x += big + 6;
  L.f = [];
  for (let i = 0; i < 3; i++) { L.f.push({ x, y: by + 3, s: sm, key: 'F' + (i + 1) }); x += sm + 2; }
  x += 8;
  L.belt = { x, y: by + 1, w: beltW, slots: [] };
  for (let i = 0; i < 4; i++) L.belt.slots.push({ x: x + 3 + i * 26, y: by + 4, s: 24 });
  x += beltW + 10;
  for (let i = 3; i < 6; i++) { L.f.push({ x, y: by + 3, s: sm, key: 'F' + (i + 1) }); x += sm + 2; }
  x += 4;
  L.rmb = { x, y: by, s: big };
  L.silver = { x: x + big + 3, y: 331, w: 46 };
  L.level = { cx: 112, cy: 343 };
  L.xp = { x: 96, y: 322, w: VIEW_W - 192 };
  L.orbL = { cx: 40, cy: 322, r: 27 };
  L.orbR = { cx: VIEW_W - 40, cy: 322, r: 27 };
  return L;
})();

export const BTN = (() => { const b = UI_ATLAS.hud_buttons; return { x: b.x, y: b.y, s: 20, g: 2, keys: b.keys, labels: b.labels }; })();
export function buttonAt(mx, my) {
  if (my < BTN.y || my >= BTN.y + BTN.s) return -1;
  const i = Math.floor((mx - BTN.x) / (BTN.s + BTN.g));
  if (i < 0 || i >= BTN.keys.length || mx - BTN.x - i * (BTN.s + BTN.g) >= BTN.s) return -1;
  return i;
}
export function isOverHud(mx, my, game = null) {
  if (my >= PANEL_Y - 4) return true;
  if (my >= 292 && (mx < 90 || mx > VIEW_W - 90)) return true;
  if (game && game.topRightVisible) {
    if (mx >= MINI.x && my >= 0 && mx < MINI.x + MINI.w && my < MINI.y + MINI.h && game.showMinimap) return true;
    if (buttonAt(mx, my) >= 0) return true;
  }
  return false;
}

export function beltSlotAt(mx, my) {
  return LAYOUT.belt.slots.findIndex((s) => mx >= s.x && mx < s.x + s.s && my >= s.y && my < s.y + s.s);
}

function woodSlot(ctx, x, y, s, active = false) {
  rect(ctx, x, y, s, s, PAL.ink);
  rect(ctx, x + 1, y + 1, s - 2, s - 2, active ? PAL.bronze : PAL.wood_md);
  rect(ctx, x + 2, y + 2, s - 4, s - 4, PAL.ink);
  rect(ctx, x + 3, y + 3, s - 6, s - 6, PAL.wood_dk);
}

function iconSword(ctx, x, y, s) {
  pline(ctx, x + 4, y + s - 5, x + s - 4, y + 4, PAL.ink);
  pline(ctx, x + 3, y + s - 5, x + s - 5, y + 3, PAL.linen);
  pline(ctx, x + 4, y + s - 4, x + s - 4, y + 4, PAL.mist);
  pline(ctx, x + 4, y + s - 10, x + 10, y + s - 4, PAL.bronze_lt);
  rect(ctx, x + 2, y + s - 4, 3, 3, PAL.bronze);
}

function iconFire(ctx, x, y, s, t) {
  const cx = x + s * 0.62, cy = y + s * 0.4;
  poly(ctx, [[x + 4, y + s - 4], [cx - 2, cy - 4], [cx + 3, cy + 4]], PAL.red);
  poly(ctx, [[x + 6, y + s - 6], [cx - 1, cy - 2], [cx + 2, cy + 2]], PAL.ember);
  disc(ctx, cx, cy, s * 0.22 + 1, PAL.red_lt);
  disc(ctx, cx, cy, s * 0.22, PAL.ember);
  disc(ctx, cx - 1, cy - 1, s * 0.12 + Math.sin(t * 8) * 0.5, PAL.flame);
}

function potionIcon(ctx, x, y, kind) {
  const c = kind === 'life' ? PAL.red : PAL.blue, cl = kind === 'life' ? PAL.red_lt : PAL.blue_lt;
  figure(ctx, [{ x: x + 3, y: y, w: 5, h: 3, c: PAL.birch }, { cx: x + 5.5, cy: y + 8, r: 4.5, c }]);
  rect(ctx, x + 3, y + 6, 2, 2, cl);
  rect(ctx, x + 4, y - 1, 3, 1, PAL.wood_md);
}

function orb(ctx, o, ratio, kind, label, value, t) {
  const { cx, cy, r } = o;
  disc(ctx, cx, cy, r + 4, PAL.ink);
  disc(ctx, cx, cy, r + 3, PAL.bronze);
  disc(ctx, cx, cy, r + 2, PAL.bronze_dk);
  disc(ctx, cx, cy, r + 1, PAL.ink);
  disc(ctx, cx, cy, r, PAL.night);
  ctx.save();
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.clip();
  const top = cy + r - 2 * r * Math.max(0, Math.min(1, ratio));
  const [dk, md, lt] = kind === 'life' ? [PAL.red_dk, PAL.red, PAL.red_lt] : [PAL.blue_dk, PAL.blue, PAL.blue_lt];
  ctx.fillStyle = md;
  ctx.beginPath();
  ctx.moveTo(cx - r, cy + r);
  for (let x = -r; x <= r; x += 2) ctx.lineTo(cx + x, top + Math.sin(x * 0.3 + t * 3) * 1.2);
  ctx.lineTo(cx + r, cy + r);
  ctx.fill();
  ctx.fillStyle = dk;
  ctx.fillRect(cx - r, Math.max(top + 6, cy + r * 0.35), 2 * r, r);
  ctx.globalAlpha = 0.8;
  ctx.fillStyle = lt;
  for (let x = -r; x <= r; x += 1) ctx.fillRect(Math.round(cx + x), Math.round(top + Math.sin(x * 0.3 + t * 3) * 1.2), 1, 1);
  ctx.globalAlpha = 0.28;
  ctx.fillStyle = PAL.linen;
  ctx.beginPath(); ctx.ellipse(cx - r * 0.38, cy - r * 0.45, r * 0.32, r * 0.2, -0.6, 0, Math.PI * 2); ctx.fill();
  ctx.restore();
  // голова змея-оберега над шаром (упрощённо)
  const sx = kind === 'life' ? cx - 10 : cx + 10;
  figure(ctx, [{ x: sx - 4, y: cy - r - 10, w: 8, h: 6, c: PAL.bronze }, { x: sx + (kind === 'life' ? 3 : -7), y: cy - r - 8, w: 4, h: 3, c: PAL.bronze_lt }]);
  rect(ctx, sx + (kind === 'life' ? 1 : -2), cy - r - 9, 1, 1, kind === 'life' ? PAL.flame : PAL.blue_lt);
  drawText(ctx, cx + 1, cy + 1, label, PAL.birch, { align: 'c', outline: true });
  drawText(ctx, cx + 1, cy + 10, value, PAL.linen, { align: 'c', outline: true });
}

function housing(ctx, left) {
  let pts = [[0, 294], [62, 294], [88, 316], [88, 360], [0, 360]];
  if (!left) pts = pts.map(([x, y]) => [VIEW_W - x, y]);
  poly(ctx, pts, PAL.wood_dk);
  ctx.save();
  ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]); for (const p of pts) ctx.lineTo(p[0], p[1]); ctx.closePath(); ctx.clip();
  for (let x = left ? 0 : VIEW_W - 90; x < (left ? 90 : VIEW_W); x += 10) rect(ctx, x, 290, 1, 70, PAL.ink);
  ctx.restore();
  ctx.strokeStyle = PAL.bronze_lt; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(pts[4][0] + (left ? 0 : 0), pts[0][1]);
  ctx.moveTo(pts[0][0], pts[0][1] + 0.5); ctx.lineTo(pts[1][0], pts[1][1] + 0.5); ctx.lineTo(pts[2][0] + 0.5, pts[2][1]); ctx.lineTo(pts[3][0] + 0.5, pts[3][1]);
  ctx.stroke();
}

let staticLayer = null;
// Статичная часть HUD (доски панели, корпуса шаров, пустые слоты) рисуется один раз.
function drawStatic(ctx) {
  if (!staticLayer) {
    staticLayer = document.createElement('canvas');
    staticLayer.width = VIEW_W; staticLayer.height = VIEW_H;
    const c = staticLayer.getContext('2d');
    const L = LAYOUT;
    rect(c, 0, PANEL_Y, VIEW_W, VIEW_H - PANEL_Y, PAL.wood_dk);
    for (let y = PANEL_Y + 7; y < VIEW_H; y += 7) rect(c, 0, y, VIEW_W, 1, PAL.ink);
    for (let y = PANEL_Y + 1; y < VIEW_H; y += 7) rect(c, 0, y, VIEW_W, 1, PAL.wood);
    rect(c, 0, PANEL_Y - 4, VIEW_W, 1, PAL.ink);
    for (let x = 0; x < VIEW_W; x += 3) { rect(c, x, PANEL_Y - 3, 2, 1, PAL.bronze_lt); rect(c, x + 1, PANEL_Y - 2, 2, 1, PAL.bronze); }
    rect(c, 0, PANEL_Y - 1, VIEW_W, 1, PAL.ink);
    housing(c, true); housing(c, false);
    for (const f of L.f) {
      woodSlot(c, f.x, f.y, f.s);
      drawText(c, f.x + 4, f.y + 3, f.key, PAL.slate_lt);
    }
    const B = L.belt;
    rect(c, B.x, B.y, B.w, 30, PAL.ink);
    rect(c, B.x + 1, B.y + 1, B.w - 2, 28, PAL.wood_dk);
    c.strokeStyle = PAL.bronze; c.strokeRect(B.x + 0.5, B.y + 0.5, B.w - 1, 29);
    rect(c, B.x + 1, B.y, B.w - 2, 1, PAL.bronze_lt);
    const S = L.silver;
    rect(c, S.x, S.y, S.w, 26, PAL.ink);
    rect(c, S.x + 1, S.y + 1, S.w - 2, 24, PAL.wood_dk);
    for (const [a, b] of [[5, 16], [9, 14], [4, 12]]) { rect(c, S.x + a, S.y + b, 6, 2, PAL.slate_lt); rect(c, S.x + a, S.y + b - 1, 6, 1, PAL.birch); }
    drawText(c, S.x + S.w - 4, S.y + 3, 'серебро', PAL.mist, { align: 'r' });
    const lv = L.level;
    disc(c, lv.cx, lv.cy, 14, PAL.ink); disc(c, lv.cx, lv.cy, 13, PAL.bronze);
    disc(c, lv.cx, lv.cy, 11, PAL.ink); disc(c, lv.cx, lv.cy, 10, PAL.wood_dk);
    drawText(c, lv.cx + 1, lv.cy - 10, 'ур.', PAL.bronze_lt, { align: 'c' });
  }
  ctx.drawImage(staticLayer, 0, 0);
}

export function drawHud(ctx, game) {
  const h = game.hero, t = game.time, L = LAYOUT;
  drawStatic(ctx);

  // опыт
  const xr = Math.max(0, Math.min(1, h.xpRatio));
  rect(ctx, L.xp.x - 1, L.xp.y - 1, L.xp.w + 2, 7, PAL.ink);
  rect(ctx, L.xp.x, L.xp.y, L.xp.w, 5, PAL.night);
  rect(ctx, L.xp.x, L.xp.y, Math.round(L.xp.w * xr), 5, PAL.bronze);
  rect(ctx, L.xp.x, L.xp.y, Math.round(L.xp.w * xr), 1, PAL.bronze_hi);
  for (let i = 1; i < 10; i++) rect(ctx, L.xp.x + Math.round(L.xp.w * i / 10), L.xp.y, 1, 5, PAL.ink);

  // слоты
  woodSlot(ctx, L.lmb.x, L.lmb.y, L.lmb.s);
  iconSword(ctx, L.lmb.x + 3, L.lmb.y + 3, L.lmb.s - 6);
  drawText(ctx, L.lmb.x + 3, L.lmb.y + L.lmb.s - 11, 'ЛКМ', PAL.birch, { outline: true });
  // пояс
  const B = L.belt;
  B.slots.forEach((s, i) => {
    const hv = game.hoverBelt === i;
    woodSlot(ctx, s.x, s.y, s.s, hv);
    const b = h.belt[i];
    if (b) {
      drawIcon(ctx, POTIONS[b.kind].icon, s.x, s.y + 1, s.s, s.s);
      if (b.count > 1) drawText(ctx, s.x + 3, s.y + 2, String(b.count), PAL.linen, { outline: true });
    }
    drawText(ctx, s.x + s.s - 7, s.y + s.s - 10, String(i + 1), PAL.bronze_hi, { outline: true });
  });
  // ПКМ — Огненный змей
  const R = L.rmb;
  woodSlot(ctx, R.x, R.y, R.s, true);
  iconFire(ctx, R.x + 3, R.y + 3, R.s - 6, t);
  if (h.yar < h.skillCost) { ctx.save(); ctx.globalAlpha = 0.55; rect(ctx, R.x + 3, R.y + 3, R.s - 6, R.s - 6, PAL.blue_dk); ctx.restore(); }
  drawText(ctx, R.x + 3, R.y + R.s - 11, 'ПКМ', PAL.birch, { outline: true });
  // серебро
  const S = L.silver;
  drawText(ctx, S.x + S.w - 4, S.y + 14, String(h.silver), PAL.linen, { align: 'r' });
  if (h.points > 0) { disc(ctx, L.level.cx + 10, L.level.cy - 11, 4, PAL.ink); disc(ctx, L.level.cx + 10, L.level.cy - 11, 3, PAL.red_lt); drawText(ctx, L.level.cx + 11, L.level.cy - 15, '+', PAL.linen, { align: 'c' }); }
  // уровень
  const lv = L.level;
  drawText(ctx, lv.cx + 1, lv.cy - 1, String(h.level), PAL.bronze_hi, { align: 'c', outline: true });
  // шары
  orb(ctx, L.orbL, h.hp / h.maxHp, 'life', 'Жизнь', Math.ceil(h.hp) + '/' + h.maxHp, t);
  orb(ctx, L.orbR, h.yar / h.maxYar, 'yar', 'Ярь', Math.floor(h.yar) + '/' + h.maxYar, t + 1.7);

  drawTopUi(ctx, game);
  drawLog(ctx, game);
}

export function drawHudTooltip(ctx, game) {
  drawTooltip(ctx, game);
}

function plate(ctx, x, y, w, h, alpha = 0.72) {
  ctx.save(); ctx.globalAlpha = alpha; rect(ctx, x, y, w, h, PAL.ink); ctx.restore();
  ctx.strokeStyle = PAL.wood_md; ctx.lineWidth = 1; ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
  for (const [px, py] of [[x, y], [x + w - 1, y], [x, y + h - 1], [x + w - 1, y + h - 1]]) rect(ctx, px, py, 1, 1, PAL.bronze_lt);
}

function drawTopUi(ctx, game) {
  const h = game.hero, ui = game.ui;
  // задание (под окном «Витязь» не рисуем)
  if (!ui.charOpen) {
    plate(ctx, 4, 4, 150, 30);
    drawText(ctx, 9, 7, 'Окрестности Залесья', PAL.bronze_hi);
    drawText(ctx, 9, 19, 'Упокой нечисть: ' + game.killsTotal + '/' + game.enemyTotal, game.killsTotal >= game.enemyTotal ? PAL.nebyl : PAL.linen);
  }
  // зона, мини-карта и кнопки меню (как на макете HUD v2); под окном «Котомка» прячутся
  if (game.topRightVisible) {
    const z1 = 'Залесье — окрестности', z2 = 'Акт I · Миссия 1 из 3';
    const w = textWidth(z1) + 10;
    ctx.save(); ctx.globalAlpha = 0.62; rect(ctx, VIEW_W - w, 0, w, 24, PAL.ink); ctx.restore();
    for (let k = 0; k < w; k += 4) rect(ctx, VIEW_W - w + k, 23, 1, 1, k % 8 ? PAL.bronze : PAL.bronze_lt);
    drawText(ctx, VIEW_W - 7, 3, z1, PAL.bronze_lt, { align: 'r', outline: true });
    drawText(ctx, VIEW_W - 7, 13, z2, PAL.mist, { align: 'r', outline: true });
    if (game.showMinimap) game.minimap.drawCorner(ctx, game);
    if (IMG.buttons && IMG.buttons.complete) ctx.drawImage(IMG.buttons, BTN.x, BTN.y);
    const hb = buttonAt(game.input.mx, game.input.my);
    if (hb >= 0) {
      const bx = BTN.x + hb * (BTN.s + BTN.g);
      rect(ctx, bx, BTN.y, BTN.s, 1, PAL.bronze_hi); rect(ctx, bx, BTN.y + BTN.s - 1, BTN.s, 1, PAL.bronze_hi);
      rect(ctx, bx, BTN.y, 1, BTN.s, PAL.bronze_hi); rect(ctx, bx + BTN.s - 1, BTN.y, 1, BTN.s, PAL.bronze_hi);
      const key = BTN.keys[hb] === 'ESC' ? 'Esc' : BTN.keys[hb];
      const txt = BTN.labels[hb] + ' (' + key + ')', tw = textWidth(txt) + 8;
      const tx = Math.min(VIEW_W - tw - 2, bx + BTN.s / 2 - tw / 2);
      plate(ctx, tx, BTN.y + BTN.s + 3, tw, 13, 0.85);
      drawText(ctx, tx + 4, BTN.y + BTN.s + 5, txt, PAL.linen);
    }
    let sy = BTN.y + BTN.s + (hb >= 0 ? 19 : 4);
    if (game.audio.muted) { drawText(ctx, VIEW_W - 6, sy, 'Звук выключен (N)', PAL.mist, { align: 'r', outline: true }); sy += 10; }
    if (game.labelsAlways) drawText(ctx, VIEW_W - 6, sy, 'Подписи: всегда (Z)', PAL.mist, { align: 'r', outline: true });
  }
  if (game.debug) drawText(ctx, VIEW_W - 6, 150, 'FPS ' + Math.round(game.fps), PAL.mist, { align: 'r' });
  // цель
  const e = game.hoverEnemy || (game.lastTarget && !game.lastTarget.dead && game.lastTarget.lastHitT < 3 ? game.lastTarget : null);
  if (e && !ui.anyOpen) {
    const w = 140, x = VIEW_W / 2 - w / 2, y = 5;
    rect(ctx, x - 2, y - 2, w + 4, 15, PAL.ink);
    rect(ctx, x - 1, y - 1, w + 2, 13, PAL.bronze);
    rect(ctx, x, y, w, 11, PAL.red_dk);
    rect(ctx, x, y, Math.round(w * e.hp / e.maxHp), 11, PAL.red);
    rect(ctx, x, y, Math.round(w * e.hp / e.maxHp), 1, PAL.red_lt);
    drawText(ctx, VIEW_W / 2, y + 1, e.name + ' · ур. ' + e.mlvl, PAL.linen, { align: 'c', outline: true });
    drawText(ctx, VIEW_W / 2, y + 15, e.def.family + ' · ' + e.def.realm, PAL.nebyl, { align: 'c', outline: true });
  }
  // подсказка в начале
  if (game.time < 14 && !game.hero.dead && !ui.anyOpen) {
    const a = game.time < 11 ? 1 : (14 - game.time) / 3;
    const s = 'ЛКМ — идти/бить/поднять · ПКМ — Огненный змей · Alt — подписи · Tab — карта · I/C — котомка/витязь · N — звук';
    const w = textWidth(s) + 10;
    ctx.save(); ctx.globalAlpha = a;
    plate(ctx, VIEW_W / 2 - w / 2, 290, w, 14, 0.6);
    drawText(ctx, VIEW_W / 2, 293, s, PAL.birch, { align: 'c' });
    ctx.restore();
  }
  // уведомление
  if (game.notice && game.time - game.notice.t < 1.6) {
    drawText(ctx, game.camCX, 64, game.notice.text, game.notice.color, { align: 'c', outline: true });
  }
}

function drawLog(ctx, game) {
  const lines = game.log.lines;
  let y = 278 - (game.time < 14 ? 16 : 0);
  for (let i = lines.length - 1; i >= 0; i--) {
    const l = lines[i];
    const age = game.log.time - l.t;
    const a = age > 6 ? Math.max(0, 1 - (age - 6) / 2) : 1;
    drawText(ctx, 96, y, l.text, l.color, { outline: true, alpha: a });
    y -= 10;
  }
}

function drawTooltip(ctx, game) {
  const m = game.input, h = game.hero;
  let txt = null;
  if (game.hoverBelt >= 0) {
    const b = h.belt[game.hoverBelt];
    txt = b ? POTIONS[b.kind].name + ' ×' + b.count + ' — клавиша ' + (game.hoverBelt + 1) : 'Пустая ячейка пояса';
  } else if (inSlot(m, LAYOUT.rmb)) txt = 'Огненный змей, ранг ' + h.skillRank + ': ' + h.skillMin + '–' + h.skillMax + ' огнём, взрыв 1 тайл · ' + h.skillCost + ' яри';
  else if (inSlot(m, LAYOUT.lmb)) txt = 'Удар оружием — урон ' + h.dmgMin + '–' + h.dmgMax + (h.equip.rhand ? ' (' + h.equip.rhand.name + ')' : ' (без оружия)');
  if (!txt) return;
  const w = textWidth(txt) + 8;
  const x = Math.max(2, Math.min(VIEW_W - w - 2, m.mx - w / 2));
  plate(ctx, x, PANEL_Y - 22, w, 13, 0.9);
  drawText(ctx, x + 4, PANEL_Y - 20, txt, PAL.linen);
}

function inSlot(m, s) { return m.mx >= s.x && m.mx < s.x + s.s && m.my >= s.y && m.my < s.y + s.s; }

export function drawCursor(ctx, game) {
  const m = game.input;
  if (game.ui.hand) return;
  const x = Math.round(m.mx), y = Math.round(m.my);
  const c = game.hoverEnemy ? PAL.red_lt : game.hoverLabel || game.hoverGround ? PAL.bronze_hi : PAL.linen;
  poly(ctx, [[x - 1, y - 1], [x + 8, y + 7], [x + 4, y + 8], [x + 2, y + 12], [x - 1, y + 11]], PAL.ink);
  poly(ctx, [[x, y], [x + 6, y + 6], [x + 3, y + 7], [x + 1, y + 10], [x, y + 10]], c);
}
