// Боевая логика: удар героя (меткость, крит, хит-стоп, отбрасывание), «Огненный змей»
// (снаряд + взрыв; взрыв не бьёт сквозь стены — проверка прямой видимости от центра взрыва),
// угли анчуток (вражеский снаряд: попадает при касании, гаснет о стену, от него можно уйти).
import { rndInt } from '../core/math.js';
import { sightClear } from '../world/collision.js';
import { hitChance, MELEE_RANGE, HIT_STOP } from '../data/progression.js';
import { SKILLS } from '../data/skills.js';
import { PAL } from '../palette.js';

export class Combat {
  constructor(game) { this.game = game; this.projectiles = []; this.lastBlast = null; }

  heroMelee(hero, target) {
    const g = this.game;
    if (!target || target.dead) return;
    if (hero.distTo(target) > MELEE_RANGE + target.r + 0.4) return;           // увернулся / убежал
    if (Math.random() >= hitChance(hero.ar, target.dfn, hero.level, target.mlvl)) {
      g.fx.text(target.x, target.y, 'Мимо', PAL.mist, target.def.height + 6, { dur: 0.7 });
      g.audio.play('miss');
      return;
    }
    const crit = Math.random() < hero.crit;
    let dmg = rndInt(hero.dmgMin, hero.dmgMax);
    if (target.def.family === 'Нечисть') dmg *= 1 + hero.vsNechist;
    if (crit) dmg *= hero.critMult;
    dmg = Math.floor(dmg);
    const dir = [target.x - hero.x, target.y - hero.y];
    const done = target.takeDamage(dmg, g, 'melee', hero, { crit, kbDir: dir, kb: crit ? 0.5 : 0.28 });
    if (hero.fireDmg && !target.dead) target.takeDamage(hero.fireDmg, g, 'fire', hero);
    if (hero.coldDmg && !target.dead) target.takeDamage(hero.coldDmg, g, 'cold', hero);
    if (hero.lifesteal) hero.hp = Math.min(hero.maxHp, hero.hp + done * hero.lifesteal);
    g.hitStop(crit ? HIT_STOP * 1.6 : HIT_STOP);
    if (crit) g.shake(1.5, 0.12);
    g.audio.play(crit ? 'crit' : 'hit');
  }

  castSkill(hero, tx, ty) {
    const sk = SKILLS.fire_serpent;
    let dx = tx - hero.x, dy = ty - hero.y;
    const d = Math.hypot(dx, dy) || 1;
    dx /= d; dy /= d;
    this.projectiles.push({
      x: hero.x + dx * 0.35, y: hero.y + dy * 0.35, vx: dx * sk.speed, vy: dy * sk.speed,
      travelled: 0, range: sk.range, r: 0.18, dmg: [hero.skillMin, hero.skillMax], t: 0, trail: [],
    });
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

  update(dt) {
    const g = this.game;
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
          if (!h.dead && Math.hypot(h.x - p.x, h.y - p.y) < h.r + p.r) {
            p.dead = true;
            g.fx.burst(p.x, p.y, PAL.ember, 8, 20, 50);
            h.takeDamage(rndInt(p.dmg[0], p.dmg[1]), g, p.element, null);
          }
          continue;
        }
        if (g.map.opaqueAt(p.x, p.y)) { p.x = ox; p.y = oy; this.explode(p); break; }     // упёрся в стену — взрыв перед ней
        if (p.travelled >= p.range) { this.explode(p); break; }
        for (const e of g.enemies) {
          if (!e.dead && Math.hypot(e.x - p.x, e.y - p.y) < e.r + p.r) { this.explode(p); break; }
        }
      }
      p.trail.push([p.x, p.y]); if (p.trail.length > 6) p.trail.shift();
      if (!p.dead && Math.random() < (p.coal ? 0.3 : 0.6)) g.fx.parts.push({ x: p.x, y: p.y, ox: 0, oy: -22, vx: 0, vy: -10, g: 0, t: 0, dur: 0.3, color: Math.random() < 0.5 ? PAL.ember : PAL.flame, size: 1 });
    }
    this.projectiles = this.projectiles.filter((p) => !p.dead);
  }

  fizzle(p) {
    p.dead = true;
    this.game.fx.burst(p.x, p.y, PAL.ember, 5, 16, 30);
  }

  explode(p) {
    const g = this.game, sk = SKILLS.fire_serpent;
    p.dead = true;
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
    this.lastBlast = { x: p.x, y: p.y, hit, blocked, t: g.time };
  }
}
