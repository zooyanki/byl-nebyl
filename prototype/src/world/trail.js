// «Лесная тропа» М1 (GDD v1.5 §8.1–8.2, act1.md М1 п.3–4): зона 128×48, извилистый коридор
// по осевой линии y(x) из data/zones/trail.json → path, по сторонам непроходимая чаща.
// Стаи, объекты и точки входа заданы по x вдоль тропы и смещению dy от осевой.
import { makeRng, hash2 } from '../core/rng.js';
import { SUB } from './collision.js';
import { GameMap, T_GRASS, T_DIRT, T_FOREST, resolveObjects } from './map.js';

/** Осевая линия тропы. */
export function trailCenter(path) {
  const { y0, a1, p1, a2, p2 } = path;
  return (x) => y0 + a1 * Math.sin(x / p1) + a2 * Math.sin(x / p2 + 1);
}

export function generateTrail(seed, zone) {
  const [W, H] = zone.size;
  const m = new GameMap(W, H);
  const rng = makeRng(seed);
  const P = zone.path, yc = trailCenter(P);
  const at = (o) => [o.x, yc(o.x) + (o.dy || 0)];
  m.yc = yc;
  m.packs = zone.packs.map((p) => { const [x, y] = at(p); return { x, y, kinds: [...p.kinds], mlvl: p.mlvl, role: p.role, ambush: !!p.ambush, champions: p.champions || null }; });
  resolveObjects(m, zone, at);
  const LM = zone.landmarks || {};
  const stone = LM.churStone ? at(LM.churStone) : null;
  const gate = m.objects.find((o) => o.type === 'gate');
  const gateX = gate ? Math.floor(gate.x) + 1 : W;      // столбец частокола капища

  // поляны: стаи, объекты, вход, Чуров камень
  const glades = [...m.packs.map((p) => [p.x, p.y, P.clearing]), ...m.objects.map((o) => [o.x, o.y, o.type === 'exit' ? 2 : 2.6])];
  if (stone) glades.push([stone[0], stone[1], 3]);
  const open = new Uint8Array(W * H);
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      if (y < 2 || y > H - 3 || x > gateX) continue;
      const cx = x + 0.5, cy = y + 0.5;
      const n = (hash2(x, y, 11) - 0.5) * 1.2 + Math.sin(x * 0.5 + y * 0.2) * 0.5;
      let ok = Math.abs(cy - yc(cx)) <= P.halfWidth + n;
      if (!ok) for (const [gx, gy, r] of glades) if (Math.hypot(cx - gx, cy - gy) <= r + n * 0.5) { ok = true; break; }
      if (ok) open[y * W + x] = 1;
    }
  }
  // земля: трава в коридоре, утоптанная тропа по осевой, пол чащи снаружи
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const i = y * W + x;
    if (!open[i]) { m.ground[i] = T_FOREST; continue; }
    m.ground[i] = Math.abs(y + 0.5 - yc(x + 0.5)) < 0.9 + Math.sin(x * 0.7) * 0.25 ? T_DIRT : T_GRASS;
  }
  // расстояние до коридора (тайлы) — для густоты чащи
  const dist = new Uint8Array(W * H).fill(255);
  const q = [];
  for (let i = 0; i < W * H; i++) if (open[i]) { dist[i] = 0; q.push(i); }
  for (let k = 0; k < q.length; k++) {
    const i = q[k], x = i % W, y = (i / W) | 0;
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nx = x + dx, ny = y + dy;
      if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue;
      const j = ny * W + nx;
      if (dist[j] > dist[i] + 1) { dist[j] = dist[i] + 1; if (dist[j] < 8) q.push(j); }
    }
  }
  // частокол капища с воротами (веха M1b: ворота ведут в капище)
  if (gate) {
    const gy = Math.floor(gate.y);
    for (let y = gy - 7; y <= gy + 8; y++) {
      if (y === gy || y === gy + 1) continue;
      m.addProp('palisade', gateX, y, 1, { axis: 'y', gatepost: y === gy - 1 ? 'left' : y === gy + 2 ? 'right' : false });
    }
    m.addProp('gate', gateX, gy, 2, { axis: 'y', fp: [gateX, gy, 1, 2] });
    for (let y = 0; y < H; y++) for (let x = gateX + 1; x < W; x++) { open[y * W + x] = 0; m.ground[y * W + x] = T_FOREST; }
    // за частоколом горит капище
    m.addProp('fire', gateX + 1, gy - 4, 2); m.addProp('fire', gateX + 1, gy + 3, 2);
    m.lights.push({ x: gateX + 2, y: gy - 3, r: 120, kind: 'fire' }, { x: gateX + 2, y: gy + 4, r: 120, kind: 'fire' });
    m.gate = { x: gate.x, y: gate.y };
  }
  // чаща: каждый тайл вне коридора непроходим и закрывает обзор; деревья гуще у кромки
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const i = y * W + x;
    if (open[i] || m.isBlocked(x, y)) continue;
    m.markRect(x, y, 1, 1, true);
    const dd = dist[i];
    // перед коридором (ближе к камере) высокие деревья закрыли бы тропу: у кромки — низкий подлесок, дальше — редкие деревья
    const front = y + 0.5 > yc(x + 0.5);
    if (front) {
      if (dd <= 2) { if (rng() < 0.8) m.addProp('bush', x, y, 1, { shared: true }); }
      else if (dd >= 9 && rng() < 0.08) m.addProp('tree', x, y, 1, { birch: rng() < 0.25, shared: true });
      else if (rng() < 0.18) m.addProp('bush', x, y, 1, { shared: true });
      continue;
    }
    const p = dd <= 1 ? 0.75 : dd === 2 ? 0.5 : dd === 3 ? 0.3 : 0.07;
    if (rng() < p) m.addProp('tree', x, y, 1, { birch: rng() < 0.25, shared: true });
  }
  m.forest = true;
  // Чуров камень у ворот капища (тихий круг 6)
  if (stone) {
    const p = m.addProp('churstone', Math.floor(stone[0]), Math.floor(stone[1]), 1);
    m.churStone = { x: p.x + 0.5, y: p.y + 0.5 };
    m.lights.push({ x: m.churStone.x, y: m.churStone.y, r: 50, kind: 'chur' });
    // Чуров камень у входа в капище — объект «коснуться» (точка возрождения после касания, ответ дизайнера 08.10)
    for (const o of m.objects) if (o.type === 'stone') { o.x = m.churStone.x; o.y = m.churStone.y; o.sx = o.x; o.sy = o.y + 0.9; o.reach = 1.3; o.prop = p; }
    if (m.entries.chur) m.entries.chur = { x: m.churStone.x, y: m.churStone.y + 1.6 };
  }
  // сундук и тело жреца (сундук стоит на полутайловом футпринте, тело — плоско на земле)
  for (const o of m.objects) {
    if (o.type === 'chest') o.prop = m.addProp('chest', o.x - 0.5, o.y - 0.5, 1, { fp: [o.x - 0.5, o.y - 0.5, 1, 0.5] });
    if (o.type === 'body') o.prop = m.addProp('body', o.x - 0.5, o.y - 0.5, 1, { fp: [o.x, o.y, 0, 0] });
  }
  // в коридоре — редкие валуны и отдельные деревья (не на тропе, не на полянах)
  const d = (ax, ay, bx, by) => Math.hypot(ax - bx, ay - by);
  const busy = (x, y) => glades.some(([gx, gy, r]) => d(x, y, gx, gy) < r + 0.8) || Math.abs(y - yc(x)) < 1.6;
  const scatter = (count, size, add) => {
    let placed = 0, tries = 0;
    while (placed < count && tries++ < count * 80) {
      const x = rng.int(6 * SUB, (gateX - 4) * SUB) / SUB, y = rng.int(3 * SUB, (H - 4) * SUB) / SUB;
      if (busy(x + size / 2, y + size / 2) || !m.rectFree(x - 1, y - 1, size + 2, size + 2)) continue;
      add(x, y); placed++;
    }
  };
  scatter(22, 1, (x, y) => m.addProp('rock', x, y, 1));
  // отдельные деревья — только в северной (дальней от камеры) половине коридора
  scatter(40, 0.5, (x, y) => { if (y < yc(x) - 1.5) m.addProp('tree', x - 0.25, y - 0.25, 1, { birch: rng() < 0.5, fp: [x, y, 0.5, 0.5] }); else m.addProp('bush', x - 0.25, y - 0.25, 1, { fp: [x, y, 0.5, 0.5] }); });

  const e = m.entries.from_zalesye;
  m.start = { x: e.x, y: e.y };
  m.computeReach();
  return m;
}
