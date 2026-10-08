// Игра: состояние, обновление, ввод -> команды герою, спавн нечисти, смерть и возвращение у крады, отрисовка.
import { ART, poseKrivsha, poseMara, poseAnchutka, poseUpyr, feedFrame } from './render/boss_art.js';
import { makeRng } from './core/rng.js';
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
import { drawHud, drawHudTooltip, drawCursor, isOverHud, beltSlotAt, buttonAt, hudSlotAt, BTN } from './render/hud.js';
import { drawDeath, drawPause, overDeathButton, pauseButtonAt } from './render/screens.js';
import { InventoryUI, compareLines } from './ui/windows.js';
import { TownUI } from './ui/town.js';
import { Inventory } from './systems/inventory.js';
import { gearPrice, sellPrice } from './systems/trade.js';
import { lightTint } from './render/world.js';
import { xpPenalty, xpToNext, hitChance, S as STATS } from './data/progression.js';
import { enemyStats } from './data/enemies.js';
import { CFG } from './data/config.js';
import { skillShort, rankBlock } from './data/skills.js';
import { UI_ATLAS } from './ui/assets.js';
import { makeItem, makePotion, rollItem, pickBase, makeUnique, itemLines } from './data/items.js';
import { dirOf } from './entities/actor.js';
import { rnd } from './core/math.js';
import { t, plural, silverText } from './core/i18n.js';
import { SKILLS, DASH, rankOf } from './data/skills.js';
import { Quest } from './systems/quest.js';
import { ZoneMixin } from './systems/zones.js';
import { KapishcheMixin } from './systems/kapishche.js';
import { PortalMixin } from './systems/portal.js';
import { enemyBark } from './entities/boss.js';

const LS_LABELS = 'byl_nebyl_labels';

/** Герой занят действием, которое не даёт начать навык ('skill') или рывок ('dash') — те же условия, что в hero.useSkill/dash. */
function heroBusy(h, what) {
  if (h.dashing || h.stun > 0) return true;
  if (!h.action) return false;
  if (what === 'dash') return !h.action.fired;
  return !(h.action.fired && h.action.t > h.action.dur * 0.85);   // конец замаха/каста: можно ставить следующий
}

export class Game {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.input = new Input(canvas);
    this.audio = new Audio();
    this.input.onGesture = () => this.audio.unlock();
    this.debug = DEBUG;
    this.fps = 60;
    this.labelsAlways = false;
    try { this.labelsAlways = localStorage.getItem(LS_LABELS) === '1'; } catch (e) { /* нет localStorage */ }
    this.showMinimap = true;
    this.counters = { hitStop: 0, shake: 0, backoff: 0, casts: {}, cdBlocked: 0, barks: 0, barksSuppressed: 0 };
    this.t = t;
    this._barks = {};
    // для автотестов и отладки из консоли
    this.dbg = { circleFree, sightClear, lineWalkable, enemyStats, xpToNext, CFG, UI_ATLAS, SKILLS, t, plural, silverText, pickBase, dirOf, rankOf, ART, poseKrivsha, poseMara, poseAnchutka, poseUpyr, feedFrame, cmp: (it) => compareLines(it, this.hero), itemLines, hitChance, short: skillShort, rankBlock, gearPrice, sellPrice, lightTint };
    // GDD §4.1, QA B-01: потеря фокуса или скрытая вкладка — пауза
    window.addEventListener('blur', () => { if (this.state === 'play') this.paused = true; });
    document.addEventListener('visibilitychange', () => { if (document.hidden && this.state === 'play') this.paused = true; });
    this.reset();
  }

  reset() {
    this.time = 0;
    this.state = 'play';
    this.paused = false;
    this.mapOverlay = false;
    this.deathT = 0;
    if (window.__seed != null) Math.random = makeRng(window.__seed);   // ?seed=N: новая игра повторяет случайность (QA B-14)
    this.deaths = 0;
    this.deathInfo = null;
    this.hero = new Hero(0, 0);
    this.fx = new FX();
    this.log = new Log();
    this.combat = new Combat(this);
    this.loot = new Loot(this);
    this.ui = new InventoryUI(this);
    this.stash = new Inventory(10, 8);
    this.stashSilver = 0;
    this.buyback = [];
    this.shops = null;
    this.shopGen = 0;
    this.town = new TownUI(this);
    this.quest = new Quest(this, 'm1');
    this.enemies = []; this.buried = []; this.npcs = [];
    this.dialogQ = []; this.dialogNext = 0; this.letter = null;
    this.killsTotal = 0;
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
    // зоны М1: у каждой своё состояние (systems/zones.js); начинаем в Залесье
    this.zoneStates = {}; this.zs = null; this.hoverObj = null; this.portal = null;
    this.enterZone('ladoga', 'start');
    this.log.add(this.zone.name + '. ' + t('quest.act') + ': «' + this.quest.title + '».', PAL.bronze_hi);
    // вводная миссии (act1): переносим по ширине журнала
    let line = '';
    for (const w of t('quest.m1.brief').split(' ')) {
      if (line && textWidth(line + ' ' + w) > 430) { this.log.add(line, PAL.birch); line = w; } else line = line ? line + ' ' + w : w;
    }
    if (line) this.log.add(line, PAL.birch);
  }

  spawnPack(i, kinds = null) {
    const p = this.map.packs[i];
    // волна (ambush): лежат под землёй, пока герой не подойдёт (systems/zones.js → updateZone)
    const into = p.ambush && !p.risen ? this.buried : this.enemies;
    let n = 0;
    for (const kind of kinds || p.kinds) {
      for (let tries = 0; tries < 40; tries++) {
        const x = p.x + rnd(-1.6, 1.6), y = p.y + rnd(-1.6, 1.6);
        if (!this.map.isReachableAt(x, y) || !circleFree(this.map, x, y, 0.36)) continue;
        if (into.some((e) => !e.dead && Math.hypot(e.x - x, e.y - y) < e.r + 0.4)) continue;
        into.push(new Enemy(kind, x, y, i, p.mlvl || 1)); n++;
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
    const ui = this.ui, left = ui.charOpen || (this.town && this.town.open), right = ui.rightOpen;
    this.camCX = right && !left ? 161 : left && !right ? 479 : VIEW_W / 2;
  }
  get topRightVisible() { return !this.ui.rightOpen && !this.mapOverlay; }
  get labelsShown() { return this.labelsAlways || this.input.altHeld; }

  // --- «сочность» удара
  hitStop(t) { this.counters.hitStop++; this.hitStopT = Math.max(this.hitStopT, t); }
  shake(px, t) { this.counters.shake++; this.shakeAmp = Math.max(this.shakeAmp, px); this.shakeT = Math.max(this.shakeT, t); this.shakeDur = Math.max(this.shakeDur, t); }

  notify(text, color, key, dur = null) {
    // повтор глушим, только если на экране уже это же сообщение (QA B-19)
    if (key && this._noticeKeys[key] && this.time - this._noticeKeys[key] < 1.2 && this.notice && this.notice.text === text) return;
    if (key) this._noticeKeys[key] = this.time;
    this.notice = { text, color, t: this.time, dur: dur || (key === 'tut' || key === 'tip' || key === 'locked' || key === 'relic' ? 3.5 : 1.6) };
  }

  // --- события
  onEnemyKilled(e) {
    this.killsTotal++;
    const h = this.hero;
    h.kills++;
    const xp = e.xp > 0 ? Math.max(1, Math.round(e.xp * xpPenalty(h.level, e.mlvl))) : 0;   // призванные Кривши — 0 (GDD v1.8)
    if (!h.dead && xp > 0) {
      this.fx.text(e.x, e.y, '+' + xp + ' опыта', PAL.bronze_lt, e.def.height + 16 + (this._xpStack = ((this._xpStack || 0) + 1) % 3) * 9, { dur: 1.1 });
      h.gainXp(xp, this);
    }
    this.audio.play('kill');
    if (!e.noLoot) this.loot.dropFrom(e);
    this.onEliteKilled(e);
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
  /** Элиты (GDD §5.3): «Жаркий» взрывается при смерти (r 1,5, телеграф 0,8 с); реплики былинных врагов; гибель вожака
   *  разгоняет анчуток стаи (§5.2); босс — в капище (systems/kapishche.js). */
  onEliteKilled(e) {
    const hot = e.modDefs && e.modDefs.hot;
    if (hot && hot.deathBlast) {
      const B = hot.deathBlast, dmg = Math.max(1, Math.round((e.dmgMin + Math.floor(Math.random() * (e.dmgMax - e.dmgMin + 1))) * B.dmgMul));
      this.combat.addTele({ shape: 'circle', x: e.x, y: e.y, r: B.r, dur: B.tele, keepOnDeath: true, onFire: (T) => {
        const h = this.hero; this.fx.burst(T.x, T.y, PAL.flame, 18, 10, 70); this.audio.play('explode'); this.counters.hotBlasts = (this.counters.hotBlasts || 0) + 1;
        if (!h.dead && Math.hypot(h.x - T.x, h.y - T.y) <= T.r + h.r * 0.5 && !this.safeAt(h.x, h.y)) h.takeDamage(dmg, this, 'fire', null);
      } });
    }
    if (e.def.barks && e.def.barks.death) enemyBark(this, e, e.def.barks.death);
    if (e.leader || e.special === 'mara' && e.kind === 'mara') {
      for (const o of this.enemies) if (!o.dead && o !== e && o.pack === e.pack && o.def.fear && o.state !== 'idle') { o.scare(o.x - this.hero.x, o.y - this.hero.y, o.def.fear.time); }
    }
    if (e.boss) this.onBossKilled(e);
  }
  onLevelUp(h) {
    this.log.add(t('ui.sys.level_up', { n: h.level }) + ' ' + t('ui.sys.level_points') + ' (C, T)', PAL.bronze_hi);
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
    this.combat.projectiles = this.combat.projectiles.filter((p) => p.hostile);   // снаряды героя гаснут (QA B-03)
    this.audio.play('death');
    this.log.add('Ратибор пал…' + (lost ? ' ' + silverText(lost, 'lost') + '.' : ''), PAL.red_lt);
    this.deathInfo.line = 'death.line' + (1 + Math.floor(Math.random() * 5));
  }
  /** Возвращение у крады (замена Ладоги в однозонном прототипе): полные жизнь и Ярь, 2 с неуязвимости.
   *  Нечисть теряет след; перебитые стаи собираются заново (замена правила GDD «при повторном входе в зону»). */
  respawnHero() {
    // гибель в другой зоне — возвращение к краде Залесья. GDD v1.7 §4.5: убитые не возвращаются (repopulate
    // «onNewSession»); старое правило прототипа «onHeroRespawn» оставлено для зон, где оно указано в данных
    for (const st of Object.values(this.zoneStates)) if (st.id !== 'zalesye' && CFG.zones[st.id] && CFG.zones[st.id].repopulate === 'onHeroRespawn') st.needRepop = true;
    // ответ дизайнера 08.10: у крады Залесья, пока не тронут Чуров камень у капища; после — у камня
    const RP = this.respawnPoint();
    if (this.zone.id !== RP.zone) this.enterZone(RP.zone, RP.entry, { respawn: true });
    const h = this.hero, k = this.map[RP.at] || this.map.krada;
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
    h.graceT = STATS.death.respawnInvuln;       // нечисть теряет след только на время «милости» возрождения (QA B-20)
    h.respawnProt = STATS.death.respawnInvulnBreaksOnAction !== false;   // снимается атакой или кастом (GDD v1.7)
    // QA B-24: гибель снимает баффы («Чур-оберег») и обнуляет перезарядки навыков, рывка и зелий
    h.buffs = {}; h.cds = {}; h.potionCds.hp = 0; h.potionCds.yar = 0; h.recalc();
    h.face(1, 1);
    // недобитые уходят к логову и восстанавливают HP, как по поводку (GDD v1.7 §4.5) — во всех зонах сессии
    for (const st of Object.values(this.zoneStates)) {
      const list = st === this.zs ? this.enemies : st.enemies || [];
      for (const e of list) if (!e.dead && e.state !== 'rise' && (e.state !== 'idle' || e.hp < e.maxHp)) { e.state = 'return'; e.path = null; }
    }
    const back = this.zone.repopulate === 'onHeroRespawn' ? this.repopulate() : 0;
    this.state = 'play';
    this.deathT = 0;
    this.lastTarget = null;
    this.updateCamera();
    this.fx.ring(h.x, h.y, 1.2, PAL.flame, 0.6);
    this.fx.rise(h.x, h.y, PAL.ember, 20, 36);
    this.audio.play('respawn');
    this.log.add(t(RP.log), PAL.flame);
    this.applyChad();
    if (back) this.log.add('Нечисть снова собралась в округе: ' + back + ' ' + plural(back, 'враг', 'врага', 'врагов') + '.', PAL.nebyl);
  }
  // стаи добираются до исходного состава; трупы убираются
  repopulate() {
    this.enemies = this.enemies.filter((e) => !e.dead);
    let n = 0;
    this.map.packs.forEach((p, i) => {
      const alive = [...this.enemies, ...this.buried].filter((e) => e.pack === i).map((e) => e.kind);
      const need = [...p.kinds];
      for (const k of alive) { const j = need.indexOf(k); if (j >= 0) need.splice(j, 1); }
      if (need.length) n += this.spawnPack(i, need);
    });
    return n;   // численность зоны (enemyTotal) не растёт — счётчик цели считает живых (QA B-06)
  }

  // --- наведение мыши
  computeHover() {
    const m = this.input, ui = this.ui;
    if (ui.anyOpen && !this.paused) ui.computeHover(m.mx, m.my); else ui.hover = {};
    this.overHud = isOverHud(m.mx, m.my, this);
    this.overUi = this.overHud || ui.over(m.mx, m.my);
    this.hoverBelt = this.state === 'play' && !ui.over(m.mx, m.my) ? beltSlotAt(m.mx, m.my) : -1;
    this.hoverEnemy = null; this.hoverGround = null; this.hoverObj = null;
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
      const hw = e.kind === 'upyr' ? 11 : e.def.torch ? 10 : 8;
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
    if (!best) this.hoverObj = this.objectAt(m.mx, m.my);
  }

  menuButton(i) {
    const key = BTN.keys[i];
    if (key === 'C') this.ui.toggleChar();
    else if (key === 'I') this.ui.toggleInv();
    else if (key === 'M') { this.mapOverlay = !this.mapOverlay; this.audio.play('ui'); }
    else if (key === 'T') this.ui.toggleSkills();
    else if (key === 'ESC') { this.paused = true; this.audio.play('ui'); }
    else { this.notify(BTN.labels[i] + ' — в следующей итерации', PAL.mist, 'soon'); this.audio.play('ui'); }
  }

  handleInput(dt) {
    const inp = this.input, h = this.hero, ui = this.ui;
    // переключатели, работающие всегда
    if (inp.pressed('KeyN')) { const m = this.audio.toggle(); this.notify(m ? 'Звук выключен' : 'Звук включён', PAL.mist, 'snd'); }
    if (inp.pressed('KeyZ')) this.toggleLabels();
    if (this.state === 'dead') {
      const D = STATS.death;
      if ((this.deathT > (D.buttonDelay ?? 1.5) && inp.leftPressed && overDeathButton(inp)) ||
          (this.deathT > (D.keyDelay ?? 2.5) && (inp.pressed('Enter') || inp.pressed('Space')))) this.respawnHero();
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
    if (inp.pressed('KeyT')) ui.toggleSkills();
    // F1–F6 (как в D2): над навыком в окне «Навыки» — положить его в ячейку; иначе — назначить навык ячейки на ПКМ
    for (let k = 0; k < 6; k++) if (inp.pressed('F' + (k + 1))) this.pressF(k);
    if (inp.wheel) this.cycleRmb(inp.wheel);
    // Пробел — «Рывок». Во время замаха/каста (до удара) нажатие запоминается и срабатывает, как только
    // действие отпустит героя (+0,3 с запаса), — QA B-23. Направление — по курсору в момент рывка.
    if (inp.pressed('Space')) {
      const [wx, wy] = this.toWorld(inp.mx, inp.my);
      const r = h.dash(this, wx, wy);
      if (r === 'cd') { this.counters.cdBlocked++; this.audio.play('error'); }
      else if (r === 'busy' && !h.dead) { this.dashBuf = { t: 0.3 }; this.rmbBuf = null; this.dropQueuedLmb(); this.counters.dashBuffered = (this.counters.dashBuffered || 0) + 1; }
      else this.dashBuf = null;
    } else if (this.dashBuf) {
      const b = this.dashBuf;
      if (h.dead) this.dashBuf = null;
      else if (!heroBusy(h, 'dash')) b.t -= dt;      // ждём, пока идёт замах; запас 0,3 с — после
      if (this.dashBuf && b.t <= 0) this.dashBuf = null;
      else if (this.dashBuf && !heroBusy(h, 'dash')) {
        const [wx, wy] = this.toWorld(inp.mx, inp.my);
        const r = h.dash(this, wx, wy);
        if (r !== 'busy') {
          this.dashBuf = null;
          if (r === 'ok') this.counters.dashBufferedFired = (this.counters.dashBufferedFired || 0) + 1;
          else if (r === 'cd') { this.counters.cdBlocked++; this.audio.play('error'); }
        }
      }
    }
    if (inp.pressed('KeyJ')) this.notify('Летопись — в следующей итерации', PAL.mist, 'soon');
    ['Digit1', 'Digit2', 'Digit3', 'Digit4'].forEach((k, i) => { if (inp.pressed(k)) h.drink(i, this); });

    // окна забирают клики на себя
    if ((ui.anyOpen || ui.hand) && (inp.leftPressed || inp.leftReleased || inp.rightPressed)) {
      if (ui.handle(inp)) { this.leftMode = null; return; }
    }
    if (inp.leftPressed) {
      this.leftMode = null;
      // GDD v1.7: ввод во время замаха/каста копится до конца действия, срабатывает последний — ЛКМ отменяет
      // запомненные ПКМ и Пробел (сама команда ЛКМ и так ждёт конца действия)
      if (h.action && heroBusy(h, 'skill') && !this.overUi) { this.rmbBuf = null; this.dashBuf = null; this.lmbQueuedOn = h.action; }
      const hb = this.topRightVisible ? buttonAt(inp.mx, inp.my) : -1;
      if (hb >= 0) this.menuButton(hb);
      else if (this.hoverBelt >= 0) h.drink(this.hoverBelt, this);
      else if (this.overUi) {   // клик по HUD: F-ячейка — навык на ПКМ; ячейка ЛКМ — «Сшибка» ↔ обычный удар
        const hs = hudSlotAt(inp.mx, inp.my);
        if (hs && hs.kind === 'f') this.pressF(hs.i);
        else if (hs && hs.kind === 'lmb') { h.lmb = h.lmb ? null : (rankOf(h, 'sshibka') ? 'sshibka' : null); this.audio.play('ui'); this.notify('ЛКМ: ' + (h.lmb ? SKILLS[h.lmb].name : 'обычный удар'), PAL.bronze_lt, 'lmb'); }
      }
      else if (this.hoverLabel || this.hoverGround) { h.pickup(this.hoverLabel || this.hoverGround); this.leftMode = 'pickup'; }
      else if (this.hoverEnemy) {
        if (this.zone.noAttack && !this.hoverEnemy.dummy) { this.notify(t('ui.error.town_attack'), PAL.red_lt, 'townatk'); this.audio.play('error'); }
        else { h.attack(this.hoverEnemy, inp.shift, h.lmbSkill(), true); this.lastTarget = this.hoverEnemy; this.leftMode = 'attack'; }
      }
      else if (this.hoverObj && (this.hoverObj.type === 'exit' || this.hoverObj.type === 'gate')) {
        const o = this.hoverObj, [tx, ty] = o.wall ? o.wall.front : [o.x, o.y];   // закрытый выход — подойти к стене (QA B-28)
        h.moveTo(this.map, tx, ty); this.leftMode = null;
      }
      else if (this.hoverObj) { h.interact(this.hoverObj); this.leftMode = 'interact'; }
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

    // M1d (GDD v1.9 §4.4): ПКМ по ячейке пояса — выпить зелье / прочитать бересту, как клавиша ячейки
    if (inp.rightPressed && this.hoverBelt >= 0 && !ui.hand) h.drink(this.hoverBelt, this);
    // ПКМ — навык панели; нажатие во время замаха запоминается до конца замаха + 0,3 с (QA B-02)
    if ((inp.rightPressed || inp.right) && !this.overUi && !ui.hand) {
      const tg = this.hoverEnemy, id = h.rmb;
      const [wx, wy] = tg ? [tg.x, tg.y] : this.toWorld(inp.mx, inp.my);
      if (inp.rightPressed || h.cdLeft(id) <= 0) {
        const r = h.useSkill(this, id, wx, wy, tg);
        if (r === 'ok') { this.rmbBuf = null; if (tg) this.lastTarget = tg; }
        else if (r === 'busy' && inp.rightPressed) { this.rmbBuf = { t: 0.3, id, wx, wy, tg }; this.dashBuf = null; this.dropQueuedLmb(); this.counters.buffered = (this.counters.buffered || 0) + 1; }
        else if (r === 'town' && inp.rightPressed) { this.notify(t('ui.error.town_attack'), PAL.red_lt, 'townatk'); this.audio.play('error'); }
        else if (r === 'cd' && inp.rightPressed) { this.counters.cdBlocked++; this.audio.play('error'); }
      }
    } else if (this.rmbBuf) {
      // QA B-02: буфер живёт весь замах/каст (таймер стоит, пока герой занят) и ещё 0,3 с после
      const b = this.rmbBuf;
      if (!heroBusy(h, 'skill')) b.t -= dt;
      if (b.t <= 0 || h.dead) this.rmbBuf = null;
      else if (!heroBusy(h, 'skill')) {
        const r = h.useSkill(this, b.id, b.tg && !b.tg.dead ? b.tg.x : b.wx, b.tg && !b.tg.dead ? b.tg.y : b.wy, b.tg && !b.tg.dead ? b.tg : null);
        if (r !== 'busy') {
          this.rmbBuf = null;
          if (r === 'ok') this.counters.bufferedFired = (this.counters.bufferedFired || 0) + 1;
          else if (r === 'cd') { this.counters.cdBlocked++; this.audio.play('error'); }
        }
      }
    }
  }

  /** ПКМ/Пробел нажаты после ЛКМ в том же замахе — побеждает последнее: команда ЛКМ снимается. */
  dropQueuedLmb() {
    const h = this.hero;
    if (this.lmbQueuedOn && this.lmbQueuedOn === h.action) { h.cmd = null; h.path = null; h.moving = false; }
    this.lmbQueuedOn = null;
  }
  pressF(k) {
    const h = this.hero, ui = this.ui;
    const hov = ui.skillsOpen ? ui.skills.hover.skill : null;
    if (hov) {
      if (!rankOf(h, hov) || SKILLS[hov].type === 'passive') { this.audio.play('error'); return; }
      // GDD v1.7: в занятую ячейку — обмен (прежний навык встаёт на место назначаемого, если тот был на панели)
      const old = h.bar.indexOf(hov), prev = h.bar[k];
      if (old >= 0) h.bar[old] = prev && prev !== hov ? prev : null;
      h.bar[k] = hov;
      this.audio.play('ui');
      this.notify(skillShort(hov) + ' → F' + (k + 1) + (old >= 0 && prev && prev !== hov ? ', ' + skillShort(prev) + ' → F' + (old + 1) : ''), PAL.bronze_lt, 'bind');
      return;
    }
    const id = h.bar[k];
    if (id && h.setRmb(id)) { this.audio.play('ui'); this.notify('ПКМ: ' + SKILLS[id].name, PAL.bronze_lt, 'rmb'); }
    else this.audio.play('error');
  }
  // колесо мыши — перебор навыков панели на ПКМ (GDD §4.1)
  cycleRmb(dir) {
    const h = this.hero, list = h.bar.filter((id) => id && rankOf(h, id));
    if (list.length < 2) return;
    const i = list.indexOf(h.rmb);
    h.setRmb(list[(i + (dir > 0 ? 1 : -1) + list.length) % list.length]);
    this.audio.play('ui');
  }
  /** Реплика над головой: одна и та же — не чаще раза в 15 с (GDD v1.4 §10.1). */
  bark(actor, key, text = null) {
    const last = this._barks[key];
    if (last != null && this.time - last < 15) { this.counters.barksSuppressed++; return false; }
    this._barks[key] = this.time;
    this.counters.barks++;
    this.fx.text(actor.x, actor.y, text || t(key), PAL.linen, (actor.def ? actor.def.height : 46) + 12, { dur: 2.6 });
    return true;
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
    this.updateZone(dt);
    this.updatePortal(dt);
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
    this.frames = (this.frames || 0) + 1; this.clock = (this.clock || 0) + dt;   // для автотестов: кадры и «прожитое» время
    if (!this.simHold) this.update(dt);   // B-35: замеры (g.simulate) держат живой цикл, чтобы кадры между await не двигали бой
    this.render();
    this.input.endFrame();
  }

  /** Точка в «тихом» круге (крада, Чуров камень): нечисть туда не бродит, не замечает героя, погоня обрывается. */
  safeAt(x, y, pad = 0) {
    if (this.zone && this.zone.safeAll) return true;
    const zs = this.zone.safeZones;
    if (!zs) return false;
    for (const z of zs) {
      const c = this.map[z.at];
      if (c && Math.hypot(x - c.x, y - c.y) < z.radius + pad) return true;
    }
    return false;
  }

  // --- отладка и автотесты (window.__game)
  /** Тестовый враг вне стай (для замеров TTK и выживания). */
  spawnTest(kind, x, y, mlvl = 1) { const e = new Enemy(kind, x, y, -1, mlvl); this.enemies.push(e); return e; }
  /** Прогнать мир на sec игровых секунд фиксированным шагом (без рендера); stop() — досрочный выход. */
  simulate(sec, stop = null, dt = 1 / 60) {
    this.input.endFrame();
    let tt = 0;
    while (tt < sec) { this.update(dt); this.input.endFrame(); tt += dt; if (stop && stop()) break; }
    return tt;
  }
  give(baseId, rarity = 'normal', opts = {}) {
    if (baseId.startsWith('scroll:')) { const left = this.hero.addScroll(baseId.slice(7), opts.count || 1); return left === 0; }
    if (baseId.startsWith('unique:')) { const u = makeUnique(baseId.slice(7)); return this.hero.inv.autoAdd(u) ? u : null; }
    const it = baseId.startsWith('potion:') ? makePotion(baseId.slice(7)) : makeItem(baseId, rarity, opts.ilvl || 6, Math.random, opts);
    if (!this.hero.inv.autoAdd(it)) return null;
    return it;
  }
  dropRandom(ilvl = 3) { const it = rollItem(ilvl); this.loot.spawnItem(this.hero.x + 1, this.hero.y, it); return it; }
  itemColorOf(it) { return itemColor(it); }
  /** Объект зоны по id (двери, сундук, тело, выходы). */
  objectById(id) { return this.map.objects.find((o) => o.id === id) || null; }
}
Object.assign(Game.prototype, ZoneMixin, KapishcheMixin, PortalMixin);

