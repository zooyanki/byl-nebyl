// Зоны М1 и их объекты (веха M1a): Залесье ↔ Лесная тропа, у каждой зоны своё состояние (карта, нечисть, добыча,
// огонь, NPC) — при возвращении всё как было. Двери изб (держи ЛКМ 2 с, урон прерывает), сундук, тело жреца,
// выходы и ворота капища; волны упырей из-под земли; первая встреча с поджигателем. Подмешивается в Game.
import { MAP_SEED } from '../config.js';
import { PAL } from '../palette.js';
import { CFG } from '../data/config.js';
import { FX } from '../render/rest_fx.js';
import { t, RU } from '../core/i18n.js';
import { generateMap } from '../world/map.js';
import { circleFree, sightClear, moveWithCollision } from '../world/collision.js';
import { WorldRenderer } from '../render/world.js';
import { Minimap } from '../render/minimap.js';
import { Npc } from '../entities/npc.js';

const SEEDS = { zalesye: MAP_SEED, trail: MAP_SEED + 7919 };

export const ZoneMixin = {
  buildZone(id) {
    const zone = CFG.zones[id];
    const map = generateMap(SEEDS[id] ?? MAP_SEED + 31, zone);
    return { id, zone, map, renderer: new WorldRenderer(map), minimap: new Minimap(map), enemies: [], buried: [], items: [], fires: [], npcs: [], fresh: true, needRepop: false, total: 0 };
  },

  saveZone() {
    const st = this.zs;
    if (!st) return;
    // уходя из зоны, погоня обрывается: нечисть возвращается к логову; раненые — тоже, там восстановят HP (GDD v1.7 §4.5)
    for (const e of this.enemies) if (!e.dead && e.state !== 'rise' && (e.state !== 'idle' || e.hp < e.maxHp)) { e.state = 'return'; e.path = null; }
    st.enemies = this.enemies; st.buried = this.buried; st.items = this.loot.items; st.fires = []; st.npcs = this.npcs.filter((n) => !n.gone);
  },

  /** Перейти в зону id к точке входа entry. opts.respawn — возрождение у крады (без надписи и без пополнения стай). */
  enterZone(id, entry = 'start', opts = {}) {
    const prev = this.zs;
    if (prev) this.saveZone();
    const st = this.zoneStates[id] || (this.zoneStates[id] = this.buildZone(id));
    this.zs = st; this.zone = st.zone; this.map = st.map; this.renderer = st.renderer; this.minimap = st.minimap;
    this.enemies = st.enemies; this.buried = st.buried; this.loot.items = st.items; this.combat.fires = st.fires; this.npcs = st.npcs;
    this.combat.projectiles = [];
    if (st.fresh) {
      st.fresh = false;
      this.map.packs.forEach((_, i) => this.spawnPack(i));
      st.total = this.enemies.length + this.buried.length;
    } else if (st.needRepop && !opts.respawn) { st.needRepop = false; this.repopulate(); }
    if (opts.respawn) st.needRepop = false;
    this.enemyTotal = st.total;
    const h = this.hero, [x, y] = this.entryPoint(entry);
    h.x = x; h.y = y; h.path = null; h.cmd = null; h.moving = false; h.kb = null; h.dashing = null;
    this.hoverEnemy = null; this.hoverGround = null; this.hoverObj = null; this.lastTarget = null; this.labelRects = [];
    for (const o of this.map.objects) o.inside = Math.hypot(h.x - o.x, h.y - o.y) <= (o.r || 0);
    this.updateCamera();
    this.minimap.lastTile = -1;
    this.minimap.reveal(h.x, h.y);
    this.counters.zoneChanges = (this.counters.zoneChanges || 0) + (prev ? 1 : 0);
    if (prev && !opts.respawn) {
      this.notify(this.zone.name, PAL.bronze_hi, 'zone');
      this.log.add(this.zone.name + ' · ' + (this.zone.mlvl ? 'ур. нечисти ' + this.zone.mlvl.join('–') : ''), PAL.bronze_lt);
      this.audio.play('ui');
    }
    this.quest.emit({ event: 'zoneEnter', zone: id });
  },

  /** Точка входа: {at:'start'|'krada'} или координаты; ищем свободное достижимое место рядом. */
  entryPoint(entry) {
    const m = this.map, e = m.entries[entry] || { at: 'start' };
    let c;
    if (e.at === 'krada' && m.krada) return this.spotNear(m.krada.x, m.krada.y, 1.6);
    if (e.at === 'start' || e.at == null && e.x == null) c = m.start; else c = e;
    if (circleFree(m, c.x, c.y, this.hero.r + 0.05) && m.isReachableAt(c.x, c.y)) return [c.x, c.y];
    return this.spotNear(c.x, c.y, 0.5);
  },
  spotNear(cx, cy, r0) {
    const m = this.map, r = this.hero.r + 0.05;
    for (let ring = r0; ring < 6; ring += 0.5) {
      for (let a = 0; a < 16; a++) {
        const ang = Math.PI * 0.25 + (a / 16) * Math.PI * 2;
        const x = cx + Math.cos(ang) * ring, y = cy + Math.sin(ang) * ring;
        if (circleFree(m, x, y, r) && m.isReachableAt(x, y)) return [x, y];
      }
    }
    return [m.start.x, m.start.y];
  },

  // --- объекты
  /** Почему нельзя взаимодействовать (ключ ru.json) или null. */
  canInteract(o) {
    if (o.done) return 'ui.obj.enemies_near';
    if (o.type === 'hut') {
      const ia = this.zone.interact || {};
      const idx = this.map.packs.findIndex((p) => p.role === o.pack);
      const alive = (e) => !e.dead && e.pack === idx;
      if (idx >= 0 && (this.enemies.some(alive) || this.buried.some(alive))) return 'ui.obj.enemies_near';
      const cr = ia.clearRadius ?? 4;
      if (this.enemies.some((e) => !e.dead && Math.hypot(e.x - o.x, e.y - o.y) < cr)) return 'ui.obj.enemies_near';
    }
    return null;
  },
  holdingInteract() { return (this.input.left && this.leftMode === 'interact') || !!this.autoHold; },

  interact(o) {
    if (o.done) return;
    const h = this.hero;
    o.done = true;
    this.counters.interacts = (this.counters.interacts || 0) + 1;
    if (o.type === 'hut') {
      this.audio.play('crit'); this.shake(1.5, 0.15);
      this.fx.burst(o.x, o.y, PAL.wood_lt, 14, 20, 60);
      const bark = RU[o.bark] || {}, who = bark['Кто'], text = bark['Текст'] || '';
      const out = [o.x, o.y + 0.6];
      const run = this.map.krada ? [this.map.krada.x + 1, this.map.krada.y + 2] : this.map.start;
      for (let i = 0; i < (o.villagers || 0); i++) {
        const female = i === 0 ? who === 'Селянка' : i % 2 === 1, old = i === 0 && who === 'Старик';
        const n = new Npc('villager', out[0] + (i - 0.5) * 0.6, out[1] + 0.2 * i, { name: i === 0 ? who : t('proto.villager'), female, old });
        n.runTo(run[0] + i * 0.7, run[1], 1.6 + i * 0.3);
        this.npcs.push(n);
      }
      if (o.npc === 'mal') {
        const n = new Npc('mal', out[0], out[1], { name: t('npc.mal'), life: 14 });
        n.face(h.x - n.x, h.y - n.y);
        this.npcs.push(n);
      }
      const actor = this.speakerActor(who) || h;
      if (text) this.bark(actor, o.bark, text);
      this.log.add((who ? who + ': ' : '') + text, PAL.linen);
      this.quest.emit({ event: 'hutFreed', hut: o.id });
    } else if (o.type === 'chest') {
      if (o.prop) { o.prop.open = true; o.prop._spr = null; }
      this.audio.play('pickup');
      this.fx.burst(o.x, o.y, PAL.bronze_hi, 10, 10, 40);
      o.drops = this.loot.dropChest(o.loot, o.x, o.y + 0.7, o.ilvl || 3);
      this.log.add(t('ui.obj.chest') + ': ' + o.drops.map((d) => d.label).join(', '), PAL.bronze_lt);
      this.quest.emit({ event: 'chestOpened', chest: o.id });
    } else if (o.type === 'body') {
      if (o.relic) {
        const r = RU['relic.' + o.relic] || {};
        h.relics.push(o.relic);
        if (o.prop) { o.prop.taken = true; o.prop._spr = null; }
        this.audio.play('pickup');
        this.log.add(t('ui.sys.relic_got', { item: r['Предмет'] }) + ' — ' + (r['Описание'] || ''), PAL.bronze_hi);
        this.notify(t('ui.sys.relic_got', { item: r['Предмет'] }), PAL.bronze_hi, 'relic');
        this.quest.emit({ event: 'relicTaken', relic: o.relic });
      }
      if (o.letter) {
        const L = RU['letter.' + o.letter] || {};
        h.letters.push(o.letter);
        this.letter = { id: o.letter, name: L.name, text: L.text, t: this.time };
        this.log.add(t('ui.sys.letter_got', { name: L.name }), PAL.bronze_lt);
        this.quest.emit({ event: 'letterRead', letter: o.letter });
      }
    }
  },

  objectLabel(o) {
    if (o.type === 'hut') return t('ui.obj.hut');
    if (o.type === 'chest') return t('ui.obj.chest');
    if (o.type === 'body') return t('proto.priest_body') + ': ' + t('ui.obj.letter').toLowerCase();
    if (o.type === 'gate') return (RU['zone.m1.kapishche'] || {})['Название'] || 'Капище';
    const z = CFG.zones[o.to];
    return t('proto.exit.to', { zone: z ? z.name : o.to });
  },

  /** Объект под курсором (экранные хитбоксы по типу). */
  objectAt(mx, my) {
    let best = null, bd = 1e9;
    for (const o of this.map.objects) {
      if (o.done) continue;
      const [sx, sy] = this.toS(o.x, o.y), dx = mx - sx, dy = my - sy;
      const box = o.type === 'hut' ? [13, -58, 4] : o.type === 'chest' ? [13, -20, 6] : o.type === 'body' ? [17, -12, 7] : [16, -34, 8];
      if (Math.abs(dx) <= box[0] && dy >= box[1] && dy <= box[2] && Math.abs(dx) + Math.abs(dy) < bd) { bd = Math.abs(dx) + Math.abs(dy); best = o; }
    }
    return best;
  },

  // --- реплики и диалоги
  speakerActor(name) {
    if (!name || name === t('npc.ratibor')) return this.hero;
    return this.npcs.find((n) => !n.gone && n.name === name) || null;
  },
  /** Реплика по ключу ru.json ({Кто, Текст}); говорит тот, кто указан в «Кто» (Ратибор — герой). */
  say(actor, key) {
    const b = RU[key];
    const text = b && typeof b === 'object' ? b['Текст'] : t(key);
    const who = b && typeof b === 'object' ? b['Кто'] : null;
    const a = this.speakerActor(who) || actor;
    if (this.bark(a, key, text)) this.log.add((who ? who + ': ' : '') + text, PAL.linen);
  },
  /** Цепочка реплик [[кто, текст], ...] — по одной над говорящим. */
  dialog(lines) {
    for (const [who, text] of lines) this.dialogQ.push({ who, text });
    this.dialogNext = Math.max(this.dialogNext || 0, this.time + 2.2);
  },
  updateDialog() {
    if (!this.dialogQ.length || this.time < this.dialogNext) return;
    const l = this.dialogQ.shift();
    const a = this.speakerActor(l.who) || this.hero;
    this.fx.text(a.x, a.y, l.text, PAL.linen, (a.def ? a.def.height : 46) + 12, { dur: 2.6 });
    this.log.add(l.who + ': ' + l.text, PAL.linen);
    this.dialogNext = this.time + 2.6;
    if (!this.dialogQ.length) {
      // Мал показывает тропу: бежит к выходу за колодцем
      const mal = this.npcs.find((n) => n.kind === 'mal' && !n.gone);
      const ex = this.map.objects.find((o) => o.type === 'exit' && o.to === 'trail');
      if (mal && ex) mal.runTo(ex.x - 0.6, ex.y - 1.2, 1.0);
    }
  },

  // --- триггеры зоны (каждый кадр)
  /** Тихий круг под точкой (с его настройками) или null. */
  safeZoneAt(x, y) {
    for (const z of this.zone.safeZones || []) {
      const c = this.map[z.at];
      if (c && Math.hypot(x - c.x, y - c.y) < z.radius) return { ...z, c };
    }
    return null;
  },
  /** Отдых (GDD v1.7 §4.5): в тихом круге Жизнь и Ярь +pctPerSec% от максимума в секунду, если noDamageSec с без урона. */
  updateRest(dt) {
    const h = this.hero, z = h.dead ? null : this.safeZoneAt(h.x, h.y), r = z && z.rest;
    const need = h.hp < h.maxHp || h.yar < h.maxYar;
    this.resting = !!(r && need && (h.sinceHurt ?? 99) >= r.noDamageSec);
    this.restZone = this.resting ? z : null;
    if (this.resting) {
      const k = (r.pctPerSec / 100) * dt;
      h.hp = Math.min(h.maxHp, h.hp + h.maxHp * k);
      h.yar = Math.min(h.maxYar, h.yar + h.maxYar * k);
      this.counters.restT = (this.counters.restT || 0) + dt;
      // совет tip.13 (act1_texts §19) — в прототипе нет экрана загрузки, поэтому показываем при первом отдыхе за сессию
      if (!this._tipRest) { this._tipRest = true; this.notify(t('tip.13'), PAL.bronze_lt, 'tip'); }
    }
    this.updateRestFx(dt);
  },
  /** Состояние эффектов отдыха (спрайты художника, src/render/rest_fx.js): источник зоны «покой»/«отдых», искры над героем,
   *  видимость кольца рез. Правила дизайнера (08.10): rest — пока идёт восстановление; искры — пока растут Жизнь или Ярь,
   *  петля доигрывает до конца; кольцо 50% — только в 3 тайлах от границы или во время отдыха. */
  updateRestFx(dt) {
    const h = this.hero, F = this.restFx || (this.restFx = { sparks: false, sparksT: 0, ending: false, rings: {}, src: null });
    const RF = (CFG.stats.restFx || {});
    const near = RF.ringNearBorder ?? 3, ringA = RF.ringOpacity ?? 0.5, fade = RF.ringFade ?? 0.25;
    // источник: крада / Чуров камень, у которого герой отдыхает
    const srcs = this.map._restSrc || (this.map._restSrc = this.map.props.filter((p) => p.krada || p.type === 'churstone'));
    const rz = this.restZone;
    F.src = null;
    for (const p of srcs) {
      const cx = p.x + p.size / 2, cy = p.y + p.size / 2;
      p.restOn = !!(rz && Math.hypot(cx - rz.c.x, cy - rz.c.y) < 1.5);
      if (p.restOn) F.src = p.krada ? 'krada' : 'churov';
    }
    // искры над героем (fx_rest_sparks: 8 кадров/с, 4 кадра)
    const sm = (FX.sheets.sparks && FX.sheets.sparks.meta) || { fps: 8, frame_count: 4 }, loopLen = sm.frame_count / sm.fps;
    if (this.resting) { if (!F.sparks) { F.sparks = true; F.sparksT = 0; } F.ending = false; }
    else if (F.sparks) F.ending = true;
    if (F.sparks) {
      const loops0 = Math.floor(F.sparksT / loopLen);
      F.sparksT += dt;
      if (F.ending && Math.floor(F.sparksT / loopLen) > loops0) { F.sparks = false; F.ending = false; F.sparksT = 0; }
    }
    F.sparksFrame = F.sparks ? Math.floor(F.sparksT * sm.fps) % sm.frame_count : -1;
    // кольца рез
    for (const sz of this.zone.safeZones || []) {
      const c = this.map[sz.at];
      if (!c) continue;
      const key = sz.at, d = Math.hypot(h.x - c.x, h.y - c.y);
      const restHere = !!(rz && rz.at === sz.at);
      const want = !h.dead && (Math.abs(d - sz.radius) <= near || restHere) ? ringA : 0;
      const R = F.rings[key] || (F.rings[key] = { a: 0, R: sz.radius, x: c.x, y: c.y });
      R.R = sz.radius; R.x = c.x; R.y = c.y; R.lit = restHere; R.want = want;
      const step = (ringA / fade) * dt;
      R.a = R.a < want ? Math.min(want, R.a + step) : Math.max(want, R.a - step);
    }
  },
  updateZone(dt) {
    const h = this.hero;
    this.updateRest(dt);
    for (const n of this.npcs) n.update(dt, this);
    if (this.npcs.some((n) => n.gone)) this.npcs = this.npcs.filter((n) => !n.gone);
    this.updateDialog();
    if (this.letter && this.time - this.letter.t > 10) this.letter = null;
    if (h.dead) return;
    // волны: упыри встают из земли, когда герой подходит
    const amb = this.zone.ambush || {};
    this.map.packs.forEach((p, i) => {
      if (!p.ambush || p.risen) return;
      if (Math.hypot(h.x - p.x, h.y - p.y) > (amb.trigger ?? 5) || this.safeAt(h.x, h.y)) return;
      p.risen = true;
      const up = this.buried.filter((e) => e.pack === i);
      this.buried = this.buried.filter((e) => e.pack !== i);
      for (const e of up) {
        e.state = 'rise'; e.t = 0; e.riseTime = amb.rise ?? 0.8; e.face(h.x - e.x, h.y - e.y);
        this.enemies.push(e);
        this.fx.burst(e.x, e.y, PAL.wood_md, 8, 2, 30);
      }
      this.audio.play('hurt');
      this.counters.waves = (this.counters.waves || 0) + 1;
    });
    // первая встреча с поджигателем
    if (!this.quest.flag('arsonistSeen')) {
      const R = (CFG.quests.events || {}).arsonistSightRange ?? 9;
      const seen = this.enemies.find((e) => !e.dead && e.def.torch && (e.state === 'chase' || e.state === 'torch' || e.state === 'attack' ||
        (Math.hypot(e.x - h.x, e.y - h.y) <= R && sightClear(this.map, h.x, h.y, e.x, e.y))));
      if (seen) { this.quest.flags.arsonistSeen = true; this.quest.emit({ event: 'arsonistSeen' }); }
    }
    // подсказка у первой избы
    if (!this._tutHut) {
      const hut = this.map.objects.find((o) => o.type === 'hut' && !o.done && Math.hypot(o.x - h.x, o.y - h.y) < 7);
      if (hut) { this._tutHut = true; this.notify(t('ui.tut.hut'), PAL.bronze_lt, 'tut'); }
    }
    // выходы и ворота
    for (const o of this.map.objects) {
      if (o.type !== 'exit' && o.type !== 'gate') continue;
      const d = Math.hypot(h.x - o.x, h.y - o.y);
      if (d > o.r) { o.inside = false; continue; }
      if (o.inside) continue;
      o.inside = true;
      if (o.event) this.quest.emit(o.event);
      const locked = o.type === 'gate' || (o.requires && !this.quest.flag(o.requires));
      if (locked) {
        this.notify(t(o.lockedKey), PAL.mist, 'locked');
        this.audio.play('error');
        const k = (o.r + 0.4) / (d || 1);
        h.stop();
        moveWithCollision(this.map, h, o.x + (h.x - o.x) * k - h.x, o.y + (h.y - o.y) * k - h.y);
        o.inside = Math.hypot(h.x - o.x, h.y - o.y) <= o.r;
        continue;
      }
      this.enterZone(o.to, o.entry);
      return;
    }
  },
};
