// PNG-ассеты окон и иконок, выгруженные из исходников художника скриптом tools/export_ui.py.
import { UI_ATLAS } from '../data/ui_atlas.js';
import { loadRestFx } from '../render/rest_fx.js';
import { loadBossArt } from '../render/boss_art.js';

export const IMG = {};
const FILES = { items: 'assets/items.png', winInv: 'assets/win_inventory.png', winChar: 'assets/win_character.png', buttons: 'assets/hud_buttons.png', winSkills: 'assets/win_skills.png', quest: 'assets/hud_quest.png' };

export function loadAssets() {
  return Promise.all([loadRestFx(), loadBossArt(), ...Object.entries(FILES).map(([k, src]) => new Promise((res) => {
    const im = new Image();
    im.onload = () => res();
    im.onerror = () => { console.warn('Не загрузился ассет', src); res(); };
    im.src = src;
    IMG[k] = im;
  }))]);
}

/** Нарисовать иконку из атласа по центру прямоугольника (x,y,w,h). */
export function drawIcon(ctx, key, x, y, w, h, alpha = 1) {
  const r = UI_ATLAS.icons[key];
  if (!r || !IMG.items || !IMG.items.complete) return;
  const dx = Math.round(x + (w - r[2]) / 2), dy = Math.round(y + (h - r[3]) / 2);
  if (alpha < 1) { ctx.save(); ctx.globalAlpha = alpha; }
  ctx.drawImage(IMG.items, r[0], r[1], r[2], r[3], dx, dy, r[2], r[3]);
  if (alpha < 1) ctx.restore();
}
/** m1i: иконка, вписанная в прямоугольник (строки лавки): уменьшается с сохранением пропорций, не увеличивается. */
export function drawIconFit(ctx, key, x, y, w, h, opts = {}) {
  const r = UI_ATLAS.icons[key];
  if (!r || !IMG.items || !IMG.items.complete) return false;
  // m1i (PM п.4): вытянутые иконки (пояса 42×16) при вписывании по ширине выходят крошечными — с opts.crop вписываем по
  // высоте (масштаб 1:1, если влезает) и берём правый край (там у поясов пряжка/узел): пряжка видна той же высоты, что и прочие иконки строк
  if (opts.crop && r[2] / r[3] > 1.8) {
    const k = Math.min(1, h / r[3]), sw = Math.min(r[2], Math.floor(w / k)), dh = Math.max(1, Math.round(r[3] * k)), dw = Math.round(sw * k);
    ctx.drawImage(IMG.items, r[0] + r[2] - sw, r[1], sw, r[3], Math.round(x + (w - dw) / 2), Math.round(y + (h - dh) / 2), dw, dh);
    return true;
  }
  const k = Math.min(1, w / r[2], h / r[3]), dw = Math.max(1, Math.round(r[2] * k)), dh = Math.max(1, Math.round(r[3] * k));
  ctx.drawImage(IMG.items, r[0], r[1], r[2], r[3], Math.round(x + (w - dw) / 2), Math.round(y + (h - dh) / 2), dw, dh);
  return true;
}
/** Размер, который drawIconFit отдаёт иконке в рамке w×h (для автотеста). */
export function iconFitSize(key, w, h, opts = {}) {
  const r = UI_ATLAS.icons[key]; if (!r) return [0, 0];
  if (opts.crop && r[2] / r[3] > 1.8) { const k = Math.min(1, h / r[3]); return [Math.round(Math.min(r[2], Math.floor(w / k)) * k), Math.max(1, Math.round(r[3] * k))]; }
  const k = Math.min(1, w / r[2], h / r[3]); return [Math.max(1, Math.round(r[2] * k)), Math.max(1, Math.round(r[3] * k))];
}
export function iconSize(key) { const r = UI_ATLAS.icons[key]; return r ? [r[2], r[3]] : [0, 0]; }
export { UI_ATLAS };
