// Навыки (data/skills.json, GDD v1.4 §3.6). ЛКМ — базовый удар оружием (Ярь не тратит, доступен всегда).
// Число [a, b] — значение a на ранге 1 и +b за каждый следующий ранг.
export const SKILLS = {};
export let RULES = null, BRANCHES = [], DASH = null;
const ALL = [];

export function applySkills(json) {
  RULES = json.rules; BRANCHES = json.branches; DASH = json.dash;
  for (const k of Object.keys(SKILLS)) delete SKILLS[k];
  ALL.length = 0;
  for (const [id, d] of Object.entries(json.skills)) {
    const s = { id, ...d };
    SKILLS[id] = s;
    if (s.implemented !== false) ALL.push(s);
  }
}

export const skillList = () => ALL;
export const branchOf = (id) => BRANCHES.find((b) => b.id === id);

// --- ранги и очки
export function pointsTotal(level) { return RULES.pointsAtStart + RULES.pointsPerLevel * (level - 1); }
/** Сколько рангов навыка куплено за очки. */
export function boughtRank(hero, id) { return hero.skills[id] || 0; }
/** Итоговый ранг с бонусами экипировки (P10a «Ратный» / P10b «Вещий» — +ранг всем изученным навыкам ветки). */
export function rankOf(hero, id) {
  const b = boughtRank(hero, id);
  if (!b) return 0;
  const sk = SKILLS[id];
  const bonus = hero.mods ? hero.mods[RULES.bonusStat[sk.branch]] || 0 : 0;
  return Math.min(sk.maxRank || RULES.maxRank, b + bonus);
}
const val = (pair, rank) => pair[0] + pair[1] * (rank - 1);

export function skillCost(hero, id) {
  const sk = SKILLS[id], r = rankOf(hero, id) || 1;
  return sk.cost ? Math.max(0, Math.floor(val(sk.cost, r))) : 0;
}
/** Подстановки для описания навыка из act1_texts §16 на ранге r. */
export function descVars(hero, id, r) {
  const sk = SKILLS[id], n = skillNumbers(hero, id, r);
  const v = { ...n, dmg: n.dmgPct ?? n.physPct ?? n.elemPct, ar: n.arPct, def: n.defPct, res: n.resAll, hp: n.hpPct, regen: n.regenPct, sec: n.slowTime, yar: n.cost };
  if (sk.min) [v.min, v.max] = spellDamage(hero, id, r);
  if (id === 'stat') v.dmg = n.physPct;
  if (id === 'veshchee') v.dmg = n.elemPct;
  return v;
}
export function skillNumbers(hero, id, rankOverride = 0) {
  const sk = SKILLS[id], r = rankOverride || rankOf(hero, id) || 1;
  const n = { rank: r, cost: Math.max(0, Math.floor(val(sk.cost || [0, 0], r))) };
  for (const k of ['dmgPct', 'arPct', 'defPct', 'resAll', 'hpPct', 'physPct', 'regenPct', 'elemPct', 'min', 'max', 'slowTime', 'range']) {
    if (sk[k]) n[k] = k === 'range' && !Array.isArray(sk[k]) ? sk[k] : Array.isArray(sk[k]) ? val(sk[k], r) : sk[k];
  }
  if (sk.cd) n.cd = sk.cd;
  return n;
}
/** Урон ведовства: rand(min,max) × (1 + Дух/100 + %ведовства) × крит (§3.3). Здесь — границы до крита. */
export function spellDamage(hero, id, rankOverride = 0) {
  const n = skillNumbers(hero, id, rankOverride);
  const m = hero.spellMul || 1;           // 1 + Дух/100 + %ведовства + «Вещее слово» (считает Hero.recalc)
  return [Math.floor(n.min * m), Math.floor(n.max * m)];
}

/** Можно ли купить ранг: уровень, предыдущий навык ветки, хватает ли очков. */
export function rankBlock(hero, id) {
  const sk = SKILLS[id];
  const have = boughtRank(hero, id);
  if (have >= (sk.maxRank || RULES.maxRank)) return 'max';
  if (hero.level < sk.req + have) return 'level';
  if (sk.needs && boughtRank(hero, sk.needs) < 1) return 'prev';
  if (pointsSpent(hero) >= pointsTotal(hero.level)) return 'points';
  return null;
}
export function pointsSpent(hero) { return ALL.reduce((s, sk) => s + boughtRank(hero, sk.id), 0) - Object.values(RULES.starter).reduce((a, b) => a + b, 0); }
export function pointsFree(hero) { return pointsTotal(hero.level) - pointsSpent(hero); }
