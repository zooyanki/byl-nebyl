// Добыча (GDD §6.6–6.7): выпадение с нечисти, предметы на земле, подбор щелчком в котомку,
// серебро подбирается само в радиусе 1 тайла.
import { rnd } from '../core/math.js';
import { circleFree } from '../world/collision.js';
import { POTIONS, SCROLLS, DROP_NORMAL, POTION_WEIGHTS, RARITY, pickWeighted, rollItem, silverAmount, potionFor, dropTable, makeScroll } from '../data/items.js';
import { silverText } from '../core/i18n.js';
import { PAL } from '../palette.js';

export function itemColor(item) {
  if (item.kind === 'potion' || item.kind === 'scroll') return PAL.birch;
  return PAL[RARITY[item.rarity].color];
}

export class Loot {
  constructor(game) { this.game = game; this.items = []; }

  spawn(x, y, data) {
    let px = x, py = y;
    for (let i = 0; i < 14; i++) {
      const a = rnd(0, Math.PI * 2), r = rnd(0.3, 1.1);
      const tx = x + Math.cos(a) * r, ty = y + Math.sin(a) * r;
      if (circleFree(this.game.map, tx, ty, 0.2) && this.game.map.isReachableAt(tx, ty)) { px = tx; py = ty; break; }   // QA B-12
    }
    const it = { ...data, x: px, y: py, fromX: x, fromY: y, dropT: 0, taken: false };
    this.items.push(it);
    return it;
  }
  spawnSilver(x, y, amount) { return this.spawn(x, y, { kind: 'silver', amount, label: silverText(amount, 'ground'), color: PAL.linen }); }   // «86 сер.» (GDD §10.1)
  spawnItem(x, y, item) {
    if (item.kind === 'potion') return this.spawn(x, y, { kind: 'potion', potion: item.potion, item, label: POTIONS[item.potion].name, color: PAL.birch });
    if (item.kind === 'scroll') return this.spawnScroll(x, y, item.scroll, item.count);
    return this.spawn(x, y, { kind: 'item', item, label: item.name, color: itemColor(item) });
  }

  spawnScroll(x, y, kind = 'beresta', count = 1) {
    return this.spawn(x, y, { kind: 'scroll', scroll: kind, count, label: SCROLLS[kind].name + (count > 1 ? ' ×' + count : ''), color: PAL.birch });
  }
  /** Класс «зелье/береста» (GDD §6.7: жизни 55, Яри 30, живая вода 10, береста 5). */
  spawnPotionRoll(x, y, mlvl) {
    const type = pickWeighted(POTION_WEIGHTS);
    if (type === 'beresta') { this.game.counters.berestaDrops = (this.game.counters.berestaDrops || 0) + 1; return this.spawnScroll(x, y, 'beresta', 1); }
    const pk = potionFor(type, mlvl);
    return this.spawn(x, y, { kind: 'potion', potion: pk, label: POTIONS[pk].name, color: PAL.birch });
  }

  dropFrom(enemy) {
    if (enemy.dropTable) return this.dropElite(enemy);
    const what = pickWeighted(DROP_NORMAL);
    if (what === 'silver') this.spawnSilver(enemy.x, enemy.y, silverAmount(enemy.mlvl));
    else if (what === 'potion') this.spawnPotionRoll(enemy.x, enemy.y, enemy.mlvl);
    else if (what === 'item') this.spawnItem(enemy.x, enemy.y, rollItem(enemy.mlvl, Math.random, this.game.hero.mf));
  }

  /** Сундук (GDD §6.7): сначала гарантированные предметы (сюжетный сундук тропы — заговорённое оружие ilvl 3),
   *  остальные броски — по таблице сундука (исходы и редкость из data/droptables.json). */
  dropChest(tableId, x, y, ilvl) {
    const T = dropTable(tableId), out = [];
    if (!T) return out;
    let rolls = T.rolls || 1;
    for (const gi of T.guaranteed || []) {
      out.push(this.spawnItem(x, y, rollItem(gi.ilvl || ilvl, Math.random, 0, { type: gi.type, forceRarity: gi.rarity })));
      rolls--;
    }
    for (let i = 0; i < rolls; i++) {
      const what = pickWeighted(T.outcome);
      if (what === 'silver') out.push(this.spawnSilver(x, y, silverAmount(ilvl)));
      else if (what === 'potion') out.push(this.spawnPotionRoll(x, y, ilvl));
      else if (what === 'item') out.push(this.spawnItem(x, y, rollItem(ilvl, Math.random, this.game.hero.mf, { rarity: T.rarity })));
    }
    return out;
  }

  /** Элиты, былинные враги и боссы (GDD §5.3–5.4, §6.7): броски по таблице, затем гарантии — extraMagic (вожак: +1 заговорённый),
   *  magicMin (≥ N заговорённых: простые повышаются, не хватает — добавляются), firstKillRarePct (первое убийство — дивный). */
  dropElite(e) {
    const T = dropTable(e.dropTable), g = this.game, out = [];
    if (!T) return out;
    const plan = [];
    for (let i = 0; i < (T.rolls || 1); i++) {
      const what = pickWeighted(T.outcome);
      if (what === 'item') { const w = { ...T.rarity }, mf = g.hero.mf, k = 0.5; if (mf) { w.magic += mf * k; w.rare += mf * k; w.unique += mf * k; } plan.push(pickWeighted(w)); }
      else if (what !== 'none') plan.push(what);
    }
    for (let i = 0; i < (T.extraMagic || 0); i++) plan.push('magic');
    const isItem = (r) => r === 'normal' || r === 'magic' || r === 'rare' || r === 'unique';
    if (T.magicMin) {
      let have = plan.filter((r) => isItem(r) && r !== 'normal').length;
      for (let i = 0; i < plan.length && have < T.magicMin; i++) if (plan[i] === 'normal') { plan[i] = 'magic'; have++; }
      while (have < T.magicMin) { plan.push('magic'); have++; }
    }
    const first = !(g.firstKills || (g.firstKills = {}))[e.kind];
    g.firstKills[e.kind] = true;
    if (T.firstKillRarePct && first && Math.random() * 100 < T.firstKillRarePct && !plan.some((r) => r === 'rare' || r === 'unique')) {
      const j = plan.findIndex((r) => r === 'magic');
      if (j >= 0 && T.magicMin && plan.filter((r) => r === 'magic').length > T.magicMin) plan[j] = 'rare'; else plan.push('rare');
    }
    for (const r of plan) {
      if (r === 'silver') out.push(this.spawnSilver(e.x, e.y, silverAmount(e.mlvl)));
      else if (r === 'potion') out.push(this.spawnPotionRoll(e.x, e.y, e.mlvl));
      else out.push(this.spawnItem(e.x, e.y, rollItem(e.mlvl, Math.random, 0, { forceRarity: r })));
    }
    e.drops = out;
    g.counters.eliteDrops = (g.counters.eliteDrops || 0) + 1;
    return out;
  }

  pickup(it) {
    if (it.taken) return false;
    const g = this.game, h = g.hero;
    if (it.kind === 'silver') {
      h.silver += it.amount;
      g.log.add(silverText(it.amount, 'pickup'), PAL.linen);
      g.audio.play('silver');
    } else if (it.kind === 'potion') {
      const where = h.addPotion(it.potion);
      if (!where) { g.notify('Некуда положить', PAL.red_lt, 'full'); g.audio.play('error'); return false; }
      g.log.add('Подобрано: ' + it.label + (where === 'belt' ? ' (пояс)' : ' (котомка)'), PAL.birch);
      g.audio.play('pickup');
    } else if (it.kind === 'scroll') {        // береста — в котомку стопкой до 20 (GDD §6.9; в пояс — только зелья)
      const left = h.addScroll(it.scroll, it.count || 1);
      if (left >= (it.count || 1)) { g.notify('Некуда положить', PAL.red_lt, 'full'); g.audio.play('error'); return false; }
      if (left > 0) { it.count = left; it.label = SCROLLS[it.scroll].name + (left > 1 ? ' ×' + left : ''); g.log.add('Подобрано: ' + SCROLLS[it.scroll].name, PAL.birch); g.audio.play('pickup'); return false; }
      g.log.add('Подобрано: ' + it.label + ' (котомка)', PAL.birch);
      g.audio.play('pickup');
    } else {
      if (!h.inv.autoAdd(it.item)) { g.notify('Некуда положить', PAL.red_lt, 'full'); g.audio.play('error'); return false; }
      g.log.add('Подобрано: ' + it.label, it.color);
      g.audio.play('pickup');
      if (it.item.rarity === 'unique') { g.counters.bylinaPicked = (g.counters.bylinaPicked || 0) + 1; g.notify(g.t('proto.bylina.got', { item: it.item.name }), PAL.bronze_lt, 'relic'); }
    }
    it.taken = true;
    g.fx.burst(it.x, it.y, PAL.bronze_hi, 6, 4, 30);
    this.items = this.items.filter((i) => !i.taken);
    return true;
  }

  update(dt) {
    const h = this.game.hero;
    for (const it of this.items) {
      it.dropT += dt;
      if (it.kind === 'silver' && !h.dead && it.dropT > 0.35 && Math.hypot(it.x - h.x, it.y - h.y) <= 1.0) this.pickup(it);
    }
  }
}
