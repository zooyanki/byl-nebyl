// Локация «Окрестности Залесья»: земля по тайлам, проходимость и видимость по полутайловой сетке
// (design/scale.md §1, §4.2), препятствия (пропсы) с футпринтом, кратным ½ тайла, точки спавна.
import { MAP_W, MAP_H, HALF_W, HALF_H } from '../config.js';
import { makeRng, hash2 } from '../core/rng.js';
import { SUB, circleFree } from './collision.js';
import { generateTrail } from './trail.js';
import { generateKapishche } from './kapishche.js';
import { generateLadoga } from './ladoga.js';

export const T_GRASS = 0, T_DIRT = 1, T_WATER = 2, T_FOREST = 3, T_ASH = 4;   // T_FOREST — пол чащи (непроходим); T_ASH — пепелище (GDD v1.8.1 B-31)
// Что закрывает обзор и останавливает снаряды (вода и крада — нет).
const OPAQUE = new Set(['tree', 'rock', 'wall', 'palisade', 'izba', 'idol', 'gate', 'perun', 'cart', 'anvil']);

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
    this.objects = [];     // интерактивные объекты зоны: двери изб, сундук, тело, выходы (data/zones/*.json → objects)
    this.entries = {};     // точки входа в зону
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
    if (!(w > 0) || !(h > 0)) return;   // m1g: пустой футпринт (декор 0×0) никогда не блокирует — раньше при нецелых x·2, y·2 метил сабтайл
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

export function generateMap(seed, zone = null) {
  if (zone && zone.path) return generateTrail(seed, zone);
  if (zone && zone.id === 'kapishche') return generateKapishche(seed, zone);
  if (zone && zone.id === 'ladoga') return generateLadoga(zone);
  // GDD v1.8.1 (B-31): тупик Мары — карта расширена на восток (zone.landmarks.maraDen.mapW); основная часть 48×48 та же
  const den = zone && zone.landmarks && zone.landmarks.maraDen;
  const m = new GameMap(den ? den.mapW : MAP_W, MAP_H);
  const rng = makeRng(seed);
  const W = m.w, H = m.h, W0 = MAP_W;
  const inDen = den ? denShape(den) : () => false;
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
  const LM = (zone && zone.landmarks) || {};
  if (LM.well) trail(S.x, S.y, LM.well.x, LM.well.y + 1);            // к колодцу (вторая половина зоны)
  if (LM.exit) trail(LM.well ? LM.well.x + 1 : S.x, LM.well ? LM.well.y + 2 : S.y, LM.exit.x, LM.exit.y);   // выход на тропу к капищу

  // --- спланированные объекты
  const fire = m.addProp('fire', S.x - 4, S.y - 4, 2);      // крада 2×2 (scale.md §3.3)
  fire.krada = true;                                         // спрайт художника fx_rest_krada (покой / отдых)
  m.krada = { x: fire.x + 1, y: fire.y + 1 };
  m.lights.push({ x: S.x - 3, y: S.y - 3, r: 110, kind: 'fire', krada: true });
  m.addProp('idol', S.x + 3, S.y - 4, 1);                   // чур
  m.addProp('izba', 11, 12, 4);                             // малая изба 4×4
  m.addProp('izba', 31, 1, 4);
  if (LM.hut3) m.addProp('izba', LM.hut3.x, LM.hut3.y, LM.hut3.size || 4, LM.hut3.door ? { door: LM.hut3.door } : {});   // изба 3 у колодца (в ней Мал, act1); m1f: дверь к колодцу (+X)
  for (let x = 28; x <= 45; x++) {                           // частокол с воротами (проём 2 тайла), толщина 1 тайл
    if (x === 38 || x === 39) continue;
    // m1i (дизайнер): в Залесье — низкий дворовый тын (колья 26–32 px, герой виден из-за него); проём без воротных столбов
    m.addProp('palisade', x, 7, 1, { gatepost: false, tyn: true });
  }
  for (let y = 2; y <= 6; y++) m.addProp('palisade', 28, y, 1, { axis: 'y', tyn: true });
  // каменные развалины: тонкая (½ тайла) Г-образная стена с проломом — обход и проверка полутайловой коллизии
  for (let x = 13; x <= 21; x++) {
    if (x === 16) continue;
    m.addProp('wall', x, 32, 1, { fp: x === 21 ? [21, 32, 0.5, 1] : [x, 32, 1, 0.5] });
  }
  for (let y = 33; y <= 39; y++) if (y !== 37) m.addProp('wall', 21, y, 1, { fp: [21, y, 0.5, 1] });
  // отдельная тонкая стена посреди поля (x 30,0–30,5), чтобы было что обходить рядом со стартом
  for (let y = 22; y <= 27; y++) m.addProp('wall', 30, y, 1, { fp: [30, y, 0.5, 1] });
  // колодец и Чуров камень (тихий круг 6 тайлов), выход на тропу (решение дизайнера по QA итерации 2)
  if (LM.well) { m.addProp('well', LM.well.x, LM.well.y, LM.well.size || 2); m.lights.push({ x: LM.well.x + 1, y: LM.well.y + 1, r: 50, kind: 'chur' }); }
  if (LM.churStone) { m.addProp('churstone', LM.churStone.x, LM.churStone.y, 1); m.churStone = { x: LM.churStone.x + 0.5, y: LM.churStone.y + 0.5 }; }
  if (LM.exit) {
    m.exit = { x: LM.exit.x, y: LM.exit.y, to: LM.exit.to };
    // проход сквозь лесную кромку
    for (let y = Math.floor(LM.exit.y) - 2; y < H; y++) for (let x = Math.floor(LM.exit.x) - 1; x <= Math.floor(LM.exit.x) + 1; x++) m.keepClear = (m.keepClear || []).concat([[x, y]]);
  }

  // стаи нечисти: из data/zones/<зона>.json (центры, состав, mlvl)
  m.packs = (zone && zone.packs ? zone.packs : []).map((p) => ({ x: p.x, y: p.y, kinds: [...p.kinds], mlvl: p.mlvl, role: p.role, ambush: !!p.ambush }));
  resolveObjects(m, zone, (o) => [o.x, o.y]);
  // перед дверьми изб — свободно (подход к двери)
  for (const o of m.objects) if (o.type === 'hut') {
    if (o.door === '+x') { for (let y = Math.floor(o.y) - 1; y <= Math.floor(o.y) + 1; y++) for (let x = Math.floor(o.x); x <= Math.floor(o.x) + 2; x++) m.keepClear = (m.keepClear || []).concat([[x, y]]); }   // m1f: поляна 3×3 перед дверью
    else for (let y = Math.floor(o.y); y <= Math.floor(o.y) + 1; y++) for (let x = Math.floor(o.x) - 1; x <= Math.floor(o.x) + 1; x++) m.keepClear = (m.keepClear || []).concat([[x, y]]);
  }
  const nearPack = (x, y, r) => m.packs.some((p) => d(x + 0.5, y + 0.5, p.x, p.y) < r);

  // --- лесная кромка по периметру: сплошная чаща (весь тайл непроходим)
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      if (m.isBlocked(x, y)) continue;
      if (m.keepClear && m.keepClear.some(([kx, ky]) => kx === x && ky === y)) continue;
      if (x >= W0) continue;                                   // восточная пристройка (тупик Мары) — ниже, своим генератором
      const e = Math.min(x, y, W0 - 1 - x, H - 1 - y);
      const p = e < 2 ? 1 : e === 2 ? 0.55 : e === 3 ? 0.18 : 0;
      if (p && rng() < p) { const birch = rng() < 0.2; if (!inDen(x, y)) m.addProp('tree', x, y, 1, { birch }); }   // те же броски — остальная карта не сдвигается
    }
  }
  // --- валуны и отдельные деревья внутри стоят на полутайловой сетке; у дерева непроходим только ствол (½×½ тайла)
  const scatter = (count, size, add) => {
    let placed = 0, tries = 0;
    while (placed < count && tries++ < count * 60) {
      const x = rng.int(8, W0 * SUB - 10) / SUB, y = rng.int(8, H * SUB - 10) / SUB;
      if (d(x, y, S.x, S.y) < 5.5 || nearPack(x, y, 3) || !m.rectFree(x - 1, y - 1, size + 2, size + 2)) continue;
      if (m.objects.some((o) => d(x, y, o.sx, o.sy) < 2.2)) continue;
      if (m.groundAt(Math.floor(x), Math.floor(y)) === T_DIRT && rng() < 0.7) continue;
      add(x, y); placed++;
    }
  };
  scatter(12, 1, (x, y) => m.addProp('rock', x, y, 1));
  scatter(5, 2, (x, y) => m.addProp('rock', x, y, 2));
  // ствол — сабтайл (x, y); рисуем дерево с центром в центре этого сабтайла
  scatter(16, 0.5, (x, y) => m.addProp('tree', x - 0.25, y - 0.25, 1, { birch: rng() < 0.6, fp: [x, y, 0.5, 0.5] }));

  if (den) carveMaraDen(m, den, inDen, makeRng(seed + 7331));   // тупик Мары (GDD v1.8.1 B-31) — после чащи кромки и россыпи
  const lad = (zone.objects || []).find((o) => o.id === 'to_ladoga');
  if (lad) clearProps(m, lad.x, lad.y, 1.6);
  // m1f (P0.1): перед дверью избы с дверью к колодцу — поляна 2–3 тайла без подлеска; стая избы — на открытом месте
  for (const o of m.objects) if (o.type === 'hut' && o.door === '+x') {
    clearProps(m, o.x + 1.5, o.y, 2.6);
    // m1f (P0.1, владелец): поляна между дверью и колодцем — деревьев нет ни на земле (прямоугольник дверь…колодец),
    // ни по экрану: деревья кромки (до 166 px), чьи кроны закрывают фасад избы, дверь или точку у колодца, убраны;
    // убранные деревья самой кромки (y ≥ H − 3) заменены низким подлеском — граница карты остаётся непроходимой
    const W = LM.well;
    if (W) {
      const x0 = Math.floor(o.x), x1 = W.x + (W.size || 2), y0 = Math.min(Math.floor(o.y), W.y) - 1, y1 = Math.max(Math.floor(o.y), W.y + (W.size || 2)) + 1;
      clearProps(m, 0, 0, 0, (p) => p.type === 'tree' && p.fp[0] + p.fp[2] > x0 && p.fp[0] < x1 && p.fp[1] + p.fp[3] > y0 && p.fp[1] < y1);
      const hz = LM.hut3 || { x: o.x - 4, y: o.y - 2, size: 4 }, hs = hz.size || 4;
      const S = (x, y) => [(x - y) * HALF_W, (x + y) * HALF_H];
      const V = [W.x - 1, W.y + 2.6];                              // где стоит герой «у колодца»
      const pts = [S(hz.x, hz.y + hs), S(hz.x + hs, hz.y), S(hz.x + hs, hz.y + hs), S(V[0], V[1])];
      const R = { x0: Math.min(...pts.map((q) => q[0])) - 8, x1: Math.max(...pts.map((q) => q[0])) + 8,
        y0: S(hz.x, hz.y)[1] - 116, y1: Math.max(...pts.map((q) => q[1])) + 4 };
      const front = hz.x + hz.y;                                    // деревья позади избы её не закрывают
      const edge = [];
      clearProps(m, 0, 0, 0, (p) => {
        if (p.type !== 'tree') return false;
        const cx = p.fp[0] + p.fp[2] / 2, cy = p.fp[1] + p.fp[3] / 2;
        if (cx + cy <= front) return false;
        const [sx, sy] = S(cx, cy), h = p.birch ? 132 : 166;
        const hit = sx + 20 > R.x0 && sx - 20 < R.x1 && sy - 20 > R.y0 && sy - h < R.y1;
        if (hit && p.fp[2] >= 1 && p.y >= m.h - 3) edge.push([p.x, p.y]);
        return hit;
      });
      for (const [x, y] of edge) m.addProp('bush', x, y, 1);
      m.glade = { R, removedEdge: edge.length };
    }
    const pk = m.packs.find((p) => p.role === o.pack);
    if (pk) clearProps(m, pk.x, pk.y, 2.2);
  }

  m.computeReach();
  return m;
}

/** Объекты зоны из JSON (двери изб, сундук, тело жреца, выходы, ворота) в мировые координаты.
 *  pos(o) → [x, y] — для тропы координаты считаются от осевой линии (x, dy).
 *  (x, y) — точка объекта, (sx, sy) — где встаёт герой. */
export function resolveObjects(m, zone, pos) {
  m.objects = [];
  for (const def of (zone && zone.objects) || []) {
    const o = { ...def, done: false };
    if (def.type === 'hut') {
      const [ix, iy] = def.izba, s = def.size || 4;
      if (def.door === '+x') {                  // m1f: дверь на фасаде +X (props.js: y+1,4…2,9) — изба Мала смотрит на колодец
        o.x = ix + s; o.y = iy + 2.15;
        o.sx = o.x + 0.75; o.sy = o.y;
        o.out = [o.x + 0.6, o.y];               // куда выходят спасённые
      } else {
        o.x = ix + 2.15; o.y = iy + s;          // дверной проём на фасаде +Y (props.js: x+1,4…2,9)
        o.sx = o.x; o.sy = o.y + 0.75;
        o.out = [o.x, o.y + 0.6];
      }
      o.reach = 1.0;
    } else {
      [o.x, o.y] = pos(def);
      o.sx = o.x; o.sy = o.y + (def.type === 'chest' || def.type === 'body' ? 0.9 : 0);
      o.reach = def.type === 'chest' || def.type === 'body' ? 1.2 : 0;
    }
    m.objects.push(o);
  }
  m.entries = {};
  for (const [id, e] of Object.entries((zone && zone.entries) || {})) {
    if (e.at) m.entries[id] = { at: e.at };
    else { const [x, y] = pos(e); m.entries[id] = { x, y }; }
  }
}


/** Тупик Мары Пепельной (GDD v1.8.1 B-31): поляна-пепелище за избой 2 на северо-востоке, вход — горловина от восточной
 *  кромки Залесья; у входа обгоревший сарай и пепел (вход читается с пути «ворота частокола → изба 3»). */
function clearProps(m, x, y, rad, pred = null) {
  const drop = m.props.filter((p) => (p.type === 'tree' || p.type === 'rock') && (pred ? pred(p) : Math.hypot(p.x + 0.5 - x, p.y + 0.5 - y) <= rad));
  if (!drop.length) return;
  const kill = new Set(drop);
  m.props = m.props.filter((p) => !kill.has(p));
  for (const p of drop) {
    const [fx, fy, fw, fh] = p.fp;
    for (let sy = Math.floor(fy * SUB); sy < Math.ceil((fy + fh) * SUB - 1e-6); sy++)
      for (let sx = Math.floor(fx * SUB); sx < Math.ceil((fx + fw) * SUB - 1e-6); sx++)
        if (sx >= 0 && sy >= 0 && sx < m.sw && sy < m.sh) { m.sub[sy * m.sw + sx] = 0; m.opaque[sy * m.sw + sx] = 0; }
  }
  for (let ty = Math.floor(y - rad); ty <= Math.ceil(y + rad); ty++)
    for (let tx = Math.floor(x - rad); tx <= Math.ceil(x + rad); tx++)
      if (m.inside(tx, ty) && m.ground[ty * m.w + tx] !== T_WATER) m.ground[ty * m.w + tx] = T_DIRT;
}

function denShape(den) {
  const [cx, cy] = den.center, C = den.corridor;
  return (x, y) => Math.hypot(x + 0.5 - cx, y + 0.5 - cy) <= den.clearR || (x >= C.x0 && x <= C.x1 && y >= C.y0 && y <= C.y1);
}
function carveMaraDen(m, den, inDen, rng) {
  const W = m.w, H = m.h, W0 = MAP_W, [cx, cy] = den.center;
  m.maraDen = { center: [...den.center], clearR: den.clearR };
  // пол: пепелище в тупике и горловине
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (inDen(x, y)) m.ground[y * W + x] = T_ASH;
  // чаща восточной пристройки: всё вне тупика непроходимо и закрывает обзор, деревья гуще у кромки поляны
  const dist = new Uint8Array(W * H).fill(255), q = [];
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (inDen(x, y)) { dist[y * W + x] = 0; q.push(y * W + x); }
  for (let k = 0; k < q.length; k++) {
    const i = q[k], x = i % W, y = (i / W) | 0;
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nx = x + dx, ny = y + dy, j = ny * W + nx;
      if (nx < 0 || ny < 0 || nx >= W || ny >= H || dist[j] <= dist[i] + 1) continue;
      dist[j] = dist[i] + 1; if (dist[j] < 8) q.push(j);
    }
  }
  for (let y = 0; y < H; y++) for (let x = W0 - 2; x < W; x++) {
    if (inDen(x, y) || m.isBlocked(x, y)) continue;
    m.ground[y * W + x] = T_FOREST;
    m.markRect(x, y, 1, 1, true);
    const dd = dist[y * W + x], p = dd <= 1 ? 0.8 : dd === 2 ? 0.5 : dd === 3 ? 0.3 : 0.08;
    if (rng() < p) {
      const birch = rng() < 0.2;
      // m1g (решение дизайнера v1.11): первый ряд елей на южной кромке поляны закрывал её кронами — вместо них горелые пни;
      // тайл остаётся непроходимым лесом (markRect выше), поток rng не меняется
      const T = den.thinSouth, front = T && (y + 0.5 > cy + T.minDy || (T.minFront != null && y + 0.5 > cy && x + y + 1 - cx - cy > T.minFront));   // юг + передняя по экрану часть юго-востока
      if (T && dd <= (T.rows || 1) && front && Math.hypot(x + 0.5 - cx, y + 0.5 - cy) <= den.clearR + 0.6 + (T.rows || 1)) {
        if (dd <= 1 || hash2(x, y, 13) < (T.stumpShare ?? 0.5)) m.addProp('stump', x, y, 1, { fp: [x + 0.5, y + 0.5, 0, 0], variant: Math.floor(hash2(x, y, 11) * 3) % 3 });
        m.thinned = (m.thinned || 0) + 1;
      } else m.addProp('tree', x, y, 1, { birch, shared: true });
    }
  }
  m.forestFrom = W0 - 2;                                   // мини-карта: непроходимые тайлы без пропса за этой x — лес
  // обгоревший сарай у входа (южнее горловины) и пепел на подходе
  const B = den.barn, b = m.addProp('izba', B[0], B[1], B[2], { burnt: true, fp: [B[0], B[1], B[2], 2] });
  b.depth = B[0] + B[2] / 2 + B[1] + 1;
  for (const [x, y] of den.ash || []) m.addProp('ash', x, y, 1, { fp: [x + 0.5, y + 0.5, 0, 0] });
  for (const [x, y] of den.ash || []) if (m.groundAt(Math.floor(x), Math.floor(y)) !== T_WATER) m.ground[Math.floor(y) * W + Math.floor(x)] = T_ASH;
  // GDD v1.11: горелые пни по краю поляны — декор без коллизии (спрайт prop_stump_burnt, кадр = вариант)
  for (const [x, y, v] of den.stumps || []) m.addProp('stump', x, y, 1, { fp: [x + 0.5, y + 0.5, 0, 0], variant: v | 0 });
}
