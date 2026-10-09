// Вещи в сетке (24 px клетка): подложка цветом редкости, иконка атласа, стопка бересты, «не по уровню».
// m1i (critics_m1f П.11): один код для «Поклажи» в «Котомке» и для «Ладьи» — без текста на клетках.
import { PAL } from '../palette.js';
import { rect } from '../render/shapes.js';
import { drawText } from '../core/font.js';
import { drawIcon } from './assets.js';
import { RARITY } from '../data/items.js';

const CELL = 24;
function frame(ctx, x, y, w, h, c) { rect(ctx, x, y, w, 1, c); rect(ctx, x, y + h - 1, w, 1, c); rect(ctx, x, y, 1, h, c); rect(ctx, x + w - 1, y, 1, h, c); }

export function drawGridEntries(ctx, game, inv, gx, gy, hover = null) {
  const h = game.hero, hand = game.ui && game.ui.hand;
  for (const e of inv.entries) {
    const x = gx + e.c * CELL, y = gy + e.r * CELL, w = e.item.w * CELL, hh = e.item.h * CELL;
    const hov = hover === e && !hand;
    ctx.save();
    ctx.globalAlpha = hov ? 0.45 : 0.4;
    rect(ctx, x + 1, y + 1, w - 1, hh - 1, hov ? PAL.bronze : e.item.kind !== 'gear' ? PAL.wood : PAL[RARITY[e.item.rarity].tint]);
    ctx.restore();
    if (hov) frame(ctx, x, y, w + 1, hh + 1, PAL.bronze_lt);
    drawIcon(ctx, e.item.icon, x, y, w + 1, hh + 1);
    if (e.item.kind === 'scroll' && game.berestaGrey && game.berestaGrey()) { ctx.save(); ctx.globalAlpha = 0.6; rect(ctx, x + 1, y + 1, w - 1, hh - 1, PAL.slate_dk); ctx.restore(); }   // арена живого босса (GDD v1.9)
    if (e.item.kind === 'scroll' && e.item.count > 1) drawText(ctx, x + w - 2, y + hh - 9, String(e.item.count), PAL.linen, { align: 'r' });   // стопка бересты
    if (e.item.kind === 'gear' && e.item.req > h.level) { ctx.save(); ctx.globalAlpha = 0.25; rect(ctx, x + 1, y + 1, w - 1, hh - 1, PAL.red); ctx.restore(); }
  }
}
