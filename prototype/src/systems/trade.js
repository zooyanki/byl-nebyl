// Торг Ладоги (GDD v1.10 §6.10): цена вверх до целого, скупка 1/5 вниз (минимум 1),
// лавка раз в 10 минут реального времени и сразу при сдаче миссии.
import { MAP_SEED } from '../config.js';
import { CFG } from '../data/config.js';
import { makeRng } from '../core/rng.js';
import { BASES, POTIONS, makeItem, makePotion } from '../data/items.js';
import { pickBase } from '../data/items.js';

const SHOP_KEY = 'byl_shops_at';

export function gearPrice(it) {
  const P = CFG.trade.price;
  const t = it.type;
  const base = (t === 'neck' || t === 'ring') ? P.base.neck : (t === 'sword' || t === 'axe' || t === 'staff') ? P.base.weapon : t === 'body' ? P.base.body : P.base.other;
  const raw = base * (P.rarity[it.rarity] || 1) * (1 + (it.ilvl || 1) / 10);
  return Math.ceil(raw - 1e-9);
}
export function priceOf(it) {
  if (!it) return 0;
  if (it.kind === 'potion') return (POTIONS[it.potion] && POTIONS[it.potion].price) || 0;
  if (it.kind === 'scroll') return CFG.trade.vedana.berestaPrice;
  return gearPrice(it);
}
export function sellPrice(it) {
  return Math.max(1, Math.floor(priceOf(it) / CFG.trade.price.sellDiv));
}

function pickId(rng, level, pred) {
  const all = BASES.filter(pred);
  const types = [...new Set(all.map((b) => b.type))];
  const type = types.length === 1 ? types[0] : types[Math.floor(rng() * types.length)];
  const pool = all.filter((b) => b.type === type);
  if (pool.length === 1) return pool[0].id;
  return pickBase(type, level, rng).id;
}

function rollGear(rng, level, n, rarityOf, pred) {
  const out = [];
  for (let i = 0; i < n; i++) out.push(makeItem(pickId(rng, level, pred), rarityOf(rng), level, rng));
  return out;
}

export function rollShops(game) {
  const T = CFG.trade, L = game.hero.level, gen = game.shopGen;
  const rt = makeRng(MAP_SEED + 17 * L + 97 * gen + 13);
  const rv = makeRng(MAP_SEED + 17 * L + 97 * gen + 26);
  const tw = T.tverdyata, vd = T.vedana;
  const gearT = [];
  const groups = {
    weapon: (b) => b.type === 'sword' || b.type === 'axe',
    body: (b) => b.type === 'body', head: (b) => b.type === 'head', shield: (b) => b.type === 'shield',
    gloves: (b) => b.type === 'gloves', feet: (b) => b.type === 'feet',
  };
  for (const [k, n] of Object.entries(tw.split)) gearT.push(...rollGear(rt, L, n, (r) => r() < tw.normalPct ? 'normal' : 'magic', groups[k]));
  const gearV = [];
  const vg = {
    ring: (b) => b.type === 'ring', obereg: (b) => b.id === 'neck_1', grivna: (b) => b.id === 'neck_2', belt: (b) => b.type === 'belt',
  };
  for (const [k, n] of Object.entries(vd.split)) gearV.push(...rollGear(rv, L, n, () => 'magic', vg[k]));
  const pots = Object.entries(vd.potions).filter(([, need]) => L >= need).map(([id]) => id);
  game.shops = { tverdyata: gearT, vedana: gearV, pots, at: Date.now(), level: L };
  try { localStorage.setItem(SHOP_KEY, String(game.shops.at)); } catch (e) { /* нет хранилища */ }
}

/** Проверка при входе в Ладогу и при сдаче (force). Пока открыто окно торга — не менять. */
export function ensureShops(game, force = false) {
  if (game.town && game.town.mode === 'trade') return;
  const now = Date.now();
  let at = game.shops && game.shops.at;
  try { const s = localStorage.getItem(SHOP_KEY); if (s) at = +s; } catch (e) { /* */ }
  const due = force || !game.shops || !game.shops.tverdyata || !at || now - at >= CFG.trade.refreshMs;
  if (!due) return;
  game.shopGen = (game.shopGen || 0) + 1;
  rollShops(game);
}
