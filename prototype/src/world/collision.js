// Столкновения на полутайловой сетке проходимости (design/scale.md §1: сабтайл 16×8 = ½ тайла по каждой оси).
// Круги персонажей против заблокированных сабтайлов, персонажи друг против друга, прямая видимость.
import { clamp } from '../core/math.js';

export const SUB = 2;          // сабтайлов на тайл по каждой оси
const CS = 1 / SUB;            // размер сабтайла в тайлах (0,5)

let ACTORS = [];
/** Список тел, которые блокируют друг друга (живые герой и нечисть). Обновляется игрой каждый кадр. */
export function setActors(list) { ACTORS = list; }
export function getActors() { return ACTORS; }

export function circleFree(map, x, y, r) {
  const s0x = Math.floor((x - r) * SUB), s1x = Math.floor((x + r) * SUB);
  const s0y = Math.floor((y - r) * SUB), s1y = Math.floor((y + r) * SUB);
  for (let sy = s0y; sy <= s1y; sy++) {
    for (let sx = s0x; sx <= s1x; sx++) {
      if (!map.subBlocked(sx, sy)) continue;
      const cx = clamp(x, sx * CS, (sx + 1) * CS), cy = clamp(y, sy * CS, (sy + 1) * CS);
      if ((x - cx) ** 2 + (y - cy) ** 2 < r * r) return false;
    }
  }
  return true;
}

// Мешает ли другое тело встать в (nx,ny)? Разрешаем движение, которое увеличивает расстояние
// (чтобы слипшиеся тела могли разойтись и никто не застревал навсегда).
export function actorBlocked(e, nx, ny) {
  for (const o of ACTORS) {
    if (o === e || o.dead) continue;
    const min = e.r + o.r - 0.02;
    const dxn = nx - o.x, dyn = ny - o.y;
    const dn2 = dxn * dxn + dyn * dyn;
    if (dn2 >= min * min) continue;
    const dxo = e.x - o.x, dyo = e.y - o.y;
    if (dn2 < dxo * dxo + dyo * dyo - 1e-9) return o;
  }
  return null;
}

/** Перемещение со «скольжением» вдоль стен и тел. Возвращает пройденное расстояние. */
export function moveWithCollision(map, e, dx, dy, bodies = true) {
  const len = Math.hypot(dx, dy);
  if (len < 1e-6) return 0;
  const steps = Math.max(1, Math.ceil(len / 0.1));
  const sx = dx / steps, sy = dy / steps;
  const ox = e.x, oy = e.y;
  e.bumped = null;
  for (let i = 0; i < steps; i++) {
    let nx = e.x + sx;
    if (circleFree(map, nx, e.y, e.r)) {
      const b = bodies ? actorBlocked(e, nx, e.y) : null;
      if (!b) e.x = nx; else e.bumped = b;
    }
    const ny = e.y + sy;
    if (circleFree(map, e.x, ny, e.r)) {
      const b = bodies ? actorBlocked(e, e.x, ny) : null;
      if (!b) e.y = ny; else e.bumped = b;
    }
  }
  return Math.hypot(e.x - ox, e.y - oy);
}

/** Проходим ли отрезок для круга радиуса r (стены) и, если задано, не задевает ли он тела avoid. */
export function lineWalkable(map, x0, y0, x1, y1, r, avoid = null) {
  const d = Math.hypot(x1 - x0, y1 - y0);
  const n = Math.max(1, Math.ceil(d / 0.12));
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    if (!circleFree(map, x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, r)) return false;
  }
  if (avoid) for (const o of avoid) if (segDist(o.x, o.y, x0, y0, x1, y1) < r + o.r - 0.02) return false;
  return true;
}

export function segDist(px, py, x0, y0, x1, y1) {
  const vx = x1 - x0, vy = y1 - y0, l2 = vx * vx + vy * vy;
  const t = l2 > 0 ? clamp(((px - x0) * vx + (py - y0) * vy) / l2, 0, 1) : 0;
  return Math.hypot(px - (x0 + vx * t), py - (y0 + vy * t));
}

/** Прямая видимость: только «высокие» препятствия (стены, частокол, избы, деревья, валуны). Вода и крада не мешают. */
export function sightClear(map, x0, y0, x1, y1) {
  const d = Math.hypot(x1 - x0, y1 - y0);
  const n = Math.max(1, Math.ceil(d / 0.1));
  for (let i = 1; i < n; i++) {
    const t = i / n;
    if (map.opaqueAt(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)) return false;
  }
  return true;
}
