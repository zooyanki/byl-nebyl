// Веха M1b: элиты зон, Мара Пепельная в Залесье, Чуров камень у капища (точка возрождения), капище Перуна —
// огнища (перебить пачку и освятить: держи ЛКМ 3 с), «Чад» (GDD §4.4), подъём Кривши (вход в Круг огнищ или
// третье освящённое огнище), гибель Кривши (добыча, «Приказ Чернояра», погасший идол, «Громовник» у подножия — веха M1c).
// Подмешивается в Game вместе с ZoneMixin.
import { CFG } from '../data/config.js';
import { MAP_SEED } from '../config.js';
import { PAL } from '../palette.js';
import { t, RU } from '../core/i18n.js';
import { makeRng } from '../core/rng.js';
import { circleFree } from '../world/collision.js';
import { setupZoneElites } from './elites.js';
import { spawnMara, Krivsha, enemyBark } from '../entities/boss.js';

export const KapishcheMixin = {
  /** Свежая зона: вожаки и матёрые (детерминированно по зерну зоны), Мара со свитой в Залесье. */
  setupZone(st) {
    const rng = makeRng(MAP_SEED + 101 + st.id.length * 7919);
    st.leaders = setupZoneElites(this, st, rng);
    if (st.id === 'zalesye' && CFG.bosses.mara) st.mara = spawnMara(this, rng);
    if (st.id === 'kapishche') st.bossState = 'dormant';
  },

  /** Сколько врагов зоны перебито (для отладочного слоя ?debug; особые — Мара, свита, призванные — не в счёт). */
  zoneKills() {
    const st = this.zs, plain = (e) => !e.special && !e.summoned && e.pack !== 'krivsha' && !e.boss;
    const alive = [...this.enemies, ...this.buried].filter((e) => !e.dead && plain(e)).length;
    return { killed: Math.max(0, (st ? st.total : 0) - alive), total: st ? st.total : 0 };
  },

  // --- Чуров камень у капища: коснуться — возрождение у камня
  touchStone(o) {
    if (this.quest.flag('churTouched')) return;
    this.quest.flags.churTouched = true;
    o.done = true;
    if (o.prop) { o.prop.awake = true; o.prop._spr = null; }
    this.fx.ring(o.x, o.y, 1.4, PAL.flame, 0.7); this.fx.rise(o.x, o.y, PAL.bronze_hi, 18, 30);
    this.audio.play('respawn');
    this.notify(t('ui.obj.chur_awake'), PAL.bronze_hi, 'chur');
    this.log.add(t('ui.obj.chur_awake') + '. ' + t('proto.chur_respawn_hint'), PAL.bronze_lt);
    this.quest.emit({ event: 'churTouched' });
  },
  /** Где очнуться (ответ дизайнера 08.10): у крады Залесья, пока не тронут Чуров камень у капища; потом — у камня. */
  respawnPoint() {
    return this.quest.flag('churTouched') ? { zone: 'trail', entry: 'chur', at: 'churStone', log: 'proto.respawn.chur' } : { zone: 'zalesye', entry: 'krada', at: 'krada', log: 'proto.respawn.krada' };
  },

  // --- капище
  chadStage() {
    if (!this.zone || this.zone.id !== 'kapishche' || this.hero.dead) return 0;
    return (this.map.hearths || []).filter((o) => !o.done).length;
  },
  applyChad() {
    const h = this.hero, n = this.chadStage();
    if ((h.chad || 0) === n) return;
    h.chad = n; h.chadDef = (CFG.zones.kapishche || {}).chad; h.recalc();
  },

  updateKapishche() {
    const h = this.hero, st = this.zs, m = this.map;
    // стоп-кадр подсказки огнища
    if (!this._tutHearth) {
      const o = m.hearths.find((x) => !x.done && Math.hypot(x.x - h.x, x.y - h.y) < 7);
      if (o) { this._tutHearth = true; this.notify(t('ui.tut.hearth'), PAL.bronze_lt, 'tut'); }
    }
    if (st.bossState !== 'dormant' || h.dead) return;
    const B = CFG.bosses.krivsha;
    if (Math.hypot(h.x - m.idol.x, h.y - m.idol.y) <= B.arena.triggerRadius) {
      if (m.hearths.some((o) => !o.done)) this.say(h, 'bark.m1.circle_early');
      this.riseBoss('circle');
    }
  },

  riseBoss(reason) {
    const st = this.zs, m = this.map;
    if (st.bossState !== 'dormant') return null;
    st.bossState = 'active';
    let [x, y] = [m.idol.x, m.idol.y + 1.6];
    if (!circleFree(m, x, y, 0.65)) { for (let a = 0; a < 16; a++) { const xx = m.idol.x + Math.cos(a / 16 * 6.283) * 1.9, yy = m.idol.y + Math.sin(a / 16 * 6.283) * 1.9; if (circleFree(m, xx, yy, 0.65)) { x = xx; y = yy; break; } } }
    const b = new Krivsha(x, y);
    b.face(this.hero.x - x, this.hero.y - y);
    this.enemies.push(b);
    st.boss = b; this.boss = b;
    this.fx.burst(x, y, PAL.flame, 30, 50, 80); this.shake(3, 0.4); this.audio.play('explode');
    this.quest.emit({ event: 'bossRise', boss: 'krivsha', reason });
    this.counters.bossRise = reason;
    return b;
  },

  hearthFreed(o) {
    const m = this.map, n = m.hearths.filter((x) => x.done).length, st = this.zs;
    if (o.prop) { o.prop.cursed = false; o.prop.doneAt = this.time; }   // doneAt — для анимации освящения (спрайт M1b)
    this.fx.burst(o.x, o.y, PAL.flame, 16, 20, 60); this.fx.ring(o.x, o.y, 1.2, PAL.bronze_hi, 0.6);
    this.audio.play('levelup');
    const after = st.bossState === 'dead';
    this.say(this.hero, after ? 'bark.m1.hearth_after' : 'bark.m1.hearth' + Math.min(3, n));
    this.quest.emit({ event: 'hearthFreed', hearth: o.id });
    this.applyChad();
    if (n >= 3 && st.bossState === 'dormant') this.riseBoss('hearth3');
  },

  onBossKilled(b) {
    const st = this.zoneStates.kapishche, m = st ? st.map : this.map;
    if (!st) return;
    st.bossState = 'dead';
    this.bossFight = { time: b.fightT, phase2: b.phase === 2 };
    // тело Кривши с грамотой «Приказ Чернояра»
    const p = m.addProp('body', b.x - 0.5, b.y - 0.5, 1, { fp: [b.x, b.y, 0, 0], burnt: true });
    m.objects.push({ id: 'krivsha_body', type: 'body', x: b.x, y: b.y, sx: b.x, sy: b.y + 0.9, reach: 1.2, letter: CFG.bosses.krivsha.letter, labelKey: 'proto.krivsha_body', prop: p, done: false });
    // идол гаснет; у подножия — «Громовник» (U2, награда М1, GDD §6.5): щелчок — вещь в котомку (systems/zones.js → interact)
    if (m.perun) { m.perun.burning = false; m.perun._spr = null; m.perun.outAt = this.time; }   // outAt — idol_perun_extinguish
    m.lights = m.lights.filter((l) => !l.perun);
    const rp = m.addProp('relic', m.idol.x, m.idol.y + 1.2, 1, { fp: [m.idol.x + 0.5, m.idol.y + 1.7, 0, 0] });
    m.objects.push({ id: 'gromovnik', type: 'reward', unique: 'U2', x: m.idol.x + 0.5, y: m.idol.y + 1.7, sx: m.idol.x + 0.5, sy: m.idol.y + 2.4, reach: 1.2, prop: rp, done: false });
    this.quest.emit({ event: 'bossKilled', boss: 'krivsha' });
  },
};
