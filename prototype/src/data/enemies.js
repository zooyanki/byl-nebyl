// Нечисть: таблица типов из data/monsters.json (GDD v1.2 §5.2), базовая шкала по mlvl из stats.json (§5.1):
//   HP = 15 + 7·mlvl, урон (1+mlvl)–(3+2·mlvl), AR 10+8·mlvl, DEF 8+6·mlvl, XP round(6+3·mlvl^1,35) × XP×.
import { monsterXp } from './progression.js';

export const ENEMIES = {};
let SCALE = null;

export function applyMonsters(json, stats) {
  for (const [id, d] of Object.entries(json)) if (!id.startsWith('_')) ENEMIES[id] = { id, ...d };
  SCALE = stats.monsterScale;
}

export function enemyStats(kind, mlvl) {
  const d = ENEMIES[kind], s = SCALE;
  const m = Math.max(d.mlvlMin, Math.min(d.mlvlMax, mlvl));
  const f = ([a, b]) => a + b * m;
  return {
    mlvl: m,
    hp: Math.max(1, Math.floor(f(s.hp) * d.hpMul)),
    dmgMin: Math.max(1, Math.floor(f(s.dmgMin) * d.dmgMul)),
    dmgMax: Math.max(1, Math.floor(f(s.dmgMax) * d.dmgMul)),
    ar: f(s.ar),
    dfn: f(s.def),              // защита (DEF); `def` у врага — запись из monsters.json
    xp: monsterXp(m, d.xpMul),
  };
}

/** Средний базовый урон монстра уровня mlvl (до множителя типа) — для «Поджога» (GDD §5.2 E11: 0,8 × средний урон mlvl). */
export function baseDamageAvg(mlvl) {
  const s = SCALE, f = ([a, b]) => a + b * mlvl;
  return (f(s.dmgMin) + f(s.dmgMax)) / 2;
}
