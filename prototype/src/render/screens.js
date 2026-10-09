// Оверлеи: экран смерти (с возвращением к краде) и меню паузы с переключателями.
import { VIEW_W, VIEW_H } from '../config.js';
import { PAL } from '../palette.js';
import { rect } from './shapes.js';
import { drawText, textWidth } from '../core/font.js';
import { t, silverText, plural } from '../core/i18n.js';
import { S as STATS } from '../data/progression.js';

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
    drawText(ctx, r.x + r.w - 8, r.y + Math.round(r.h / 2) - 5, t(on ? 'proto.toggle.on' : 'proto.toggle.off'), on ? PAL.nebyl : PAL.mist, { align: 'r', outline: true });
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
  // тексты гибели — act1_texts §20/§21 (data/ru.json); серебро без склонения: «Потеряно серебра: N» (GDD §10.1)
  drawText(ctx, VIEW_W / 2, 84, t('death.title'), PAL.red_lt, { align: 'c', outline: true, scale: 3 });
  drawText(ctx, VIEW_W / 2, 124, t(d.line || 'death.line1'), PAL.birch, { align: 'c', outline: true });
  drawText(ctx, VIEW_W / 2, 144, d.lost > 0 ? silverText(d.lost, 'lost') + ' ' + t('proto.death.penalty_note') : t('ui.death.penalty_none'), PAL.flame, { align: 'c', outline: true });
  drawText(ctx, VIEW_W / 2, 158, t('proto.death.keep'), PAL.mist, { align: 'c', outline: true });
  drawText(ctx, VIEW_W / 2, 172, t('ui.hud.level', { level: h.level }) + ' · ' + game.killsTotal + ' ' + plural(game.killsTotal, 'proto.plural.vrag_upokoen') + ' · ' + t('proto.death.deaths', { n: String(game.deaths) }), PAL.mist, { align: 'c', outline: true });
  const D = STATS.death || {};
  if (game.deathT > (D.buttonDelay ?? 1.5)) {
    button(ctx, DEATH_BTN, t('ui.death.button'), overDeathButton(game.input));   // m1f P1.7: текст — ключ ui.death.button (act1_texts)
  }
  if (game.deathT > (D.keyDelay ?? 2.5)) drawText(ctx, VIEW_W / 2, 222, t('proto.death.or_enter'), PAL.mist, { align: 'c', outline: true, alpha: 0.7 + 0.3 * Math.sin(game.time * 4) });
}

const PW = 360, PH = 250, PX = VIEW_W / 2 - PW / 2, PY = 40;
// m1i (critics_m1f П.13): подпись и «вкл/выкл» разведены — подпись слева, состояние в отдельной плашке справа;
// весь блок (подпись + плашка) — зона щелчка. Тексты — ru.json (proto.pause.*, proto.toggle.*).
const TG = { w: 108, h: 16, sw: 34 };
export const PAUSE_BTNS = [
  { id: 'sound', key: 'proto.pause.sound', x: PX + 14, y: PY + PH - 56, w: TG.w, h: TG.h },
  { id: 'labels', key: 'proto.pause.labels', x: PX + 14 + 112, y: PY + PH - 56, w: TG.w, h: TG.h },
  { id: 'minimap', key: 'proto.pause.minimap', x: PX + 14 + 224, y: PY + PH - 56, w: TG.w, h: TG.h },
];
export function pauseButtonAt(m) { const b = PAUSE_BTNS.find((b) => inR(m, b)); return b ? b.id : null; }
/** Строки справки: [клавиша, действие] — ключи ru.json; рывок (Пробел) — m1i. */
export const HELP_KEYS = [
  ['proto.help.move.key', 'proto.help.move'], ['proto.help.stand.key', 'proto.help.stand'], ['proto.help.pickup.key', 'proto.help.pickup'],
  ['proto.help.rmb.key', 'proto.help.rmb'], ['ui.hud.dash', 'proto.help.dash'], ['proto.help.belt.key', 'proto.help.belt'],
  ['proto.help.labels.key', 'proto.help.labels'], ['proto.help.map.key', 'proto.help.map'], ['proto.help.windows.key', 'proto.help.windows'],
  ['proto.help.sound.key', 'proto.help.sound'], ['proto.help.esc.key', 'proto.help.esc'],
];

function toggle(ctx, b, label, on, hover) {
  const sx = b.x + b.w - TG.sw;
  drawText(ctx, b.x + 2, b.y + Math.round((b.h - 9) / 2), label, hover ? PAL.flame : PAL.birch, { outline: true });
  rect(ctx, sx, b.y, TG.sw, b.h, PAL.ink);
  rect(ctx, sx + 1, b.y + 1, TG.sw - 2, b.h - 2, hover ? PAL.bronze_lt : PAL.bronze_dk);
  rect(ctx, sx + 2, b.y + 2, TG.sw - 4, b.h - 4, on ? PAL.nebyl_dk : PAL.wood_dk);
  drawText(ctx, sx + TG.sw / 2, b.y + Math.round((b.h - 9) / 2), t(on ? 'proto.toggle.on' : 'proto.toggle.off'), on ? PAL.nebyl : PAL.mist, { align: 'c', outline: true });
}

export function drawPause(ctx, game) {
  ctx.save(); ctx.globalAlpha = 0.6; rect(ctx, 0, 0, VIEW_W, VIEW_H, PAL.ink); ctx.restore();
  frame(ctx, PX, PY, PW, PH);
  drawText(ctx, VIEW_W / 2, PY + 9, t('ui.menu.title'), PAL.bronze_hi, { align: 'c', outline: true, scale: 2 });
  const rows = HELP_KEYS.map(([k, d]) => [t(k), t(d, { n: game.hero.skillCost })]);
  rows.forEach(([a, b], i) => {
    drawText(ctx, PX + 22, PY + 34 + i * 14, a, PAL.birch);
    drawText(ctx, PX + 150, PY + 34 + i * 14, b, PAL.linen);
  });
  game.pauseLines = rows;   // для автотеста m1i
  const st = { sound: !game.audio.muted, labels: game.labelsAlways, minimap: game.showMinimap };
  for (const b of PAUSE_BTNS) toggle(ctx, b, t(b.key).replace(/ \(.\)$/, ''), st[b.id], inR(game.input, b));
  drawText(ctx, VIEW_W / 2, PY + PH - 22, t('proto.pause.hint'), PAL.mist, { align: 'c' });
}

// --- m1i (critics_m1f П.15, GDD §10/§11): главное меню, один слот. «Продолжить» — загрузка слота (серая, если слота нет),
// «Новая игра» — при занятом слоте спрашивает подтверждение (ui.menu.slot_new_confirm). Тексты — ui.menu.* из ru.json.
const MB = { w: 200, h: 20 };
export const MENU_BTNS = [
  { id: 'continue', key: 'ui.menu.continue', x: VIEW_W / 2 - MB.w / 2, y: 150, w: MB.w, h: MB.h },
  { id: 'new', key: 'ui.menu.new_game', x: VIEW_W / 2 - MB.w / 2, y: 176, w: MB.w, h: MB.h },
];
export const MENU_CONFIRM = [
  { id: 'yes', key: 'ui.common.yes', x: VIEW_W / 2 - 104, y: 214, w: 96, h: MB.h },
  { id: 'no', key: 'ui.common.no', x: VIEW_W / 2 + 8, y: 214, w: 96, h: MB.h },
];
export function mainMenuAt(m, menu) {
  const list = menu.confirm ? MENU_CONFIRM : MENU_BTNS.filter((b) => b.id !== 'continue' || menu.slot);
  const b = list.find((b) => inR(m, b));
  return b ? b.id : null;
}
export function drawMainMenu(ctx, game) {
  const menu = game.menu, m = game.input;
  ctx.save(); ctx.globalAlpha = 0.72; rect(ctx, 0, 0, VIEW_W, VIEW_H, PAL.ink); ctx.restore();
  drawText(ctx, VIEW_W / 2, 64, t('ui.menu.title'), PAL.bronze_hi, { align: 'c', outline: true, scale: 3 });
  for (let k = VIEW_W / 2 - 120; k < VIEW_W / 2 + 120; k += 4) rect(ctx, k, 104, 2, 1, k % 8 ? PAL.bronze : PAL.bronze_lt);
  if (menu.confirm) {
    frame(ctx, VIEW_W / 2 - 150, 150, 300, 94);
    const words = t('ui.menu.slot_new_confirm').split(' '), lines = [];
    let cur = '';
    for (const w of words) { const nx = cur ? cur + ' ' + w : w; if (cur && textWidth(nx) > 270) { lines.push(cur); cur = w; } else cur = nx; }
    if (cur) lines.push(cur);
    lines.forEach((l, i) => drawText(ctx, VIEW_W / 2, 166 + i * 12, l, PAL.linen, { align: 'c', outline: true }));
    for (const b of MENU_CONFIRM) button(ctx, b, t(b.key), inR(m, b));
    return;
  }
  for (const b of MENU_BTNS) {
    const off = b.id === 'continue' && !menu.slot;
    if (off) { ctx.save(); ctx.globalAlpha = 0.45; button(ctx, b, t(b.key), false); ctx.restore(); }
    else button(ctx, b, t(b.key), inR(m, b));
  }
  const s = menu.slot;
  const info = s ? t('ui.menu.slot_info', { level: s.hero.level, zone: game.zoneName ? game.zoneName(s.zone) : s.zone }) : t('ui.menu.slot_empty');
  drawText(ctx, VIEW_W / 2, 210, info, s ? PAL.birch : PAL.mist, { align: 'c', outline: true });
}
