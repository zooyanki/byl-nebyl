// Загрузка балансных конфигов из data/*.json и data/zones/*.json (GDD v1.2 §15) через fetch() — без сборки.
// После загрузки модули progression / enemies / skills / items заполняют свои таблицы из CFG.
import { applyStats } from './progression.js';
import { applyMonsters } from './enemies.js';
import { applySkills } from './skills.js';
import { applyItems } from './items.js';

export const CONFIG_FILES = ['stats', 'skills', 'monsters', 'items_base', 'affixes', 'droptables'];
export const ZONE_FILES = ['zalesye'];          // data/zones/*.json — по зоне на файл (GDD §15)
export const CFG = {};

export async function loadConfig(base = 'data/') {
  const parts = await Promise.all(CONFIG_FILES.map(async (name) => {
    const r = await fetch(base + name + '.json', { cache: 'no-cache' });
    if (!r.ok) throw new Error('Не загрузился конфиг ' + name + '.json: ' + r.status);
    return [name, await r.json()];
  }));
  for (const [k, v] of parts) CFG[k] = v;
  CFG.zones = {};
  for (const id of ZONE_FILES) {
    const r = await fetch(base + 'zones/' + id + '.json', { cache: 'no-cache' });
    if (!r.ok) throw new Error('Не загрузилась зона ' + id + '.json: ' + r.status);
    CFG.zones[id] = await r.json();
  }
  applyStats(CFG.stats);
  applySkills(CFG.skills, CFG.stats);
  applyMonsters(CFG.monsters, CFG.stats);
  applyItems(CFG.items_base, CFG.affixes, CFG.droptables);
  return CFG;
}
