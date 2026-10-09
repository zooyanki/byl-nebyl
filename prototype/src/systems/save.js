// m1i (critics_m1f П.15, GDD §11): один слот сохранения в localStorage, автосейв при входе в Ладогу и при сдаче миссии.
// В слоте — герой (уровень, опыт, свойства, навыки, панель, снаряжение, котомка, пояс, серебро, ступень Удали), ладья
// (вещи и серебро), задание (цели, счётчики, флаги m1.* и прочие), лавки (ассортимент и метка обновления), что уже
// сделано в зонах (выбитые двери, освящённые огнища, открытые сундуки, тела, путевой камень). Монстры и добыча на земле
// не сохраняются (§11): при загрузке зоны полные — это «новая сессия» §4.5. Грузимся всегда в Ладогу.
import { Inventory } from './inventory.js';
import { bumpUid } from '../data/items.js';

export const SAVE_KEY = 'bylnebyl.v1.slot1';
export const SCHEMA = 1;
const HERO_KEYS = ['level', 'xp', 'base', 'points', 'silver', 'relics', 'letters', 'kills', 'skills', 'bar', 'rmb', 'lmb',
  'yarTier', 'yarBonusMax', 'yarRegenBonus', 'bonusSkillPoints', 'equip', 'belt', 'hp', 'yar'];
const DONE_TYPES = new Set(['hut', 'hearth', 'chest', 'body', 'stone', 'reward']);
const clone = (v) => (v === undefined ? undefined : JSON.parse(JSON.stringify(v)));
const invOut = (inv) => inv.entries.map((e) => ({ item: e.item, c: e.c, r: e.r }));
function invIn(list, w, h) { const inv = new Inventory(w, h); for (const e of list || []) inv.add(e.item, e.c, e.r); return inv; }

/** Снимок состояния игры (JSON-совместимый). */
export function snapshot(g) {
  const h = g.hero, q = g.quest, hero = {};
  for (const k of HERO_KEYS) hero[k] = clone(h[k]);
  hero.inv = clone(invOut(h.inv));
  const zones = {};
  for (const [id, st] of Object.entries(g.zoneStates || {})) {
    const ids = (st.map.objects || []).filter((o) => DONE_TYPES.has(o.type) && o.done).map((o) => o.id);
    const prev = (g.savedZoneDone || {})[id] || [];
    zones[id] = [...new Set([...prev, ...ids])];
  }
  for (const [id, ids] of Object.entries(g.savedZoneDone || {})) if (!zones[id]) zones[id] = ids;   // зоны, где в этой сессии не были
  return {
    schemaVersion: SCHEMA, savedAt: Date.now(), zone: 'ladoga',
    hero, stash: clone(invOut(g.stash)), stashSilver: g.stashSilver,
    quest: { id: q.id, flags: clone(q.flags), missionDone: !!q.missionDone, fired: [...q.fired], obj: q.obj.map((o) => ({ id: o.id, state: o.state, n: o.n, seen: o.seen ? [...o.seen] : null })) },
    shops: clone(g.shops), zones, bosses: { dead: [...(g.bossesDead || [])] }, deaths: g.deaths || 0, killsTotal: g.killsTotal || 0,
    town: g.town ? { seen: clone(g.town.seen), rumor: g.town.rumor || 0 } : null,
  };
}

export function hasSave() { try { return !!localStorage.getItem(SAVE_KEY); } catch (e) { return false; } }
export function readSave() {
  try {
    const s = localStorage.getItem(SAVE_KEY);
    if (!s) return null;
    const d = JSON.parse(s);
    return d && d.schemaVersion === SCHEMA && d.hero ? d : null;
  } catch (e) { return null; }
}
export function writeSave(g, reason) {
  try {
    const d = snapshot(g);
    localStorage.setItem(SAVE_KEY, JSON.stringify(d));
    g.lastSave = { reason, at: d.savedAt, time: g.time };
    g.counters.saves = (g.counters.saves || 0) + 1;
    return true;
  } catch (e) { g.lastSave = { reason, error: String(e) }; return false; }
}

/** Применить слот к только что сброшенной игре (g.reset({ load: true })). */
export function applySave(g, d) {
  const h = g.hero;
  for (const k of HERO_KEYS) if (d.hero[k] !== undefined && k !== 'hp' && k !== 'yar') h[k] = clone(d.hero[k]);
  h.inv = invIn(d.hero.inv, h.inv.w, h.inv.h);
  h.recalc();
  h.hp = Math.min(h.maxHp, d.hero.hp ?? h.maxHp); h.yar = Math.min(h.maxYar, d.hero.yar ?? h.maxYar);
  if (!(h.hp > 0)) h.hp = h.maxHp;
  g.stash = invIn(d.stash, g.stash.w, g.stash.h);
  g.stashSilver = d.stashSilver || 0;
  const q = g.quest, Q = d.quest || {};
  q.flags = clone(Q.flags || {});
  q.missionDone = !!Q.missionDone;
  q.fired = new Set(Q.fired || []);
  for (const so of Q.obj || []) {
    const o = q.get(so.id);
    if (!o) continue;
    o.state = so.state; o.n = so.n || 0; o.doneT = so.state === 'done' ? -1e9 : null;
    if (so.seen) o.seen = new Set(so.seen);
  }
  if (d.shops) g.shops = clone(d.shops);
  g.savedZoneDone = clone(d.zones || {});
  g.bossesDeadLoaded = new Set(((d.bosses || {}).dead || []).filter((id) => typeof id === 'string'));
  g.bossesDead = new Set(g.bossesDeadLoaded);
  g.deaths = d.deaths || 0; g.killsTotal = d.killsTotal || 0;
  if (g.town && d.town) { g.town.seen = clone(d.town.seen || {}); g.town.rumor = d.town.rumor || 0; }
  // «Громовой знак»: подобран — больше не кладётся; Кривша повержен, а знак не подобран — снова у идола (GDD §6.9 v1.10)
  try {
    if (q.flag('m1.gromovnik')) sessionStorage.setItem('byl_m1_gromovnik', 'taken');
    else if ((q.get('krivsha') || {}).state === 'done') sessionStorage.setItem('byl_m1_gromovnik', 'pending');
    else sessionStorage.removeItem('byl_m1_gromovnik');
  } catch (e) { /* */ }
  // самый большой uid вещей — чтобы новые вещи не совпали с загруженными
  let maxUid = 0;
  const scan = (it) => { if (it && typeof it.uid === 'number') maxUid = Math.max(maxUid, it.uid); };
  Object.values(h.equip).forEach(scan); h.inv.items.forEach(scan); g.stash.items.forEach(scan);
  for (const list of Object.values(g.shops || {})) if (Array.isArray(list)) list.forEach(scan);
  bumpUid(maxUid);
}

/** Сделанное в зоне по слоту: двери, огнища, сундуки, тела, путевой камень — как были (вызывается при постройке зоны). */
export function applyZoneDone(g, st) {
  const ids = new Set(((g.savedZoneDone || {})[st.id]) || []);
  if (!ids.size) return 0;
  let n = 0;
  for (const o of st.map.objects) {
    if (!ids.has(o.id) || !DONE_TYPES.has(o.type)) continue;
    o.done = true; n++;
    const p = o.prop;
    if (!p) continue;
    if (o.type === 'chest') p.open = true;
    if (o.type === 'body' || o.type === 'reward') p.taken = true;
    if (o.type === 'stone') p.awake = true;
    if (o.type === 'hearth') { p.cursed = false; p.doneAt = -99; }
    p._spr = null;
  }
  return n;
}
