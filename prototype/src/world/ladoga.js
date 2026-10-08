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
    if (!gap(gaps, P.x1, y)) m.addProp('palisade', P.x1, y, 1, { axis: 'y', gatepost: y === 20 || y === 23 ? (y === 20 ? 'left' : 'right') : false });
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
  for (const [type, x, y, size, fp] of zone.props) {
    const p = m.addProp(type, x, y, size, { fp: [...fp], len: type === 'ladya' ? 12 : 0, beam: type === 'ladya' ? 3 : 0 });
    if (type === 'churstone') m.churStone = { x: x + 0.5, y: y + 0.5 };
  }
  resolveObjects(m, zone, (o) => [o.x, o.y]);
  for (const o of m.objects) if (o.type === 'stash') { o.reach = o.reach || 1.6; o.sx = zone.entries.start.x; o.sy = zone.entries.start.y; }
  m.captions = zone.captions || [];
  m.computeReach();
  return m;
}
