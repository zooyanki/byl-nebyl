// m1i (critics_m1f П.11–12): рамка и шапка окон «Ладья» и торга — те же, что у «Котомки». Нового арта нет: куски
// запечённого фона assets/win_inventory.png (углы, кромки, плашка заголовка, клетка сетки) режутся и тянутся кодом,
// название пишется шрифтом «устав» (как на плашке «КОТОМКА»).
import { PAL } from '../palette.js';
import { rect } from '../render/shapes.js';
import { drawText, textWidth } from '../core/font.js';
import { IMG } from './assets.js';

const SRC_W = 316, SRC_H = 287, B = 10;                 // размер фона «Котомки», толщина кромки
const PLATE = { l: [103, 0, 16, 19], r: [198, 0, 16, 19], m: [119, 0, 1, 19] };   // концы плашки и чистая полоса середины
const GRAIN = [10, 10, 44, 13];                         // волокна дерева внутри рамки
const CELL_SRC = [38, 160, 24, 24];                     // одна клетка сетки «Поклажи»

const ready = () => IMG.winInv && IMG.winInv.complete && IMG.winInv.naturalWidth > 0;
function tile(ctx, s, x, y, w, h) {   // кусок s = [sx, sy, sw, sh] замостить в (x, y, w, h)
  for (let yy = 0; yy < h; yy += s[3]) for (let xx = 0; xx < w; xx += s[2]) {
    const cw = Math.min(s[2], w - xx), ch = Math.min(s[3], h - yy);
    ctx.drawImage(IMG.winInv, s[0], s[1], cw, ch, x + xx, y + yy, cw, ch);
  }
}

/** Рамка окна как у «Котомки»; title — на плашке посередине верхней кромки (может быть пустым). */
export function drawBagFrame(ctx, x, y, w, h, title = '') {
  if (!ready()) { rect(ctx, x, y, w, h, PAL.ink); rect(ctx, x + 1, y + 1, w - 2, h - 2, PAL.wood_dk); }
  else {
    rect(ctx, x + 2, y + 2, w - 4, h - 4, PAL.ink);
    for (let k = 0; k < 3; k++) {                       // волокна — в тех же местах, что на «Котомке»
      const gx = x + 8 + Math.round(((k * 97) % (w - 70))), gy = y + 12 + Math.round(((k * 61) % Math.max(1, h - 40)));
      ctx.drawImage(IMG.winInv, GRAIN[0], GRAIN[1], GRAIN[2], GRAIN[3], gx, gy, GRAIN[2], GRAIN[3]);
    }
    tile(ctx, [B + 2, 0, 48, B], x + B, y, w - 2 * B, B);
    tile(ctx, [B + 2, SRC_H - B, 48, B], x + B, y + h - B, w - 2 * B, B);
    tile(ctx, [0, B + 2, B, 48], x, y + B, B, h - 2 * B);
    tile(ctx, [SRC_W - B, 40, B, 48], x + w - B, y + B, B, h - 2 * B);
    ctx.drawImage(IMG.winInv, 0, 0, B, B, x, y, B, B);
    ctx.drawImage(IMG.winInv, SRC_W - B, 0, B, B, x + w - B, y, B, B);
    ctx.drawImage(IMG.winInv, 0, SRC_H - B, B, B, x, y + h - B, B, B);
    ctx.drawImage(IMG.winInv, SRC_W - B, SRC_H - B, B, B, x + w - B, y + h - B, B, B);
  }
  if (title) drawPlate(ctx, x + w / 2, y, title);
}

/** Плашка заголовка (как «КОТОМКА»): концы с фона, середина тянется, текст — уставом. Возвращает прямоугольник. */
export function drawPlate(ctx, cx, y, title) {
  const s = String(title).toUpperCase(), tw = textWidth(s, 'ustav');
  const mw = tw + 10, w = mw + PLATE.l[2] + PLATE.r[2], x = Math.round(cx - w / 2);
  if (ready()) {
    ctx.drawImage(IMG.winInv, ...PLATE.l, x, y, PLATE.l[2], PLATE.l[3]);
    ctx.drawImage(IMG.winInv, ...PLATE.m, x + PLATE.l[2], y, mw, PLATE.m[3]);
    ctx.drawImage(IMG.winInv, ...PLATE.r, x + PLATE.l[2] + mw, y, PLATE.r[2], PLATE.r[3]);
  } else rect(ctx, x, y, w, 19, PAL.wood_md);
  drawText(ctx, Math.round(cx), y + 5, s, PAL.bronze_hi, { align: 'c', font: 'ustav' });
  return { x, y, w, h: 19 };
}

/** Сетка cols×rows клеток по 24 px — та же клетка, что в «Поклаже» «Котомки». */
export function drawGrid(ctx, gx, gy, cols, rows) {
  rect(ctx, gx - 2, gy - 2, cols * 24 + 3, rows * 24 + 3, PAL.bronze_dk);
  rect(ctx, gx - 1, gy - 1, cols * 24 + 1, rows * 24 + 1, PAL.ink);
  if (!ready()) { for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) rect(ctx, gx + c * 24 + 1, gy + r * 24 + 1, 22, 22, PAL.night); return; }
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) ctx.drawImage(IMG.winInv, ...CELL_SRC, gx + c * 24, gy + r * 24, 24, 24);
}

/** Иконка атласа, вписанная в квадрат (для строк лавки): уменьшается с сохранением пропорций, не увеличивается. */
export function fitScale(iw, ih, w, h) { return Math.min(1, w / Math.max(1, iw), h / Math.max(1, ih)); }
