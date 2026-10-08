// Селяне и Мал (act1, М1): выходят из выбитой избы и бегут к цели (селяне — к пристани/краде, Мал — к тропе), потом исчезают.
import { Actor } from './actor.js';

export class Npc extends Actor {
  constructor(kind, x, y, opts = {}) {
    super(x, y, 0.25);
    this.kind = kind;               // 'villager' | 'mal'
    this.name = opts.name || '';
    this.female = !!opts.female; this.old = !!opts.old;
    this.def = { height: kind === 'mal' ? 30 : 38 };
    this.speed = opts.speed || 3.2;
    this.target = null;             // [x, y] — куда бежать
    this.wait = opts.wait || 0;     // сколько стоять перед бегом (с)
    this.life = opts.life || 9;     // через сколько секунд бега растаять
    this.t = 0; this.alpha = 1; this.gone = false;
  }
  runTo(x, y, wait = 0) { this.target = [x, y]; this.wait = wait; this.path = null; this.t = 0; }
  update(dt, game) {
    if (this.gone) return;
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
}
