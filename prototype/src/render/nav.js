// Стрелка у края и маркер над целью (GDD v1.13 §10.2, §7.4; задача D5). Арт: ui_nav_arrow (8 кадров e, se, s, sw, w, nw, n, ne;
// 12×12, pivot 6,6; кадр = round(atan2(dy, dx) / 45°) mod 8 в экранных координатах), ui_nav_mark (9×9, 2 кадра, pivot 4,8).
// Числа — stats.json → nav. Цель — game.navTarget() (метка обязательной цели в зоне; в Ладоге после Кривши — Вышата).
import { VIEW_W, PANEL_Y } from '../config.js';
import { PAL } from '../palette.js';
import { CFG } from '../data/config.js';
import { drawText } from '../core/font.js';
import { VA } from './village_art.js';
import { MINI } from './minimap.js';
import { UI_ATLAS } from '../data/ui_atlas.js';

const NAV = () => (CFG.stats && CFG.stats.nav) || {};
const FIELD_H = PANEL_Y;   // игровое поле 640×314 (до панели HUD)

/** Запретные зоны у края: трекер, мини-карта (+ кнопки под ней), шары. */
function blockers(game) {
  const out = [];
  const Q = UI_ATLAS.quest_layout;
  if (Q && !game.dlgWin) out.push({ x: Q.frame[0] - 2, y: Q.frame[1] - 2, w: Q.frame[2] + 4, h: Q.frame[3] + 4 });
  if (game.showMinimap !== false) out.push({ x: MINI.x - 2, y: 0, w: VIEW_W - MINI.x + 2, h: MINI.y + MINI.h + 28 });
  out.push({ x: 0, y: FIELD_H - 34, w: 72, h: 34 }, { x: VIEW_W - 72, y: FIELD_H - 34, w: 72, h: 34 });   // шары (r 27 у (40; 322))
  return out;
}
const inside = (x, y, r, pad = 7) => x > r.x - pad && x < r.x + r.w + pad && y > r.y - pad && y < r.y + r.h + pad;

export function drawNav(ctx, game) {
  game.navDrawn = null;
  if (game.settings && game.settings.navArrow === false) return;
  if (game.state !== 'play' || game.hero.dead || game.dlgWin) return;
  const T = game.navTarget && game.navTarget();
  if (!T) return;
  const N = NAV(), A = N.arrow || {}, M = N.mark || {}, h = game.hero, time = game.time;
  const [hx, hy0] = game.toS(h.x, h.y), hy = hy0 - 22;
  const [tx, ty0] = game.toS(T.x, T.y), lift = T.kind === 'gate' ? (M.hGate ?? 96) : T.kind === 'npc' ? 58 : (M.h ?? 40), ty = ty0 - lift;
  const combat = game.enemies.some((e) => !e.dead && !e.dummy && e.state !== 'idle' && e.state !== 'return' && e.state !== 'wander' && !e.buried);
  const flash = game.navFlashUntil && time < game.navFlashUntil;
  const [a0, a1] = A.alpha || [0.7, 1.0];
  let alpha = combat ? (A.combatAlpha ?? 0.4) : a0 + (a1 - a0) * (0.5 + 0.5 * Math.sin(time * Math.PI * 2 * (A.pulseHz ?? 1)));
  if (flash) alpha = Math.floor(time * 4) % 2 === 0 ? 1.0 : 0.35;   // §7.4 п. 7: 3 с ярче, 2 Гц
  const dist = Math.hypot(T.x - h.x, T.y - h.y);
  // «цель на экране» — виден сам ромб (точка над целью в поле 640×314, не под панелью HUD); иначе — стрелка у края
  const onScreen = ty >= 10 && ty <= FIELD_H - 10 && tx >= 10 && tx <= VIEW_W - 10;
  if (onScreen) {
    // маркер: дальше hideR — виден, ближе — гаснет за fade с
    const want = dist > (M.hideR ?? 3) ? 1 : 0, f = M.fade ?? 0.3, dt = Math.min(0.1, Math.max(0, time - (game._navT ?? time)));
    game.navMarkA = want ? Math.min(1, (game.navMarkA ?? 1) + dt / f) : Math.max(0, (game.navMarkA ?? 1) - dt / f);
    game._navT = time;
    if (game.navMarkA <= 0.01) { game.navDrawn = { kind: 'none', target: T.id, dist }; return; }
    const bob = Math.round(Math.sin(time * Math.PI * 2) * (M.bob ?? 2)), S = VA.ui.ui_nav_mark;
    const a = (combat ? (A.combatAlpha ?? 0.4) : 1) * game.navMarkA * (flash ? alpha : 1);
    ctx.save(); ctx.globalAlpha = a;
    if (S) { const fr = Math.floor(time * 2) % 2, [px, py] = S.meta.pivot || [4, 8]; ctx.drawImage(S.img, fr * 9, 0, 9, 9, Math.round(tx - px), Math.round(ty + bob - py), 9, 9); }
    else { ctx.fillStyle = PAL.bronze_hi; ctx.beginPath(); ctx.moveTo(tx, ty + bob - 8); ctx.lineTo(tx + 4, ty + bob - 4); ctx.lineTo(tx, ty + bob); ctx.lineTo(tx - 4, ty + bob - 4); ctx.fill(); }
    ctx.restore();
    game.navDrawn = { kind: 'mark', target: T.id, x: Math.round(tx), y: Math.round(ty + bob), alpha: +a.toFixed(2), dist };
    return;
  }
  game._navT = time; game.navMarkA = 1;
  // стрелка: пересечение луча «центр героя → цель» с рамкой в margin px от края поля
  const m = A.margin ?? 14, x0 = m, y0 = m, x1 = VIEW_W - m, y1 = FIELD_H - m;
  const dx = tx - hx, dy = ty - hy;
  let k = Infinity;
  if (dx > 0) k = Math.min(k, (x1 - hx) / dx); if (dx < 0) k = Math.min(k, (x0 - hx) / dx);
  if (dy > 0) k = Math.min(k, (y1 - hy) / dy); if (dy < 0) k = Math.min(k, (y0 - hy) / dy);
  let px = hx + dx * k, py = hy + dy * k;
  // не заходить на трекер, мини-карту и шары: сдвиг вдоль рамки до ближайшего свободного места
  const B = blockers(game), bad = (x, y) => B.some((r) => inside(x, y, r));
  if (bad(px, py)) {
    const per = 2 * (x1 - x0) + 2 * (y1 - y0);
    const toP = (s) => { s = ((s % per) + per) % per; if (s < x1 - x0) return [x0 + s, y0]; s -= x1 - x0; if (s < y1 - y0) return [x1, y0 + s]; s -= y1 - y0; if (s < x1 - x0) return [x1 - s, y1]; s -= x1 - x0; return [x0, y1 - s]; };
    const fromP = (x, y) => (Math.abs(y - y0) < 0.5 ? x - x0 : Math.abs(x - x1) < 0.5 ? (x1 - x0) + (y - y0) : Math.abs(y - y1) < 0.5 ? (x1 - x0) + (y1 - y0) + (x1 - x) : 2 * (x1 - x0) + (y1 - y0) + (y1 - y));
    const s0 = fromP(px, py);
    for (let d = 2; d < per / 2; d += 2) {
      const [ax, ay] = toP(s0 + d); if (!bad(ax, ay)) { px = ax; py = ay; break; }
      const [bx, by] = toP(s0 - d); if (!bad(bx, by)) { px = bx; py = by; break; }
    }
  }
  const ang = Math.atan2(ty - py, tx - px), fr = ((Math.round(ang / (Math.PI / 4)) % 8) + 8) % 8, S = VA.ui.ui_nav_arrow;
  ctx.save(); ctx.globalAlpha = alpha;
  if (S) ctx.drawImage(S.img, fr * 12, 0, 12, 12, Math.round(px) - 6, Math.round(py) - 6, 12, 12);
  else { ctx.fillStyle = PAL.bronze_hi; ctx.beginPath(); ctx.arc(px, py, 4, 0, 7); ctx.fill(); }
  ctx.restore();
  const steps = Math.round(dist);
  if (steps > (A.distOver ?? 15)) drawText(ctx, Math.round(px), Math.round(py) + 8, String(steps), PAL.mist, { align: 'c', alpha });
  game.navDrawn = { kind: 'arrow', target: T.id, x: Math.round(px), y: Math.round(py), frame: fr, alpha: +alpha.toFixed(2), steps, dist, blocked: B };
}
