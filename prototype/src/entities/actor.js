// Базовый класс для всех ходячих: позиция, радиус, движение по пути, отбрасывание, направление взгляда.
import { moveWithCollision, getActors } from '../world/collision.js';
import { findPath } from '../world/pathfind.js';

export class Actor {
  constructor(x, y, r) {
    this.x = x; this.y = y; this.r = r;
    this.path = null;
    this.facing = 1;          // знак экранного X: 1 — смотрит вправо, -1 — влево
    this.dir = 0;             // 8 направлений на экране: 0 — вниз (к камере), 1 — вниз-влево, 2 — влево, 3 — вверх-влево, 4 — вверх, 5 — вверх-вправо, 6 — вправо, 7 — вниз-вправо
    this.moving = false;
    this.walkPhase = 0;
    this.flash = 0;           // вспышка при получении урона
    this.dead = false;
    this.kb = null;           // отбрасывание {vx, vy, t}
    this._stuck = 0;
  }

  /** Путь к точке. avoid=true — обходить другие тела (кроме except). */
  setPath(map, tx, ty, avoid = false, except = null) {
    const list = avoid ? getActors().filter((o) => o !== this && o !== except && !o.dead && Math.hypot(o.x - this.x, o.y - this.y) < 9) : null;
    this.path = findPath(map, this.x, this.y, tx, ty, this.r, { avoid: list });
    this._stuck = 0;
    return !!this.path;
  }

  face(dx, dy) {
    const sx = dx - dy; // экранный X ~ (x - y)
    if (Math.abs(sx) > 0.02) this.facing = sx > 0 ? 1 : -1;
    if (Math.abs(dx) + Math.abs(dy) > 1e-3) this.dir = dirOf(dx, dy);
  }
  /** Единичный мировой вектор текущего направления взгляда. */
  dirVec() { return dirVector(this.dir); }

  knock(dx, dy, dist, dur = 0.14) {
    const d = Math.hypot(dx, dy) || 1;
    this.kb = { vx: (dx / d) * dist / dur, vy: (dy / d) * dist / dur, t: dur };
  }
  // true, пока идёт отбрасывание (в это время ИИ/команды не двигают тело)
  updateKnock(map, dt) {
    if (!this.kb) return false;
    const k = this.kb, s = Math.min(dt, k.t);
    moveWithCollision(map, this, k.vx * s, k.vy * s);
    k.t -= dt;
    if (k.t <= 0) this.kb = null;
    return true;
  }

  // Шаг вдоль пути. true — путь закончен (или застряли).
  followPath(map, dt, speed) {
    if (!this.path || !this.path.length) { this.moving = false; this.path = null; return true; }
    const [px, py] = this.path[0];
    const dx = px - this.x, dy = py - this.y;
    const d = Math.hypot(dx, dy);
    const step = speed * dt;
    let moved;
    if (d <= step) {
      moved = moveWithCollision(map, this, dx, dy);
      if (Math.hypot(px - this.x, py - this.y) < 0.05) this.path.shift();
    } else {
      moved = moveWithCollision(map, this, (dx / d) * step, (dy / d) * step);
    }
    this.face(dx, dy);
    this.moving = true;
    this.walkPhase += moved * 4;
    if (moved < step * 0.25) {
      this._stuck += dt;
      if (this._stuck > 0.25) { this.path = null; this.moving = false; return true; }
    } else this._stuck = 0;
    if (!this.path.length) { this.path = null; this.moving = false; return true; }
    return false;
  }

  // Прямое движение к точке (без поиска пути). Возвращает пройденное.
  stepToward(map, tx, ty, speed, dt) {
    const dx = tx - this.x, dy = ty - this.y, d = Math.hypot(dx, dy);
    if (d < 1e-4) return 0;
    const s = Math.min(d, speed * dt);
    const moved = moveWithCollision(map, this, (dx / d) * s, (dy / d) * s);
    this.face(dx, dy);
    this.moving = moved > 1e-4;
    this.walkPhase += moved * 4;
    return moved;
  }

  distTo(o) { return Math.hypot(o.x - this.x, o.y - this.y); }
  gapTo(o) { return this.distTo(o) - this.r - o.r; }
}

/** Направление 0–7 по мировому вектору: угол на экране (изометрия 2:1), 0 — вниз, по часовой стрелке через «влево». */
export function dirOf(dx, dy) {
  const sx = (dx - dy) * 16, sy = (dx + dy) * 8;
  const a = Math.atan2(sy, sx);
  return ((Math.round((a - Math.PI / 2) / (Math.PI / 4)) % 8) + 8) % 8;
}
export function dirVector(dir) {
  const a = Math.PI / 2 + dir * Math.PI / 4;
  const sx = Math.cos(a), sy = Math.sin(a);
  const dx = (sx / 16 + sy / 8) / 2, dy = (sy / 8 - sx / 16) / 2, d = Math.hypot(dx, dy);
  return [dx / d, dy / d];
}
/** Экранный единичный вектор направления (для отрисовки). */
export function dirScreen(dir) { const a = Math.PI / 2 + dir * Math.PI / 4; return [Math.cos(a), Math.sin(a)]; }
