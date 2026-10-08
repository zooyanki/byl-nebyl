// Локация «Окрестности Залесья»: земля по тайлам, проходимость и видимость по полутайловой сетке
// (design/scale.md §1, §4.2), препятствия (пропсы) с футпринтом, кратным ½ тайла, точки спавна.
import { MAP_W, MAP_H } from '../config.js';
import { makeRng, hash2 } from '../core/rng.js';
import { SUB, circleFree } from './collision.js';

export const T_GRASS = 0, T_DIRT = 1, T_WATER = 2;
// Что закрывает обзор и останавливает снаряды (вода и крада — нет).
const OPAQUE = new Set(['tree', 'rock', 'wall', 'palisade', 'izba', 'idol']);

export class GameMap {
  constructor(w, h) {
    this.w = w; this.h = h;
    this.sw = w * SUB; this.sh = h * SUB;
    this.ground = new Uint8Array(w * h);
    this.sub = new Uint8Array(this.sw * this.sh);      // 1 — сабтайл непроходим
    this.opaque = new Uint8Array(this.sw * this.sh);   // 1 — сабтайл закрывает обзор
    this.water = new Uint8Array(this.sw * this.sh);
    this.props = [];
    this.packs = [];
    this.lights = [];
    this.start = { x: 0.5, y: 0.5 };
    this.passCache = new Map();
    this.reach = null;
  }
  inside(tx, ty) { return tx >= 0 && ty >= 0 && tx < this.w && ty < this.h; }
  subBlocked(sx, sy) { return sx < 0 || sy < 0 || sx >= this.sw || sy >= this.sh || this.sub[sy * this.sw + sx] === 1; }
  blockedAt(x, y) { return this.subBlocked(Math.floor(x * SUB), Math.floor(y * SUB)); }
  opaqueAt(x, y) {
    const sx = Math.floor(x * SUB), sy = Math.floor(y * SUB);
    return sx < 0 || sy < 0 || sx >= this.sw || sy >= this.sh || this.opaque[sy * this.sw + sx] === 1;
  }
  waterSub(sx, sy) { return sx >= 0 && sy >= 0 && sx < this.sw && sy < this.sh && this.water[sy * this.sw + sx] === 1; }
  // тайл заблокирован, если заблокирован хоть один его сабтайл
  isBlocked(tx, ty) {
    if (!this.inside(tx, ty)) return true;
    for (let j = 0; j < SUB; j++) for (let i = 0; i < SUB; i++) if (this.sub[(ty * SUB + j) * this.sw + tx * SUB + i]) return true;
    return false;
  }
  groundAt(tx, ty) { return this.inside(tx, ty) ? this.ground[ty * this.w + tx] : T_GRASS; }
  areaFree(tx, ty, s = 1, margin = 0) {
    for (let y = ty - margin; y < ty + s + margin; y++)
      for (let x = tx - margin; x < tx + s + margin; x++)
        if (this.isBlocked(x, y)) return false;
    return true;
  }
  rectFree(x, y, w, h) {
    for (let sy = Math.floor(y * SUB); sy < Math.ceil((y + h) * SUB); sy++)
      for (let sx = Math.floor(x * SUB); sx < Math.ceil((x + w) * SUB); sx++)
        if (this.subBlocked(sx, sy)) return false;
    return true;
  }
  markRect(x, y, w, h, opaque) {
    for (let sy = Math.floor(y * SUB); sy < Math.ceil((y + h) * SUB - 1e-6); sy++)
      for (let sx = Math.floor(x * SUB); sx < Math.ceil((x + w) * SUB - 1e-6); sx++) {
        if (sx < 0 || sy < 0 || sx >= this.sw || sy >= this.sh) continue;
        this.sub[sy * this.sw + sx] = 1;
        if (opaque) this.opaque[sy * this.sw + sx] = 1;
      }
  }
  /** Пропс: (x,y,size) — квадрат для отрисовки; fp = [x,y,w,h] — футпринт проходимости (кратен ½ тайла). */
  addProp(type, x, y, size = 1, extra = {}) {
    const fp = extra.fp || [x, y, size, size];
    this.markRect(fp[0], fp[1], fp[2], fp[3], OPAQUE.has(type));
    const p = { type, x, y, size, seed: hash2(Math.round(x * 2), Math.round(y * 2), 7), ...extra, fp };
    p.depth = fp[0] + fp[2] / 2 + fp[1] + fp[3] / 2;   // сортировка по центру футпринта
    this.props.push(p);
    return p;
  }

  // Узлы поиска пути — решётка с шагом ½ тайла (scale.md: «шаг пути A* — 0,5 тайла»), включая центры тайлов.
  get nw() { return this.sw + 1; }
  /** Сетка узлов, где помещается круг радиуса r (кэш по r). */
  passGrid(r) {
    const key = Math.round(r * 100);
    let g = this.passCache.get(key);
    if (g) return g;
    const NW = this.sw + 1, NH = this.sh + 1;
    g = new Uint8Array(NW * NH);
    for (let j = 0; j < NH; j++) for (let i = 0; i < NW; i++) g[j * NW + i] = circleFree(this, i / SUB, j / SUB, r) ? 1 : 0;
    this.passCache.set(key, g);
    return g;
  }
  computeReach() {
    const g = this.passGrid(0.3), NW = this.sw + 1, NH = this.sh + 1;
    const r = new Uint8Array(NW * NH);
    const s = Math.round(this.start.y * SUB) * NW + Math.round(this.start.x * SUB);
    const q = [s]; r[s] = 1;
    while (q.length) {
      const i = q.pop(), x = i % NW, y = (i / NW) | 0;
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        const nx = x + dx, ny = y + dy;
        if (nx < 0 || ny < 0 || nx >= NW || ny >= NH) continue;
        const ni = ny * NW + nx;
        if (g[ni] && !r[ni]) { r[ni] = 1; q.push(ni); }
      }
    }
    this.reach = r;
  }
  isReachableAt(x, y) {
    const i = Math.round(x * SUB), j = Math.round(y * SUB), NW = this.sw + 1;
    return i >= 0 && j >= 0 && i < NW && j <= this.sh && this.reach && this.reach[j * NW + i] === 1;
  }
}

export function generateMap(seed) {
  const m = new GameMap(MAP_W, MAP_H);
  const rng = makeRng(seed);
  const W = m.w, H = m.h;
  const S = { x: 24, y: 26 };
  m.start = { x: S.x + 0.5, y: S.y + 0.5 };
  const d = (ax, ay, bx, by) => Math.hypot(ax - bx, ay - by);

  // --- вода (Волхов) в левом углу — с точностью до сабтайла, чтобы берег шёл «ступеньками» по ½ тайла
  const isWater = (x, y) => y - x > 27 + Math.sin(x * 0.45) * 1.6 + Math.sin(y * 0.3) * 1.2;
  for (let sy = 0; sy < m.sh; sy++) {
    for (let sx = 0; sx < m.sw; sx++) {
      const x = (sx + 0.5) / SUB - 0.5, y = (sy + 0.5) / SUB - 0.5;
      if (isWater(x, y)) { m.water[sy * m.sw + sx] = 1; m.sub[sy * m.sw + sx] = 1; }
    }
  }
  // --- земля: трава, утоптанная земля у кострища, тропы
  const setG = (x, y, t) => { if (m.inside(x, y)) m.ground[y * W + x] = t; };
  const allWater = (x, y) => { let n = 0; for (let j = 0; j < SUB; j++) for (let i = 0; i < SUB; i++) n += m.waterSub(x * SUB + i, y * SUB + j) ? 1 : 0; return n === SUB * SUB; };
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      if (allWater(x, y)) { setG(x, y, T_WATER); continue; }
      if (d(x, y, S.x - 1, S.y - 2) < 4.2 + hash2(x, y, 3) * 1.8) setG(x, y, T_DIRT);
    }
  }
  const trail = (ax, ay, bx, by) => {
    const n = Math.ceil(d(ax, ay, bx, by) * 2);
    for (let i = 0; i <= n; i++) {
      const t = i / n;
      const x = ax + (bx - ax) * t + Math.sin(t * 9) * 0.8, y = ay + (by - ay) * t;
      for (const [ox, oy] of [[0, 0], [1, 0], [0, 1]]) {
        const tx = Math.floor(x) + ox, ty = Math.floor(y) + oy;
        if (m.groundAt(tx, ty) !== T_WATER) setG(tx, ty, T_DIRT);
      }
    }
  };
  trail(S.x, S.y, 38, 7);     // к воротам частокола
  trail(S.x, S.y, 17, 35);    // к развалинам
  trail(S.x, S.y, 14, 17);    // к избе

  // --- спланированные объекты
  const fire = m.addProp('fire', S.x - 4, S.y - 4, 2);      // крада 2×2 (scale.md §3.3)
  m.krada = { x: fire.x + 1, y: fire.y + 1 };
  m.lights.push({ x: S.x - 3, y: S.y - 3, r: 110, kind: 'fire' });
  m.addProp('idol', S.x + 3, S.y - 4, 1);                   // чур
  m.addProp('izba', 11, 12, 4);                             // малая изба 4×4
  m.addProp('izba', 31, 1, 4);
  for (let x = 28; x <= 45; x++) {                           // частокол с воротами (проём 2 тайла), толщина 1 тайл
    if (x === 38 || x === 39) continue;
    m.addProp('palisade', x, 7, 1, { gatepost: x === 37 ? 'left' : x === 40 ? 'right' : false });
  }
  for (let y = 2; y <= 6; y++) m.addProp('palisade', 28, y, 1, { axis: 'y' });
  // каменные развалины: тонкая (½ тайла) Г-образная стена с проломом — обход и проверка полутайловой коллизии
  for (let x = 13; x <= 21; x++) {
    if (x === 16) continue;
    m.addProp('wall', x, 32, 1, { fp: x === 21 ? [21, 32, 0.5, 1] : [x, 32, 1, 0.5] });
  }
  for (let y = 33; y <= 39; y++) if (y !== 37) m.addProp('wall', 21, y, 1, { fp: [21, y, 0.5, 1] });
  // отдельная тонкая стена посреди поля (x 30,0–30,5), чтобы было что обходить рядом со стартом
  for (let y = 22; y <= 27; y++) m.addProp('wall', 30, y, 1, { fp: [30, y, 0.5, 1] });

  // --- стаи нечисти (центры) и уровень монстров (mlvl): ближе к краде слабее (GDD §8.2: М1 начинается с mlvl 1–3)
  m.packs = [
    { x: 32.5, y: 29.5, kinds: ['anchutka', 'anchutka', 'anchutka', 'anchutka'], mlvl: 1 },
    { x: 17.5, y: 29.5, kinds: ['upyr', 'upyr'], mlvl: 2 },
    { x: 17.5, y: 36.5, kinds: ['upyr', 'upyr', 'upyr'], mlvl: 2 },
    { x: 40.5, y: 4.5, kinds: ['upyr', 'upyr', 'anchutka', 'anchutka', 'anchutka'], mlvl: 3 },
    { x: 9.5, y: 19.5, kinds: ['anchutka', 'anchutka', 'anchutka', 'anchutka', 'anchutka'], mlvl: 2 },
    { x: 37.5, y: 17.5, kinds: ['upyr', 'upyr', 'upyr'], mlvl: 3 },
    { x: 29.5, y: 40.5, kinds: ['upyr', 'upyr', 'anchutka', 'anchutka'], mlvl: 3 },
    { x: 41.5, y: 33.5, kinds: ['anchutka', 'anchutka', 'anchutka', 'anchutka'], mlvl: 2 },
  ];
  const nearPack = (x, y, r) => m.packs.some((p) => d(x + 0.5, y + 0.5, p.x, p.y) < r);

  // --- лесная кромка по периметру: сплошная чаща (весь тайл непроходим)
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      if (m.isBlocked(x, y)) continue;
      const e = Math.min(x, y, W - 1 - x, H - 1 - y);
      const p = e < 2 ? 1 : e === 2 ? 0.55 : e === 3 ? 0.18 : 0;
      if (p && rng() < p) m.addProp('tree', x, y, 1, { birch: rng() < 0.2 });
    }
  }
  // --- валуны и отдельные деревья внутри стоят на полутайловой сетке; у дерева непроходим только ствол (½×½ тайла)
  const scatter = (count, size, add) => {
    let placed = 0, tries = 0;
    while (placed < count && tries++ < count * 60) {
      const x = rng.int(8, W * SUB - 10) / SUB, y = rng.int(8, H * SUB - 10) / SUB;
      if (d(x, y, S.x, S.y) < 5.5 || nearPack(x, y, 3) || !m.rectFree(x - 1, y - 1, size + 2, size + 2)) continue;
      if (m.groundAt(Math.floor(x), Math.floor(y)) === T_DIRT && rng() < 0.7) continue;
      add(x, y); placed++;
    }
  };
  scatter(12, 1, (x, y) => m.addProp('rock', x, y, 1));
  scatter(5, 2, (x, y) => m.addProp('rock', x, y, 2));
  // ствол — сабтайл (x, y); рисуем дерево с центром в центре этого сабтайла
  scatter(16, 0.5, (x, y) => m.addProp('tree', x - 0.25, y - 0.25, 1, { birch: rng() < 0.6, fp: [x, y, 0.5, 0.5] }));

  m.computeReach();
  return m;
}
