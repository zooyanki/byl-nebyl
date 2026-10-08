// Герой: характеристики по GDD §3 (свойства, экипировка), команды (идти / бить / поднять), удар и каст,
// зелья, опыт, получение урона (блок, сопротивления, оглушение).
import { Actor } from './actor.js';
import {
  HERO_START, POINTS_PER_LEVEL, HERO_SPEED, MELEE_RANGE, HIT_FRAME, CAST_TIME, CAST_RELEASE, UNARMED, xpToNext, MAX_LEVEL, S as STATS,
} from '../data/progression.js';
import { SKILLS, RULES, DASH, rankOf, skillCost, skillNumbers, spellDamage, rankBlock, pointsFree } from '../data/skills.js';
import { circleFree, sightClear, moveWithCollision } from '../world/collision.js';
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
    this.relics = [];     // заветное (сюжетные предметы, GDD §6.11)
    this.letters = [];    // прочитанные грамоты
    this.kills = 0;
    this.cmd = null;      // {type:'move'|'attack'|'pickup', ...}
    this.action = null;   // {type:'attack'|'cast', t, dur, hitAt, fired}
    this.effects = [];    // действие выпитых зелий
    this.potionCds = { hp: 0, yar: 0 };   // GDD v1.6 §4.4: перезарядка своя у каждого вида
    this.stun = 0;        // оглушение от сильного удара
    this.invuln = 0;
    this.graceT = 0;          // «милость» после возрождения: нечисть не замечает героя (в отличие от неуязвимости рывка)
    this.levelFx = 0;
    // навыки (GDD §3.6): купленные ранги, панель F1–F6, навык на ПКМ, перезарядки, баффы
    this.skills = { ...RULES.starter };
    this.bar = [...RULES.starterBar];
    this.rmb = RULES.starterRmb;
    this.lmb = RULES.starterLmb || null;   // «Сшибка» на ЛКМ (решение дизайнера); null — обычный удар
    this.cds = {};
    this.buffs = {};
    this.dashing = null;
    this.equip = Object.fromEntries(SLOTS.map((s) => [s, null]));
    this.inv = new Inventory();
    // GDD §4.4: на старте 3 слабых зелья жизни и 2 зелья Яри; §6.2 — стартовый комплект (скрамасакс, малый щит, шишак, кольчуга)
    this.belt = STARTER_BELT.map((b) => (b ? { ...b } : null));
    for (const k of STARTER_KIT) this.equip[k.slot] = makeItem(k.base, 'normal', 1, Math.random, k.armor != null ? { armor: k.armor } : {});
    this.recalc();
    this.hp = this.maxHp; this.yar = this.maxYar;
  }

  /** Совместимость: «КД зелий» — наибольший из двух; запись ставит оба. */
  get potionCd() { return Math.max(this.potionCds.hp, this.potionCds.yar); }
  set potionCd(v) { this.potionCds.hp = v; this.potionCds.yar = v; }

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
    const stat = rankOf(this, 'stat') ? skillNumbers(this, 'stat') : null;          // «Богатырская стать»
    const vesh = rankOf(this, 'veshchee') ? skillNumbers(this, 'veshchee') : null;  // «Вещее слово»
    const chur = this.buffs && this.buffs.chur ? this.buffs.chur : null;            // «Чур-оберег»
    if (stat) this.maxHp = Math.floor(this.maxHp * (1 + stat.hpPct / 100));
    if (vesh) this.yarRegen *= 1 + vesh.regenPct / 100;
    if (chur) this.def = Math.floor(this.def * (1 + chur.defPct / 100));
    this.elemPct = vesh ? vesh.elemPct : 0;
    this.spellMul = 1 + this.ene / 100 + g('spellPct') / 100 + this.elemPct / 100;
    this.dmgMul = 1 + this.str / 100 + g('ed') / 100 + (stat ? stat.physPct / 100 : 0);
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
    const ra = chur ? chur.resAll : 0;
    this.res = { fire: Math.min(C.res, g('resFire') + ra), cold: Math.min(C.res, g('resCold') + ra), poison: Math.min(C.res, g('resPoison') + ra) };
    this.block = this.equip.lhand && this.equip.lhand.block ? Math.min(C.block, this.equip.lhand.block) / 100 : 0;
    // навык на ПКМ — для HUD и подсказок
    const rs = this.rmb && SKILLS[this.rmb] ? this.rmb : null;
    this.skillRank = rs ? rankOf(this, rs) : 0;
    this.skillCost = rs ? skillCost(this, rs) : 0;
    if (rs && SKILLS[rs].min) [this.skillMin, this.skillMax] = spellDamage(this, rs); else { this.skillMin = 0; this.skillMax = 0; }
    // «Чад» капища (GDD §4.4): за каждую ступень −10% восстановления Яри и −5% меткости (числа — kapishche.json → chad)
    if (this.chad > 0) {
      const C2 = this.chadDef || { regenPctPerStage: 10, arPctPerStage: 5 };
      this.yarRegen *= 1 - (this.chad * C2.regenPctPerStage) / 100;
      this.ar = Math.round(this.ar * (1 - (this.chad * C2.arPctPerStage) / 100));
    }
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
  /** Навык ЛКМ, если выучен. */
  /** Скорость шага с учётом замедления («Студёный» элит, GDD §5.3: −30% на 2 с). */
  curSpeed() { return this.slowT > 0 ? this.speed * (1 - (this.slowPct || 0) / 100) : this.speed; }
  lmbSkill() { return this.lmb && SKILLS[this.lmb] && rankOf(this, this.lmb) ? this.lmb : null; }
  attack(target, stand = false, skill = null, lmb = false) {
    if (this.cmd && this.cmd.type === 'attack' && this.cmd.target === target && this.cmd.skill === skill) { this.cmd.swung = false; this.cmd.stand = stand; return; }
    this.cmd = { type: 'attack', target, repath: 0, swung: false, repeat: false, stand, skill, lmb };
  }
  pickup(item) { this.cmd = { type: 'pickup', item, repath: 0 }; }
  /** Подойти к объекту зоны (дверь избы, сундук, тело) и взаимодействовать; hold — держать ЛКМ (GDD §8.2). */
  interact(obj) {
    if (this.cmd && this.cmd.type === 'interact' && this.cmd.obj === obj && !this.cmd.started) return;
    this.cmd = { type: 'interact', obj, repath: 0, fails: 0, holdT: 0, started: false };
  }
  stop() { this.cmd = null; this.path = null; this.moving = false; }

  // --- навыки
  get skillPoints() { return pointsFree(this); }
  /** Купить ранг навыка (окно «Навыки»). Новый активный навык встаёт в свободную ячейку F1–F6. */
  learn(id, game) {
    const why = rankBlock(this, id);
    if (why) return why;
    const first = !this.skills[id];
    this.skills[id] = (this.skills[id] || 0) + 1;
    const sk = SKILLS[id];
    if (first && sk.type !== 'passive') {
      if (!this.bar.includes(id)) { const k = this.bar.indexOf(null); if (k >= 0) this.bar[k] = id; }
    }
    const oldMax = this.maxHp;
    this.recalc();
    this.hp += Math.max(0, this.maxHp - oldMax);
    return null;
  }
  setRmb(id) { if (!id || !SKILLS[id] || !rankOf(this, id) || SKILLS[id].type === 'passive') return false; this.rmb = id; this.recalc(); return true; }
  cdLeft(id) { return this.cds[id] || 0; }

  /** Применить навык. Возвращает 'ok' | 'busy' | 'yar' | 'cd' | 'none' | 'stun' | 'dead'. */
  useSkill(game, id, tx, ty, target = null) {
    if (this.dead) return 'dead';
    if (this.stun > 0 || this.dashing) return 'busy';
    const sk = SKILLS[id];
    if (!sk || !rankOf(this, id) || sk.type === 'passive') return 'none';
    if (this.action && !(this.action.type === 'cast' && this.action.fired && this.action.t > this.action.dur * 0.85)) return 'busy';
    if (this.cdLeft(id) > 0) return 'cd';            // перезарядка видна сектором и цифрой на ячейке (GDD §12.2.1: без текста)
    const cost = skillCost(this, id);
    if (this.yar < cost) { game.notify(game.t('ui.error.no_yar'), PAL.blue_lt, 'noyar'); return 'yar'; }
    if (sk.type === 'melee') {
      // «Сшибка»: по врагу — подойти и ударить; по земле — удар на месте в сторону курсора
      if (target) { this.attack(target, false, id); return 'ok'; }
      this.yar -= cost;
      this.face(tx - this.x, ty - this.y);
      this.action = { type: 'attack', skill: id, target: null, t: 0, dur: this.attackTime, hitAt: this.attackTime * HIT_FRAME, fired: false };
      this.path = null; this.moving = false; this.cmd = null;
      return 'ok';
    }
    if (sk.type === 'teleport') {
      // GDD v1.7 §3.6 (B-22): по врагу — приземление перед целью на расстоянии r героя + r врага
      if (target && !target.dead) {
        const dx = this.x - target.x, dy = this.y - target.y, d = Math.hypot(dx, dy) || 1, k = (this.r + target.r + 0.001) / d;
        if (d > this.r + target.r + 0.3) { tx = target.x + dx * k; ty = target.y + dy * k; }
      }
      const dest = this.teleportPoint(game.map, tx, ty, skillNumbers(this, id).range, game.enemies);
      if (!dest) return 'none';
      tx = dest[0]; ty = dest[1];
    }
    this.yar -= cost;
    const ct = sk.castTime ? sk.castTime * (this.castTime / CAST_TIME) : this.castTime;
    this.action = { type: 'cast', skill: id, tx, ty, t: 0, dur: ct, hitAt: Math.min(CAST_RELEASE, ct * 0.5), fired: false };
    if (sk.cd) this.cds[id] = sk.cd;
    this.face(tx - this.x, ty - this.y);
    this.path = null; this.moving = false;
    if (this.cmd && this.cmd.type !== 'attack') this.cmd = null;
    game.audio.play('skill');
    game.counters.casts[id] = (game.counters.casts[id] || 0) + 1;
    return 'ok';
  }
  // совместимость: ПКМ текущим навыком
  tryCast(game, tx, ty, target = null) { return this.useSkill(game, this.rmb, tx, ty, target) === 'ok'; }

  /** «Перунов скок»: видимая проходимая точка не дальше range; если курсор дальше или в стене — ближайшая годная по линии. */
  teleportPoint(map, tx, ty, range, bodies = []) {
    let dx = tx - this.x, dy = ty - this.y, d = Math.hypot(dx, dy);
    if (d < 0.3) return null;
    if (d > range) { dx *= range / d; dy *= range / d; d = range; }
    // QA B-22: и не внутрь тел — по врагу приземляемся у края его тела (шаг по линии 0,05 тайла)
    const clearOfBodies = (x, y) => bodies.every((e) => e.dead || Math.hypot(e.x - x, e.y - y) >= this.r + e.r);
    const steps = Math.ceil(d / 0.05);
    for (let i = steps; i >= Math.max(1, Math.floor(steps * 0.1)); i--) {
      const k = i / steps, x = this.x + dx * k, y = this.y + dy * k;
      if (circleFree(map, x, y, this.r) && clearOfBodies(x, y) && sightClear(map, this.x, this.y, x, y) && map.isReachableAt(x, y)) return [x, y];
    }
    return null;
  }

  /** Рывок (Пробел): 3 тайла за 0,2 с, неуязвимость 0,15 с, КД 4 с, Яри не стоит, сквозь стены не проходит. */
  dash(game, tx, ty) {
    if (this.dead || this.stun > 0 || this.dashing) return 'busy';
    if (this.action && !this.action.fired) return 'busy';
    if (this.cdLeft('dash') > 0) return 'cd';
    let dx = tx - this.x, dy = ty - this.y, d = Math.hypot(dx, dy);
    if (d < 0.05) { [dx, dy] = this.dirVec(); d = 1; }
    this.face(dx, dy);
    this.action = null; this.cmd = null; this.path = null;
    this.dashing = { vx: (dx / d) * DASH.dist / DASH.time, vy: (dy / d) * DASH.dist / DASH.time, t: DASH.time, x0: this.x, y0: this.y };
    this.invuln = Math.max(this.invuln, DASH.invuln);
    this.cds.dash = DASH.cd;
    game.audio.play('dash');
    game.counters.casts.dash = (game.counters.casts.dash || 0) + 1;
    return 'ok';
  }

  startAttack(target, skill = null, game = null) {
    if (skill) {            // «Сшибка» платит Ярь в начале замаха
      const cost = skillCost(this, skill);
      if (this.yar < cost && this.cmd && this.cmd.lmb) {
        skill = null;                                   // ЛКМ без Яри — обычный удар (решение дизайнера)
        if (game) game.counters.lmbFallback = (game.counters.lmbFallback || 0) + 1;
      } else if (this.yar < cost) { if (game) game.notify(game.t('ui.error.no_yar'), PAL.blue_lt, 'noyar'); this.cmd = null; return; }
      else {
        this.yar -= cost;
        if (game) { game.audio.play('skill'); game.counters.casts[skill] = (game.counters.casts[skill] || 0) + 1; }
      }
    }
    this.action = { type: 'attack', skill, target, t: 0, dur: this.attackTime, hitAt: this.attackTime * HIT_FRAME, fired: false };
    this.face(target.x - this.x, target.y - this.y);
    this.path = null; this.moving = false;
  }

  // --- зелья
  drink(slot, game) {
    if (this.dead) return;
    const s = this.belt[slot];
    if (!s) { game.notify('Ячейка ' + (slot + 1) + ' пуста', PAL.mist, 'empty'); return; }
    if (!this.canDrink(s.kind, game)) return;
    this.applyPotion(s.kind, game);
    s.count--;
    if (s.count <= 0) {
      this.belt[slot] = null;
      this.refillBelt(slot, s.kind);
    }
  }
  /** Можно ли выпить зелье сейчас: КД своего вида (с пояса и из котомки — QA B-15, GDD v1.6 §4.4) и полная шкала (QA B-04). */
  canDrink(kind, game) {
    if (this.dead) return false;
    const p = POTIONS[kind];
    // живая вода — мгновенно и вне перезарядки; зелья жизни и Яри — каждое со своей перезарядкой 1 с
    if (p.res !== 'both' && this.potionCds[p.res] > 0) { game.counters.potionCdBlocked = (game.counters.potionCdBlocked || 0) + 1; return false; }
    const hpFull = this.hp >= this.maxHp, yarFull = this.yar >= this.maxYar;
    if ((p.res === 'hp' && hpFull) || (p.res === 'yar' && yarFull) || (p.res === 'both' && hpFull && yarFull)) {
      game.notify(p.res === 'yar' ? 'Ярь и так полна' : 'Жизнь и так полна', PAL.mist, 'full_' + p.res);
      return false;
    }
    return true;
  }
  /** Пустые ячейки пояса добираются зельями из котомки (QA B-05: и если ячейка опустела раньше, чем зелья появились). */
  fillBelt() {
    for (let i = 0; i < BELT_SIZE; i++) if (!this.belt[i] && this.inv.items.some((it) => it.kind === 'potion')) this.refillBelt(i, null);
  }
  applyPotion(kind, game) {
    const p = POTIONS[kind];
    if (p.res !== 'both') this.potionCds[p.res] = POTION_COOLDOWN;
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
    // сначала зелья того же вида, иначе — любого (QA B-05)
    let fromBag = this.inv.items.filter((it) => it.kind === 'potion' && it.potion === kind);
    if (!fromBag.length) { const any = this.inv.items.find((it) => it.kind === 'potion'); if (any) fromBag = this.inv.items.filter((it) => it.kind === 'potion' && it.potion === any.potion); }
    if (!fromBag.length) return;
    kind = fromBag[0].potion;
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
    if (dmg > 0) this.sinceHurt = 0;          // отдых в тихом круге — только после 2 с без урона (GDD v1.7 §4.5)
    this.flash = 0.12;
    game.fx.text(this.x, this.y, '-' + dmg, PAL.red_lt, 50);
    // урон прерывает удержание (выбить дверь, GDD §8.2)
    if (this.cmd && this.cmd.type === 'interact' && this.cmd.started && this.cmd.obj.hold) {
      this.cmd = null;
      game.notify(game.t('ui.obj.interrupted'), PAL.red_lt, 'interrupt');
      game.counters.holdInterrupted = (game.counters.holdInterrupted || 0) + 1;
    }
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
      if (this.buffs.chur) { this.buffs = {}; this.recalc(); }   // QA B-24: бафф снимается в момент гибели (как в D2)
      this.cds = {};
      game.onHeroDeath();
    }
    return dmg;
  }

  gainXp(n, game) {
    if (this.dead || this.level >= MAX_LEVEL) return;      // посмертно опыт не идёт (QA B-03)
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
    this.potionCds.hp = Math.max(0, this.potionCds.hp - dt); this.potionCds.yar = Math.max(0, this.potionCds.yar - dt);
    this.beltT = (this.beltT || 0) - dt;
    if (this.beltT <= 0) { this.beltT = 0.25; if (this.belt.includes(null)) this.fillBelt(); }
    this.invuln = Math.max(0, this.invuln - dt);
    // GDD v1.7 (ответ дизайнера 08.10): неуязвимость возрождения (2 с) снимается раньше, если герой атакует или кастует
    if (this.respawnProt) {
      if (this.invuln <= 0) this.respawnProt = false;
      else if (this.action && (this.action.type === 'attack' || this.action.type === 'cast')) {
        this.invuln = 0; this.graceT = 0; this.respawnProt = false;
        game.counters.respawnInvulnBroken = (game.counters.respawnInvulnBroken || 0) + 1;
      }
    }
    if (this.graceT > 0) this.graceT = Math.max(0, this.graceT - dt);
    if (this.slowT > 0) this.slowT = Math.max(0, this.slowT - dt);
    this.sinceHurt = (this.sinceHurt ?? 99) + dt;
    for (const k in this.cds) this.cds[k] = Math.max(0, this.cds[k] - dt);
    if (this.buffs.chur) { this.buffs.chur.t -= dt; if (this.buffs.chur.t <= 0) { delete this.buffs.chur; this.recalc(); } }
    this.yar = Math.min(this.maxYar, this.yar + this.yarRegen * dt);   // жизнь сама не восстанавливается (GDD §3.3)
    for (const e of this.effects) {
      const a = e.rate * Math.min(dt, e.t);
      if (e.res === 'hp') this.hp = Math.min(this.maxHp, this.hp + a);
      else this.yar = Math.min(this.maxYar, this.yar + a);
      e.t -= dt;
    }
    this.effects = this.effects.filter((e) => e.t > 0);
    if (this.dashing) {
      const D = this.dashing, st = Math.min(dt, D.t);
      moveWithCollision(game.map, this, D.vx * st, D.vy * st);
      this.moving = true; this.walkPhase += st * 20;
      if (Math.random() < 0.8) game.fx.parts.push({ x: this.x, y: this.y, ox: 0, oy: -20, vx: 0, vy: 0, g: 0, t: 0, dur: 0.25, color: PAL.mist, size: 2 });
      D.t -= dt;
      if (D.t <= 0) { this.dashing = null; this.moving = false; }
      return;
    }
    if (this.updateKnock(game.map, dt)) return;
    if (this.stun > 0) { this.stun -= dt; this.moving = false; return; }

    // текущее действие (замах / каст); после выпуска снаряда остаток каста можно прервать ходьбой
    if (this.action) {
      const a = this.action;
      a.t += dt;
      if (!a.fired && a.t >= a.hitAt) {
        a.fired = true;
        if (a.type === 'attack') game.combat.heroMelee(this, a.target, a.skill);
        else game.combat.release(this, a.skill, a.tx, a.ty);
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
      if (this.followPath(map, dt, this.curSpeed())) {
        // упёрлись в тело — пробуем обойти (не больше трёх раз)
        if (Math.hypot(c.x - this.x, c.y - this.y) > 0.4 && c.retries < 3) { c.retries++; this.setPath(map, c.x, c.y, true); }
        else { this.cmd = null; this.moving = false; }
      }
    } else if (c.type === 'attack') {
      const e = c.target;
      if (e.dead || (c.swung && !c.repeat)) { this.cmd = null; this.moving = false; return; }
      if (this.distTo(e) <= MELEE_RANGE + e.r * 0.5 || (c.stand && this.distTo(e) <= MELEE_RANGE + 0.6)) {
        c.swung = true;
        this.startAttack(e, c.skill, game);
        return;
      }
      if (c.stand) { c.swung = true; this.startAttack(e, c.skill, game); return; }    // Shift+ЛКМ — удар на месте
      c.repath -= dt;
      if (c.repath <= 0 || !this.path) { this.setPath(map, e.x, e.y, true, e); c.repath = 0.25; }
      this.followPath(map, dt, this.curSpeed());
    } else if (c.type === 'interact') {
      const o = c.obj;
      if (o.done) { this.cmd = null; this.moving = false; return; }
      if (Math.hypot(o.x - this.x, o.y - this.y) <= o.reach) {
        this.path = null; this.moving = false;
        this.face(o.x - this.x, o.y - this.y);
        if (!c.started) {
          const err = game.canInteract(o);
          if (err) { this.cmd = null; game.notify(game.t(err), PAL.mist, 'interact'); game.audio.play('error'); return; }
          c.started = true;
          if (!o.hold) { this.cmd = null; game.interact(o); return; }
        }
        if (!game.holdingInteract()) { this.cmd = null; return; }     // отпустили ЛКМ — удержание сброшено
        c.holdT += dt;
        if (c.holdT >= o.hold) { this.cmd = null; game.interact(o); }
        return;
      }
      c.repath -= dt;
      if (c.repath <= 0 || !this.path) { this.setPath(map, o.sx, o.sy, true); c.repath = 0.5; }
      if (this.followPath(map, dt, this.curSpeed()) && Math.hypot(o.x - this.x, o.y - this.y) > o.reach) {
        c.fails++;
        if (c.fails > 6) { this.cmd = null; game.notify('Не дотянуться', PAL.mist, 'reach'); }
      }
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
      if (this.followPath(map, dt, this.curSpeed()) && Math.hypot(it.x - this.x, it.y - this.y) > 0.8) {
        c.fails = (c.fails || 0) + 1;
        if (c.fails > 6) { this.cmd = null; game.notify('Не дотянуться', PAL.mist, 'reach'); }
      }
    }
  }
}
