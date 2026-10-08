// Игра: состояние, обновление, ввод -> команды герою, спавн нечисти, смерть/рестарт, отрисовка.
import { VIEW_W, VIEW_H, PLAYFIELD_CY, MAP_SEED, DEBUG } from './config.js';
import { PAL } from './palette.js';
import { w2s, s2w } from './core/iso.js';
import { Input } from './core/input.js';
import { generateMap } from './world/map.js';
import { moveWithCollision, circleFree } from './world/collision.js';
import { Hero } from './entities/hero.js';
import { Enemy } from './entities/enemy.js';
import { FX } from './systems/fx.js';
import { Log } from './systems/log.js';
import { Combat } from './systems/combat.js';
import { Loot } from './systems/loot.js';
import { WorldRenderer } from './render/world.js';
import { drawHud, drawCursor, isOverHud, beltSlotAt } from './render/hud.js';
import { drawDeath, drawPause, drawInventory, INV_RECT } from './render/screens.js';
import { rnd } from './core/math.js';

const RESPAWN_DELAY = 40;

export class Game {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.input = new Input(canvas);
    this.debug = DEBUG;
    this.map = generateMap(MAP_SEED);
    this.renderer = new WorldRenderer(this.map);
    this.fps = 60;
    this.reset();
  }

  reset() {
    this.time = 0;
    this.state = 'play';
    this.paused = false;
    this.showInv = false;
    this.deathT = 0;
    this.hero = new Hero(this.map.start.x, this.map.start.y);
    this.fx = new FX();
    this.log = new Log();
    this.combat = new Combat(this);
    this.loot = new Loot(this);
    this.enemies = [];
    this.killsTotal = 0;
    this.packCleared = new Map();
    this.map.packs.forEach((_, i) => this.spawnPack(i));
    this.enemyTotal = this.enemies.length;
    this.cam = { x: 0, y: 0 };
    this.camCY = PLAYFIELD_CY;
    this.updateCamera();
    this.hoverEnemy = null; this.hoverLabel = null; this.hoverBelt = -1;
    this.labelRects = [];
    this.lastTarget = null;
    this.leftMode = null; this.holdT = 0;
    this.notice = null; this._noticeKeys = {};
    this.log.add('Ратибор пришёл в Залесье. Упокой нечисть!', PAL.bronze_hi);
  }

  spawnPack(i) {
    const p = this.map.packs[i];
    let n = 0;
    for (const kind of p.kinds) {
      for (let tries = 0; tries < 30; tries++) {
        const x = p.x + rnd(-1.6, 1.6), y = p.y + rnd(-1.6, 1.6);
        if (!this.map.isReachable(Math.floor(x), Math.floor(y)) || !circleFree(this.map, x, y, 0.35)) continue;
        this.enemies.push(new Enemy(kind, x, y, i)); n++;
        break;
      }
    }
    return n;
  }

  // --- координаты
  toS(x, y) {
    const [ix, iy] = w2s(x, y);
    return [Math.round(ix - this.cam.x + VIEW_W / 2), Math.round(iy - this.cam.y + this.camCY)];
  }
  toWorld(mx, my) { return s2w(mx - VIEW_W / 2 + this.cam.x, my - this.camCY + this.cam.y); }
  // для автотестов: экранные (client) координаты мировой точки
  clientOf(x, y, lift = 0) {
    const [sx, sy] = this.toS(x, y);
    const r = this.canvas.getBoundingClientRect();
    return [r.left + (sx * r.width) / VIEW_W, r.top + ((sy - lift) * r.height) / VIEW_H];
  }
  updateCamera() {
    const [ix, iy] = w2s(this.hero.x, this.hero.y);
    this.cam.x = Math.round(ix); this.cam.y = Math.round(iy);
  }

  notify(text, color, key) {
    if (key && this._noticeKeys[key] && this.time - this._noticeKeys[key] < 1.2) return;
    if (key) this._noticeKeys[key] = this.time;
    this.notice = { text, color, t: this.time };
  }

  // --- события
  onEnemyKilled(e) {
    this.killsTotal++;
    this.hero.kills++;
    this.fx.text(e.x, e.y, '+' + e.def.xp + ' опыта', PAL.bronze_lt, e.def.height + 16, { dur: 1.1 });
    this.hero.gainXp(e.def.xp, this);
    this.loot.dropFrom(e);
  }
  onLevelUp(h) {
    this.log.add('Новый уровень: ' + h.level + '! Жизнь и Ярь восполнены.', PAL.bronze_hi);
    this.fx.text(h.x, h.y, 'Новый уровень!', PAL.bronze_hi, 60, { dur: 1.8, big: true });
    this.fx.rise(h.x, h.y, PAL.bronze_hi, 26, 40);
  }
  onHeroDeath() {
    this.state = 'dead';
    this.deathT = 0;
    this.showInv = false;
    this.log.add('Ратибор пал…', PAL.red_lt);
  }

  // --- наведение мыши
  computeHover() {
    const m = this.input;
    this.hoverBelt = this.state === 'play' ? beltSlotAt(m.mx, m.my) : -1;
    this.hoverEnemy = null;
    this.overUi = isOverHud(m.mx, m.my) || (this.showInv && m.mx >= INV_RECT.x && m.my >= INV_RECT.y && m.mx < INV_RECT.x + INV_RECT.w && m.my < INV_RECT.y + INV_RECT.h);
    if (this.overUi || this.state !== 'play') { this.hoverLabel = null; return; }
    this.hoverLabel = null;
    for (const r of this.labelRects) if (!r.item.taken && m.mx >= r.x && m.mx < r.x + r.w && m.my >= r.y && m.my < r.y + r.h) this.hoverLabel = r.item;
    if (this.hoverLabel) return;
    let best = null, bd = -Infinity;
    for (const e of this.enemies) {
      if (e.dead) continue;
      const [sx, sy] = this.toS(e.x, e.y);
      const hw = e.kind === 'upyr' ? 11 : 8;
      if (Math.abs(m.mx - sx) <= hw && m.my >= sy - e.def.height - 3 && m.my <= sy + 3) {
        if (e.x + e.y > bd) { bd = e.x + e.y; best = e; }
      }
    }
    if (!best) {
      const [wx, wy] = this.toWorld(m.mx, m.my);
      let bdist = 0.6;
      for (const e of this.enemies) if (!e.dead) { const d = Math.hypot(e.x - wx, e.y - wy); if (d < bdist) { bdist = d; best = e; } }
    }
    this.hoverEnemy = best;
  }

  handleInput(dt) {
    const inp = this.input, h = this.hero;
    if (this.state === 'dead') {
      if (this.deathT > 1.5 && (inp.leftPressed || inp.pressed('Enter') || inp.pressed('Space'))) this.reset();
      return;
    }
    if (inp.pressed('Escape')) {
      if (this.showInv) this.showInv = false; else this.paused = !this.paused;
    }
    if (this.paused) return;
    if (inp.pressed('KeyI') || inp.pressed('KeyC') || inp.pressed('KeyB')) this.showInv = !this.showInv;
    ['Digit1', 'Digit2', 'Digit3', 'Digit4'].forEach((k, i) => { if (inp.pressed(k)) h.drink(i, this); });

    if (inp.leftPressed) {
      this.leftMode = null;
      if (this.hoverBelt >= 0) h.drink(this.hoverBelt, this);
      else if (this.overUi) { /* клик по HUD */ }
      else if (this.hoverLabel) { h.pickup(this.hoverLabel); this.leftMode = 'pickup'; }
      else if (this.hoverEnemy) { h.attack(this.hoverEnemy); this.lastTarget = this.hoverEnemy; this.leftMode = 'attack'; }
      else {
        const [wx, wy] = this.toWorld(inp.mx, inp.my);
        h.moveTo(this.map, wx, wy);
        this.fx.ring(wx, wy, 0.35, PAL.bronze_lt, 0.3);
        this.leftMode = 'move'; this.holdT = 0;
      }
    } else if (inp.left) {
      if (this.leftMode === 'move' && !this.overUi) {
        this.holdT += dt;
        if (this.holdT >= 0.12) {
          this.holdT = 0;
          const [wx, wy] = this.toWorld(inp.mx, inp.my);
          if (!h.action) h.moveTo(this.map, wx, wy);
          else h.cmd = { type: 'move', x: wx, y: wy };
        }
      }
    } else this.leftMode = null;
    if (h.cmd && h.cmd.type === 'attack') h.cmd.repeat = inp.left && this.leftMode === 'attack';

    if ((inp.rightPressed || inp.right) && !this.overUi) {
      const t = this.hoverEnemy;
      const [wx, wy] = t ? [t.x, t.y] : this.toWorld(inp.mx, inp.my);
      if (h.tryCast(this, wx, wy) && t) this.lastTarget = t;
    }
  }

  update(dt) {
    this.computeHover();
    this.handleInput(dt);
    if (this.paused) return;
    this.time += dt;
    if (this.state === 'dead') this.deathT += dt;
    this.hero.update(dt, this);
    for (const e of this.enemies) e.update(dt, this);
    this.separate();
    this.combat.update(dt);
    this.loot.update(dt);
    this.fx.update(dt);
    this.log.update(dt);
    this.enemies = this.enemies.filter((e) => !e.dead || e.corpseT < 10);
    this.respawn(dt);
    this.updateCamera();
  }

  separate() {
    const list = this.enemies.filter((e) => !e.dead);
    for (let i = 0; i < list.length; i++) {
      const a = list[i];
      for (let j = i + 1; j < list.length; j++) {
        const b = list[j];
        const dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy), min = a.r + b.r;
        if (d < min && d > 1e-4) {
          const push = (min - d) / 2;
          moveWithCollision(this.map, a, (-dx / d) * push, (-dy / d) * push);
          moveWithCollision(this.map, b, (dx / d) * push, (dy / d) * push);
        }
      }
      const h = this.hero;
      if (!h.dead) {
        const dx = a.x - h.x, dy = a.y - h.y, d = Math.hypot(dx, dy), min = a.r + h.r;
        if (d < min && d > 1e-4) moveWithCollision(this.map, a, (dx / d) * (min - d), (dy / d) * (min - d));
      }
    }
  }

  respawn(dt) {
    this.map.packs.forEach((p, i) => {
      const alive = this.enemies.some((e) => e.pack === i && !e.dead);
      if (alive) { this.packCleared.delete(i); return; }
      const t = (this.packCleared.get(i) || 0) + dt;
      this.packCleared.set(i, t);
      if (t > RESPAWN_DELAY && Math.hypot(this.hero.x - p.x, this.hero.y - p.y) > 12 && this.state === 'play') {
        const n = this.spawnPack(i);
        this.enemyTotal += n;
        this.packCleared.delete(i);
        this.log.add('Нечисть снова собирается в округе…', PAL.nebyl);
      }
    });
  }

  render() {
    const ctx = this.ctx;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.imageSmoothingEnabled = false;
    this.renderer.render(ctx, this);
    drawHud(ctx, this);
    if (this.showInv) drawInventory(ctx, this);
    if (this.state === 'dead') drawDeath(ctx, this);
    if (this.paused) drawPause(ctx);
    drawCursor(ctx, this);
  }

  frame(dt) {
    this.fps = this.fps * 0.95 + (1 / Math.max(dt, 1e-3)) * 0.05;
    this.update(dt);
    this.render();
    this.input.endFrame();
  }
}
