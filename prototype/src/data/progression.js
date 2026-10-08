// Характеристики героя и формулы (GDD v1.2 §3.2–3.5). Числа — из data/stats.json (applyStats при старте).
// Экспортируемые `let` — живые привязки: импортёры видят значения после загрузки конфига.
export const ATTRS = [];
export let HERO_START = { str: 20, dex: 20, vit: 25, ene: 15 };
export let POINTS_PER_LEVEL = 5;
export let MAX_LEVEL = 20;
export let HERO_SPEED = 4.5;
export let MELEE_RANGE = 1.2;
export let HIT_FRAME = 0.6;
export let CAST_TIME = 0.8;
export let CAST_RELEASE = 0.3;
export let UNARMED = { min: 1, max: 2, speed: 1.2 };
export let HIT_STOP = 0.05;
export let S = null;                  // весь stats.json

export function applyStats(s) {
  S = s;
  ATTRS.length = 0; ATTRS.push(...s.attrs);
  HERO_START = { ...s.heroStart };
  POINTS_PER_LEVEL = s.pointsPerLevel; MAX_LEVEL = s.maxLevel;
  HERO_SPEED = s.heroSpeed; MELEE_RANGE = s.meleeRange; HIT_FRAME = s.hitFrame;
  CAST_TIME = s.castTime; CAST_RELEASE = s.castRelease; UNARMED = { ...s.unarmed }; HIT_STOP = s.hitStop;
}

// XP_до_след(L) = round(100·L^1,75, до десятков); на максимальном уровне — кап
export function xpToNext(level) {
  if (level >= MAX_LEVEL) return Infinity;
  const c = S.xpCurve;
  return Math.round((c.base * Math.pow(level, c.exp)) / c.roundTo) * c.roundTo;
}
// Опыт за монстра: round(6 + 3·mlvl^1,35) × множитель типа
export function monsterXp(mlvl, mult) {
  const m = S.monsterXp;
  return Math.max(1, Math.round(Math.round(m.base + m.k * Math.pow(mlvl, m.exp)) * mult));
}
// штраф: −20% за каждый уровень разницы сверх 5, минимум 10%
export function xpPenalty(heroLevel, mlvl) {
  const p = S.xpPenalty, d = heroLevel - mlvl;
  return d <= p.freeDiff ? 1 : Math.max(p.min, 1 - p.perLevel * (d - p.freeDiff));
}
// Шанс попадания (только физический урон): clamp(2·AR/(AR+DEF) · L_A/(L_A+L_D), 5%, 95%)
export function hitChance(arA, defD, lvlA, lvlD) {
  const h = ((2 * arA) / (arA + defD)) * (lvlA / (lvlA + lvlD));
  return Math.min(S.hitChance.max, Math.max(S.hitChance.min, h));
}
