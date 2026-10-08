// Селяне и Мал (act1, М1): выходят из выбитой избы и бегут к цели (селяне — к пристани/краде, Мал — к тропе), потом исчезают.
import { Actor } from './actor.js';
import { PAL } from '../palette.js';

export class Npc extends Actor {
  constructor(kind, x, y, opts = {}) {
    super(x, y, 0.25);
    this.kind = kind;               // 'villager' | 'mal' | 'town'
    this.name = opts.name || '';
    this.role = opts.role || '';
    this.grey = !!opts.grey;
    this.female = !!opts.female; this.old = !!opts.old;
    this.route = opts.route || null;
    this.stopR = opts.stop || 2;
    this.ri = 0; this.pause = 0; this.mark = '';
    this.def = { height: kind === 'mal' ? 30 : opts.height || 40 };
    this.speed = opts.speed || 3.2;
    this.target = null;             // [x, y] — куда бежать
    this.wait = opts.wait || 0;     // сколько стоять перед бегом (с)
    this.life = opts.life || 9;     // через сколько секунд бега растаять
    this.t = 0; this.alpha = 1; this.gone = false;
  }
  runTo(x, y, wait = 0) { this.target = [x, y]; this.wait = wait; this.path = null; this.t = 0; }
  update(dt, game) {
    if (this.gone) return;
    if (this.route) return this.followRoute(dt, game);
    if (!this.target) { this.moving = false; return; }
    if (this.wait > 0) { this.wait -= dt; this.moving = false; this.face(game.hero.x - this.x, game.hero.y - this.y); return; }
    this.t += dt;
    if (!this.path && !this.arrived) this.setPath(game.map, this.target[0], this.target[1]);
    if (!this.arrived && this.followPath(game.map, dt, this.speed)) this.arrived = true;
    if (this.arrived || this.t > this.life) {
      this.alpha -= dt / 0.8; this.moving = false;
      if (this.alpha <= 0) this.gone = true;
    }
  }

  /** Мал в Ладоге: круг из точек, пауза, стоп если герой ближе stopR (GDD §7.2). */
  followRoute(dt, game) {
    const h = game.hero;
    if (h && Math.hypot(h.x - this.x, h.y - this.y) <= this.stopR) {
      this.moving = false; this.path = null; this.face(h.x - this.x, h.y - this.y); return;
    }
    if (this.pause > 0) { this.pause -= dt; this.moving = false; return; }
    const p = this.route[this.ri % this.route.length];
    if (!this.path) this.setPath(game.map, p[0], p[1]);
    if (this.followPath(game.map, dt, this.speed) || Math.hypot(this.x - p[0], this.y - p[1]) < 0.4) {
      this.ri = (this.ri + 1) % this.route.length; this.pause = 5; this.path = null; this.moving = false;
    }
    const o = game.map.objects.find((x) => x.npc === this);
    if (o) { o.x = this.x; o.y = this.y; o.sx = this.x; o.sy = this.y + 0.7; }
  }
}

/** Соломенник: единственная цель удара в Ладоге. Не гибнет, опыта и добычи нет (GDD §7.2). */
export class Dummy extends Actor {
  constructor(x, y) {
    super(x, y, 0.35);
    this.dummy = true; this.dead = false; this.hp = this.maxHp = 1;
    this.dfn = 0; this.mlvl = 1; this.state = 'idle'; this.kind = 'dummy'; this.id = 9001;
    this.res = {}; this.hits = 0; this.name = '';
    this.def = { height: 36, mass: 99, family: '', name: '' };
  }
  update() { this.moving = false; this.state = 'idle'; this.hp = this.maxHp; this.dead = false; }
  takeDamage(amount, game) {
    const dmg = Math.max(1, Math.floor(amount));
    game.fx.text(this.x, this.y, String(dmg), PAL.linen, this.def.height + 6, {});
    game.fx.burst(this.x, this.y, PAL.birch, 4, 14);
    this.hits++;
    game.counters.dummyHits = (game.counters.dummyHits || 0) + 1;
    this.hp = this.maxHp; this.dead = false;
    return dmg;
  }
}
