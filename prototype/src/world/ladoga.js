// Ладога 48×48 по GDD v1.10 §7.1. Серый ящик: постройки — простые формы, координаты из data/zones/ladoga.json.
import { SUB } from './collision.js';
import { GameMap, T_DIRT, T_WATER, resolveObjects } from './map.js';

const gap = (gaps, x, y) => gaps.some(([gx, gy, gw, gh]) => x >= gx && x < gx + gw && y >= gy && y < gy + gh);

export function generateLadoga(zone) {
  const [W, H] = zone.size;
  const m = new GameMap(W, H);
  const S = zone.entries.start;
  m.start = { x: S.x, y: S.y };
  const waterY = zone.waterFromY, [px, py, pw, ph] = zone.pier, [gx, gy] = zone.gangway;
  m.pier = [px, py, pw, ph];   // v2light: настил пристани рисуется досками (world.js buildFloor)
  const pier = (x, y) => x >= px && x < px + pw && y >= py && y < py + ph;
  const gang = (x, y) => x === gx && y === gy;
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    if (y >= waterY && !pier(x, y) && !gang(x, y)) {
      m.ground[y * W + x] = T_WATER;
      m.markRect(x, y, 1, 1, false);
      for (let j = 0; j < SUB; j++) for (let i = 0; i < SUB; i++) m.water[(y * SUB + j) * m.sw + x * SUB + i] = 1;
    }
  }
  const ns = zone.roads.ns, we = zone.roads.we, [sy0, sy1] = zone.sand;
  const dirt = (x, y) => {
    if (y >= waterY) return false;
    if (x >= ns[0] && x <= ns[1] && y >= ns[2] && y <= ns[3]) return true;
    if (y >= we[2] && y <= we[3] && x >= we[0] && x <= we[1]) return true;
    if (y >= sy0 && y <= sy1) return true;
    return false;
  };
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (dirt(x, y)) m.ground[y * W + x] = T_DIRT;
  const P = zone.palisade, gaps = P.gaps;
  for (let y = P.y0; y <= P.y1; y++) {
    if (!gap(gaps, P.x0, y)) m.addProp('palisade', P.x0, y, 1, { axis: 'y' });
    if (!gap(gaps, P.x1, y)) m.addProp('palisade', P.x1, y, 1, { axis: 'y' });   // m1k: столбы ворот — сегменты листов художника
  }
  for (let x = P.x0; x <= P.x1; x++) {
    if (!gap(gaps, x, P.y0)) m.addProp('palisade', x, P.y0, 1);
    if (!gap(gaps, x, P.y1)) m.addProp('palisade', x, P.y1, 1);
  }
  const [kx, ky] = zone.krada;
  const fire = m.addProp('fire', kx, ky, 2);
  fire.krada = true;
  m.krada = { x: kx + 1, y: ky + 1 };
  m.lights.push({ x: m.krada.x, y: m.krada.y, r: 110, kind: 'fire', krada: true });
  for (const [type, x, y, size, fp, ex] of zone.props) {
    // m1k (§7.1.1, §15): [kind, x, y, size, fp, {id, variant, door}]; сортировка — центр футпринта (addProp)
    const p = m.addProp(type, x, y, size, { ...(ex || {}), fp: [...fp], len: type === 'ladya' ? 12 : 0, beam: type === 'ladya' ? 3 : 0 });
    // v1.13.3 (ответ 5): дым только у жилых построек с печью — по виду постройки из ladoga.json smokeKinds, а не по точке в листе
    p.smoke = (zone.smokeKinds || []).includes(type);
    if (type === 'churstone') m.churStone = { x: x + 0.5, y: y + 0.5 };
  }
  resolveObjects(m, zone, (o) => [o.x, o.y]);
  buildGates(m, zone);
  fixFenceDepth(m);
  for (const o of m.objects) if (o.type === 'stash') { o.reach = o.reach || 1.6; o.sx = zone.entries.start.x; o.sy = zone.entries.start.y; }
  m.captions = zone.captions || [];
  m.computeReach();
  return m;
}

/** m1k (v1.13.2): ворота 4 клетки (столб, проём, проём, столб) на всех стенах. Столбы — сегменты _A/_B листов художника,
 *  каждый сортируется как клетка тына (x + y + 1); проём закрытых ворот перекрывается (syncExitWalls), открылись — снимается. */
function buildGates(m, zone) {
  const G = zone.gates;
  if (!G) return;
  m.gates = [];
  for (const side of ['east', 'south', 'north', 'west']) {
    const g = G[side];
    if (!g) continue;
    const [gx, gy] = g.at, ay = g.axis === 'y';
    const closable = g.open !== true, segs = [];
    for (const [k, seg] of [[0, 'A'], [3, 'B']]) {
      const x = ay ? gx : gx + k, y = ay ? gy + k : gy;
      if (g.torches || closable) m.lights.push({ x: x + 0.5, y: y + 0.5, r: Math.round(3 * 16 * Math.SQRT2), kind: 'fire', gate: null, seg });   // факел: свет r 3 тайла (§7.4)
      segs.push(m.addProp('gateseg', x, y, 1, { axis: g.axis, anchor: [gx, gy], openSheet: g.sheet + '_open_' + seg, closedSheet: closable ? g.sheet + '_closed_' + seg : null, open: !closable, side }));
    }
    const o = { id: 'gate_' + side, type: 'lgate', side, x: ay ? gx + 0.5 : gx + 2, y: ay ? gy + 2 : gy + 0.5, r: 1.2, axis: g.axis,
      opens: closable ? g.open : null, hoverKey: g.hoverKey, segs, torches: !!g.torches,
      cells: ay ? [[gx, gy + 1, 1, 2]] : [[gx + 1, gy, 2, 1]], done: false };
    for (const l of m.lights) if (l.seg && l.gate === null && segs.some((q) => q.x + 0.5 === l.x && q.y + 0.5 === l.y)) l.gate = segs[0];
    m.objects.push(o); m.gates.push(o);
  }
  m.gateRules = { closedHoverKey: G.closedHoverKey, closedNear: G.closedNear, closedClick: G.closedClick };
  if (zone.sign) m.sign = zone.sign;
}

/** m1k: клетка тына / сегмент ворот, стоящая по диагонали перед большой постройкой (art/sprites/src/fence_scan.py,
 *  правило «cell in front»: x ≥ x0 + A или y ≥ y0 + B), при сортировке по центрам (x + y + 1 против x0 + A/2 + y0 + B/2)
 *  может оказаться «за» ней — тогда клетка встаёт сразу перед постройкой. В Ладоге v1.13.2 это одна клетка (8; 29) у seni_sw. */
function fixFenceDepth(m) {
  const blds = m.props.filter((p) => p.type !== 'palisade' && p.type !== 'gateseg' && p.fp[2] >= 2 && p.fp[3] >= 2);
  m.fenceFixed = [];
  for (const c of m.props) {
    if (c.type !== 'palisade' && c.type !== 'gateseg') continue;
    for (const b of blds) {
      const [x0, y0, A, B] = b.fp;
      const front = c.x >= x0 + A || c.y >= y0 + B, near = c.x >= x0 - 1 && c.x <= x0 + A && c.y >= y0 - 1 && c.y <= y0 + B;
      if (front && near && c.depth <= b.depth) { c.depth = b.depth + 0.01; m.fenceFixed.push([c.x, c.y, b.id || b.type]); }
      // v2art r2: церковь 11×6 — клетка тына целиком за постройкой (x + 1 ≤ x0 или y + 1 ≤ y0) встаёт сразу за ней
      const behind = !front && (c.x + 1 <= x0 || c.y + 1 <= y0);
      if (behind && near && c.depth >= b.depth) { c.depth = b.depth - 0.01; (m.fenceBehind || (m.fenceBehind = [])).push([c.x, c.y, b.id || b.type]); }
    }
  }
}
