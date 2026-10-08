// Растровые шрифты FONT_RU и FONT_USTAV (из art/ui/src/fonts_ru.py), рисуются в нативном разрешении.
import { FONT_RU, FONT_USTAV } from '../data/font_ru.js';
import { PAL } from '../palette.js';

class BitmapFont {
  constructor(def) {
    this.G = def.glyphs; this.H = def.h; this.SP = def.sp; this.top = def.top || 0;
    this.index = {};
    let w = 0;
    for (const k of Object.keys(this.G)) { const gw = this.G[k][0].length; this.index[k] = { x: w, w: gw }; w += gw + 1; }
    this.atlasW = w;
    this.base = document.createElement('canvas');
    this.base.width = w; this.base.height = this.H;
    const b = this.base.getContext('2d');
    b.fillStyle = '#fff';
    for (const k of Object.keys(this.G)) {
      const gx = this.index[k].x;
      this.G[k].forEach((row, ry) => { for (let rx = 0; rx < row.length; rx++) if (row[rx] === '#') b.fillRect(gx + rx, ry, 1, 1); });
    }
    this.tinted = new Map();
  }
  atlas(color) {
    let c = this.tinted.get(color);
    if (!c) {
      c = document.createElement('canvas');
      c.width = this.atlasW; c.height = this.H;
      const t = c.getContext('2d');
      t.drawImage(this.base, 0, 0);
      t.globalCompositeOperation = 'source-in';
      t.fillStyle = color; t.fillRect(0, 0, this.atlasW, this.H);
      this.tinted.set(color, c);
    }
    return c;
  }
  key(ch) {
    if (this.G[ch]) return ch;
    const u = ch.toUpperCase();
    if (this.G[u]) return u;
    if (ch === '\u2212' && this.G['-']) return '-';
    return null;
  }
  width(s) {
    let w = 0, n = 0;
    for (const ch of String(s)) { const k = this.key(ch); if (!k) { if (ch === ' ') { w += 3 + this.SP; n++; } continue; } w += this.index[k].w + this.SP; n++; }
    return n ? w - this.SP : 0;
  }
  raw(ctx, x, y, s, color) {
    const a = this.atlas(color);
    let cx = x;
    for (const ch of s) {
      const k = this.key(ch);
      if (!k) { if (ch === ' ') cx += 3 + this.SP; continue; }
      const g = this.index[k];
      ctx.drawImage(a, g.x, 0, g.w, this.H, cx, y, g.w, this.H);
      cx += g.w + this.SP;
    }
  }
}

const FONTS = { ru: new BitmapFont(FONT_RU), ustav: new BitmapFont(FONT_USTAV) };
export const LINE_H = FONTS.ru.H;

export function textWidth(s, font = 'ru') { return FONTS[font].width(s); }

const OUTLINE = [[-1, 0], [1, 0], [0, -1], [0, 1], [-1, -1], [1, -1], [-1, 1], [1, 1]];

// Кэш готовых надписей (с обводкой/тенью): текст в HUD почти не меняется от кадра к кадру.
const cache = new Map();
const CACHE_MAX = 900;
function rendered(s, color, outline, shadow, edge, font) {
  const k = font + '\u0002' + s + '\u0001' + color + (outline ? 'o' : shadow ? 's' : 'n') + edge;
  let c = cache.get(k);
  if (c) return c;
  const F = FONTS[font];
  const w = F.width(s);
  c = document.createElement('canvas');
  c.width = Math.max(1, w + 3); c.height = F.H + 3;
  const t = c.getContext('2d');
  if (outline) for (const [ox, oy] of OUTLINE) F.raw(t, 1 + ox, 1 + oy, s, edge);
  else if (shadow) F.raw(t, 2, 2, s, edge);
  F.raw(t, 1, 1, s, color);
  if (cache.size >= CACHE_MAX) cache.clear();
  cache.set(k, c);
  return c;
}

/**
 * drawText(ctx, x, y, text, color, {align:'l'|'c'|'r', outline, shadow, scale, alpha, font:'ru'|'ustav'})
 * Возвращает ширину строки в нативных пикселях (без учёта scale).
 */
export function drawText(ctx, x, y, s, color, opts = {}) {
  s = String(s);
  const { align = 'l', outline = false, shadow = true, edge = PAL.ink, scale = 1, alpha = 1, font = 'ru' } = opts;
  const w = FONTS[font].width(s);
  const dx = align === 'c' ? -w / 2 : align === 'r' ? -w : 0;
  const img = rendered(s, color, outline, shadow, edge, font);
  const px = Math.round(x + dx * scale) - scale, py = Math.round(y) - scale;
  if (alpha < 1) { ctx.save(); ctx.globalAlpha *= alpha; }
  if (scale === 1) ctx.drawImage(img, px, py);
  else ctx.drawImage(img, px, py, img.width * scale, img.height * scale);
  if (alpha < 1) ctx.restore();
  return w;
}
