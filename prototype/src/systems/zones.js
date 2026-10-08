// Зоны М1 и их объекты (веха M1a): Залесье ↔ Лесная тропа, у каждой зоны своё состояние (карта, нечисть, добыча,
// огонь, NPC) — при возвращении всё как было. Двери изб (держи ЛКМ 2 с, урон прерывает), сундук, тело жреца,
// выходы и ворота капища; волны упырей из-под земли; первая встреча с поджигателем. Подмешивается в Game.
import { MAP_SEED } from '../config.js';
import { PAL } from '../palette.js';
import { CFG } from '../data/config.js';
import { FX } from '../render/rest_fx.js';
import { t, RU } from '../core/i18n.js';
import { generateMap } from '../world/map.js';
import { circleFree, sightClear } from '../world/collision.js';
import { WorldRenderer } from '../render/world.js';
import { Minimap } from '../render/minimap.js';
import { Npc, Dummy } from '../entities/npc.js';
import { makeUnique, makePotion, POTIONS } from '../data/items.js';

const SEEDS = { zalesye: MAP_SEED, trail: MAP_SEED + 7919, kapishche: MAP_SEED + 4241, ladoga: MAP_SEED + 9001 };

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
    // GDD v1.9 (журнал п.4): выход из зоны живого вступившего в бой босса — поводок (полное HP, фаза заново, призванные рассыпаются)
    if (prev && prev.zone.id !== id && prev.boss && !prev.boss.dead && prev.boss.state !== 'idle' && prev.boss.leash) prev.boss.leash(this, 'zone', true);
    if (prev && prev.id === 'ladoga' && id !== 'ladoga' && this.town) this.town.onLeave();
    if (prev) { this.finishDialog(prev); this.saveZone(); }
    const st = this.zoneStates[id] || (this.zoneStates[id] = this.buildZone(id));
    this.zs = st; this.zone = st.zone; this.map = st.map; this.renderer = st.renderer; this.minimap = st.minimap;
    this.enemies = st.enemies; this.buried = st.buried; this.loot.items = st.items; this.combat.fires = st.fires; this.npcs = st.npcs;
    this.combat.projectiles = [];
    if (st.malPending) {      // QA B-26: Мал уже «убежал к выходу» за время отсутствия героя — убираем его
      st.malPending = false;
      for (const n of this.npcs) if (n.kind === 'mal') n.gone = true;
      this.npcs = st.npcs = this.npcs.filter((n) => !n.gone);
    }
    if (st.fresh) {
      st.fresh = false;
      this.map.packs.forEach((_, i) => this.spawnPack(i));
      st.total = this.enemies.length + this.buried.length;      // обычные стаи зоны (Мара со свитой — сверх, systems/kapishche.js)
      this.setupZone(st);
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
    this.boss = st.boss && !st.boss.dead ? st.boss : null;
    this.applyChad();
    this.syncExitWalls();
    if (id === 'ladoga' && this.town) this.town.onEnter();
  },

  /** Точка входа: {at:'start'|'krada'} или координаты; ищем свободное достижимое место рядом. */
  entryPoint(entry) {
    const m = this.map, e = typeof entry === 'object' && entry ? entry : m.entries[entry] || { at: 'start' };   // {x, y} — выход из Чурова прохода (M1c)
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
    if (o.type === 'hearth') {
      // огнище (GDD §8.2): сначала перебить пачку у огнища, рядом никого (радиус как у избы)
      const ia = this.zone.interact || {}, idx = this.map.packs.findIndex((p) => p.role === o.pack), cr = ia.clearRadius ?? 4;
      if (idx >= 0 && this.enemies.some((e) => !e.dead && e.pack === idx)) return 'ui.obj.enemies_near';
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
      if (o.npc === 'mal') this.malGift();   // GDD v1.9: награда Мала — после его реплик (в очереди диалога), вещи — сразу
    } else if (o.type === 'hearth') {
      this.hearthFreed(o);
    } else if (o.type === 'stone') {
      o.done = false; this.touchStone(o);
    } else if (o.type === 'portal') {
      o.done = false; this.usePortal(o);
    } else if (o.type === 'npc') {
      o.done = false; if (this.town) this.town.openNpc(o.npc);
    } else if (o.type === 'stash') {
      o.done = false; if (this.town) this.town.openStash();
    } else if (o.type === 'reward') {
      // «Громовник» (U2, GDD §6.5) у подножия погасшего идола: награда М1, выдаётся один раз — в котомку (нет места — на землю)
      const it = makeUnique(o.unique || 'U2');
      this.rewardsGiven = this.rewardsGiven || {};
      this.rewardsGiven[o.id] = true;
      if (o.id === 'gromovnik') { this.quest.flags['m1.gromovnik'] = true; try { sessionStorage.setItem('byl_m1_gromovnik', 'taken'); } catch (e) { /* */ } }
      if (o.prop) { o.prop.taken = true; o.prop._spr = null; }
      this.audio.play('pickup');
      if (h.inv.autoAdd(it)) this.log.add(t('ui.sys.item_got', { item: it.name }) + ' — ' + it.lore, PAL.bronze_lt);
      else this.loot.spawnItem(o.x, o.y + 0.6, it);
      this.notify(t('proto.bylina.got', { item: it.name }), PAL.bronze_lt, 'relic');
      this.counters.bylinaPicked = (this.counters.bylinaPicked || 0) + 1;
      this.quest.emit({ event: 'rewardTaken', reward: 'gromovnik' });
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
    if (o.type === 'body') return t(o.labelKey || 'proto.priest_body') + ': ' + t('ui.obj.letter').toLowerCase();
    if (o.type === 'hearth') return t('ui.obj.hearth');
    if (o.type === 'stone') return t('ui.obj.chur_stone');
    if (o.type === 'reward') return t('item.u2.name');
    if (o.type === 'portal') return this.portalLabel(o);
    if (o.type === 'npc') return o.npc ? o.npc.name : '';
    if (o.type === 'stash') return t('obj.stash');
    if (o.type === 'gate') return (RU['zone.m1.kapishche'] || {})['Название'] || 'Капище';
    const z = CFG.zones[o.to];
    return t('proto.exit.to', { zone: z ? z.name : o.to });
  },

  /** Объект под курсором (экранные хитбоксы по типу). */
  objectAt(mx, my) {
    let best = null, bd = 1e9;
    for (const o of this.map.objects) {
      if (o.done) continue;
      if (o.type === 'portal' && this.portal && this.portal.closing) continue;   // closing: неюзабелен, без hover
      const [sx, sy] = this.toS(o.x, o.y), dx = mx - sx, dy = my - sy;
      const box = o.type === 'hut' ? [13, -58, 4] : o.type === 'chest' || o.type === 'reward' ? [13, -20, 6] : o.type === 'body' ? [17, -12, 7] : o.type === 'hearth' ? [16, -30, 8] : o.type === 'stone' ? [10, -38, 6] : o.type === 'portal' ? [14, -55, 8] : o.type === 'npc' ? [16, -52, 8] : o.type === 'stash' ? [18, -28, 10] : [16, -34, 8];
      if (Math.abs(dx) <= box[0] && dy >= box[1] && dy <= box[2] && Math.abs(dx) + Math.abs(dy) < bd) { bd = Math.abs(dx) + Math.abs(dy); best = o; }
    }
    return best;
  },

  /** GDD v1.9 (журнал п.7): награда Мала при выходе из избы — один раз за М1, без опыта (quests.m1.malGift).
   *  Зелья — в пояс, иначе в котомку, иначе на землю у героя; серебро — в котомку. Реплика bark.m1.mal_gift над Малом. */
  malGift() {
    const G = (CFG.quests.m1 || {}).malGift, h = this.hero;
    if (!G || (G.once && this.quest.flags.malGift)) return false;
    this.quest.flags.malGift = true;
    for (const [kind, n] of Object.entries(G.potions || {})) for (let i = 0; i < n; i++) if (!h.addPotion(kind)) this.loot.spawnItem(h.x + 0.6, h.y + 0.4, makePotion(kind));
    if (G.silver) { h.silver += G.silver; this.audio.play('silver'); }
    this.counters.malGift = (this.counters.malGift || 0) + 1;
    const b = RU[G.barkKey], text = b && typeof b === 'object' ? b['Текст'] : t(G.barkKey);
    // реплика — в очередь диалога сразу после первой реплики Мала («Они с капища шли!…»), чтобы не накладываться на неё
    const who = (b && b['Кто']) || t('npc.mal'), i = this.dialogQ.findIndex((l) => l.who === who);
    if (i >= 0) this.dialogQ.splice(i + 1, 0, { who, text }); else this.dialog([[who, text]]);
    this.log.add('Получено: ' + POTIONS.life1.name + ' ×' + ((G.potions || {}).life1 || 0) + ', ' + G.silver + ' сер.', PAL.birch);
    return true;
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
    // QA B-26: реплика говорящего, которого нет в зоне, идёт только в журнал (не над Ратибором)
    const a = this.speakerActor(l.who);
    if (a) this.fx.text(a.x, a.y, l.text, PAL.linen, (a.def ? a.def.height : 46) + 12, { dur: 2.6 });
    this.log.add(l.who + ': ' + l.text, PAL.linen);
    this.dialogNext = this.time + 2.6;
    if (!this.dialogQ.length) this.afterMalDialog();
  },
  /** Мал показывает тропу: бежит к выходу за колодцем и тает. */
  afterMalDialog() {
    const mal = this.npcs.find((n) => n.kind === 'mal' && !n.gone);
    const ex = this.map.objects.find((o) => o.type === 'exit' && o.to === 'trail');
    if (mal && ex) mal.runTo(ex.x - 0.6, ex.y - 1.2, 1.0);
  },
  /** Уход из зоны посреди диалога (QA B-26): оставшиеся реплики — в журнал, действие после диалога выполняется сразу:
   *  Мал «убегает» — при возвращении его у избы уже нет. Мал, уже бегущий к выходу, тоже считается ушедшим. */
  finishDialog(st) {
    const hadMal = this.dialogQ.length > 0 && this.npcs.some((n) => n.kind === 'mal' && !n.gone);
    for (const l of this.dialogQ) this.log.add(l.who + ': ' + l.text, PAL.linen);
    this.dialogQ.length = 0; this.dialogNext = 0;
    if (hadMal || this.npcs.some((n) => n.kind === 'mal' && !n.gone && n.target)) st.malPending = true;
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
    const h = this.hero, z = h.dead ? null : this.safeZoneAt(h.x, h.y);
    const all = !h.dead && this.zone.rest && this.zone.rest.area === 'all';
    const r = all ? this.zone.rest : (z && z.rest);
    const need = h.hp < h.maxHp || h.yar < h.maxYar;
    this.resting = !!(r && need && (h.sinceHurt ?? 99) >= r.noDamageSec);
    this.restZone = this.resting && z ? z : null;
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
  exitLocked(o) {
    if (o.opens) return !this.quest.flag(o.opens);
    return !CFG.zones[o.to] || CFG.zones[o.to].implemented === false || !!(o.requires && !this.quest.flag(o.requires));
  },
  /** Закрытый выход — стена поперёк прохода до кромки карты: герой упирается, враги не уходят в проход (QA B-28).
   *  Открылся — стена снимается (прежние клетки восстанавливаются), карта проходимости пересчитывается. */
  syncExitWalls() {
    const m = this.map;
    let changed = false;
    for (const o of m.objects) {
      if (o.type !== 'exit' && o.type !== 'gate') continue;
      const lock = this.exitLocked(o);
      if (lock && !o.wall) {
        const r = o.r, W = m.w, H = m.h, e = Math.min(o.x, o.y, W - o.x, H - o.y);
        const R = e === H - o.y ? [o.x - r - 1, o.y - r, 2 * r + 2, H - (o.y - r)] : e === o.y ? [o.x - r - 1, 0, 2 * r + 2, o.y + r]
          : e === o.x ? [0, o.y - r - 1, o.x + r, 2 * r + 2] : [o.x - r, o.y - r - 1, W - (o.x - r), 2 * r + 2];
        const SUB = m.sw / W, cells = [];
        for (let sy = Math.max(0, Math.floor(R[1] * SUB)); sy < Math.min(m.sh, Math.ceil((R[1] + R[3]) * SUB)); sy++)
          for (let sx = Math.max(0, Math.floor(R[0] * SUB)); sx < Math.min(m.sw, Math.ceil((R[0] + R[2]) * SUB)); sx++) { const i = sy * m.sw + sx; cells.push([i, m.sub[i]]); m.sub[i] = 1; }
        const F = r + 0.8, front = e === H - o.y ? [o.x, o.y - F] : e === o.y ? [o.x, o.y + F] : e === o.x ? [o.x + F, o.y] : [o.x - F, o.y];
        o.wall = { rect: R, cells, front }; changed = true;
      } else if (!lock && o.wall) {
        for (const [i, v] of o.wall.cells) m.sub[i] = v;
        o.wall = null; o.inside = Math.hypot(this.hero.x - o.x, this.hero.y - o.y) <= o.r; changed = true;
      }
    }
    if (changed) { m.passCache.clear(); m.computeReach(); }
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
    // Чуров камень у капища: коснуться (подойти ближе touch) — возрождение у камня
    for (const o of this.map.objects) if (o.type === 'stone' && !o.done && Math.hypot(h.x - o.x, h.y - o.y) <= (o.touch ?? 1.5)) this.touchStone(o);
    if (this.zone.id === 'kapishche') this.updateKapishche();
    this.applyChad();
    if (this.zone.id === 'ladoga') this.updateLadoga();
    // выходы и ворота (QA B-28): переход — только по намерению (приказ идти в круг выхода или щелчок по выходу);
    // закрытый выход — обычная стена (syncExitWalls), без выталкивания; сообщение и звук ошибки — один раз на попытку
    this.syncExitWalls();
    const c = h.cmd;
    for (const o of this.map.objects) {
      if (o.type !== 'exit' && o.type !== 'gate') continue;
      const d = Math.hypot(h.x - o.x, h.y - o.y);
      const intent = c && ((c.type === 'move' && Math.hypot(c.x - o.x, c.y - o.y) <= o.r + (o.wall ? 1.0 : 0.6)) || (c.type === 'interact' && c.obj === o));
      if (o.wall) {
        // одна попытка — одно сообщение: пока намерение длится (зажатая ЛКМ, повторные щелчки чаще 1,2 с) — тишина
        const near = !!(o.approach && d <= o.approach);
        const fresh = (intent || near) && this.time - (o.intentT ?? -9) > 0.5 && this.time - (o.warnT ?? -9) > 1.2;
        if (intent) o.intentT = this.time;
        if (fresh) {
          o.warnT = this.time;
          this.notify(t(o.lockedKey), PAL.mist, 'locked');
          this.audio.play('error');
          this.counters.exitLockedWarn = (this.counters.exitLockedWarn || 0) + 1;
        }
        continue;
      }
      if (d > o.r) { o.inside = false; continue; }
      if (!o.inside) { o.inside = true; if (o.event) this.quest.emit(o.event); }
      if (!intent) { this.counters.exitNoIntent = (this.counters.exitNoIntent || 0) + (o.noIntentT === this.time ? 0 : 1); o.noIntentT = this.time; continue; }
      if (!CFG.zones[o.to]) continue;   // ворота открыты, а зоны миссии ещё нет (М2/М3 не начаты)
      this.enterZone(o.to, o.entry);
      return;
    }
  },

  spawnLadoga() {
    for (const d of this.zone.npcs || []) {
      const at = d.pier || [d.x, d.y];
      const n = new Npc('town', at[0], at[1], { name: t(d.nameKey), female: !!d.female, grey: true, role: d.role, height: 40 });
      n.role = d.role;
      this.npcs.push(n);
      this.map.objects.push({ id: d.id, type: 'npc', role: d.role, npc: n, x: at[0], y: at[1], sx: at[0], sy: at[1] + 0.7, reach: 1.35, done: false });
    }
    const D = this.zone.dummy;
    if (D) {
      const d = new Dummy(D[0], D[1]);
      d.name = t('obj.dummy'); d.def.name = d.name;
      this.enemies.push(d);
    }
  },
  updateLadoga() {
    const q = this.quest, h = this.hero;
    if (!q.flag('vyshataIntro') && this.time > 1 && !h.dead) {
      q.flags.vyshataIntro = true; q.flags.vyshataSpoke = true;
      const lines = RU['npc.vyshata.s0'];
      if (Array.isArray(lines)) this.dialog(lines);
    }
    if (!this._tutAtk) {
      const d = this.enemies.find((e) => e.dummy);
      if (d && Math.hypot(d.x - h.x, d.y - h.y) < 6) { this._tutAtk = true; this.notify(t('ui.tut.attack'), PAL.bronze_lt, 'tut'); }
    }
    for (const n of this.npcs) if (n.role === 'vyshata') {
      n.mark = !q.flag('vyshataIntro') ? '!' : (q.missionDone && !q.flag('m1.turnedIn')) ? '?' : '';
    }
  },
};
