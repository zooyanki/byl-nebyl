// Умения (data/skills.json, GDD v1.2 §3.6). ЛКМ — удар оружием, ПКМ — «Огненный змей».
export const SKILLS = { strike: { id: 'strike', name: 'Удар оружием', key: 'ЛКМ' } };
let EVERY = 2;

export function applySkills(json, stats) {
  for (const [id, d] of Object.entries(json)) if (!id.startsWith('_')) SKILLS[id] = { id, ...d };
  EVERY = stats.skillRankEveryLevels || 2;
}

// Очков навыков в прототипе ещё нет (дерево — позже): ранг растёт сам, «половина очков в основной навык» (GDD §9.1).
export function serpentRank(level, bonus = 0) { return Math.min(SKILLS.fire_serpent.maxRank, 1 + Math.floor((level - 1) / EVERY)) + bonus; }
export function serpentCost(rank) { const s = SKILLS.fire_serpent; return Math.floor(s.cost + s.costPerRank * (rank - 1)); }
export function serpentDamage(rank) {
  const s = SKILLS.fire_serpent;
  return [s.dmgMin + s.perRankMin * (rank - 1), s.dmgMax + s.perRankMax * (rank - 1)];
}
