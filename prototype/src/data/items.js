// Предметы (GDD v1.4 §6): 10 слотов, базы, редкость, аффиксы (тир T1 для ilvl 1–6, T2 7–12, T3 13+),
// таблицы выпадения §6.7, зелья §4.4, серебро §6.6. Все числа — из data/items_base.json, affixes.json,
// droptables.json (applyItems при старте); здесь только логика.

export const SLOTS = [];
export const SLOT_NAMES = {};
export const TYPE_SLOTS = {};
export const RARITY = {};
export const BASES = [];
export const BASE = {};
export const AFFIXES = [];
export const POTIONS = {};
export let STARTER_KIT = [];
export let STARTER_BELT = [];
export let BELT_SIZE = 4;
export let BELT_STACK = 5;
export let POTION_COOLDOWN = 0.5;
export const DROP_NORMAL = {};
export const RARITY_WEIGHTS = {};
export const TYPE_WEIGHTS = {};
export const POTION_WEIGHTS = {};
let DT = null, TIERS = { t1Max: 6, t2Max: 12 }, MAGIC = null, RARE_ADJ = [], RARE_NOUN = [];
const ARMOR = ['body', 'head', 'shield', 'gloves', 'feet', 'belt'];

export function applyItems(ib, af, dt) {
  SLOTS.length = 0; SLOTS.push(...ib.slots);
  Object.assign(SLOT_NAMES, ib.slotNames); Object.assign(TYPE_SLOTS, ib.typeSlots); Object.assign(RARITY, ib.rarity);
  BASES.length = 0;
  for (const b of ib.bases) {
    const base = { ...b, g: b.gender, req: b.reqLevel ?? b.req, shortName: b.shortName || b.name };
    BASE[b.id] = base;
    if (b.implemented !== false) BASES.push(base);      // посохи описаны, но в прототипе не выпадают
  }
  for (const [k, p] of Object.entries(ib.potions)) POTIONS[k] = { id: k, ...p };
  STARTER_KIT = ib.starterKit; STARTER_BELT = ib.starterBelt;
  BELT_SIZE = ib.beltSize; BELT_STACK = ib.beltStack; POTION_COOLDOWN = ib.potionCooldown;
  AFFIXES.length = 0;
  for (const a of af.affixes) AFFIXES.push({ ...a, forms: a.names, fmt: (v) => a.text.replace('{v}', v) });
  TIERS = af.tiers; MAGIC = af.magic;
  RARE_ADJ = af.rareNames.adjectives; RARE_NOUN = af.rareNames.nouns;
  DT = dt;
  Object.assign(DROP_NORMAL, dt.normal.outcome); Object.assign(RARITY_WEIGHTS, dt.normal.rarity);
  Object.assign(TYPE_WEIGHTS, dt.itemType); Object.assign(POTION_WEIGHTS, dt.potionType);
}

/** Зелье нужного вида по уровню монстра (слабое на mlvl 1–7, обычное с 6, крепкое с 12; в зоне перехода — случайно). */
export function potionFor(type, mlvl, rng = Math.random) {
  if (type === 'zhivaya') return 'zhivaya';
  const c = Object.values(POTIONS).filter((p) => p.res === (type === 'life' ? 'hp' : 'yar') && p.mlvl && mlvl >= p.mlvl[0] && mlvl <= p.mlvl[1]);
  return c.length ? c[Math.floor(rng() * c.length)].id : type + '1';
}
// Горсть серебра: round(rand(0,5;1,5) × (5 + 3·mlvl))
export function silverAmount(mlvl, rng = Math.random) {
  const s = DT.silver;
  return Math.max(1, Math.round((s.randMin + rng() * (s.randMax - s.randMin)) * (s.base + s.perMlvl * mlvl)));
}

export function pickWeighted(table, rng = Math.random) {
  let sum = 0;
  for (const k in table) sum += table[k];
  let r = rng() * sum;
  for (const k in table) { r -= table[k]; if (r < 0) return k; }
  return Object.keys(table)[0];
}
const pick = (arr, rng) => arr[Math.floor(rng() * arr.length)];
const roll = ([a, b], rng) => a + Math.floor(rng() * (b - a + 1));
export const tierOf = (ilvl) => (ilvl <= TIERS.t1Max ? 0 : ilvl <= TIERS.t2Max ? 1 : 2);

let UID = 1;
function groupsOf(base) {
  const t = base.type;
  const g = ['all'];
  if (t === 'sword' || t === 'axe' || t === 'staff') g.push('weapon'); else if (ARMOR.includes(t)) g.push('armor');
  g.push(t);
  return g;
}

/** Создать предмет по базе. rarity: normal|magic|rare. */
export function makeItem(baseId, rarity = 'normal', ilvl = 1, rng = Math.random, opts = {}) {
  const base = BASE[baseId];
  if (base.magicOnly && rarity === 'normal') rarity = 'magic';
  if (rarity === 'unique') rarity = 'rare';     // былинных предметов в прототипе ещё нет
  const it = {
    uid: UID++, kind: 'gear', base: base.id, type: base.type, w: base.w, h: base.h, rarity, ilvl, req: base.req,
    baseName: base.name, icon: base.icons ? pick(base.icons, rng) : base.icon, mods: {}, affixes: [],
  };
  if (base.dmg) { it.dmg = [...base.dmg]; it.speed = base.speed; }
  if (base.armor) it.armorBase = opts.armor != null ? opts.armor : roll(base.armor, rng);
  if (base.block) it.block = base.block;
  if (base.crit) it.mods.crit = base.crit;
  if (base.vsNechist) it.mods.vsNechist = base.vsNechist;
  // аффиксы
  const groups = groupsOf(base);
  const fits = (a) => a.slots.some((s) => groups.includes(s));
  const tier = tierOf(ilvl);
  let nPre = 0, nSuf = 0;
  if (opts.affixes) { for (const [id, v] of opts.affixes) addAffix(it, AFFIXES.find((a) => a.id === id), v); }
  else if (rarity === 'magic') {
    const r = rng();
    if (r < MAGIC.prefixOnly) nPre = 1; else if (r < MAGIC.prefixOnly + MAGIC.suffixOnly) nSuf = 1; else { nPre = 1; nSuf = 1; }
  } else if (rarity === 'rare') {
    const n = rng() < 0.5 ? 3 : 4;
    nPre = n === 4 ? 2 : 1 + (rng() < 0.5 ? 1 : 0); nSuf = n - nPre;
  }
  const used = new Set();
  const take = (kind) => {
    const pool = AFFIXES.filter((a) => a.kind === kind && fits(a) && !used.has(a.id) && a.tiers[tier]);
    if (!pool.length) return;
    const a = pick(pool, rng); used.add(a.id);
    addAffix(it, a, roll(a.tiers[tier], rng));
  };
  for (let i = 0; i < nPre; i++) take('prefix');
  for (let i = 0; i < nSuf; i++) take('suffix');
  // итоговые числа
  if (it.dmg && it.mods.maxdmg) it.dmg[1] += it.mods.maxdmg;
  if (it.armorBase != null) it.armor = Math.floor((it.armorBase + (it.mods.flatArmor || 0)) * (1 + (it.mods.pctArmor || 0) / 100));
  // имя
  if (rarity === 'rare') {
    const [noun, ng] = pick(RARE_NOUN, rng);
    it.name = pick(RARE_ADJ, rng)[ng] + ' ' + noun;
  } else if (rarity === 'magic') {
    const pre = it.affixes.find((a) => a.kind === 'prefix'), suf = it.affixes.find((a) => a.kind === 'suffix');
    // act1_texts §12.3: с суффиксом — короткое имя базы («Калёный меч сокола»), без суффикса — полное
    let n = suf ? base.shortName : base.name;
    if (pre) n = AFFIXES.find((a) => a.id === pre.id).forms[base.g] + ' ' + n[0].toLowerCase() + n.slice(1);
    if (suf) n += ' ' + AFFIXES.find((a) => a.id === suf.id).word;
    it.name = n;
  } else it.name = base.name;
  return it;
}

function addAffix(it, a, v) {
  it.affixes.push({ id: a.id, kind: a.kind, stat: a.stat, value: v });
  it.mods[a.stat] = (it.mods[a.stat] || 0) + v;
}

export function makePotion(kind) {
  const p = POTIONS[kind];
  return { uid: UID++, kind: 'potion', potion: kind, w: 1, h: 1, name: p.name, icon: p.icon, rarity: 'potion' };
}

/** Случайный предмет с обычного монстра уровня ilvl. Слот выбирается до базы. Базы: треб. уровень ≤ ilvl;
 *  тиры = разные треб. уровни баз слота: верхний доступный 50%, предыдущий 35%, прочие вместе 15% (droptables.baseTiers). */
export function pickBase(type, ilvl, rng = Math.random) {
  const all = BASES.filter((b) => b.type === type);
  let cands = all.filter((b) => b.req <= ilvl);
  if (!cands.length) { const m = Math.min(...all.map((b) => b.req)); cands = all.filter((b) => b.req === m); }
  const tiers = [...new Set(cands.map((b) => b.req))].sort((a, b) => b - a);   // от верхнего
  const T = DT.baseTiers;
  const tw = tiers.map((_, i) => (i === 0 ? T.top : i === 1 ? T.prev : T.rest / (tiers.length - 2)));
  const W = cands.map((b) => { const i = tiers.indexOf(b.req); return tw[i] / cands.filter((c) => c.req === b.req).length; });
  let r = rng() * W.reduce((a, b) => a + b, 0);
  for (let i = 0; i < cands.length; i++) { r -= W[i]; if (r < 0) return cands[i]; }
  return cands[cands.length - 1];
}
export function rollItem(ilvl, rng = Math.random, mf = 0) {
  const w = { ...RARITY_WEIGHTS }, k = DT.mfToWeights;
  if (mf) { w.magic += mf * k; w.rare += mf * k; w.unique += mf * k; }
  const rarity = pickWeighted(w, rng);
  let type = pickWeighted(TYPE_WEIGHTS, rng);
  if (type === 'weapon') type = rng() < DT.weaponSplit.sword ? 'sword' : 'axe';
  const base = pickBase(type, ilvl, rng);
  return makeItem(base.id, rarity, ilvl, rng);
}

// --- описание для подсказки
const fmtAffix = (a) => AFFIXES.find((x) => x.id === a.id).fmt(a.value);
export function itemLines(it) {
  // [text, colorKey]
  const L = [];
  if (it.kind === 'potion') {
    const p = POTIONS[it.potion];
    L.push([it.name, 'birch']);
    if (p.res === 'both') L.push([`Мгновенно восполняет ${Math.round(p.pct * 100)}% жизни и Яри`, 'linen']);
    else L.push([`+${p.amount} ${p.res === 'hp' ? 'к жизни' : 'к Яри'} за ${p.dur} с`, 'linen']);
    L.push(['ПКМ — выпить', 'mist']);
    return { lines: L, seps: [0] };
  }
  const rc = RARITY[it.rarity].color;
  L.push([it.name, rc]);
  const seps = [];
  if (it.rarity !== 'normal') L.push([it.baseName, 'birch']);
  seps.push(L.length - 1);
  if (it.dmg) L.push([`Урон: ${it.dmg[0]}–${it.dmg[1]}`, 'linen']);
  if (it.speed) L.push([`Атак в секунду: ${String(it.speed).replace('.', ',')}`, 'mist']);
  if (it.armor != null) L.push([`Броня: ${it.armor}`, it.mods.flatArmor || it.mods.pctArmor ? 'blue_lt' : 'linen']);
  if (it.block) L.push([`Блок щитом: ${it.block}%`, 'linen']);
  L.push([`Требуется уровень: ${it.req}`, 'req']);
  const base = BASE[it.base];
  const special = [];
  if (base.crit) special.push([`+${base.crit}% к шансу удачного удара`, 'linen']);
  if (base.vsNechist) special.push([`+${base.vsNechist}% к урону по Нечисти`, 'linen']);
  const aff = it.affixes.map((a) => [fmtAffix(a), 'blue_lt']);
  if (special.length || aff.length) { seps.push(L.length - 1); L.push(...special, ...aff); }
  return { lines: L, seps };
}
