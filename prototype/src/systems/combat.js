// Боевая логика: удар героя (меткость, крит, хит-стоп, отбрасывание), «Огненный змей»
// (снаряд + взрыв; взрыв не бьёт сквозь стены — проверка прямой видимости от центра взрыва),
// угли анчуток (вражеский снаряд: попадает при касании, гаснет о стену, от него можно уйти).
import { rndInt } from '../core/math.js';
import { sightClear } from '../world/collision.js';
import { hitChance, MELEE_RANGE, HIT_STOP } from '../data/progression.js';
import { SKILLS, skillNumbers, spellDamage, rankOf } from '../data/skills.js';
import { PAL } from '../palette.js';
import { baseDamageAvg } from '../data/enemies.js';

let FIRE_ID = 1;

export class Combat {
  constructor(game) { this.game = game; this.projectiles = []; this.fires = []; this.lastBlast = null; }

  heroMelee(hero, target, skill = null) {
    const g = this.game;
    const sk = skill ? skillNumbers(hero, skill) : null;
    if (sk) {
      g.fx.ring(hero.x + hero.dirVec()[0] * 0.8, hero.y + hero.dirVec()[1] * 0.8, 0.6, PAL.bronze_lt, 0.25);
      g.lastBash = { t: g.time, target: target ? target.id : null };
      g.audio.play('bash');
      // «Сшибка» по земле: бьёт ближайшего врага перед собой
      if (!target) {
        const [fx, fy] = hero.dirVec();
        let best = null, bd = 1e9;
        for (const e of g.enemies) {
          if (e.dead) continue;
          const dx = e.x - hero.x, dy = e.y - hero.y, d = Math.hypot(dx, dy);
          if (d > MELEE_RANGE + e.r + 0.2 || (dx * fx + dy * fy) / (d || 1) < 0.5) continue;
          if (d < bd) { bd = d; best = e; }
        }
        target = best;
      }
    }
    if (!target || target.dead) return;
    if (hero.distTo(target) > MELEE_RANGE + target.r + 0.4) return;           // увернулся / убежал
    const ar = sk ? hero.ar * (1 + sk.arPct / 100) : hero.ar;
    if (Math.random() >= hitChance(ar, target.dfn, hero.level, target.mlvl)) {
      g.fx.text(target.x, target.y, 'Мимо', PAL.mist, target.def.height + 6, { dur: 0.7 });
      g.audio.play('miss');
      return;
    }
    const crit = Math.random() < hero.crit;
    let dmg = rndInt(hero.dmgMin, hero.dmgMax);
    if (target.def.family === 'Нечисть') dmg *= 1 + hero.vsNechist;
    if (crit) dmg *= hero.critMult;
    if (sk) dmg *= sk.dmgPct / 100;
    dmg = Math.floor(dmg);
    const dir = [target.x - hero.x, target.y - hero.y];
    // «Сшибка» (GDD v1.6 §3.6): на 1 тайл отбрасывает только добивающий удар, с ранга 3 — ещё и удачный (крит);
    // обычные попадания не отбрасывают. Масса врага не смягчает: knock делится на mass, поэтому домножаем
    let kb, killKb;
    if (sk) {
      const S = SKILLS[skill], rule = S.knockbackRule || {};
      kb = crit && rankOf(hero, skill) >= (rule.onCritFromRank ?? 3) ? S.knockback * target.def.mass : 0;
      killKb = rule.onKill != null ? S.knockback : undefined;
    } else kb = crit ? 0.5 : 0.28;
    const done = target.takeDamage(dmg, g, 'melee', hero, { crit, kbDir: dir, kb, killKb });
    if (hero.fireDmg && !target.dead) target.takeDamage(hero.fireDmg, g, 'fire', hero);
    if (hero.coldDmg && !target.dead) target.takeDamage(hero.coldDmg, g, 'cold', hero);
    if (hero.lifesteal) hero.hp = Math.min(hero.maxHp, hero.hp + done * hero.lifesteal);
    g.hitStop(crit ? HIT_STOP * 1.6 : HIT_STOP);
    if (crit) g.shake(1.5, 0.12);
    g.audio.play(crit ? 'crit' : 'hit');
  }

  /** Выпуск навыка на кадре каста (Hero.update). */
  release(hero, id, tx, ty) {
    const sk = SKILLS[id], g = this.game;
    if (sk.type === 'projectile') return this.castProjectile(hero, id, tx, ty);
    if (sk.type === 'buff') {
      const n = skillNumbers(hero, id);
      hero.buffs.chur = { t: sk.duration, dur: sk.duration, defPct: n.defPct, resAll: n.resAll };
      hero.recalc();
      g.audio.play('buff');
      g.fx.ring(hero.x, hero.y, 1.1, PAL.bronze_hi, 0.6);
      g.fx.burst(hero.x, hero.y, PAL.bronze_lt, 14, 22, 50);
      g.log.add(sk.name + ': +' + n.defPct + '% к защите на ' + sk.duration + ' с', PAL.bronze_lt);
      return;
    }
    if (sk.type === 'teleport') return this.perunSkok(hero, id, tx, ty);
  }

  castProjectile(hero, id, tx, ty) {
    const sk = SKILLS[id];
    let dx = tx - hero.x, dy = ty - hero.y;
    let d = Math.hypot(dx, dy);
    if (d < 0.05) { [dx, dy] = hero.dirVec(); d = Math.hypot(dx, dy); }   // цель в точке героя (QA B-11)
    dx /= d; dy /= d;
    const n = skillNumbers(hero, id);
    this.projectiles.push({
      skill: id, element: sk.element, radius: sk.radius, knockback: sk.knockback,
      slow: sk.slowPct ? { pct: sk.slowPct, time: n.slowTime } : null,
      x: hero.x + dx * 0.35, y: hero.y + dy * 0.35, vx: dx * sk.speed, vy: dy * sk.speed,
      travelled: 0, range: sk.range, r: id === 'morozko' ? 0.14 : 0.18, dmg: spellDamage(hero, id), t: 0, trail: [],
    });
  }
  // старое имя (автотесты итерации 2)
  castSkill(hero, tx, ty) { this.castProjectile(hero, 'zmey', tx, ty); }

  /** «Перунов скок»: молния переносит героя в точку, при приземлении — огонь по кругу (тоже без стен между). */
  perunSkok(hero, id, tx, ty) {
    const g = this.game, sk = SKILLS[id];
    const from = [hero.x, hero.y];
    // QA B-22: враг мог шагнуть в точку за время каста — приземляемся у края тела, а не внутри
    if (g.enemies.some((e) => !e.dead && Math.hypot(e.x - tx, e.y - ty) < hero.r + e.r - 0.01)) {
      const fix = hero.teleportPoint(g.map, tx, ty, Infinity, g.enemies);
      if (fix) { tx = fix[0]; ty = fix[1]; }
    }
    hero.x = tx; hero.y = ty; hero.path = null; hero.cmd = null;
    g.fx.bolt(from[0], from[1], tx, ty);
    g.fx.light(tx, ty, 110, 0.4);
    g.fx.ring(tx, ty, sk.radius, PAL.blue_lt, 0.35);
    g.shake(1.5, 0.12);
    g.audio.play('thunder');
    const [a, b] = spellDamage(hero, id), hit = [];
    for (const e of g.enemies) {
      if (e.dead || Math.hypot(e.x - tx, e.y - ty) > sk.radius + e.r || !sightClear(g.map, tx, ty, e.x, e.y)) continue;
      const crit = Math.random() < hero.crit;
      e.takeDamage(Math.floor(rndInt(a, b) * (crit ? hero.critMult : 1)), g, 'fire', hero, { crit, kbDir: [e.x - tx, e.y - ty], kb: 0.4 });
      hit.push(e.id);
    }
    g.lastSkok = { from, to: [tx, ty], hit, t: g.time };
  }

  throwCoal(enemy, tx, ty) {
    const rg = enemy.def.ranged;
    let dx = tx - enemy.x, dy = ty - enemy.y;
    const d = Math.hypot(dx, dy) || 1;
    dx /= d; dy /= d;
    this.projectiles.push({
      hostile: true, coal: true, src: enemy, x: enemy.x + dx * 0.3, y: enemy.y + dy * 0.3, vx: dx * rg.projSpeed, vy: dy * rg.projSpeed,
      travelled: 0, range: rg.range + 0.8, r: 0.12, dmg: [enemy.dmgMin, enemy.dmgMax], element: rg.element, t: 0, trail: [],
    });
    this.game.audio.play('throw');
  }

  /** «Поджог» (GDD v1.5 §5.2 E11): факел летит в точку, телеграф 0,8 с (красный круг), затем зона Ø 2 тайла
   *  горит 4 с: огонь floor(0,8 × средний урон mlvl) в секунду (тики по 0,5 с с переносом дробной части). */
  throwTorch(enemy, tx, ty) {
    const tc = enemy.def.torch, d = Math.hypot(tx - enemy.x, ty - enemy.y);
    const f = {
      id: FIRE_ID++, src: enemy, x: tx, y: ty, fx: enemy.x, fy: enemy.y, t: 0, lit: false, litT: 0,
      flight: Math.min(tc.telegraph * 0.9, d / tc.flight), tele: tc.telegraph, burn: tc.burn, r: tc.radius,
      dps: Math.floor(tc.dpsMul * baseDamageAvg(enemy.mlvl)), tick: tc.tick, tickT: 0, acc: 0, ticks: 0, dealt: 0,
    };
    this.fires.push(f);
    const g = this.game;
    g.counters.torches = (g.counters.torches || 0) + 1;
    g.audio.play('throw');
    if (!g._tutTelegraph) { g._tutTelegraph = true; g.notify(g.t('ui.tut.telegraph'), PAL.red_lt, 'tut'); }
    return f;
  }
  /** Сколько зон огня держит поджигатель (не больше torch.maxZones). */
  zonesOf(enemy) { let n = 0; for (const f of this.fires) if (f.src === enemy) n++; return n; }
  /** Точка в огне (или под телеграфом) — поджигатель сам туда не заходит. */
  fireAt(x, y, pad = 0) { return this.fires.some((f) => Math.hypot(x - f.x, y - f.y) < f.r + pad); }

  updateFires(dt) {
    const g = this.game, h = g.hero;
    for (const f of this.fires) {
      f.t += dt;
      if (!f.lit && f.t >= f.tele) {
        f.lit = true; f.litT = 0;
        g.fx.burst(f.x, f.y, PAL.ember, 12, 6, 40);
        g.fx.light(f.x, f.y, 80, 0.3);
        g.audio.play('explode');
      }
      if (!f.lit) continue;
      f.litT += dt; f.tickT += dt;
      while (f.tickT >= f.tick - 1e-9 && f.litT <= f.burn + 1e-9) {
        f.tickT -= f.tick;
        if (h.dead || Math.hypot(h.x - f.x, h.y - f.y) > f.r + h.r * 0.5 || g.safeAt(h.x, h.y)) continue;   // в тихом круге огонь не жжёт
        f.acc += f.dps * f.tick;
        const n = Math.floor(f.acc + 1e-9);
        if (n >= 1) { f.acc -= n; f.ticks++; f.dealt += h.takeDamage(n, g, 'fire', null); g.counters.fireTicks = (g.counters.fireTicks || 0) + 1; }
      }
      if (Math.random() < 0.5) g.fx.parts.push({ x: f.x + (Math.random() - 0.5) * f.r * 1.4, y: f.y + (Math.random() - 0.5) * f.r * 1.4, ox: 0, oy: -6, vx: 0, vy: -18, g: 0, t: 0, dur: 0.5, color: Math.random() < 0.5 ? PAL.ember : PAL.flame, size: 1 });
      if (f.litT >= f.burn) f.dead = true;
    }
    if (this.fires.some((f) => f.dead)) this.fires = this.fires.filter((f) => !f.dead);
  }

  update(dt) {
    const g = this.game;
    this.updateFires(dt);
    for (const p of this.projectiles) {
      if (p.dead) continue;
      p.t += dt;
      const steps = 5;
      for (let i = 0; i < steps && !p.dead; i++) {
        const ox = p.x, oy = p.y;
        p.x += (p.vx * dt) / steps; p.y += (p.vy * dt) / steps;
        p.travelled += (Math.hypot(p.vx, p.vy) * dt) / steps;
        if (p.hostile) {
          const h = g.hero;
          if (g.map.opaqueAt(p.x, p.y) || p.travelled >= p.range) { this.fizzle(p); break; }
          if (g.safeAt(p.x, p.y)) { this.fizzle(p); g.counters.safeFizzle = (g.counters.safeFizzle || 0) + 1; break; }   // GDD v1.6 §4.5: гаснет на границе тихого круга
          if (!h.dead && Math.hypot(h.x - p.x, h.y - p.y) < h.r + p.r) {
            // QA B-21: герой уже в тихом круге (снаряд у самой границы) — уголь гаснет, урона нет
            if (g.safeAt(h.x, h.y)) { this.fizzle(p); g.counters.safeFizzle = (g.counters.safeFizzle || 0) + 1; break; }
            p.dead = true;
            g.fx.burst(p.x, p.y, PAL.ember, 8, 20, 50);
            h.takeDamage(rndInt(p.dmg[0], p.dmg[1]), g, p.element, null);
          }
          continue;
        }
        if (g.map.opaqueAt(p.x, p.y)) { p.x = ox; p.y = oy; this.explode(p); break; }     // упёрся в стену — взрыв перед ней
        if (p.travelled >= p.range) { this.explode(p); break; }
        for (const e of g.enemies) {
          if (!e.dead && Math.hypot(e.x - p.x, e.y - p.y) < e.r + p.r) { this.explode(p, e); break; }
        }
      }
      p.trail.push([p.x, p.y]); if (p.trail.length > 6) p.trail.shift();
      if (!p.dead && Math.random() < (p.coal ? 0.3 : 0.6)) g.fx.parts.push({ x: p.x, y: p.y, ox: 0, oy: -22, vx: 0, vy: -10, g: 0, t: 0, dur: 0.3, color: p.element === 'cold' ? (Math.random() < 0.5 ? PAL.blue_lt : PAL.linen) : Math.random() < 0.5 ? PAL.ember : PAL.flame, size: 1 });
    }
    this.projectiles = this.projectiles.filter((p) => !p.dead);
  }

  fizzle(p) {
    p.dead = true;
    this.game.fx.burst(p.x, p.y, PAL.ember, 5, 16, 30);
  }

  explode(p, direct = null) {
    const g = this.game, sk = { radius: p.radius ?? 1, knockback: p.knockback ?? 0.55 };
    p.dead = true;
    if (p.element === 'cold') {          // «Дыхание Морозко»: одна цель, холод и замедление
      g.fx.burst(p.x, p.y, PAL.blue_lt, 10, 18, 50);
      g.fx.burst(p.x, p.y, PAL.linen, 6, 18, 30);
      g.audio.play('frost');
      const e = direct;
      if (e && !e.dead) {
        const crit = Math.random() < g.hero.crit;
        const strong = e.def.boss || e.elite || e.leader;     // боссы и вожаки: замедление вдвое слабее (GDD v1.6 §3.6)
        const slow = p.slow && strong ? { ...p.slow, pct: p.slow.pct * (SKILLS[p.skill].slowBossMul ?? 1) } : p.slow;
        e.takeDamage(Math.floor(rndInt(p.dmg[0], p.dmg[1]) * (crit ? g.hero.critMult : 1)), g, 'cold', g.hero, { crit, kbDir: [p.vx, p.vy], kb: sk.knockback, slow });
      }
      this.lastBlast = { x: p.x, y: p.y, hit: e ? [e.id] : [], blocked: [], t: g.time, skill: p.skill };
      return;
    }
    g.fx.ring(p.x, p.y, sk.radius, PAL.ember, 0.35);
    g.fx.burst(p.x, p.y, PAL.flame, 16, 18, 80);
    g.fx.burst(p.x, p.y, PAL.ember, 12, 18, 60);
    g.fx.light(p.x, p.y, 90, 0.35);
    g.audio.play('explode');
    g.shake(1, 0.1);
    const hit = [], blocked = [];
    for (const e of g.enemies) {
      if (e.dead) continue;
      if (Math.hypot(e.x - p.x, e.y - p.y) > sk.radius + e.r) continue;
      // стена между центром взрыва и целью гасит огонь
      if (!sightClear(g.map, p.x, p.y, e.x, e.y)) { blocked.push(e.id); continue; }
      hit.push(e.id);
      const crit = Math.random() < g.hero.crit;      // урон ведовства тоже бывает удачным (GDD §3.3)
      const dmg = Math.floor(rndInt(p.dmg[0], p.dmg[1]) * (crit ? g.hero.critMult : 1));
      e.takeDamage(dmg, g, 'fire', g.hero, { crit, kbDir: [e.x - p.x, e.y - p.y], kb: sk.knockback });
    }
    this.lastBlast = { x: p.x, y: p.y, hit, blocked, t: g.time, skill: p.skill };
  }
}
