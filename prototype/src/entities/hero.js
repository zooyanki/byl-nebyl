// Герой: характеристики по GDD §3 (свойства, экипировка), команды (идти / бить / поднять), удар и каст,
// зелья, опыт, получение урона (блок, сопротивления, оглушение).
import { Actor } from './actor.js';
import {
  HERO_START, POINTS_PER_LEVEL, HERO_SPEED, MELEE_RANGE, HIT_FRAME, CAST_TIME, CAST_RELEASE, UNARMED, xpToNext, MAX_LEVEL, S as STATS,
} from '../data/progression.js';
import { serpentRank, serpentCost, serpentDamage } from '../data/skills.js';
import { POTIONS, BELT_SIZE, BELT_STACK, POTION_COOLDOWN, SLOTS, TYPE_SLOTS, STARTER_KIT, STARTER_BELT, makeItem, makePotion } from '../data/items.js';
import { Inventory } from '../systems/inventory.js';
import { PAL } from '../palette.js';

// суммарный опыт для начала уровня L
export function xpAtLevel(L) { let s = 0; for (let i = 1; i < L; i++) s += xpToNext(i); return s; }

export class Hero extends Actor {
  constructor(x, y) {
    super(x, y, 0.3);
    this.name = 'Ратибор';
    this.level = 1;
    this.xp = 0;                       // всего опыта
    this.base = { ...HERO_START };     // вложенные очки входят сюда
    this.points = 0;
    this.silver = 0;
    this.kills = 0;
    this.cmd = null;      // {type:'move'|'attack'|'pickup', ...}
    this.action = null;   // {type:'attack'|'cast', t, dur, hitAt, fired}
    this.effects = [];    // действие выпитых отваров
    this.potionCd = 0;
    this.stun = 0;        // оглушение от сильного удара
    this.invuln = 0;
    this.levelFx = 0;
    this.equip = Object.fromEntries(SLOTS.map((s) => [s, null]));
    this.inv = new Inventory();
    // GDD §4.4: на старте 3 слабых зелья жизни и 2 зелья Яри; §6.2 — стартовый комплект (скрамасакс, малый щит, шишак, кольчуга)
    this.belt = STARTER_BELT.map((b) => (b ? { ...b } : null));
    for (const k of STARTER_KIT) this.equip[k.slot] = makeItem(k.base, 'normal', 1, Math.random, k.armor != null ? { armor: k.armor } : {});
    this.recalc();
    this.hp = this.maxHp; this.yar = this.maxYar;
  }

  get xpStart() { return xpAtLevel(this.level); }
  get xpNext() { return this.level >= MAX_LEVEL ? Infinity : xpAtLevel(this.level + 1); }
  get xpNeed() { return xpToNext(this.level); }
  get xpRatio() { return this.level >= MAX_LEVEL ? 1 : (this.xp - this.xpStart) / this.xpNeed; }

  // --- характеристики: база + очки + экипировка (GDD §3.3)
  gearMods() {
    const m = { armorSum: 0 };
    for (const s of SLOTS) {
      const it = this.equip[s];
      if (!it) continue;
      for (const k in it.mods) m[k] = (m[k] || 0) + it.mods[k];
      if (it.armor) m.armorSum += it.armor;
    }
    return m;
  }
  recalc() {
    const m = this.gearMods(), g = (k) => m[k] || 0, L = this.level;
    this.mods = m;
    this.str = this.base.str + g('str'); this.dex = this.base.dex + g('dex');
    this.vit = this.base.vit + g('vit'); this.ene = this.base.ene + g('ene');
    const F = STATS, C = F.caps;
    this.maxHp = Math.floor(F.hp.base + F.hp.perVit * this.vit + F.hp.perLevel * (L - 1) + g('hp'));
    this.maxYar = Math.floor(F.yar.base + F.yar.perEne * this.ene + F.yar.perLevel * (L - 1) + g('mana'));
    this.yarRegen = (F.yarRegenPctPerSec / 100) * this.maxYar * (1 + g('regenPct') / 100);
    this.hpRegen = F.hpRegenPerSec;
    this.ar = F.ar.perDex * this.dex + F.ar.perLevel * L + g('ar');
    this.def = m.armorSum + Math.floor(this.dex / F.defDexDiv);
    this.armor = m.armorSum;
    this.crit = Math.min(F.crit.cap, F.crit.base + F.crit.perDex * this.dex + g('crit')) / 100;
    this.critMult = F.crit.mult;
    const w = this.equip.rhand;
    const wd = w ? w.dmg : [UNARMED.min, UNARMED.max], ws = w ? w.speed : UNARMED.speed;
    this.dmgMul = 1 + this.str / 100 + g('ed') / 100;
    this.dmgMin = Math.max(1, Math.floor(wd[0] * this.dmgMul));
    this.dmgMax = Math.max(this.dmgMin, Math.floor(wd[1] * this.dmgMul));
    this.fireDmg = g('fireDmg'); this.coldDmg = g('coldDmg');
    this.vsNechist = g('vsNechist') / 100;
    this.lifesteal = g('lifesteal') / 100;
    this.thorns = g('thorns');
    this.mf = g('mf');
    this.attacksPerSec = ws * (1 + Math.min(C.ias, g('ias')) / 100);
    this.attackTime = 1 / this.attacksPerSec;
    this.speed = HERO_SPEED * (1 + Math.min(C.frw, g('frw')) / 100);
    this.castTime = CAST_TIME * (1 - Math.min(C.fcr, g('fcr')) / 100);
    this.res = { fire: Math.min(C.res, g('resFire')), cold: Math.min(C.res, g('resCold')), poison: Math.min(C.res, g('resPoison')) };
    this.block = this.equip.lhand && this.equip.lhand.block ? Math.min(C.block, this.equip.lhand.block) / 100 : 0;
    this.skillRank = serpentRank(L, g('skillVed'));
    this.skillCost = serpentCost(this.skillRank);
    const [a, b] = serpentDamage(this.skillRank), sm = 1 + this.ene / 100 + g('spellPct') / 100;
    this.skillMin = Math.floor(a * sm); this.skillMax = Math.floor(b * sm);
    if (this.hp != null) { this.hp = Math.min(this.hp, this.maxHp); this.yar = Math.min(this.yar, this.maxYar); }
  }

  spendPoint(attr) {
    if (this.points <= 0 || !(attr in this.base)) return false;
    this.base[attr]++; this.points--;
    const oldMax = this.maxHp, oldY = this.maxYar;
    this.recalc();
    this.hp += Math.max(0, this.maxHp - oldMax); this.yar += Math.max(0, this.maxYar - oldY);
    return true;
  }

  // --- экипировка
  canEquip(item, slot) {
    if (!item || item.kind !== 'gear') return 'type';
    if (!TYPE_SLOTS[item.type].includes(slot)) return 'type';
    if (this.level < item.req) return 'level';
    return null;
  }
  slotFor(item) {
    const s = TYPE_SLOTS[item.type];
    if (!s) return null;
    return s.find((x) => !this.equip[x]) || s[0];
  }
  /** Надеть предмет в слот; возвращает снятый предмет (или null). Проверку canEquip делает вызывающий. */
  putOn(item, slot) {
    const old = this.equip[slot];
    this.equip[slot] = item;
    this.recalc();
    return old;
  }
  takeOff(slot) {
    const old = this.equip[slot];
    this.equip[slot] = null;
    this.recalc();
    return old;
  }

  // --- команды от контроллера
  moveTo(map, x, y) {
    if (this.cmd && this.cmd.type === 'move' && this.path && Math.hypot(this.cmd.x - x, this.cmd.y - y) < 0.15) return;
    this.cmd = { type: 'move', x, y, retries: 0 };
    this.setPath(map, x, y, true);
  }
  attack(target, stand = false) {
    if (this.cmd && this.cmd.type === 'attack' && this.cmd.target === target) { this.cmd.swung = false; this.cmd.stand = stand; return; }
    this.cmd = { type: 'attack', target, repath: 0, swung: false, repeat: false, stand };
  }
  pickup(item) { this.cmd = { type: 'pickup', item, repath: 0 }; }
  stop() { this.cmd = null; this.path = null; this.moving = false; }

  tryCast(game, tx, ty) {
    if (this.dead || this.stun > 0) return false;
    if (this.action && !(this.action.type === 'cast' && this.action.fired && this.action.t > this.action.dur * 0.85)) return false;
    if (this.yar < this.skillCost) {
      game.notify('Ярь на исходе', PAL.blue_lt, 'noyar');
      return false;
    }
    this.yar -= this.skillCost;
    this.action = { type: 'cast', tx, ty, t: 0, dur: this.castTime, hitAt: Math.min(CAST_RELEASE, this.castTime * 0.5), fired: false };
    this.face(tx - this.x, ty - this.y);
    this.path = null; this.moving = false;
    if (this.cmd && this.cmd.type !== 'attack') this.cmd = null;
    game.audio.play('skill');
    return true;
  }

  startAttack(target) {
    this.action = { type: 'attack', target, t: 0, dur: this.attackTime, hitAt: this.attackTime * HIT_FRAME, fired: false };
    this.face(target.x - this.x, target.y - this.y);
    this.path = null; this.moving = false;
  }

  // --- зелья
  drink(slot, game) {
    if (this.dead) return;
    const s = this.belt[slot];
    if (!s) { game.notify('Ячейка ' + (slot + 1) + ' пуста', PAL.mist, 'empty'); return; }
    if (this.potionCd > 0) return;
    this.applyPotion(s.kind, game);
    s.count--;
    if (s.count <= 0) {
      this.belt[slot] = null;
      this.refillBelt(slot, s.kind);
    }
  }
  applyPotion(kind, game) {
    const p = POTIONS[kind];
    this.potionCd = POTION_COOLDOWN;
    if (p.res === 'both') {
      this.hp = Math.min(this.maxHp, this.hp + this.maxHp * p.pct);
      this.yar = Math.min(this.maxYar, this.yar + this.maxYar * p.pct);
    } else {
      // зелья одного вида (жизни / Яри) не складываются: новое перезапускает таймер, прибавляя остаток
      const old = this.effects.find((e) => e.res === p.res);
      const rest = old ? old.rate * old.t : 0;
      this.effects = this.effects.filter((e) => e.res !== p.res);
      this.effects.push({ kind, res: p.res, rate: (p.amount + rest) / p.dur, t: p.dur });
    }
    const col = p.res === 'hp' ? PAL.red_lt : p.res === 'yar' ? PAL.blue_lt : PAL.bronze_hi;
    game.fx.burst(this.x, this.y, col, 12, 30);
    game.log.add('Выпито: ' + p.name, col);
    game.audio.play('potion');
  }
  // пустую ячейку пояса пополняем зельями того же вида из котомки
  refillBelt(slot, kind) {
    const fromBag = this.inv.items.filter((it) => it.kind === 'potion' && it.potion === kind);
    if (!fromBag.length) return;
    const n = Math.min(BELT_STACK, fromBag.length);
    for (let i = 0; i < n; i++) this.inv.remove(fromBag[i]);
    this.belt[slot] = { kind, count: n };
  }
  /** Подобрать зелье: сначала в пояс, потом в котомку. Возвращает 'belt' | 'bag' | null. */
  addPotion(kind) {
    for (let i = 0; i < BELT_SIZE; i++) { const s = this.belt[i]; if (s && s.kind === kind && s.count < BELT_STACK) { s.count++; return 'belt'; } }
    for (let i = 0; i < BELT_SIZE; i++) if (!this.belt[i]) { this.belt[i] = { kind, count: 1 }; return 'belt'; }
    return this.inv.autoAdd(makePotion(kind)) ? 'bag' : null;
  }

  // --- урон / опыт
  /** Урон по герою. type: 'melee' | 'fire' | 'cold' | 'poison'. Возвращает итоговый урон. */
  takeDamage(amount, game, type = 'melee', attacker = null) {
    if (this.dead || this.invuln > 0) return 0;
    if (type === 'melee' && this.block > 0 && Math.random() < this.block) {
      game.fx.text(this.x, this.y, 'Блок', PAL.bronze_lt, 50);
      game.audio.play('block');
      return 0;
    }
    let dmg = amount;
    if (type !== 'melee') dmg = dmg * (1 - (this.res[type] || 0) / 100);
    dmg = Math.max(1, Math.floor(dmg));
    this.hp -= dmg;
    this.flash = 0.12;
    game.fx.text(this.x, this.y, '-' + dmg, PAL.red_lt, 50);
    game.audio.play('hurt');
    if (attacker && this.thorns && type === 'melee') attacker.takeDamage(this.thorns, game, 'thorns', this);
    // удар > 12% макс. жизни прерывает героя на 0,2 с
    if (dmg > this.maxHp * STATS.heroStun.hpFrac && this.hp > 0) {
      this.stun = STATS.heroStun.time;
      if (this.action && !this.action.fired) this.action = null;
    }
    if (this.hp <= 0) {
      this.hp = 0;
      this.dead = true;
      this.action = null; this.cmd = null; this.path = null; this.moving = false; this.effects = [];
      game.onHeroDeath();
    }
    return dmg;
  }

  gainXp(n, game) {
    if (this.level >= MAX_LEVEL) return;
    this.xp += n;
    while (this.level < MAX_LEVEL && this.xp >= this.xpNext) {
      this.level++;
      this.points += POINTS_PER_LEVEL;
      this.recalc();
      this.hp = this.maxHp; this.yar = this.maxYar;
      this.levelFx = 1.6;
      game.onLevelUp(this);
    }
  }

  update(dt, game) {
    if (this.dead) return;
    this.flash = Math.max(0, this.flash - dt);
    this.levelFx = Math.max(0, this.levelFx - dt);
    this.potionCd = Math.max(0, this.potionCd - dt);
    this.invuln = Math.max(0, this.invuln - dt);
    this.yar = Math.min(this.maxYar, this.yar + this.yarRegen * dt);   // жизнь сама не восстанавливается (GDD §3.3)
    for (const e of this.effects) {
      const a = e.rate * Math.min(dt, e.t);
      if (e.res === 'hp') this.hp = Math.min(this.maxHp, this.hp + a);
      else this.yar = Math.min(this.maxYar, this.yar + a);
      e.t -= dt;
    }
    this.effects = this.effects.filter((e) => e.t > 0);
    if (this.updateKnock(game.map, dt)) return;
    if (this.stun > 0) { this.stun -= dt; this.moving = false; return; }

    // текущее действие (замах / каст); после выпуска снаряда остаток каста можно прервать ходьбой
    if (this.action) {
      const a = this.action;
      a.t += dt;
      if (!a.fired && a.t >= a.hitAt) {
        a.fired = true;
        if (a.type === 'attack') game.combat.heroMelee(this, a.target);
        else game.combat.castSkill(this, a.tx, a.ty);
      }
      const cancel = a.type === 'cast' && a.fired && this.cmd && this.cmd.type === 'move';
      if (a.t < a.dur && !cancel) return;
      this.action = null;
    }

    const c = this.cmd;
    if (!c) { this.moving = false; return; }
    const map = game.map;
    if (c.type === 'move') {
      if (!this.path && !this.setPath(map, c.x, c.y, true)) { this.cmd = null; this.moving = false; return; }
      if (this.followPath(map, dt, this.speed)) {
        // упёрлись в тело — пробуем обойти (не больше трёх раз)
        if (Math.hypot(c.x - this.x, c.y - this.y) > 0.4 && c.retries < 3) { c.retries++; this.setPath(map, c.x, c.y, true); }
        else { this.cmd = null; this.moving = false; }
      }
    } else if (c.type === 'attack') {
      const e = c.target;
      if (e.dead || (c.swung && !c.repeat)) { this.cmd = null; this.moving = false; return; }
      if (this.distTo(e) <= MELEE_RANGE + e.r * 0.5 || (c.stand && this.distTo(e) <= MELEE_RANGE + 0.6)) {
        c.swung = true;
        this.startAttack(e);
        return;
      }
      if (c.stand) { c.swung = true; this.startAttack(e); return; }    // Shift+ЛКМ — удар на месте
      c.repath -= dt;
      if (c.repath <= 0 || !this.path) { this.setPath(map, e.x, e.y, true, e); c.repath = 0.25; }
      this.followPath(map, dt, this.speed);
    } else if (c.type === 'pickup') {
      const it = c.item;
      if (it.taken) { this.cmd = null; this.moving = false; return; }
      if (Math.hypot(it.x - this.x, it.y - this.y) <= 0.8) {
        this.cmd = null; this.moving = false;
        game.loot.pickup(it);
        return;
      }
      c.repath -= dt;
      if (c.repath <= 0 || !this.path) { this.setPath(map, it.x, it.y, true); c.repath = 0.5; }
      if (this.followPath(map, dt, this.speed) && Math.hypot(it.x - this.x, it.y - this.y) > 0.8) {
        c.fails = (c.fails || 0) + 1;
        if (c.fails > 6) { this.cmd = null; game.notify('Не дотянуться', PAL.mist, 'reach'); }
      }
    }
  }
}
