// PNG-ассеты окон и иконок, выгруженные из исходников художника скриптом tools/export_ui.py.
import { UI_ATLAS } from '../data/ui_atlas.js';
import { loadRestFx } from '../render/rest_fx.js';

export const IMG = {};
const FILES = { items: 'assets/items.png', winInv: 'assets/win_inventory.png', winChar: 'assets/win_character.png', buttons: 'assets/hud_buttons.png', winSkills: 'assets/win_skills.png', quest: 'assets/hud_quest.png' };

export function loadAssets() {
  return Promise.all([loadRestFx(), ...Object.entries(FILES).map(([k, src]) => new Promise((res) => {
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
export function iconSize(key) { const r = UI_ATLAS.icons[key]; return r ? [r[2], r[3]] : [0, 0]; }
export { UI_ATLAS };
