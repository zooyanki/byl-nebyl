// «Капище Перуна» М1 (GDD v1.7 §8.1–8.2, §5.4; act1.md М1 п.5–7): двор 64×64 в лесной кромке, вход с запада
// (ворота с Лесной тропы), горящий идол Перуна в центре арены «Круг огнищ» 24×24, три огнища по краю арены.
// Стаи и огнища — data/zones/kapishche.json. Тихих кругов в зоне нет (Чуров камень входа — на тропе у ворот).
import { HALF_W } from '../config.js';
import { makeRng, hash2 } from '../core/rng.js';
import { SUB } from './collision.js';
import { GameMap, T_DIRT, resolveObjects } from './map.js';

export function generateKapishche(seed, zone) {
  const [W, H] = zone.size;
  const m = new GameMap(W, H);
  const rng = makeRng(seed);
  const d = (ax, ay, bx, by) => Math.hypot(ax - bx, ay - by);
  const LM = zone.landmarks || {}, I = LM.idol || { x: 40, y: 32 };
  const E = zone.entries.from_trail;
  m.start = { x: E.x, y: E.y };
  m.idol = { x: I.x, y: I.y };
  m.arena = { x: I.x, y: I.y, half: LM.arenaHalf || 12 };
  m.packs = zone.packs.map((p) => ({ x: p.x, y: p.y, kinds: [...p.kinds], mlvl: p.mlvl, role: p.role, ambush: !!p.ambush, leader: !!p.leader, champions: p.champions || null }));
  resolveObjects(m, zone, (o) => [o.x, o.y]);
  // огнища — интерактивные объекты (освятить: держи ЛКМ 3 с) и пропсы (зелёное пламя Небыли → тёплое)
  const hold = (zone.interact || {}).hold ?? 3;
  m.hearths = [];
  for (const h of zone.hearths || []) {
    const prop = m.addProp('hearth', Math.floor(h.x), Math.floor(h.y), 1, { cursed: true });
    const o = { ...h, type: 'hearth', x: prop.x + 0.5, y: prop.y + 0.5, sx: prop.x + 0.5, sy: prop.y + 1.6, reach: 1.25, hold, done: false, prop };
    m.objects.push(o); m.hearths.push(o);
    const HL = zone.light || { r: 3 };
    m.lights.push({ x: o.x, y: o.y, r: (HL.r || 3) * HALF_W * Math.SQRT2, rTiles: HL.r || 3, kind: 'fire', hearth: o });
  }
  // земля: утоптанный круг у идола, тропа от ворот, пятна у огнищ
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const cx = x + 0.5, cy = y + 0.5, n = hash2(x, y, 3) * 1.6;
    let dirt = d(cx, cy, I.x, I.y) < 8.5 + n;
    if (!dirt && Math.abs(cy - (E.y + Math.sin(cx * 0.25) * 1.2)) < 1.2 && cx < I.x) dirt = true;
    for (const h of m.hearths) if (d(cx, cy, h.x, h.y) < 2.4 + n * 0.5) dirt = true;
    if (dirt) m.ground[y * W + x] = T_DIRT;
  }
  // идол Перуна 2×2 (горит, пока жив Кривша)
  m.perun = m.addProp('perun', Math.floor(I.x) - 1, Math.floor(I.y) - 1, 2, { burning: true });
  m.lights.push({ x: I.x, y: I.y, r: 150, kind: 'fire', perun: true });
  // догорающие постройки капища (декор, огонь)
  const fires = [[7, 9], [55, 7], [6, 56], [57, 57], [28, 6]];
  for (const [fx, fy] of fires) { m.addProp('fire', fx, fy, 2); m.lights.push({ x: fx + 1, y: fy + 1, r: 110, kind: 'fire' }); }
  // вход: свободный проход у западной кромки
  const keep = (x, y) => (x < 7 && Math.abs(y + 0.5 - E.y) < 3) || d(x + 0.5, y + 0.5, I.x, I.y) < 10;
  const nearPack = (x, y, r) => m.packs.some((p) => d(x + 0.5, y + 0.5, p.x, p.y) < r) || m.hearths.some((h) => d(x + 0.5, y + 0.5, h.x, h.y) < r);
  // лесная кромка по периметру
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    if (m.isBlocked(x, y) || keep(x, y)) continue;
    const e = Math.min(x, y, W - 1 - x, H - 1 - y);
    const p = e < 2 ? 1 : e === 2 ? 0.55 : e === 3 ? 0.18 : 0;
    if (p && rng() < p) m.addProp('tree', x, y, 1, { birch: rng() < 0.15 });
  }
  // у входа — столбы ворот (частокол), остальное по краю закрывает лес
  for (let y = Math.floor(E.y) - 5; y <= Math.floor(E.y) + 5; y++) {
    if (Math.abs(y + 0.5 - E.y) < 2.2) continue;
    if (!m.isBlocked(0, y)) m.addProp('palisade', 0, y, 1, { axis: 'y', gatepost: false });
  }
  // валуны и одинокие деревья во дворе
  const scatter = (count, size, add) => {
    let placed = 0, tries = 0;
    while (placed < count && tries++ < count * 60) {
      const x = rng.int(8, W * SUB - 10) / SUB, y = rng.int(8, H * SUB - 10) / SUB;
      if (keep(Math.floor(x), Math.floor(y)) || nearPack(x, y, 3.2) || !m.rectFree(x - 1, y - 1, size + 2, size + 2)) continue;
      if (Math.abs(y - E.y) < 2.5 && x < I.x) continue;
      if (Math.max(Math.abs(x - I.x), Math.abs(y - I.y)) < (LM.arenaHalf ?? 12) + 1) continue;     // Круг огнищ 24×24 у идола — голая утоптанная земля, ничего не загораживает бой
      add(x, y); placed++;
    }
  };
  scatter(16, 1, (x, y) => m.addProp('rock', x, y, 1));
  scatter(4, 2, (x, y) => m.addProp('rock', x, y, 2));
  scatter(14, 0.5, (x, y) => m.addProp('tree', x - 0.25, y - 0.25, 1, { birch: rng() < 0.4, fp: [x, y, 0.5, 0.5] }));
  m.computeReach();
  return m;
}
