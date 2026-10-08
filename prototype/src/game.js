// Игра: состояние, обновление, ввод -> команды герою, спавн нечисти, смерть и возвращение у крады, отрисовка.
import { VIEW_W, VIEW_H, PLAYFIELD_CY, MAP_SEED, DEBUG } from './config.js';
import { PAL } from './palette.js';
import { w2s, s2w } from './core/iso.js';
import { Input } from './core/input.js';
import { textWidth } from './core/font.js';
import { generateMap } from './world/map.js';
import { moveWithCollision, circleFree, setActors, sightClear, lineWalkable } from './world/collision.js';
import { Hero } from './entities/hero.js';
import { Enemy } from './entities/enemy.js';
import { FX } from './systems/fx.js';
import { Log } from './systems/log.js';
import { Combat } from './systems/combat.js';
import { Loot, itemColor } from './systems/loot.js';
import { Audio } from './systems/audio.js';
import { WorldRenderer } from './render/world.js';
import { Minimap } from './render/minimap.js';
import { drawHud, drawHudTooltip, drawCursor, isOverHud, beltSlotAt, buttonAt, BTN } from './render/hud.js';
import { drawDeath, drawPause, overDeathButton, pauseButtonAt } from './render/screens.js';
import { InventoryUI } from './ui/windows.js';
import { xpPenalty, xpToNext, S as STATS } from './data/progression.js';
import { enemyStats } from './data/enemies.js';
import { CFG } from './data/config.js';
import { UI_ATLAS } from './ui/assets.js';
import { makeItem, makePotion, rollItem } from './data/items.js';
import { rnd } from './core/math.js';

const LS_LABELS = 'byl_nebyl_labels';

export class Game {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.input = new Input(canvas);
    this.audio = new Audio();
    this.input.onGesture = () => this.audio.unlock();
    this.debug = DEBUG;
    this.zone = CFG.zones.zalesye;
    this.map = generateMap(MAP_SEED, this.zone);
    this.renderer = new WorldRenderer(this.map);
    this.fps = 60;
    this.labelsAlways = false;
    try { this.labelsAlways = localStorage.getItem(LS_LABELS) === '1'; } catch (e) { /* нет localStorage */ }
    this.showMinimap = true;
    this.counters = { hitStop: 0, shake: 0 };
    // для автотестов и отладки из консоли
    this.dbg = { circleFree, sightClear, lineWalkable, enemyStats, xpToNext, CFG, UI_ATLAS };
    window.addEventListener('blur', () => { if (this.state === 'play') this.paused = true; });   // GDD §4.1: потеря фокуса — пауза
    this.reset();
  }

  reset() {
    this.time = 0;
    this.state = 'play';
    this.paused = false;
    this.mapOverlay = false;
    this.deathT = 0;
    this.deaths = 0;
    this.deathInfo = null;
    this.hero = new Hero(this.map.start.x, this.map.start.y);
    this.fx = new FX();
    this.log = new Log();
    this.combat = new Combat(this);
    this.loot = new Loot(this);
    this.minimap = new Minimap(this.map);
    this.ui = new InventoryUI(this);
    this.enemies = [];
    this.killsTotal = 0;
    this.map.packs.forEach((_, i) => this.spawnPack(i));
    this.enemyTotal = this.enemies.length;
    this.cam = { x: 0, y: 0 };
    this.camCX = VIEW_W / 2; this.camCY = PLAYFIELD_CY;
    this.shakeX = 0; this.shakeY = 0; this.shakeT = 0; this.shakeDur = 0; this.shakeAmp = 0;
    this.hitStopT = 0;
    this.updateCamera();
    this.hoverEnemy = null; this.hoverLabel = null; this.hoverGround = null; this.hoverBelt = -1;
    this.labelRects = [];
    this.lastTarget = null;
    this.leftMode = null; this.holdT = 0;
    this.notice = null; this._noticeKeys = {};
    this.log.add('Ратибор пришёл в Залесье. Очисти округу от нечисти!', PAL.bronze_hi);
  }

  spawnPack(i, kinds = null) {
    const p = this.map.packs[i];
    let n = 0;
    for (const kind of kinds || p.kinds) {
      for (let tries = 0; tries < 40; tries++) {
        const x = p.x + rnd(-1.6, 1.6), y = p.y + rnd(-1.6, 1.6);
        if (!this.map.isReachableAt(x, y) || !circleFree(this.map, x, y, 0.36)) continue;
        if (this.enemies.some((e) => !e.dead && Math.hypot(e.x - x, e.y - y) < e.r + 0.4)) continue;
        this.enemies.push(new Enemy(kind, x, y, i, p.mlvl || 1)); n++;
        break;
      }
    }
    return n;
  }

  // --- координаты
  toS(x, y) {
    const [ix, iy] = w2s(x, y);
    return [Math.round(ix - this.cam.x + this.camCX + this.shakeX), Math.round(iy - this.cam.y + this.camCY + this.shakeY)];
  }
  toWorld(mx, my) { return s2w(mx - this.camCX + this.cam.x, my - this.camCY + this.cam.y); }
  // для автотестов: экранные (client) координаты мировой точки / нативной точки экрана
  clientOf(x, y, lift = 0) {
    const [sx, sy] = this.toS(x, y);
    return this.clientOfScreen(sx, sy - lift);
  }
  clientOfScreen(sx, sy) {
    const r = this.canvas.getBoundingClientRect();
    return [r.left + ((sx + 0.5) * r.width) / VIEW_W, r.top + ((sy + 0.5) * r.height) / VIEW_H];
  }
  updateCamera() {
    const [ix, iy] = w2s(this.hero.x, this.hero.y);
    this.cam.x = Math.round(ix); this.cam.y = Math.round(iy);
    // открыта одна панель — герой смещается в свободную половину экрана (как в D2)
    const ui = this.ui;
    this.camCX = ui.invOpen && !ui.charOpen ? 161 : ui.charOpen && !ui.invOpen ? 479 : VIEW_W / 2;
  }
  get topRightVisible() { return !this.ui.invOpen && !this.mapOverlay; }
  get labelsShown() { return this.labelsAlways || this.input.altHeld; }

  // --- «сочность» удара
  hitStop(t) { this.counters.hitStop++; this.hitStopT = Math.max(this.hitStopT, t); }
  shake(px, t) { this.counters.shake++; this.shakeAmp = Math.max(this.shakeAmp, px); this.shakeT = Math.max(this.shakeT, t); this.shakeDur = Math.max(this.shakeDur, t); }

  notify(text, color, key) {
    if (key && this._noticeKeys[key] && this.time - this._noticeKeys[key] < 1.2) return;
    if (key) this._noticeKeys[key] = this.time;
    this.notice = { text, color, t: this.time };
  }

  // --- события
  onEnemyKilled(e) {
    this.killsTotal++;
    const h = this.hero;
    h.kills++;
    const xp = Math.max(1, Math.round(e.xp * xpPenalty(h.level, e.mlvl)));
    this.fx.text(e.x, e.y, '+' + xp + ' опыта', PAL.bronze_lt, e.def.height + 16, { dur: 1.1 });
    this.audio.play('kill');
    h.gainXp(xp, this);
    this.loot.dropFrom(e);
    // GDD §5.2: анчутки при гибели сородича рядом с шансом 30% с визгом удирают на 3 с
    for (const o of this.enemies) {
      const f = o.def.fear;
      if (!f || o.dead || o === e || o.state === 'flee' || o.state === 'idle') continue;
      if (Math.hypot(o.x - e.x, o.y - e.y) <= f.radius && Math.random() < f.chance) {
        o.scare(o.x - h.x, o.y - h.y, f.time);
        this.fx.text(o.x, o.y, 'И-и-и!', PAL.nebyl, o.def.height + 10, { dur: 0.8 });
      }
    }
  }
  onLevelUp(h) {
    this.log.add('Новый уровень: ' + h.level + '! +5 очков свойств (C).', PAL.bronze_hi);
    this.fx.text(h.x, h.y, 'Новый уровень!', PAL.bronze_hi, 60, { dur: 1.8, big: true });
    this.fx.rise(h.x, h.y, PAL.bronze_hi, 26, 40);
    this.audio.play('levelup');
  }
  onHeroDeath() {
    const h = this.hero;
    this.state = 'dead';
    this.deathT = 0;
    this.deaths++;
    // GDD §4.5: −10% серебра при себе (вверх), опыт и вещи остаются
    const lost = Math.ceil(h.silver * STATS.death.silverLossPct / 100);
    h.silver -= lost;
    this.deathInfo = { lost, x: h.x, y: h.y };
    this.ui.closeAll();
    this.mapOverlay = false;
    this.audio.play('death');
    this.log.add('Ратибор пал…' + (lost ? ' Потеряно ' + lost + ' серебра.' : ''), PAL.red_lt);
  }
  /** Возвращение у крады (замена Ладоги в однозонном прототипе): полные жизнь и Ярь, 2 с неуязвимости.
   *  Нечисть теряет след; перебитые стаи собираются заново (замена правила GDD «при повторном входе в зону»). */
  respawnHero() {
    const h = this.hero, k = this.map.krada;
    let spot = null;
    for (let ring = 1.6; ring < 5 && !spot; ring += 0.5) {
      for (let a = 0; a < 16; a++) {
        const ang = Math.PI * 0.25 + (a / 16) * Math.PI * 2;
        const x = k.x + Math.cos(ang) * ring, y = k.y + Math.sin(ang) * ring;
        if (circleFree(this.map, x, y, h.r + 0.05) && this.map.isReachableAt(x, y)) { spot = [x, y]; break; }
      }
    }
    if (!spot) spot = [this.map.start.x, this.map.start.y];
    h.x = spot[0]; h.y = spot[1];
    h.dead = false;
    h.hp = h.maxHp; h.yar = h.maxYar;
    h.cmd = null; h.action = null; h.path = null; h.moving = false; h.kb = null; h.stun = 0; h.effects = [];
    h.invuln = STATS.death.respawnInvuln;
    h.face(1, 1);
    for (const e of this.enemies) if (!e.dead && e.state !== 'idle') { e.state = 'return'; e.path = null; }
    const back = this.repopulate();
    this.state = 'play';
    this.deathT = 0;
    this.lastTarget = null;
    this.updateCamera();
    this.fx.ring(h.x, h.y, 1.2, PAL.flame, 0.6);
    this.fx.rise(h.x, h.y, PAL.ember, 20, 36);
    this.audio.play('respawn');
    this.log.add('Ратибор очнулся у крады.', PAL.flame);
    if (back) this.log.add('Нечисть снова собралась в округе (' + back + ').', PAL.nebyl);
  }
  // стаи добираются до исходного состава; трупы убираются
  repopulate() {
    this.enemies = this.enemies.filter((e) => !e.dead);
    let n = 0;
    this.map.packs.forEach((p, i) => {
      const alive = this.enemies.filter((e) => e.pack === i).map((e) => e.kind);
      const need = [...p.kinds];
      for (const k of alive) { const j = need.indexOf(k); if (j >= 0) need.splice(j, 1); }
      if (need.length) n += this.spawnPack(i, need);
    });
    this.enemyTotal += n;
    return n;
  }

  // --- наведение мыши
  computeHover() {
    const m = this.input, ui = this.ui;
    if (ui.anyOpen && !this.paused) ui.computeHover(m.mx, m.my); else ui.hover = {};
    this.overHud = isOverHud(m.mx, m.my, this);
    this.overUi = this.overHud || ui.over(m.mx, m.my);
    this.hoverBelt = this.state === 'play' && !ui.over(m.mx, m.my) ? beltSlotAt(m.mx, m.my) : -1;
    this.hoverEnemy = null; this.hoverGround = null;
    if (this.overUi || this.state !== 'play' || this.paused || ui.hand) { this.hoverLabel = null; return; }
    this.hoverLabel = null;
    for (const r of this.labelRects) if (!r.item.taken && m.mx >= r.x && m.mx < r.x + r.w && m.my >= r.y && m.my < r.y + r.h) this.hoverLabel = r.item;
    if (this.hoverLabel) return;
    // предмет под курсором (без Alt подписывается только он)
    let bestG = null, bg = 1e9;
    for (const it of this.loot.items) {
      if (it.dropT < 0.3) continue;
      const [sx, sy] = this.toS(it.x, it.y);
      const dx = m.mx - sx, dy = m.my - sy;
      const lw = textWidth(it.label) / 2 + 4;
      const onSprite = Math.abs(dx) <= 10 && dy >= -14 && dy <= 4;
      const onLabel = this._lastGround === it && Math.abs(dx) <= lw && dy >= -27 && dy <= -12;
      if ((onSprite || onLabel) && Math.abs(dx) + Math.abs(dy) < bg) { bg = Math.abs(dx) + Math.abs(dy); bestG = it; }
    }
    this.hoverGround = this._lastGround = bestG;
    if (bestG) return;
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

  menuButton(i) {
    const key = BTN.keys[i];
    if (key === 'C') this.ui.toggleChar();
    else if (key === 'I') this.ui.toggleInv();
    else if (key === 'M') { this.mapOverlay = !this.mapOverlay; this.audio.play('ui'); }
    else if (key === 'ESC') { this.paused = true; this.audio.play('ui'); }
    else { this.notify(BTN.labels[i] + ' — в следующей итерации', PAL.mist, 'soon'); this.audio.play('ui'); }
  }

  handleInput(dt) {
    const inp = this.input, h = this.hero, ui = this.ui;
    // переключатели, работающие всегда
    if (inp.pressed('KeyN')) { const m = this.audio.toggle(); this.notify(m ? 'Звук выключен' : 'Звук включён', PAL.mist, 'snd'); }
    if (inp.pressed('KeyZ')) this.toggleLabels();
    if (this.state === 'dead') {
      if (this.deathT > 1.5 && ((inp.leftPressed && overDeathButton(inp)) || inp.pressed('Enter') || inp.pressed('Space'))) this.respawnHero();
      return;
    }
    if (inp.pressed('Escape')) {
      if (this.paused) this.paused = false;
      else if (this.mapOverlay) this.mapOverlay = false;
      else if (!ui.closeAll()) this.paused = true;
    }
    if (this.paused) {
      if (inp.leftPressed) {
        const b = pauseButtonAt(inp);
        if (b === 'sound') this.audio.toggle();
        else if (b === 'labels') this.toggleLabels();
        else if (b === 'minimap') this.showMinimap = !this.showMinimap;
        if (b) this.audio.play('ui');
      }
      return;
    }
    if (inp.pressed('Tab') || inp.pressed('KeyM')) this.mapOverlay = !this.mapOverlay;
    if (inp.pressed('KeyI') || inp.pressed('KeyB')) ui.toggleInv();
    if (inp.pressed('KeyC')) ui.toggleChar();
    if (inp.pressed('KeyT')) this.notify('Навыки — в следующей итерации', PAL.mist, 'soon');
    if (inp.pressed('KeyJ')) this.notify('Летопись — в следующей итерации', PAL.mist, 'soon');
    ['Digit1', 'Digit2', 'Digit3', 'Digit4'].forEach((k, i) => { if (inp.pressed(k)) h.drink(i, this); });

    // окна забирают клики на себя
    if ((ui.anyOpen || ui.hand) && (inp.leftPressed || inp.leftReleased || inp.rightPressed)) {
      if (ui.handle(inp)) { this.leftMode = null; return; }
    }
    if (inp.leftPressed) {
      this.leftMode = null;
      const hb = this.topRightVisible ? buttonAt(inp.mx, inp.my) : -1;
      if (hb >= 0) this.menuButton(hb);
      else if (this.hoverBelt >= 0) h.drink(this.hoverBelt, this);
      else if (this.overUi) { /* клик по HUD */ }
      else if (this.hoverLabel || this.hoverGround) { h.pickup(this.hoverLabel || this.hoverGround); this.leftMode = 'pickup'; }
      else if (this.hoverEnemy) { h.attack(this.hoverEnemy, inp.shift); this.lastTarget = this.hoverEnemy; this.leftMode = 'attack'; }
      else if (inp.shift) { h.stop(); const [wx, wy] = this.toWorld(inp.mx, inp.my); h.face(wx - h.x, wy - h.y); }
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
          else h.cmd = { type: 'move', x: wx, y: wy, retries: 0 };
        }
      }
    } else this.leftMode = null;
    if (h.cmd && h.cmd.type === 'attack') h.cmd.repeat = inp.left && this.leftMode === 'attack';

    if ((inp.rightPressed || inp.right) && !this.overUi && !ui.hand) {
      const t = this.hoverEnemy;
      const [wx, wy] = t ? [t.x, t.y] : this.toWorld(inp.mx, inp.my);
      if (h.tryCast(this, wx, wy) && t) this.lastTarget = t;
    }
  }

  toggleLabels() {
    this.labelsAlways = !this.labelsAlways;
    try { localStorage.setItem(LS_LABELS, this.labelsAlways ? '1' : '0'); } catch (e) { /* нет localStorage */ }
    this.notify(this.labelsAlways ? 'Подписи добычи: всегда' : 'Подписи добычи: по Alt', PAL.mist, 'lbl');
  }

  update(dt) {
    this.computeHover();
    this.handleInput(dt);
    this.updateCamera();
    if (this.paused) return;
    this.time += dt;
    // тряска
    if (this.shakeT > 0) {
      this.shakeT = Math.max(0, this.shakeT - dt);
      const a = this.shakeAmp * (this.shakeT / Math.max(1e-3, this.shakeDur));
      this.shakeX = Math.round((Math.random() * 2 - 1) * a); this.shakeY = Math.round((Math.random() * 2 - 1) * a * 0.6);
      if (this.shakeT === 0) { this.shakeAmp = 0; this.shakeDur = 0; this.shakeX = this.shakeY = 0; }
    }
    // стоп-кадр при попадании: мир замирает на ~50 мс
    if (this.hitStopT > 0) { this.hitStopT -= dt; this.fx.update(dt * 0.25); return; }
    if (this.state === 'dead') this.deathT += dt;
    setActors([this.hero, ...this.enemies].filter((a) => !a.dead));
    this.hero.update(dt, this);
    for (const e of this.enemies) e.update(dt, this);
    this.separate();
    this.combat.update(dt);
    this.loot.update(dt);
    this.fx.update(dt);
    this.log.update(dt);
    this.enemies = this.enemies.filter((e) => !e.dead || e.corpseT < 10);
    this.updateCamera();
    this.minimap.reveal(this.hero.x, this.hero.y);
  }

  // страховка: если тела всё же перекрылись (отбрасывание, спавн) — мягко раздвигаем, только по стенам
  separate() {
    const list = this.enemies.filter((e) => !e.dead);
    const h = this.hero;
    for (let i = 0; i < list.length; i++) {
      const a = list[i];
      for (let j = i + 1; j < list.length; j++) {
        const b = list[j];
        const dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy), min = a.r + b.r;
        if (d < min - 0.02 && d > 1e-4) {
          const push = Math.min(0.05, (min - d) / 2);
          moveWithCollision(this.map, a, (-dx / d) * push, (-dy / d) * push, false);
          moveWithCollision(this.map, b, (dx / d) * push, (dy / d) * push, false);
        }
      }
      if (!h.dead) {
        const dx = a.x - h.x, dy = a.y - h.y, d = Math.hypot(dx, dy), min = a.r + h.r;
        if (d < min - 0.02 && d > 1e-4) moveWithCollision(this.map, a, (dx / d) * Math.min(0.08, min - d), (dy / d) * Math.min(0.08, min - d), false);
      }
    }
  }

  render() {
    const ctx = this.ctx;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.imageSmoothingEnabled = false;
    this.renderer.render(ctx, this);
    if (this.mapOverlay) this.minimap.drawOverlay(ctx, this);
    drawHud(ctx, this);
    this.ui.draw(ctx);
    if (!this.ui.over(this.input.mx, this.input.my)) drawHudTooltip(ctx, this);
    if (this.state === 'dead') drawDeath(ctx, this);
    if (this.paused) drawPause(ctx, this);
    drawCursor(ctx, this);
  }

  frame(dt) {
    this.fps = this.fps * 0.95 + (1 / Math.max(dt, 1e-3)) * 0.05;
    this.update(dt);
    this.render();
    this.input.endFrame();
  }

  // --- отладка и автотесты (window.__game)
  give(baseId, rarity = 'normal', opts = {}) {
    const it = baseId.startsWith('potion:') ? makePotion(baseId.slice(7)) : makeItem(baseId, rarity, opts.ilvl || 6, Math.random, opts);
    if (!this.hero.inv.autoAdd(it)) return null;
    return it;
  }
  dropRandom(ilvl = 3) { const it = rollItem(ilvl); this.loot.spawnItem(this.hero.x + 1, this.hero.y, it); return it; }
  itemColorOf(it) { return itemColor(it); }
}

