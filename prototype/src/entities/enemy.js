// Нечисть: бродит у логова, замечает героя в радиусе агрессии, преследует, бьёт (с телеграфом замаха).
// Сильный удар оглушает на 0,25 с (не чаще раза в 1,5 с), удары отбрасывают. Анчутка (GDD v1.2 §5.2)
// держится на расстоянии и кидает угли (дальность 4, снаряд 8 тайлов/с), после броска с шансом 30%
// отбегает на 2–3 тайла; если рядом погиб сородич — с шансом 30% удирает на 3 с. Далеко от логова — возвращается и лечится.
import { Actor } from './actor.js';
import { ENEMIES, enemyStats } from '../data/enemies.js';
import { hitChance, S as STATS } from '../data/progression.js';
import { lineWalkable, sightClear } from '../world/collision.js';
import { rnd } from '../core/math.js';
import { PAL } from '../palette.js';

let NEXT_ID = 1;

export class Enemy extends Actor {
  constructor(kind, x, y, pack, mlvl = 1) {
    const def = ENEMIES[kind];
    super(x, y, def.r);
    this.id = NEXT_ID++;
    this.def = def;
    this.kind = kind;
    this.name = def.name;
    Object.assign(this, enemyStats(kind, mlvl));    // mlvl, hp, dmgMin, dmgMax, ar, dfn, xp
    this.maxHp = this.hp;
    this.speed = def.speed * rnd(0.92, 1.08);
    this.homeX = x; this.homeY = y;
    this.pack = pack;
    this.state = 'idle';
    this.t = 0;
    this.thinkT = rnd(0, 0.5);
    this.los = false;
    this.wanderT = rnd(1, 4);
    this.corpseT = 0;
    this.lastHitT = 99;
    this.attackFired = false;
    this.fleeDir = [0, 0];
    this.stagger = 0;
    this.lastStagger = -99;
    this.age = 0;
    this.torchCd = 0;          // «Поджог» поджигателя (def.torch)
    // у экземпляра свои сопротивления и темп удара: элиты (GDD §5.3) меняют их модификаторами (systems/elites.js)
    this.res = { ...def.res };
    this.attackTime = def.attackTime; this.hitAt = def.hitAt;
    this.invuln = 0;
    this.elite = null; this.mods = []; this.leader = false; this.retinue = false;
  }

  /** Удар по герою прошёл (dealt — нанесённый урон): модификаторы элит (Жаркий, Студёный, Кровопийца). */
  onHitHero(dealt, game) {
    if (!this.mods.length || !dealt) return;
    const M = this.modDefs || {};
    const h = game.hero;
    if (M.hot && !h.dead) h.takeDamage(Math.max(1, Math.floor(dealt * M.hot.fireAddPct / 100)), game, 'fire', null);
    if (M.cold && !h.dead) { h.slowPct = M.cold.slowPct; h.slowT = Math.max(h.slowT || 0, M.cold.slowTime); }
    if (M.leech) { this.hp = Math.min(this.maxHp, this.hp + Math.max(1, Math.round(dealt * M.leech.lifeStealPct / 100))); }
  }

  aggro(game, spread = true) {
    if (this.dead || game.hero.dead) return;
    if (this.state === 'idle' || this.state === 'return') { this.state = 'chase'; this.path = null; this.thinkT = 0; }
    if (spread) for (const o of game.enemies) if (o !== this && !o.dead && o.pack === this.pack && o.state === 'idle') o.aggro(game, false);
  }

  /** type: 'melee' | 'fire' | 'cold' | 'thorns'. opts: {crit, kbDir:[dx,dy], kb}. */
  takeDamage(amount, game, type = 'melee', src = null, opts = {}) {
    if (this.dead) return 0;
    if (this.invuln > 0) { game.fx.text(this.x, this.y, 'Неуязвим', PAL.mist, this.def.height + 6, { dur: 0.5 }); return 0; }
    let dmg = amount;
    const res = this.res[type] || 0;
    if (res) dmg = dmg * (1 - res);
    dmg = Math.max(1, Math.floor(dmg));
    this.hp -= dmg;
    this.flash = 0.12;
    this.lastHitT = 0;
    const col = opts.crit ? PAL.flame : type === 'fire' ? PAL.ember : type === 'cold' ? PAL.blue_lt : PAL.linen;
    game.fx.text(this.x, this.y, String(dmg), col, this.def.height + 6, opts.crit ? { dur: 1.0 } : {});
    game.fx.burst(this.x, this.y, this.kind === 'upyr' ? PAL.nebyl_dk : PAL.red, opts.crit ? 9 : 5, this.def.height * 0.6);
    if (this.hp <= 0) {
      this.hp = 0;
      this.dead = true;
      this.moving = false;
      this.path = null;
      this.kb = null;
      if (opts.kbDir) this.knock(opts.kbDir[0], opts.kbDir[1], opts.killKb ?? 0.5, 0.18);   // тело отлетает («Сшибка» — на 1 тайл)
      game.onEnemyKilled(this);
      return dmg;
    }
    // отбрасывание (лёгких — сильнее) и оглушение: удар > 10% макс. HP прерывает на 0,25 с, не чаще раза в 1,5 с
    if (opts.kbDir && opts.kb) this.knock(opts.kbDir[0], opts.kbDir[1], opts.kb / this.def.mass);
    // замедление холодом («Дыхание Морозко»): всё тело — шаг, замах, бросок — идёт медленнее
    if (opts.slow) { this.slowPct = opts.slow.pct; this.slowT = Math.max(this.slowT || 0, opts.slow.time); }
    const st = STATS.monsterStagger;
    if (dmg > this.maxHp * st.hpFrac && this.age - this.lastStagger >= st.cooldown) {
      this.stagger = st.time; this.lastStagger = this.age;
      if (this.state === 'attack' && !this.attackFired) { this.state = 'chase'; this.t = 0; }
    }
    // GDD v1.6 §4.5: бьют из тихого круга — враг уходит к логову и восстанавливает HP (как по поводку)
    if (game.safeAt(game.hero.x, game.hero.y) && src === game.hero) {
      if (this.state !== 'return') { this.state = 'return'; this.path = null; game.counters.safeReturn = (game.counters.safeReturn || 0) + 1; }
      return dmg;
    }
    this.aggro(game);
    return dmg;
  }

  /** Обход по кругу (Мара Пепельная, GDD §5.3: «бродит по Залесью по кругу»): точки маршрута по очереди. */
  patrol(game, dt) {
    const R = this.route, map = game.map;
    if (!this.path || this.reachedWp) {
      this.reachedWp = false;
      for (let k = 0; k < R.pts.length; k++) {
        R.i = (R.i + 1) % R.pts.length;
        const [tx, ty] = R.pts[R.i];
        if (!map.blockedAt(tx, ty) && !game.safeAt(tx, ty, 1) && this.setPath(map, tx, ty) !== false && this.path) break;
      }
    }
    if (this.path) { if (this.followPath(map, dt, this.speed * R.speedMul)) this.reachedWp = true; }
    else this.moving = false;
    this.homeX = this.x; this.homeY = this.y;
  }

  scare(dx, dy, time) {
    this.state = 'flee'; this.t = 0; this.fleeTime = time; this.path = null;
    const a = Math.atan2(dy, dx) + rnd(-0.6, 0.6);
    this.fleeDir = [Math.cos(a), Math.sin(a)];
  }

  update(dt, game) {
    this.flash = Math.max(0, this.flash - dt);
    this.lastHitT += dt;
    this.age += dt;
    if (this.dead) { this.corpseT += dt; this.updateKnock(game.map, dt); return; }
    const hero = game.hero, map = game.map, def = this.def;
    if (this.slowT > 0) { this.slowT -= dt; dt *= 1 - this.slowPct / 100; }
    if (this.updateKnock(map, dt)) return;
    if (this.stagger > 0) { this.stagger -= dt; this.moving = false; return; }
    const dHero = this.distTo(hero);
    const px = this.x, py = this.y;
    if (this.torchCd > 0) this.torchCd -= dt;
    this.t += dt;
    this.thinkT -= dt;
    if (this.thinkT <= 0) {
      this.thinkT = 0.2 + Math.random() * 0.1;
      this.los = lineWalkable(map, this.x, this.y, hero.x, hero.y, this.r * 0.8);
    }
    const heroTargetable = !hero.dead && hero.invuln <= 0;          // по неуязвимому не бьём и не бросаем
    // QA B-20: неуязвимость «Рывка» — защита от урона, а не невидимость: погоню обрывают только смерть и
    // «милость» после возрождения (graceT), но не 0,15 с рывка
    const heroPresent = !hero.dead && !(hero.graceT > 0);
    // тихие круги (крада 10, Чуров камень 6 — QA B-16, решение дизайнера): там нечисть героя не замечает
    const heroSafe = game.safeAt(hero.x, hero.y);

    switch (this.state) {
      case 'idle': {
        if (this.route) { this.patrol(game, dt); if (heroPresent && !heroSafe && dHero < def.aggro && (this.los || dHero < 2.5)) this.aggro(game); break; }
        if (this.follow && !this.follow.dead) { this.homeX = this.follow.x + this.followOff[0]; this.homeY = this.follow.y + this.followOff[1]; if (Math.hypot(this.x - this.homeX, this.y - this.homeY) > 2.5) this.wanderT = 0; }
        this.wanderT -= dt;
        if (this.path) this.followPath(map, dt, this.speed * (this.follow ? 0.6 : 0.3));
        else this.moving = false;
        if (this.wanderT <= 0) {
          this.wanderT = rnd(2, 5);
          const tx = this.homeX + rnd(-1.6, 1.6), ty = this.homeY + rnd(-1.6, 1.6);
          if (!map.blockedAt(tx, ty) && !game.safeAt(tx, ty, 0.5)) this.setPath(map, tx, ty);
        }
        if (heroPresent && !heroSafe && dHero < def.aggro && (this.los || dHero < 2.5)) this.aggro(game);
        break;
      }
      case 'chase': {
        if (!heroPresent || heroSafe) { this.state = 'return'; this.path = null; if (heroSafe) game.counters.safeBreaks = (game.counters.safeBreaks || 0) + 1; break; }
        if (Math.hypot(this.x - this.homeX, this.y - this.homeY) > def.leash && dHero > 3) { this.state = 'return'; this.path = null; break; }
        const tc = def.torch;
        // «Поджог» (GDD §5.2 E11): герой в 2–6 тайлах, КД готов, своей зоны огня нет
        if (tc && this.torchCd <= 0 && dHero >= tc.rangeMin && dHero <= tc.rangeMax && game.combat.zonesOf(this) < tc.maxZones && sightClear(map, this.x, this.y, hero.x, hero.y)) {
          this.state = 'torch'; this.t = 0; this.attackFired = false; this.moving = false; this.path = null;
          this.face(hero.x - this.x, hero.y - this.y);
          break;
        }
        const rg = def.ranged;
        if (rg && dHero <= rg.range && dHero > 0.3 && sightClear(map, this.x, this.y, hero.x, hero.y)) {
          this.state = 'attack'; this.t = 0; this.attackFired = false; this.moving = false; this.path = null;
          this.face(hero.x - this.x, hero.y - this.y);
          break;
        }
        if (!rg && dHero <= def.reach + hero.r * 0.5) {
          this.state = 'attack'; this.t = 0; this.attackFired = false; this.moving = false; this.path = null;
          this.face(hero.x - this.x, hero.y - this.y);
          break;
        }
        this.detourT = Math.max(0, (this.detourT || 0) - dt);
        if (this.los && this.detourT <= 0) {
          this.path = null; this.stepToward(map, hero.x, hero.y, this.speed, dt);
          if (this.bumped && this.bumped !== hero) { this.detourT = 0.8; this.path = null; }
        } else {
          // упёрлись в сородича или нет прямой — обходим (с учётом других тел)
          if (!this.path || this.t > 0.6) { this.t = 0; this.setPath(map, hero.x, hero.y, true, hero); }
          this.followPath(map, dt, this.speed);
        }
        break;
      }
      case 'attack': {
        this.face(hero.x - this.x, hero.y - this.y);
        if (!this.attackFired && this.t >= this.hitAt && def.ranged) {
          this.attackFired = true;
          if (heroTargetable && !heroSafe) game.combat.throwCoal(this, hero.x, hero.y);
        }
        if (!this.attackFired && this.t >= this.hitAt) {
          this.attackFired = true;
          if (heroTargetable && !heroSafe && this.distTo(hero) <= def.reach + hero.r + 0.35) {
            if (Math.random() < hitChance(this.ar, hero.def, this.mlvl, hero.level)) {
              this.onHitHero(hero.takeDamage(this.dmgMin + Math.floor(Math.random() * (this.dmgMax - this.dmgMin + 1)), game, 'melee', this), game);
            } else game.fx.text(hero.x, hero.y, 'Мимо', PAL.mist, 50, { dur: 0.6 });
          }
        }
        if (this.t >= this.attackTime) {
          this.state = 'chase'; this.t = 0;
          const rg = def.ranged;
          // анчутка: после броска с шансом 30% отбегает на 2–3 тайла; слишком близко к герою — отходит всегда
          // отход «слишком близко» — не чаще раза в rg.keepMinCooldown с (решение дизайнера 08.10)
          const now = game.time || 0;
          const tooClose = this.distTo(hero) < rg?.keepMin && now - (this.lastBackoff ?? -99) >= (rg?.keepMinCooldown ?? 3);
          if (rg && (Math.random() < rg.retreatChance || tooClose)) {
            if (tooClose) { this.lastBackoff = now; game.counters && game.counters.backoff++; }
            const dist = rg.retreatDist[0] + Math.random() * (rg.retreatDist[1] - rg.retreatDist[0]);
            this.scare(this.x - hero.x, this.y - hero.y, dist / this.speed);
            this.retreating = true;
          }
        }
        break;
      }
      case 'torch': {
        const tc = def.torch;
        this.face(hero.x - this.x, hero.y - this.y);
        this.moving = false;
        if (!this.attackFired && this.t >= tc.windup) {
          this.attackFired = true;
          this.torchCd = tc.cooldown;
          if (heroTargetable && !heroSafe) {
            // факел — на землю перед героем, на 1,5 тайла ближе к поджигателю
            const d = this.distTo(hero) || 1, k = Math.min(tc.towardSelf, Math.max(0, d - 0.6)) / d;
            const tx = hero.x + (this.x - hero.x) * k, ty = hero.y + (this.y - hero.y) * k;
            if (!game.safeAt(tx, ty, tc.radius)) game.combat.throwTorch(this, tx, ty);
          }
        }
        if (this.t >= (tc.animTime ?? tc.windup + 0.2)) { this.state = 'chase'; this.t = 0; this.attackFired = false; }
        break;
      }
      case 'rise': {
        // волна: встаёт из земли, потом сразу в погоню
        this.moving = false;
        if (this.t >= (this.riseTime || 0.8)) { this.state = 'idle'; this.t = 0; this.aggro(game, false); }
        break;
      }
      case 'flee': {
        this.stepToward(map, this.x + this.fleeDir[0], this.y + this.fleeDir[1], this.speed, dt);
        if (this.t >= (this.fleeTime || 1)) { this.state = 'chase'; this.t = 0; this.retreating = false; }
        break;
      }
      case 'return': {
        if (!this.path) this.setPath(map, this.homeX, this.homeY, true);
        const done = this.followPath(map, dt, this.speed);
        if (done || Math.hypot(this.x - this.homeX, this.y - this.homeY) < 0.6) {
          if (Math.hypot(this.x - this.homeX, this.y - this.homeY) < 2) { this.state = 'idle'; this.hp = this.maxHp; this.wanderT = rnd(1, 3); }
          this.path = null;
        }
        if (heroPresent && !heroSafe && dHero < def.aggro * 0.6 && this.los) this.aggro(game);
        break;
      }
    }
    if (this.tick) this.tick(this, dt, game);    // особые враги (Мара Пепельная: пепельный след, лечение, реплики)
    // поджигатель сам в огонь (и под телеграф) не заходит
    if (def.torch && (this.x !== px || this.y !== py) && game.combat.fireAt(this.x, this.y, this.r) && !game.combat.fireAt(px, py, this.r)) {
      this.x = px; this.y = py; this.path = null; this.moving = false;
      game.counters.fireAvoid = (game.counters.fireAvoid || 0) + 1;
    }
  }
}
