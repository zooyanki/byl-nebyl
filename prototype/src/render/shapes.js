// Примитивы грей-бокса: пиксельные прямоугольники, ромбы, изо-коробки, эллипсы, фигуры с обводкой.
import { PAL } from '../palette.js';
import { HALF_W, HALF_H } from '../config.js';

export function rect(ctx, x, y, w, h, c) {
  ctx.fillStyle = c;
  ctx.fillRect(Math.round(x), Math.round(y), Math.round(w), Math.round(h));
}

export function poly(ctx, pts, c) {
  ctx.fillStyle = c;
  ctx.beginPath();
  ctx.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
  ctx.closePath();
  ctx.fill();
}

export function strokePoly(ctx, pts, c, close = true) {
  ctx.strokeStyle = c;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(pts[0][0] + 0.5, pts[0][1] + 0.5);
  for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0] + 0.5, pts[i][1] + 0.5);
  if (close) ctx.closePath();
  ctx.stroke();
}

export function ellipse(ctx, cx, cy, rx, ry, c, alpha = 1) {
  ctx.save();
  ctx.globalAlpha *= alpha;
  ctx.fillStyle = c;
  ctx.beginPath();
  ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

export function ellipseStroke(ctx, cx, cy, rx, ry, c, alpha = 1, lw = 1) {
  ctx.save();
  ctx.globalAlpha *= alpha;
  ctx.strokeStyle = c;
  ctx.lineWidth = lw;
  ctx.beginPath();
  ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();
}

export function disc(ctx, cx, cy, r, c) {
  ctx.fillStyle = c;
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.fill();
}

// Пиксельный ромб тайла 32x16, (x,y) — левый верхний угол описанного прямоугольника.
export function diamond(ctx, x, y, c) {
  ctx.fillStyle = c;
  for (let r = 0; r < 16; r++) {
    const half = r < 8 ? 2 * (r + 1) : 2 * (16 - r);
    ctx.fillRect(x + 16 - half, y + r, half * 2, 1);
  }
}

/**
 * Изо-коробка. (ox,oy) — экранная точка верхнего (дальнего) угла основания.
 * sx, sy — размер основания в тайлах по осям X и Y; h — высота в пикселях.
 */
export function isoBox(ctx, ox, oy, sx, sy, h, cTop, cLeft, cRight, edge = PAL.ink) {
  const T = [ox, oy];
  const R = [ox + sx * HALF_W, oy + sx * HALF_H];
  const B = [ox + (sx - sy) * HALF_W, oy + (sx + sy) * HALF_H];
  const L = [ox - sy * HALF_W, oy + sy * HALF_H];
  const up = (p) => [p[0], p[1] - h];
  poly(ctx, [L, B, up(B), up(L)], cLeft);
  poly(ctx, [B, R, up(R), up(B)], cRight);
  poly(ctx, [up(T), up(R), up(B), up(L)], cTop);
  if (edge) strokePoly(ctx, [up(T), up(R), R, B, L, up(L)], edge);
  return { T, R, B, L, up };
}

/**
 * Фигура из частей с общей обводкой: parts = [{x,y,w,h,c}] | [{cx,cy,r,c}].
 * flash — залить всё светлым (попадание).
 */
export function figure(ctx, parts, flash = false, outline = PAL.ink) {
  ctx.fillStyle = outline;
  for (const p of parts) {
    if (p.noOutline) continue;
    if (p.r !== undefined) { ctx.beginPath(); ctx.arc(p.cx, p.cy, p.r + 1, 0, Math.PI * 2); ctx.fill(); }
    else ctx.fillRect(Math.round(p.x) - 1, Math.round(p.y) - 1, Math.round(p.w) + 2, Math.round(p.h) + 2);
  }
  const fill = (color) => {
    for (const p of parts) {
      ctx.fillStyle = color || p.c;
      if (p.r !== undefined) { ctx.beginPath(); ctx.arc(p.cx, p.cy, p.r, 0, Math.PI * 2); ctx.fill(); }
      else ctx.fillRect(Math.round(p.x), Math.round(p.y), Math.round(p.w), Math.round(p.h));
    }
  };
  fill(null);
  if (flash) { ctx.save(); ctx.globalAlpha *= 0.55; fill(PAL.linen); ctx.restore(); }
}

// Пиксельная линия (Брезенхем) — для клинков и посохов.
export function pline(ctx, x0, y0, x1, y1, c) {
  x0 = Math.round(x0); y0 = Math.round(y0); x1 = Math.round(x1); y1 = Math.round(y1);
  const dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0);
  const sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
  let err = dx + dy;
  ctx.fillStyle = c;
  for (let i = 0; i < 200; i++) {
    ctx.fillRect(x0, y0, 1, 1);
    if (x0 === x1 && y0 === y1) break;
    const e2 = 2 * err;
    if (e2 >= dy) { err += dy; x0 += sx; }
    if (e2 <= dx) { err += dx; y0 += sy; }
  }
}
