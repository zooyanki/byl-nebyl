// Снимок карты Залесья из генератора прототипа (только чтение; прототип не меняется).
// node dump_map.mjs [zone_override.json] > out.json
import fs from 'fs';
const P = '/workspace/game/prototype';
const { generateMap } = await import(P + '/src/world/map.js');
const zone = JSON.parse(fs.readFileSync(P + '/data/zones/zalesye.json', 'utf8'));
if (process.argv[2]) { const ov = JSON.parse(fs.readFileSync(process.argv[2], 'utf8')); Object.assign(zone.landmarks.maraDen, ov); }
const m = generateMap(1337, zone);
const keys = Object.keys(m).filter(k => typeof m[k] !== 'function');
const out = { W: m.w ?? m.W, H: m.h ?? m.H, keys, ground: Array.from(m.ground || []), props: (m.props || []).map(p => ({ type: p.type, x: p.x, y: p.y, size: p.size, fp: p.fp, birch: p.birch, seed: p.seed })) };
// проходимость по полутайлам
const W = out.W, H = out.H;
out.walk = [];
for (let y = 0; y < H * 2; y++) { let row = ''; for (let x = 0; x < W * 2; x++) row += (m.subBlocked(x, y) ? '#' : (m.isReachableAt((x + 0.5) / 2, (y + 0.5) / 2) ? '.' : ',')); out.walk.push(row); }
out.glade = m.glade; out.maraDen = m.maraDen; out.forestFrom = m.forestFrom;
console.log(JSON.stringify(out));
