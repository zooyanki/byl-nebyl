// Элитные враги (GDD v1.7 §5.3): вожаки (имя из генератора act1_texts §9, в М1 — 1 модификатор, свита ×1,5 опыта),
// матёрые (×3 HP / ×1,5 урона / ×3 опыта, холодный тинт), модификаторы (Могучий, Прыткий, Каменнокожий, Жаркий,
// Студёный, Кровопийца). Числа — data/stats.json → elites; таблицы выпадения — data/droptables.json.
import { CFG } from '../data/config.js';
import { RU, t } from '../core/i18n.js';

const FEM_KINDS = new Set(['anchutka']);   // «Матёрая анчутка»; упырь и поджигатель — м. р.

/** Имя вожака: прозвище (А) + примета (Б) в роде прозвища, порядок «А Б», с шансом swapPct% — «Б А». */
export function leaderName(rng) {
  const G = RU['namegen.leader'];
  if (!G) return { name: t('ui.target.leader'), fem: false };
  const [a, g] = G.a[Math.floor(rng() * G.a.length)], b = G.b[Math.floor(rng() * G.b.length)][g === 'f' ? 1 : 0];
  return { name: rng() * 100 < (G.swapPct ?? 25) ? b + ' ' + a : a + ' ' + b, fem: g === 'f' };
}

/** Применить модификаторы к врагу (статы — сразу, реакции на удар — Enemy.onHitHero, взрыв — при гибели). */
export function applyMods(e, mods) {
  const M = CFG.stats.elites.mods;
  e.mods = [...mods]; e.modDefs = {};
  for (const id of mods) {
    const m = M[id];
    if (!m) continue;
    e.modDefs[id] = m;
    if (m.dmgMul) { e.dmgMin = Math.floor(e.dmgMin * m.dmgMul); e.dmgMax = Math.floor(e.dmgMax * m.dmgMul); }
    if (m.speedMul) e.speed *= m.speedMul;
    if (m.atkSpeedMul) { e.attackTime /= m.atkSpeedMul; e.hitAt /= m.atkSpeedMul; }
    if (m.physRes) e.res.melee = Math.max(e.res.melee || 0, m.physRes);
    if (m.coldRes) e.res.cold = Math.max(e.res.cold || 0, m.coldRes);
  }
}

/** Сделать врага элитой: type 'champion' | 'leader' | 'bylina'. */
export function makeElite(e, type, opts = {}) {
  const E = CFG.stats.elites[type];
  e.elite = type;
  if (type !== 'bylina') {
    e.maxHp = e.hp = Math.floor(e.maxHp * E.hp);
    e.dmgMin = Math.floor(e.dmgMin * E.dmg); e.dmgMax = Math.floor(e.dmgMax * E.dmg);
    e.xp = Math.round(e.xp * E.xp);
  }
  e.dropTable = E.drop;
  if (type === 'leader') {
    e.leader = true;
    const n = leaderName(opts.rng || Math.random);
    e.name = n.name; e.fem = n.fem;
  }
  if (type === 'champion') e.fem = FEM_KINDS.has(e.kind);
  if (opts.mods && opts.mods.length) applyMods(e, opts.mods);
  return e;
}

/** Подпись под именем на плашке цели: «Вожак · Могучий», «Матёрый», «Былинный враг · Жаркая». */
export function eliteTitle(e) {
  const g = e.fem ? '.f' : '.m';
  const mods = (e.mods || []).map((m) => RU['ui.target.mod.' + m + g] || RU['ui.target.mod.' + m] || m);
  if (e.elite === 'leader') return [t('ui.target.leader'), ...mods].join(' · ');
  if (e.elite === 'champion') return [RU['ui.target.champion' + g] || 'Матёрый', ...mods].join(' · ');
  if (e.elite === 'bylina') return ['Былинный враг', ...mods].join(' · ');
  return null;
}

/** Генерация вожаков и матёрых зоны (после спавна стай). rng — детерминированный (зерно зоны). */
export function setupZoneElites(game, st, rng) {
  const Z = st.zone, L = CFG.stats.elites.leader, nMods = (L.mods || {})[Z.mission] ?? 1;
  const MODS = Object.keys(CFG.stats.elites.mods);
  const all = [...game.enemies, ...game.buried];
  const pickMods = () => { const pool = [...MODS], out = []; for (let i = 0; i < nMods && pool.length; i++) out.push(pool.splice(Math.floor(rng() * pool.length), 1)[0]); return out; };
  const crown = (pi) => {
    const mem = all.filter((e) => e.pack === pi && !e.dead);
    const cand = mem.filter((e) => L.kinds.includes(e.kind));
    if (!cand.length) return null;
    const kinds = [...new Set(cand.map((e) => e.kind))], kind = kinds[Math.floor(rng() * kinds.length)];
    const lead = cand.find((e) => e.kind === kind);
    makeElite(lead, 'leader', { rng, mods: pickMods() });
    for (const e of mem) if (e !== lead) { e.retinue = true; e.xp = Math.round(e.xp * L.retinueXp); e.dropTable = L.retinueDrop; }
    return lead;
  };
  const leaders = [];
  game.map.packs.forEach((p, i) => {
    if (p.leader) { const l = crown(i); if (l) leaders.push(l); }
    if (p.champions) {
      const need = [...p.champions];
      for (const e of all) { const j = need.indexOf(e.kind); if (e.pack === i && j >= 0) { need.splice(j, 1); makeElite(e, 'champion'); } }
    }
  });
  // вожаки «по правилу зоны» (тропа: 1 вожак во второй половине, mlvl 3, упырь или анчутка; ответ дизайнера 08.10)
  const R = Z.leaders;
  if (R && R.count) {
    const ok = game.map.packs.map((p, i) => i).filter((i) => {
      const p = game.map.packs[i];
      return !p.ambush && !p.champions && p.x >= (R.minX ?? 0) && (!R.mlvl || p.mlvl === R.mlvl) && p.kinds.length >= 1 + L.retinue[0] && p.kinds.some((k) => L.kinds.includes(k));
    });
    for (let n = 0; n < R.count && ok.length; n++) { const l = crown(ok.splice(Math.floor(rng() * ok.length), 1)[0]); if (l) leaders.push(l); }
  }
  return leaders;
}
