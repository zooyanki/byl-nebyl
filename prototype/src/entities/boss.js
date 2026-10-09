// Былинный враг М1 «Мара Пепельная» и босс «Кривша, Обгорелый страж» (GDD v1.7 §5.3–5.4, act1.md, act1_texts §6–7).
// Числа — data/bosses.json (заглушки помечены _ph). Мара — враг на общем ИИ (как волхв-прислужник: огонь издали,
// отход, лечение союзника; без воскрешения) + обход по кругу, пепельный след и свита анчуток. Кривша — свой ИИ:
// подъём из пламени идола, удар когтями (конус, телеграф), огненный след, подъём упырей, прыжок в неосвящённое огнище
// на 50% HP (2 с неуязвим, огненный ореол, сопр. огню +25%, +25% скорости атаки), возврат к идолу при гибели героя.
import { Enemy } from './enemy.js';
import { hitChance } from '../data/progression.js';
import { CFG } from '../data/config.js';
import { RU, t } from '../core/i18n.js';
import { PAL } from '../palette.js';
import { makeElite } from '../systems/elites.js';
import { circleFree, lineWalkable } from '../world/collision.js';

/** Реплика врага по ключу act1_texts (поле «Текст»): над головой и в журнал. */
export function enemyBark(game, e, key) {
  const b = RU[key], text = b && typeof b === 'object' ? b['Текст'] : null;
  if (!text) return;
  if (game.bark(e, key, text)) game.log.add(e.name + ': ' + text, PAL.red_lt);
}

// --- Мара Пепельная
export function spawnMara(game, rng) {
  const B = CFG.bosses.mara, R = B.route, m = game.map;
  const pts = [];
  for (let i = 0; i < R.points; i++) { const a = (i / R.points) * Math.PI * 2; pts.push([R.center[0] + Math.cos(a) * R.radius, R.center[1] + Math.sin(a) * R.radius]); }
  const ok = pts.filter(([x, y]) => circleFree(m, x, y, B.r + 0.05) && m.isReachableAt(x, y) && !game.safeAt(x, y, 1));
  if (!ok.length) return null;
  const [sx, sy] = ok[0];
  const mara = new Enemy('mara', sx, sy, 'mara', B.mlvl);
  makeElite(mara, 'bylina', { mods: B.mods });
  mara.name = B.name; mara.fem = true; mara.special = 'mara';
  mara.route = { pts: ok, i: 0, speedMul: R.speedMul };
  mara.tick = maraTick; mara.healT = 0; mara.ashT = 0;
  const anchor = { x: R.center[0], y: R.center[1], r: R.leash ?? 8 };   // v1.8.1: поводок 8 тайлов от центра круга (Мара и свита)
  mara.anchor = anchor;
  game.enemies.push(mara);
  const n = rng.int(B.retinue.count[0], B.retinue.count[1]);
  for (let i = 0; i < n; i++) {
    for (let k = 0; k < 8; k++) {
      const a = ((i + k * 0.37) / n) * Math.PI * 2, x = sx + Math.cos(a) * 1.3, y = sy + Math.sin(a) * 1.3;
      if (!circleFree(m, x, y, 0.3) || !m.isReachableAt(x, y)) continue;
      const e = new Enemy(B.retinue.kind, x, y, 'mara', B.retinue.mlvl);
      e.follow = mara; e.followOff = [Math.cos(a) * 1.3, Math.sin(a) * 1.3]; e.special = 'mara'; e.anchor = anchor;
      game.enemies.push(e);
      break;
    }
  }
  return mara;
}

function maraTick(e, dt, game) {
  const B = e.def;
  if ((e.state === 'chase' || e.state === 'attack') && !e.barked) { e.barked = true; enemyBark(game, e, B.barks.aggro); }
  // пепельный след: земля под ней горит 3 с (8% макс. HP героя в секунду), новое пятно — если под ней своего нет
  e.ashT += dt;
  const A = B.ashTrail;
  if (e.ashT >= A.every) {
    e.ashT = 0;
    if (!game.combat.fires.some((f) => f.src === e && f.litT < A.burn - A.every && Math.hypot(f.x - e.x, f.y - e.y) < A.r * 0.8)) game.combat.addPatch(e, e.x, e.y, A);
  }
  // лечение союзника (как у волхва-прислужника): раз в 8 с на 15% его макс. HP — самого раненого в радиусе 6
  e.healT += dt;
  const H = B.heal;
  if (e.healAnim != null) { e.healAnim += dt; if (e.healAnim >= 0.6) e.healAnim = null; }   // анимация лечения (косметика, спрайт M1b)
  if (e.healT >= H.every - 0.3) {
    let best = null;
    for (const o of game.enemies) if (!o.dead && o !== e && o.pack === e.pack && o.hp < o.maxHp && Math.hypot(o.x - e.x, o.y - e.y) <= H.radius && (!best || o.hp / o.maxHp < best.hp / best.maxHp)) best = o;
    if (best && e.healT < H.every) { if (e.healAnim == null) e.healAnim = e.healT - (H.every - 0.3); }   // за 0,3 с: кадр 3 (apply_frame) = лечение
    else if (best) {
      e.healT = 0; e.healAnim = 0.3;
      const v = Math.max(1, Math.round(best.maxHp * H.pct / 100));
      best.hp = Math.min(best.maxHp, best.hp + v);
      game.fx.text(best.x, best.y, '+' + v, PAL.nebyl, best.def.height + 6, { dur: 0.8 });
      game.fx.burst(best.x, best.y, PAL.nebyl, 6, best.def.height * 0.5, 30);
      game.counters.maraHeals = (game.counters.maraHeals || 0) + 1;
    }
  }
}

// --- Кривша
export class Krivsha extends Enemy {
  constructor(x, y) {
    const B = CFG.bosses.krivsha;
    super('krivsha', x, y, 'krivsha', B.mlvl);
    this.B = B; this.boss = true; this.elite = 'boss'; this.name = B.name; this.dropTable = B.drop;
    this.homeX = x; this.homeY = y;
    this.state = 'rise'; this.t = 0; this.invuln = B.rise;
    this.phase = 1; this.phaseDone = false; this.aura = false; this.atkMul = 1;
    this.summonT = B.summon.first; this.minions = []; this.summonBarked = false;
    this.trailT = 0; this.cycleT = 0; this.auraT = 0; this.fightT = 0;
  }

  takeDamage(amount, game, type = 'melee', src = null, opts = {}) {
    const d = super.takeDamage(amount, game, type, src, { ...opts, kbDir: null, kb: 0 });
    if (!this.dead && this.state === 'idle' && src === game.hero) this.engage(game);
    return d;
  }
  aggro(game) { if (this.state === 'idle' || this.state === 'return') this.engage(game); }
  engage(game) { this.state = 'fight'; this.t = 0; this.path = null; }

  update(dt, game) {
    this.flash = Math.max(0, this.flash - dt);
    this.lastHitT += dt; this.age += dt;
    if (this.dead) { this.corpseT += dt; return; }
    const B = this.B, h = game.hero, map = game.map;
    this.invuln = Math.max(0, this.invuln - dt);
    this.t += dt;
    const px = this.x, py = this.y;
    const present = !h.dead && !(h.graceT > 0);
    if (this.state !== 'rise' && this.state !== 'idle' && this.state !== 'return') this.fightT += dt;
    switch (this.state) {
      case 'rise':
        this.moving = false;
        if (this.t >= B.rise) { this.state = 'fight'; this.t = 0; enemyBark(game, this, B.barks.rise); }
        break;
      case 'idle':
        this.moving = false;
        if (present && Math.hypot(h.x - this.homeX, h.y - this.homeY) < game.map.arena.half) this.engage(game);
        break;
      case 'return': {
        if (!this.path) this.setPath(map, this.homeX, this.homeY, true);
        const done = this.followPath(map, dt, this.speed);
        if (done || Math.hypot(this.x - this.homeX, this.y - this.homeY) < 0.8) {
          if (this.leashed) { this.leashed = false; this.state = 'idle'; this.t = 0; this.path = null; this.moving = false; }   // уже сброшен поводком
          else this.reset(game);
        }
        break;
      }
      case 'fight': {
        if (!present) { this.state = 'return'; this.path = null; break; }
        // GDD v1.9 §4.4/§8.2 (журнал п.4): поводок пешком — герой дальше arena.leashWalk (25) от идола: сброс сразу
        const LW = B.arena && B.arena.leashWalk, I = map[(B.arena && B.arena.lockAt) || 'idol'];
        if (LW && I && Math.hypot(h.x - I.x, h.y - I.y) > LW) { this.leash(game, 'walk'); break; }
        // огненная фаза: на 50% HP — прыжок в ближайшее неосвящённое огнище (если все отбиты — фазы нет)
        const P = B.hearthPhase;
        if (!this.phaseDone && this.hp <= this.maxHp * P.atHpPct / 100) {
          this.phaseDone = true;
          const free = game.map.hearths.filter((o) => !o.done);
          if (free.length) {
            free.sort((a, b) => Math.hypot(a.x - this.x, a.y - this.y) - Math.hypot(b.x - this.x, b.y - this.y));
            const o = free[0];
            // приземление — у самого огнища, в свободной и достижимой точке (иначе босс r 0,6 застревал у камней огнища)
            let [x1, y1] = [o.sx, o.sy];
            if (!circleFree(game.map, x1, y1, this.r + 0.05) || !game.map.isReachableAt(x1, y1)) {
              let best = null;
              for (let rr = 1.0; rr <= 3.01 && !best; rr += 0.25) for (let k = 0; k < 24; k++) {
                const a = (k / 24) * Math.PI * 2, x = o.x + Math.cos(a) * rr, y = o.y + Math.sin(a) * rr;
                if (!circleFree(game.map, x, y, this.r + 0.05) || !game.map.isReachableAt(x, y)) continue;
                const d = Math.hypot(x - h.x, y - h.y); if (!best || d < best[2]) best = [x, y, d];
              }
              if (best) [x1, y1] = best;
            }
            this.jump = { x0: this.x, y0: this.y, x1, y1, hearth: o };
            this.state = 'jump'; this.t = 0; this.invuln = P.invuln; this.moving = false; this.path = null;
            game.counters.krivshaJump = o.id;
            enemyBark(game, this, B.barks.hearth);
            break;
          }
          game.counters.krivshaNoPhase = (game.counters.krivshaNoPhase || 0) + 1;
        }
        this.cycleT -= dt;
        const C = B.claw, d = this.distTo(h);
        this.face(h.x - this.x, h.y - this.y);
        if (d <= C.range + h.r * 0.5 && this.cycleT <= 0) { this.startClaw(game); break; }
        if (d > C.range * 0.6) {
          this.los = lineWalkable(map, this.x, this.y, h.x, h.y, this.r * 0.8);
          if (this.los) { this.path = null; this.stepToward(map, h.x, h.y, this.speed, dt); }
          else { if (!this.path || this.t > 0.5) { this.t = 0; this.setPath(map, h.x, h.y, true, h); } this.followPath(map, dt, this.speed); }
        } else this.moving = false;
        break;
      }
      case 'claw':
        this.moving = false;
        if (this.t >= B.claw.telegraph + 0.25) { this.state = 'fight'; this.t = 0; this.cycleT = B.claw.cycle / this.atkMul - (B.claw.telegraph + 0.25); }
        break;
      case 'jump': {
        // прыжок дугой в огнище (0,6 с), затем в пламени до конца неуязвимости, выход с огненным ореолом
        const J = this.jump, q = Math.min(1, this.t / 0.6);
        this.x = J.x0 + (J.x1 - J.x0) * q; this.y = J.y0 + (J.y1 - J.y0) * q; this.lift = Math.sin(q * Math.PI) * 40;
        this.moving = false;
        // «огнище питает» (GDD v1.8 §5.4, спрайт fx_krivsha_feed): эффект стартует с кадром 0 fire_emerge (t = неуязвимость − 0,75 с),
        // +15% HP — на его кадре 6 (через 0,6 с, за 0,15 с до выхода)
        if (!J.fed && this.t >= B.hearthPhase.invuln - 0.75 + 0.6) { J.fed = true; this.feedHeal(game); }
        if (this.t >= B.hearthPhase.invuln) {
          this.lift = 0; this.state = 'fight'; this.t = 0; this.phase = 2; this.aura = true;
          this.atkMul = 1 + (B.hearthPhase.atkSpeedPct || 0) / 100;      // v1.8: 0 — скорость атаки прежняя
          if (!J.fed) { J.fed = true; this.feedHeal(game); }
          Object.assign(this.res, B.hearthPhase.res);
          game.fx.burst(this.x, this.y, PAL.flame, 24, 40, 70); game.shake(3, 0.3); game.audio.play('explode');
          game.counters.krivshaPhase2 = (game.counters.krivshaPhase2 || 0) + 1;
        }
        break;
      }
    }
    // призыв упырей: таймер боя идёт и во время удара когтями (раз в 15 с по GDD)
    // анимация призыва (косметика, спрайт M1b): начинается за 0,5 с до таймера, кадр 5 (spawn_frame) = появление упырей
    if (this.sumAnim != null) { this.sumAnim += dt; if (this.sumAnim >= 0.8 || this.state === 'jump' || this.state === 'return' || this.state === 'idle') this.sumAnim = null; }
    else if (this.state === 'fight' && this.summonT > dt && this.summonT <= 0.5 && this.minions.filter((e) => !e.dead).length < this.B.summon.max) this.sumAnim = 0.5 - this.summonT;
    if (this.state === 'fight' || this.state === 'claw') this.updateSummon(dt, game);
    // огненный след: за ним 4 с горит земля
    if (this.x !== px || this.y !== py) {
      this.trailT += dt;
      const T = B.fireTrail;
      if (this.trailT >= T.every && this.state !== 'jump') { this.trailT = 0; game.combat.addPatch(this, px, py, T); }
    }
    // огненный ореол: r 1,5, 6% макс. HP героя в секунду (тики 0,5 с)
    if (this.aura && !h.dead) {
      const A = B.hearthPhase.aura;
      this.auraT += dt;
      while (this.auraT >= A.tick) {
        this.auraT -= A.tick;
        if (Math.hypot(h.x - this.x, h.y - this.y) <= A.r + h.r * 0.5) {
          this.auraAcc = (this.auraAcc || 0) + h.maxHp * A.pctMaxHpPerSec / 100 * A.tick;
          const n = Math.floor(this.auraAcc);
          if (n >= 1) { this.auraAcc -= n; this.auraDealt = (this.auraDealt || 0) + h.takeDamage(n, game, 'fire', null); }
        }
      }
    }
  }

  /** v1.8: «огнище его питает» — +15% макс. HP (hearthPhase.healPct). */
  feedHeal(game) {
    const heal = Math.round(this.maxHp * (this.B.hearthPhase.healPct || 0) / 100);
    if (heal <= 0) return;
    this.hp = Math.min(this.maxHp, this.hp + heal); this.phaseHeal = heal;
    game.fx.text(this.x, this.y, '+' + heal, PAL.flame, 100, { dur: 1 });
    game.counters.krivshaFeed = (game.counters.krivshaFeed || 0) + 1;
  }

  startClaw(game) {
    const B = this.B, C = B.claw, h = game.hero;
    this.state = 'claw'; this.t = 0; this.moving = false; this.path = null; this.clawHitT = null;
    const dir = Math.atan2(h.y - this.y, h.x - this.x), me = this;
    this.clawTele = game.combat.addTele({
      shape: 'cone', x: this.x, y: this.y, r: C.range, dir, half: (C.halfAngleDeg * Math.PI) / 180, dur: C.telegraph / this.atkMul, src: this,
      onFire(T) {
        const g = game, hh = g.hero;
        g.counters.krivshaClaws = (g.counters.krivshaClaws || 0) + 1; me.clawHitT = me.t;   // clawHitT — кадр 6 спрайта (hit_frame) с этого момента
        if (hh.dead || !g.combat.inTele(T, hh.x, hh.y, hh.r * 0.5)) return;
        if (C.hitRoll && !(Math.random() < hitChance(me.ar, hh.def, me.mlvl, hh.level))) {   // v1.8: проверка попадания (§3.3)
          g.counters.krivshaClawMiss = (g.counters.krivshaClawMiss || 0) + 1; g.fx.text(hh.x, hh.y, t('ui.combat.miss'), PAL.mist, 50, { dur: 0.6 }); return;
        }
        const dmg = Math.round((me.dmgMin + Math.floor(Math.random() * (me.dmgMax - me.dmgMin + 1))) * C.mul);
        const dealt = hh.takeDamage(dmg, g, 'melee', me);
        me.clawDealt = (me.clawDealt || 0) + dealt;
        g.counters.krivshaClawHits = (g.counters.krivshaClawHits || 0) + 1;
        g.shake(2, 0.12);
      },
    });
  }

  updateSummon(dt, game) {
    const S = this.B.summon;
    this.summonT -= dt;
    if (this.summonT > 0) return;
    this.summonT = S.every;
    this.minions = this.minions.filter((e) => !e.dead);
    const n = Math.min(S.count, S.max - this.minions.length);
    if (n > 0) this.sumAnim = 0.5;                                     // синхрон кадра 5 с моментом призыва
    let made = 0;
    for (let i = 0; i < n; i++) {
      for (let k = 0; k < 12; k++) {
        const a = Math.random() * Math.PI * 2, r = 1.6 + Math.random() * 1.4, x = this.x + Math.cos(a) * r, y = this.y + Math.sin(a) * r;
        if (!circleFree(game.map, x, y, 0.4) || !game.map.isReachableAt(x, y)) continue;
        const e = new Enemy(S.kind, x, y, 'krivsha', S.mlvl);
        e.state = 'rise'; e.t = 0; e.riseTime = 0.8; e.summoned = true;
        if (S.xpMul === 0) e.xp = 0; if (S.drop === false) e.noLoot = true;   // v1.8: призванные без опыта и добычи
        game.enemies.push(e); this.minions.push(e); made++;
        game.fx.burst(x, y, PAL.wood_md, 8, 2, 30);
        break;
      }
    }
    if (made) {
      game.counters.krivshaSummons = (game.counters.krivshaSummons || 0) + made;
      if (!this.summonBarked) { this.summonBarked = true; enemyBark(game, this, this.B.barks.summon); }
    }
  }

  /** Герой пал или ушёл: к идолу, полное HP, бой начнётся заново (GDD v1.7 §4.5 — недобитые лечатся). */
  reset(game) {
    this.state = 'idle'; this.t = 0; this.path = null; this.moving = false;
    this.hp = this.maxHp; this.phase = 1; this.phaseDone = false; this.aura = false; this.atkMul = 1; this.lift = 0;
    this.res = { ...this.def.res }; this.summonT = this.B.summon.first; this.cycleT = 0; this.fightT = 0;
    this.summonBarked = false; this.sumAnim = null;
    // GDD v1.8.1 (B-33): призванные рассыпаются вместе со сбросом босса — без опыта, добычи и трупа
    if (this.B.summon.despawnOnReset !== false) this.crumbleMinions(game);
    game.counters.krivshaResets = (game.counters.krivshaResets || 0) + 1;
  }
  /** Поводок (GDD v1.9): полное HP, фаза заново, призванные рассыпаются (B-33) — сразу; потом пешком к идолу.
   *  home = true (герой ушёл из зоны) — босс сразу у идола и ждёт (зона без героя не обновляется). */
  leash(game, why, home = false) {
    this.reset(game);
    game.counters.krivshaLeash = (game.counters.krivshaLeash || 0) + 1; game.counters.krivshaLeashWhy = why;
    if (home) { this.x = this.homeX; this.y = this.homeY; this.leashed = false; return; }
    if (Math.hypot(this.x - this.homeX, this.y - this.homeY) >= 0.8) { this.state = 'return'; this.path = null; this.leashed = true; }
  }
  crumbleMinions(game) {
    const gone = new Set(this.minions.filter((e) => !e.dead));
    for (const e of game.enemies) if (e.summoned && e.pack === 'krivsha' && !e.dead) gone.add(e);
    for (const e of gone) { game.fx.burst(e.x, e.y, PAL.wood_md, 10, 6, 30); game.fx.burst(e.x, e.y, PAL.slate_lt, 6, 14, 20); }
    if (gone.size) {
      game.enemies = game.enemies.filter((e) => !gone.has(e));
      game.counters.krivshaCrumbled = (game.counters.krivshaCrumbled || 0) + gone.size;
    }
    this.minions = [];
  }
}
