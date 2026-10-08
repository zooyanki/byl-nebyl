// Оверлеи: экран смерти (с возвращением к краде) и меню паузы с переключателями.
import { VIEW_W, VIEW_H } from '../config.js';
import { PAL } from '../palette.js';
import { rect } from './shapes.js';
import { drawText } from '../core/font.js';

function frame(ctx, x, y, w, h) {
  rect(ctx, x, y, w, h, PAL.ink);
  rect(ctx, x + 1, y + 1, w - 2, h - 2, PAL.bronze);
  rect(ctx, x + 2, y + 2, w - 4, h - 4, PAL.ink);
  rect(ctx, x + 3, y + 3, w - 6, h - 6, PAL.wood_dk);
  for (let yy = y + 9; yy < y + h - 4; yy += 8) rect(ctx, x + 3, yy, w - 6, 1, PAL.wood);
}
function button(ctx, r, text, hover, on = null) {
  rect(ctx, r.x, r.y, r.w, r.h, PAL.ink);
  rect(ctx, r.x + 1, r.y + 1, r.w - 2, r.h - 2, hover ? PAL.bronze_lt : PAL.bronze_dk);
  rect(ctx, r.x + 2, r.y + 2, r.w - 4, r.h - 4, hover ? PAL.red_dk : PAL.wood_dk);
  drawText(ctx, r.x + r.w / 2, r.y + Math.round(r.h / 2) - 5, text, hover ? PAL.flame : PAL.linen, { align: 'c', outline: true });
  if (on !== null) {
    drawText(ctx, r.x + r.w - 8, r.y + Math.round(r.h / 2) - 5, on ? 'вкл' : 'выкл', on ? PAL.nebyl : PAL.mist, { align: 'r', outline: true });
  }
}
const inR = (m, r) => m.mx >= r.x && m.my >= r.y && m.mx < r.x + r.w && m.my < r.y + r.h;

export const DEATH_BTN = { x: VIEW_W / 2 - 80, y: 196, w: 160, h: 20 };
export function overDeathButton(m) { return inR(m, DEATH_BTN); }

export function drawDeath(ctx, game) {
  const k = Math.min(1, game.deathT / 1.2);
  ctx.save();
  ctx.globalAlpha = 0.72 * k;
  rect(ctx, 0, 0, VIEW_W, VIEW_H, PAL.ink);
  ctx.globalAlpha = 0.35 * k;
  rect(ctx, 0, 0, VIEW_W, VIEW_H, PAL.red_dk);
  ctx.restore();
  if (k < 0.6) return;
  const h = game.hero, d = game.deathInfo || { lost: 0 };
  drawText(ctx, VIEW_W / 2, 84, 'Пал ты, витязь…', PAL.red_lt, { align: 'c', outline: true, scale: 3 });
  drawText(ctx, VIEW_W / 2, 124, 'Но Ярь ещё теплится: огонь крады вернёт тебя в Явь.', PAL.birch, { align: 'c', outline: true });
  drawText(ctx, VIEW_W / 2, 144, d.lost > 0 ? 'Нечисть растащила ' + d.lost + ' серебра (10% носимого).' : 'Серебра при тебе не было — и терять нечего.', PAL.flame, { align: 'c', outline: true });
  drawText(ctx, VIEW_W / 2, 158, 'Опыт и снаряжение остаются при тебе.', PAL.mist, { align: 'c', outline: true });
  drawText(ctx, VIEW_W / 2, 172, 'Уровень ' + h.level + ' · Упокоено нечисти: ' + game.killsTotal + ' · Смертей: ' + game.deaths, PAL.mist, { align: 'c', outline: true });
  if (game.deathT > 1.5) {
    button(ctx, DEATH_BTN, 'Очнуться у крады', overDeathButton(game.input));
    drawText(ctx, VIEW_W / 2, 222, 'или Enter', PAL.mist, { align: 'c', outline: true, alpha: 0.7 + 0.3 * Math.sin(game.time * 4) });
  }
}

const PW = 360, PH = 250, PX = VIEW_W / 2 - PW / 2, PY = 40;
export const PAUSE_BTNS = [
  { id: 'sound', label: 'Звук (N)', x: PX + 20, y: PY + PH - 54, w: 100, h: 18 },
  { id: 'labels', label: 'Подписи (Z)', x: PX + 130, y: PY + PH - 54, w: 100, h: 18 },
  { id: 'minimap', label: 'Мини-карта', x: PX + 240, y: PY + PH - 54, w: 100, h: 18 },
];
export function pauseButtonAt(m) { const b = PAUSE_BTNS.find((b) => inR(m, b)); return b ? b.id : null; }

export function drawPause(ctx, game) {
  ctx.save(); ctx.globalAlpha = 0.6; rect(ctx, 0, 0, VIEW_W, VIEW_H, PAL.ink); ctx.restore();
  frame(ctx, PX, PY, PW, PH);
  drawText(ctx, VIEW_W / 2, PY + 9, 'Быль и Небыль', PAL.bronze_hi, { align: 'c', outline: true, scale: 2 });
  const lines = [
    ['ЛКМ / зажать ЛКМ', 'идти; по нечисти — бить'],
    ['Shift + ЛКМ', 'бить на месте'],
    ['ЛКМ по подписи', 'поднять добычу (серебро — само)'],
    ['ПКМ', 'Огненный змей (яри: ' + game.hero.skillCost + ')'],
    ['1–4', 'выпить отвар из пояса'],
    ['Alt (держать) / Z', 'подписи добычи / всегда'],
    ['Tab или M', 'большая карта поверх мира'],
    ['I или B / C', 'котомка / витязь'],
    ['N', 'звук вкл/выкл'],
    ['Esc', 'закрыть окна / пауза'],
  ];
  lines.forEach(([a, b], i) => {
    drawText(ctx, PX + 22, PY + 36 + i * 14, a, PAL.birch);
    drawText(ctx, PX + 150, PY + 36 + i * 14, b, PAL.linen);
  });
  const st = { sound: !game.audio.muted, labels: game.labelsAlways, minimap: game.showMinimap };
  for (const b of PAUSE_BTNS) button(ctx, b, b.label.replace(/ \(.\)$/, ''), inR(game.input, b), st[b.id]);
  drawText(ctx, VIEW_W / 2, PY + PH - 22, 'Пауза — Esc, чтобы продолжить', PAL.mist, { align: 'c' });
}
