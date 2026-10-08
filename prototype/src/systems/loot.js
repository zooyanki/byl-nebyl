// Добыча (GDD §6.6–6.7): выпадение с нечисти, предметы на земле, подбор щелчком в котомку,
// серебро подбирается само в радиусе 1 тайла.
import { rnd } from '../core/math.js';
import { circleFree } from '../world/collision.js';
import { POTIONS, DROP_NORMAL, POTION_WEIGHTS, RARITY, pickWeighted, rollItem, silverAmount, potionFor } from '../data/items.js';
import { silverText } from '../core/i18n.js';
import { PAL } from '../palette.js';

export function itemColor(item) {
  if (item.kind === 'potion') return PAL.birch;
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
    return this.spawn(x, y, { kind: 'item', item, label: item.name, color: itemColor(item) });
  }

  dropFrom(enemy) {
    const what = pickWeighted(DROP_NORMAL);
    if (what === 'silver') this.spawnSilver(enemy.x, enemy.y, silverAmount(enemy.mlvl));
    else if (what === 'potion') {
      let type = pickWeighted(POTION_WEIGHTS);
      if (type === 'beresta') type = 'life';       // береста возврата — в следующих итерациях
      const pk = potionFor(type, enemy.mlvl);
      this.spawn(enemy.x, enemy.y, { kind: 'potion', potion: pk, label: POTIONS[pk].name, color: PAL.birch });
    } else if (what === 'item') this.spawnItem(enemy.x, enemy.y, rollItem(enemy.mlvl, Math.random, this.game.hero.mf));
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
    } else {
      if (!h.inv.autoAdd(it.item)) { g.notify('Некуда положить', PAL.red_lt, 'full'); g.audio.play('error'); return false; }
      g.log.add('Подобрано: ' + it.label, it.color);
      g.audio.play('pickup');
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
